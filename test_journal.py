import json
import time
import unittest
import uuid
from unittest.mock import MagicMock, patch

# server.py connects to Redis at import time, so patch before import.
mock_redis = MagicMock()
patch("upstash_redis.Redis", return_value=mock_redis).start()

from server import app


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.username = f"test_user_journal_{uuid.uuid4().hex}@example.com"
        self.headers = {"Content-Type": "application/json"}
        self._store = {}
        self._setup_redis_mock()
        self._authenticate(self.client, self.username)

    def _authenticate(self, client, username):
        with client.session_transaction() as sess:
            sess["user"] = {"sub": f"sub-{username}", "email": username}

    def _setup_redis_mock(self):
        def hset(key, field, value):
            self._store.setdefault(key, {})[field] = value

        def hgetall(key):
            return dict(self._store.get(key, {}))

        def hdel(key, field):
            self._store.get(key, {}).pop(field, None)

        mock_redis.hset.side_effect = hset
        mock_redis.hgetall.side_effect = hgetall
        mock_redis.hdel.side_effect = hdel

    def test_valid_entry(self):
        res = self.client.post(
            "/api/entries",
            data=json.dumps({"title": "My Day", "content": "Today was great."}),
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["title"], "My Day")
        self.assertEqual(data["content"], "Today was great.")
        self.assertIn("id", data)
        self.assertIn("timestamp", data)

    def test_requires_authentication(self):
        unauth = app.test_client()
        res = unauth.get("/api/entries")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Authentication required")

    def test_get_empty_for_new_user(self):
        res = self.client.get("/api/entries", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), [])

    def test_get_returns_saved_entries_newest_first(self):
        self.client.post(
            "/api/entries",
            data=json.dumps({"title": "First", "content": "Entry one."}),
            headers=self.headers,
        )
        time.sleep(0.02)
        self.client.post(
            "/api/entries",
            data=json.dumps({"title": "Second", "content": "Entry two."}),
            headers=self.headers,
        )
        res = self.client.get("/api/entries", headers=self.headers)
        entries = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["title"], "Second")
        self.assertEqual(entries[1]["title"], "First")

    def test_get_is_user_scoped(self):
        user_b_client = app.test_client()
        user_b = f"test_user_journal_{uuid.uuid4().hex}@example.com"
        self._authenticate(user_b_client, user_b)

        self.client.post(
            "/api/entries",
            data=json.dumps({"title": "A", "content": "User A entry."}),
            headers=self.headers,
        )
        user_b_client.post(
            "/api/entries",
            data=json.dumps({"title": "B", "content": "User B entry."}),
            headers=self.headers,
        )

        entries_a = self.client.get("/api/entries", headers=self.headers).get_json()
        entries_b = user_b_client.get("/api/entries", headers=self.headers).get_json()
        self.assertEqual(len(entries_a), 1)
        self.assertEqual(len(entries_b), 1)
        self.assertEqual(entries_a[0]["title"], "A")
        self.assertEqual(entries_b[0]["title"], "B")

    def test_delete_removes_entry(self):
        res = self.client.post(
            "/api/entries",
            data=json.dumps({"title": "Gone", "content": "Delete me."}),
            headers=self.headers,
        )
        entry_id = res.get_json()["id"]
        del_res = self.client.delete(f"/api/entries/{entry_id}", headers=self.headers)
        self.assertEqual(del_res.status_code, 200)
        entries = self.client.get("/api/entries", headers=self.headers).get_json()
        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()