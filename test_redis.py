import json
from dotenv import load_dotenv
import os
from upstash_redis import Redis

load_dotenv()

redis = Redis(
    url=os.environ["UPSTASH_REDIS_REST_URL"],
    token=os.environ["UPSTASH_REDIS_REST_TOKEN"],
)

TEST_KEY = "journal:test_user"

# Write a test entry
entry = {"id": "1", "title": "Test Entry", "content": "Hello Redis!", "timestamp": 1000}
redis.hset(TEST_KEY, "1", json.dumps(entry))
print("✓ Write successful")

# Read it back
data = redis.hgetall(TEST_KEY)
print(f"✓ Read successful: {list(data.values())}")

# Delete it
redis.hdel(TEST_KEY, "1")
print("✓ Delete successful")

print("\nAll good — Redis is connected and working!")

# ── Check-in tests ─────────────────────────────────────────────────────────────
CHECKIN_KEY = "checkin:test_user"

# Write a check-in entry
checkin = {
    "id": "2000",
    "words": ["Happy", "Calm", "Grateful"],
    "moodScore": 80,
    "moodLabel": "Great",
    "timestamp": 2000,
}
redis.hset(CHECKIN_KEY, "2000", json.dumps(checkin))
print("✓ Check-in write successful")

# Read it back and verify fields
checkin_data = redis.hgetall(CHECKIN_KEY)
retrieved = json.loads(list(checkin_data.values())[0])
assert retrieved["moodScore"] == 80, "moodScore should be 80"
assert retrieved["words"] == ["Happy", "Calm", "Grateful"], "words mismatch"
print("✓ Check-in read and field validation successful")

# Delete it
redis.hdel(CHECKIN_KEY, "2000")
assert redis.hgetall(CHECKIN_KEY) == {}, "Check-in key should be empty after delete"
print("✓ Check-in delete successful")

# ── Multiple entries sort order ────────────────────────────────────────────────
SORT_KEY = "journal:sort_test"

entries = [
    {"id": "100", "title": "Older", "content": "First entry", "timestamp": 100},
    {"id": "200", "title": "Newer", "content": "Second entry", "timestamp": 200},
]
for e in entries:
    redis.hset(SORT_KEY, e["id"], json.dumps(e))

raw = redis.hgetall(SORT_KEY)
sorted_entries = sorted([json.loads(v) for v in raw.values()], key=lambda e: e["timestamp"], reverse=True)
assert sorted_entries[0]["id"] == "200", "Most recent entry should come first"
print("✓ Multiple entries sort order correct")

# Cleanup
for e in entries:
    redis.hdel(SORT_KEY, e["id"])

print("\nAll tests passed!")
