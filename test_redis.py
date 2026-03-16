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
