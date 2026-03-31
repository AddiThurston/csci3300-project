import json
import os
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from upstash_redis import Redis

load_dotenv()

app = Flask(__name__, static_folder=".")
redis = Redis(
    url=os.environ["UPSTASH_REDIS_REST_URL"],
    token=os.environ["UPSTASH_REDIS_REST_TOKEN"],
)


def get_username():
    """Get the username from the X-Username header."""
    return request.headers.get("X-Username", "").strip() or None


# Serve HTML files
@app.route("/")
@app.route("/<path:filename>")
def static_files(filename="index.html"):
    return send_from_directory(".", filename)


# GET /api/entries — fetch all journal entries for a user
@app.get("/api/entries")
def get_entries():
    username = get_username()
    if not username:
        return jsonify({"error": "Username required"}), 401

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
        return jsonify({"error": "Username required"}), 401

    body = request.get_json()
    content = (body or {}).get("content", "").strip()
    if not content:
        return jsonify({"error": "Content is required"}), 400

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
        return jsonify({"error": "Username required"}), 401

    redis.hdel(f"journal:{username}", entry_id)
    return jsonify({"success": True})


# POST /api/checkin — save a three-word mood check-in
@app.post("/api/checkin")
def create_checkin():
    username = get_username()
    if not username:
        return jsonify({"error": "Username required"}), 401

    body       = request.get_json() or {}
    words      = body.get("words", [])
    mood_score = body.get("moodScore")
    mood_label = body.get("moodLabel", "")

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
        return jsonify({"error": "Username required"}), 401

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
        return jsonify({"error": "Username required"}), 401

    redis.hdel(f"checkin:{username}", checkin_id)
    return jsonify({"success": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(port=port, debug=True)