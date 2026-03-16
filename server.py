import base64
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


def get_user_sub():
    """Decode the Google JWT from the Authorization header and return the user's sub."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        token = auth.split(" ")[1]
        segment = token.split(".")[1]
        segment += "=" * (4 - len(segment) % 4)  # fix base64 padding
        payload = json.loads(base64.b64decode(segment))
        return payload.get("sub")
    except Exception:
        return None


# Serve HTML files
@app.route("/")
@app.route("/<path:filename>")
def static_files(filename="index.html"):
    return send_from_directory(".", filename)


# GET /api/entries — fetch all journal entries for the logged-in user
@app.get("/api/entries")
def get_entries():
    sub = get_user_sub()
    if not sub:
        return jsonify({"error": "Unauthorized"}), 401

    data = redis.hgetall(f"journal:{sub}")
    if not data:
        return jsonify([])

    entries = [json.loads(v) for v in data.values()]
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return jsonify(entries)


# POST /api/entries — save a new journal entry
@app.post("/api/entries")
def create_entry():
    sub = get_user_sub()
    if not sub:
        return jsonify({"error": "Unauthorized"}), 401

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

    redis.hset(f"journal:{sub}", entry["id"], json.dumps(entry))
    return jsonify(entry), 201


# DELETE /api/entries/<id> — delete a journal entry
@app.delete("/api/entries/<entry_id>")
def delete_entry(entry_id):
    sub = get_user_sub()
    if not sub:
        return jsonify({"error": "Unauthorized"}), 401

    redis.hdel(f"journal:{sub}", entry_id)
    return jsonify({"success": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(port=port, debug=True)
