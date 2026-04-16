import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from upstash_redis import Redis

load_dotenv() # load the environment variables from the .env file

app = Flask(__name__, static_folder=".")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
AUTH_REQUIRED_ERROR = {"error": "Authentication required"}

# redis needs a URL and token to connect to the database
redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL", "http://localhost:6379"),
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN", "local-dev-token"),
)

def verify_google_credential(id_token):
    query = urlencode({"id_token": id_token})
    url = f"{GOOGLE_TOKENINFO_URL}?{query}"
    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError):
        return None

    aud = payload.get("aud")
    if GOOGLE_CLIENT_ID and aud != GOOGLE_CLIENT_ID:
        return None
    if not payload.get("sub"):
        return None
    if payload.get("email_verified") not in (True, "true"):
        return None
    return payload


def current_user():
    user = session.get("user")
    if isinstance(user, dict):
        return user
    return None


def get_username():
    user = current_user()
    if not user:
        return None
    return (user.get("email") or user.get("sub") or "").strip() or None


# Serve HTML files
@app.route("/", methods=["GET"])
@app.route("/<path:filename>", methods=["GET"])
def static_files(filename="index.html"):
    return send_from_directory(".", filename)


@app.post("/api/auth/google")
def google_signin():
    body = request.get_json() or {}
    credential = body.get("credential")
    if not isinstance(credential, str) or not credential.strip():
        return jsonify({"error": "Google credential is required"}), 400

    payload = verify_google_credential(credential.strip())
    if not payload:
        return jsonify({"error": "Invalid Google credential"}), 401

    user = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "picture": payload.get("picture"),
    }
    session["user"] = user
    return jsonify({"user": user})


@app.get("/api/auth/session")
def auth_session():
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401
    return jsonify({"user": user})


@app.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"success": True})


# GET /api/entries — fetch all journal entries for a user
@app.get("/api/entries")
def get_entries():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    data = redis.hgetall(f"journal:{username}")
    if not data:
        return jsonify([])

    entries = [json.loads(v) for v in data.values()]
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return jsonify(entries)


# POST /api/entries — save a new journal entry
@app.post("/api/entries")
def create_entry():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    body = request.get_json()
    content = (body or {}).get("content", "").strip()
    if not content:
        return jsonify({"error": "Content is required"}), 400

    # kysen code review: This function validates input, builds the entry dict, AND persists it.
    # Consider extracting build_entry(body) and save_entry(username, entry) as separate helpers.
    entry = {
        "id": str(int(time.time() * 1000)),
        "title": (body.get("title") or "Untitled").strip(),
        "content": content,
        "timestamp": int(time.time() * 1000),
    }

    redis.hset(f"journal:{username}", entry["id"], json.dumps(entry))
    return jsonify(entry), 201


# DELETE /api/entries/<id> — delete a journal entry
@app.delete("/api/entries/<entry_id>")
def delete_entry(entry_id):
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    redis.hdel(f"journal:{username}", entry_id)
    return jsonify({"success": True})


# POST /api/checkin — save a three-word mood check-in
@app.post("/api/checkin")
def create_checkin():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    body       = request.get_json() or {}
    words      = body.get("words", [])
    mood_score = body.get("moodScore")
    mood_label = body.get("moodLabel", "")

    # kysen code review: Validation, entry construction, and persistence are all mixed here.
    # Same pattern as create_entry — extract validate_checkin(body), build_checkin(body),
    # and save_checkin(username, entry) to give each step a single responsibility.
    if not words or not isinstance(words, list) or len(words) > 3:
        return jsonify({"error": "Provide 1–3 words"}), 400
    if mood_score is None or not isinstance(mood_score, (int, float)):
        return jsonify({"error": "moodScore is required"}), 400

    entry = {
        "id":        str(int(time.time() * 1000)),
        "words":     [str(w).strip()[:50] for w in words],
        "moodScore": int(mood_score),
        "moodLabel": str(mood_label).strip()[:32],
        "timestamp": int(time.time() * 1000),
    }

    redis.hset(f"checkin:{username}", entry["id"], json.dumps(entry))
    return jsonify(entry), 201


# GET /api/checkin — fetch all check-ins for a user
@app.get("/api/checkin")
def get_checkins():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    limit_raw = request.args.get("limit")
    limit = None
    if limit_raw is not None:
        try:
            limit = int(limit_raw)
            if limit < 1:
                raise ValueError
        except ValueError:
            return jsonify({"error": "limit must be a positive integer"}), 400

    data = redis.hgetall(f"checkin:{username}")
    if not data:
        return jsonify({"entries": [], "total": 0, "hasMore": False})

    entries = [json.loads(v) for v in data.values()]
    entries.sort(key=lambda e: e["timestamp"], reverse=True)

    if limit is not None:
        total = len(entries)
        limited_entries = entries[:limit]
        return jsonify({
            "entries": limited_entries,
            "total": total,
            "hasMore": total > limit,
        })

    return jsonify(entries)


# DELETE /api/checkin/<id> — delete a single check-in
@app.delete("/api/checkin/<checkin_id>")
def delete_checkin(checkin_id):
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    redis.hdel(f"checkin:{username}", checkin_id)
    return jsonify({"success": True})


QUESTIONNAIRE_QUESTION_IDS = {
    "mood", "sleep", "energy", "calm", "connection", "motivation",
    "focus", "responsibilities", "hope", "anxiety_free", "progress",
    "physical", "grounded",
}


# POST /api/questionnaire — save a check-in questionnaire response
@app.post("/api/questionnaire")
def create_questionnaire():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    body = request.get_json() or {}
    responses = body.get("responses")

    if not isinstance(responses, dict):
        return jsonify({"error": "responses object is required"}), 400

    cleaned = {}
    for qid, score in responses.items():
        if qid not in QUESTIONNAIRE_QUESTION_IDS:
            return jsonify({"error": f"Unknown question id: {qid}"}), 400
        if not isinstance(score, (int, float)) or not (1 <= int(score) <= 5):
            return jsonify({"error": f"Score for '{qid}' must be 1–5"}), 400
        cleaned[qid] = int(score)

    if len(cleaned) != len(QUESTIONNAIRE_QUESTION_IDS):
        return jsonify({"error": "All questions must be answered"}), 400

    entry = {
        "id": str(int(time.time() * 1000)),
        "responses": cleaned,
        "timestamp": int(time.time() * 1000),
    }

    redis.hset(f"questionnaire:{username}", entry["id"], json.dumps(entry))
    return jsonify(entry), 201


# GET /api/questionnaire — fetch all questionnaire responses for a user
@app.get("/api/questionnaire")
def get_questionnaires():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    data = redis.hgetall(f"questionnaire:{username}")
    if not data:
        return jsonify([])

    entries = [json.loads(v) for v in data.values()]
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return jsonify(entries)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(port=port, debug=True)