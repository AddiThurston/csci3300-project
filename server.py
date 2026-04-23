import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from google import genai

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

client = None
MODEL_NAME = "gemini-2.5-flash-lite"


def get_ai_client():
    global client
    if client is not None:
        return client

    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GOOGLE_GENAI_API_KEY")
    )
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
    except Exception:
        client = None
    return client

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


def load_user_records(bucket, username):
    data = redis.hgetall(f"{bucket}:{username}")
    if not data:
        return []

    records = [json.loads(value) for value in data.values()]
    records.sort(key=lambda record: record.get("timestamp", 0), reverse=True)
    return records


def format_timestamp(timestamp_ms):
    if not isinstance(timestamp_ms, (int, float)):
        return "Unknown time"
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def normalize_journal_entries(entries):
    normalized = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue

        content = str(entry.get("content") or "").strip()
        if not content:
            continue

        timestamp = entry.get("timestamp")
        timestamp = int(timestamp) if isinstance(timestamp, (int, float)) else 0
        normalized.append(
            {
                "title": str(entry.get("title") or "Untitled").strip() or "Untitled",
                "content": content,
                "timestamp": timestamp,
            }
        )

    normalized.sort(key=lambda entry: entry["timestamp"], reverse=True)
    return normalized[:8]


def format_journal_context(entries):
    entries = normalize_journal_entries(entries)
    if not entries:
        return "No journal entries available."

    lines = []
    for entry in entries:
        lines.append(f"- [{format_timestamp(entry['timestamp'])}] {entry['title']}")
        lines.append(f"  {entry['content'][:1200]}")
    return "\n".join(lines)


def normalize_checkins(entries):
    normalized = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue

        mood_score = entry.get("moodScore")
        if not isinstance(mood_score, (int, float)):
            continue

        timestamp = entry.get("timestamp")
        timestamp = int(timestamp) if isinstance(timestamp, (int, float)) else 0
        raw_words = entry.get("words")
        words = []
        if isinstance(raw_words, list):
            words = [str(word).strip() for word in raw_words if str(word).strip()]

        normalized.append(
            {
                "words": words[:3],
                "moodScore": int(mood_score),
                "moodLabel": str(entry.get("moodLabel") or "Unknown").strip() or "Unknown",
                "timestamp": timestamp,
            }
        )

    normalized.sort(key=lambda entry: entry["timestamp"], reverse=True)
    return normalized[:12]


def format_checkins_context(entries):
    entries = normalize_checkins(entries)
    if not entries:
        return "No check-ins available."

    chronological = sorted(entries, key=lambda entry: entry.get("timestamp", 0))
    scores = [
        int(entry.get("moodScore"))
        for entry in chronological
        if isinstance(entry.get("moodScore"), (int, float))
    ]
    if not scores:
        return "No check-ins available."

    delta = scores[-1] - scores[0]
    if delta >= 5:
        trend_label = "Improving"
    elif delta <= -5:
        trend_label = "Declining"
    else:
        trend_label = "Stable"

    all_words = []
    for entry in chronological:
        raw_words = entry.get("words")
        if isinstance(raw_words, list):
            all_words.extend(str(word).strip().lower() for word in raw_words if str(word).strip())

    common_words = Counter(all_words).most_common(5)
    word_summary = ", ".join(f"{word} ({count})" for word, count in common_words) if common_words else "None"
    latest = chronological[-1]
    latest_label = str(latest.get("moodLabel") or "Unknown").strip() or "Unknown"

    lines = [
        f"Mood trend: {trend_label}",
        f"Average mood score: {sum(scores) / len(scores):.1f}",
        f"Latest mood: {latest_label} ({scores[-1]}) on {format_timestamp(latest.get('timestamp'))}",
        f"Common check-in words: {word_summary}",
        "Individual check-ins (newest first):",
    ]
    for entry in entries:
        words_str = ", ".join(entry["words"]) if entry["words"] else "no words"
        lines.append(
            f"- [{format_timestamp(entry['timestamp'])}] "
            f"{entry['moodLabel']} ({entry['moodScore']}/100) — {words_str}"
        )
    return "\n".join(lines)


QUESTIONNAIRE_QUESTIONS = (
    ("mood", "Mood"),
    ("sleep", "Sleep"),
    ("energy", "Energy"),
    ("calm", "Calm"),
    ("connection", "Connection"),
    ("motivation", "Motivation"),
    ("focus", "Focus"),
    ("responsibilities", "Responsibilities"),
    ("hope", "Hope"),
    ("anxiety_free", "Freedom From Anxiety"),
    ("progress", "Progress"),
    ("physical", "Physical Health"),
    ("grounded", "Grounded"),
)
QUESTIONNAIRE_QUESTION_IDS = {question_id for question_id, _ in QUESTIONNAIRE_QUESTIONS}


def normalize_questionnaire_entries(entries):
    normalized = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue

        responses = entry.get("responses")
        if not isinstance(responses, dict):
            continue

        cleaned = {}
        for question_id, score in responses.items():
            if question_id not in QUESTIONNAIRE_QUESTION_IDS:
                continue
            if not isinstance(score, (int, float)):
                continue
            cleaned[question_id] = int(score)

        if not cleaned:
            continue

        timestamp = entry.get("timestamp")
        timestamp = int(timestamp) if isinstance(timestamp, (int, float)) else 0
        normalized.append(
            {
                "responses": cleaned,
                "timestamp": timestamp,
            }
        )

    normalized.sort(key=lambda entry: entry["timestamp"], reverse=True)
    return normalized[:6]


def format_questionnaire_context(entries):
    entries = normalize_questionnaire_entries(entries)
    if not entries:
        return "No questionnaire responses available."

    lines = ["Recent questionnaire responses (newest first):"]
    for entry in entries[:4]:
        responses = entry["responses"]
        average = sum(responses.values()) / len(responses)
        score_parts = []
        for question_id, label in QUESTIONNAIRE_QUESTIONS:
            score = responses.get(question_id)
            if score is not None:
                score_parts.append(f"{label}: {int(score)}")
        lines.append(f"- [{format_timestamp(entry['timestamp'])}] Average: {average:.1f}/5")
        lines.append(f"  {'; '.join(score_parts)}")
    return "\n".join(lines)


def build_date_context(journal_entries, checkins, questionnaires):
    lines = [
        (
            "Use the timestamps below to reason about chronology, recency, and whether a pattern is recent, "
            "recurring, or older context. Keep that as internal analysis support and avoid explicitly mentioning "
            "exact dates unless the user's question needs them."
        )
    ]

    normalized_entries = normalize_journal_entries(journal_entries)
    if normalized_entries:
        newest_entry = normalized_entries[0]
        oldest_entry = normalized_entries[-1]
        lines.append(
            "Journal window: "
            f"{format_timestamp(oldest_entry['timestamp'])} to {format_timestamp(newest_entry['timestamp'])} "
            f"({len(normalized_entries)} entries, listed newest first)."
        )
        lines.append(f"Most recent journal entry: {format_timestamp(newest_entry['timestamp'])}.")
    else:
        lines.append("Journal window: No journal entries available.")

    checkins = normalize_checkins(checkins)
    if checkins:
        chronological_checkins = sorted(checkins, key=lambda entry: entry.get("timestamp", 0))
        lines.append(
            "Check-in window: "
            f"{format_timestamp(chronological_checkins[0].get('timestamp'))} to "
            f"{format_timestamp(chronological_checkins[-1].get('timestamp'))} "
            f"({len(chronological_checkins)} check-ins)."
        )
    else:
        lines.append("Check-in window: No check-ins available.")

    questionnaires = normalize_questionnaire_entries(questionnaires)
    if questionnaires:
        chronological_questionnaires = sorted(questionnaires, key=lambda entry: entry.get("timestamp", 0))
        lines.append(
            "Questionnaire window: "
            f"{format_timestamp(chronological_questionnaires[0].get('timestamp'))} to "
            f"{format_timestamp(chronological_questionnaires[-1].get('timestamp'))} "
            f"({len(chronological_questionnaires)} responses)."
        )
    else:
        lines.append("Questionnaire window: No questionnaire responses available.")

    return "\n".join(lines)


def build_ai_prompt(user_message, journal_entries, checkins, questionnaires):
    return "\n\n".join(
        [
            (
                "You are a supportive mental health assistant for a student wellness journal. "
                "Answer with empathy, keep the response concise, ground your answer in the provided history, "
                "and avoid making clinical diagnoses. Pay close attention to dates and timestamps so you can "
                "weigh recent entries more heavily and identify changes over time. Use that timing information "
                "to improve the analysis, but do not explicitly mention exact dates unless the user's question requires it."
            ),
            f"User Question:\n{user_message}",
            f"Date Context:\n{build_date_context(journal_entries, checkins, questionnaires)}",
            f"Journal Entries:\n{format_journal_context(journal_entries)}",
            f"Check-In History:\n{format_checkins_context(checkins)}",
            f"Questionnaire Responses:\n{format_questionnaire_context(questionnaires)}",
        ]
    )


# Serve HTML files
@app.route("/", methods=["GET"])
@app.route("/<path:filename>", methods=["GET"])
def static_files(filename="login.html"):
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

@app.post("/api/gemini")
def get_ai_insight():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401

    body = request.get_json(silent=True) or {}
    message = str(body.get("message") or body.get("content") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    supplied_entries = body.get("journalEntries")
    if isinstance(supplied_entries, list):
        journal_entries = normalize_journal_entries(supplied_entries)
    else:
        journal_entries = load_user_records("journal", username)

    supplied_checkins = body.get("checkins")
    if isinstance(supplied_checkins, list):
        checkins = normalize_checkins(supplied_checkins)
    else:
        checkins = load_user_records("checkin", username)

    supplied_questionnaires = body.get("questionnaires")
    if isinstance(supplied_questionnaires, list):
        questionnaires = normalize_questionnaire_entries(supplied_questionnaires)
    else:
        questionnaires = load_user_records("questionnaire", username)
    prompt = build_ai_prompt(message, journal_entries, checkins, questionnaires)

    ai_client = get_ai_client()
    if ai_client is None:
        return jsonify({"error": "Chat service unavailable"}), 502

    try:
        ai_output = ai_client.models.generate_content(model=MODEL_NAME, contents=prompt)
    except Exception:
        return jsonify({"error": "Chat service unavailable"}), 502

    reply = str(getattr(ai_output, "text", "") or "").strip()
    if not reply:
        return jsonify({"error": "Chat service unavailable"}), 502

    return jsonify({"reply": reply, "message": reply})


# POST /api/trends/share — grant a specific email access to owner's trends
@app.post("/api/trends/share")
def add_trends_share():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401
    body = request.get_json() or {}
    viewer_email = (body.get("email") or "").strip().lower()
    if not viewer_email or "@" not in viewer_email:
        return jsonify({"error": "Valid email is required"}), 400
    if viewer_email == username.lower():
        return jsonify({"error": "You cannot share with yourself"}), 400
    redis.sadd(f"trends_shares:{username}", viewer_email)
    redis.sadd(f"trends_shared_with:{viewer_email}", username.lower())
    return jsonify({"success": True})


# DELETE /api/trends/share — revoke a specific email's access
@app.delete("/api/trends/share")
def remove_trends_share():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401
    body = request.get_json() or {}
    viewer_email = (body.get("email") or "").strip().lower()
    if not viewer_email:
        return jsonify({"error": "Email is required"}), 400
    redis.srem(f"trends_shares:{username}", viewer_email)
    redis.srem(f"trends_shared_with:{viewer_email}", username.lower())
    return jsonify({"success": True})


# GET /api/trends/shared-with-me — list owners who have shared their trends with current user
@app.get("/api/trends/shared-with-me")
def shared_with_me():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401
    owners = redis.smembers(f"trends_shared_with:{username.lower()}") or []
    return jsonify({"owners": list(owners)})


# GET /api/trends/shares — list emails the owner has granted access to
@app.get("/api/trends/shares")
def list_trends_shares():
    username = get_username()
    if not username:
        return jsonify(AUTH_REQUIRED_ERROR), 401
    members = redis.smembers(f"trends_shares:{username}") or []
    return jsonify({"viewers": list(members)})


# GET /api/trends/shared-checkins?owner=email — fetch another user's check-ins if access was granted
@app.get("/api/trends/shared-checkins")
def get_shared_checkins():
    viewer = get_username()
    if not viewer:
        return jsonify(AUTH_REQUIRED_ERROR), 401
    owner = (request.args.get("owner") or "").strip().lower()
    if not owner:
        return jsonify({"error": "owner parameter is required"}), 400
    is_member = redis.sismember(f"trends_shares:{owner}", viewer.lower())
    if not is_member:
        return jsonify({"error": "Access denied"}), 403
    data = redis.hgetall(f"checkin:{owner}")
    if not data:
        return jsonify([])
    entries = [json.loads(v) for v in data.values()]
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return jsonify(entries)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(port=port, debug=True)
