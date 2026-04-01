import json
import os

import pytest
from dotenv import load_dotenv
from upstash_redis import Redis

load_dotenv()

@pytest.fixture
def redis_client():
    return Redis(
        url=os.environ["UPSTASH_REDIS_REST_URL"],
        token=os.environ["UPSTASH_REDIS_REST_TOKEN"],
    )


def test_journal_write_read_delete(redis_client):
    key = "journal:test_user"
    entry = {"id": "1", "title": "Test Entry", "content": "Hello Redis!", "timestamp": 1000}

    redis_client.hset(key, "1", json.dumps(entry))

    data = redis_client.hgetall(key)
    assert "1" in data

    redis_client.hdel(key, "1")
    assert redis_client.hgetall(key) == {}


def test_checkin_write_read_delete(redis_client):
    key = "checkin:test_user"
    checkin = {
        "id": "2000",
        "words": ["Happy", "Calm", "Grateful"],
        "moodScore": 80,
        "moodLabel": "Great",
        "timestamp": 2000,
    }

    redis_client.hset(key, "2000", json.dumps(checkin))

    data = redis_client.hgetall(key)
    retrieved = json.loads(list(data.values())[0])
    assert retrieved["moodScore"] == 80
    assert retrieved["words"] == ["Happy", "Calm", "Grateful"]

    redis_client.hdel(key, "2000")
    assert redis_client.hgetall(key) == {}


def test_entries_sort_order(redis_client):
    key = "journal:sort_test"
    entries = [
        {"id": "100", "title": "Older", "content": "First entry", "timestamp": 100},
        {"id": "200", "title": "Newer", "content": "Second entry", "timestamp": 200},
    ]

    for e in entries:
        redis_client.hset(key, e["id"], json.dumps(e))

    raw = redis_client.hgetall(key)
    sorted_entries = sorted(
        [json.loads(v) for v in raw.values()],
        key=lambda e: e["timestamp"],
        reverse=True,
    )
    assert sorted_entries[0]["id"] == "200"

    for e in entries:
        redis_client.hdel(key, e["id"])
