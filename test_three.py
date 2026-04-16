import json
import time
import unittest
import uuid
from unittest.mock import MagicMock, patch

mock_redis = MagicMock()
patch("upstash_redis.Redis", return_value=mock_redis).start()

from server import app


class ThreeWordReflectionTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.username = f"test_user_reflection_{uuid.uuid4().hex}@example.com"
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

    def test_valid_checkin(self):
        payload = {"words": ["Happy", "Calm"], "moodScore": 70, "moodLabel": "Good"}
        res = self.client.post("/api/checkin", data=json.dumps(payload), headers=self.headers)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["words"], ["Happy", "Calm"])
        self.assertEqual(data["moodScore"], 70)
        self.assertEqual(data["moodLabel"], "Good")

    def test_no_words(self):
        res = self.client.post(
            "/api/checkin",
            data=json.dumps({"words": [], "moodScore": 50}),
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)

    def test_requires_authentication(self):
        unauth = app.test_client()
        res = unauth.get("/api/checkin")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Authentication required")

    def test_get_history_empty_for_new_user(self):
        res = self.client.get("/api/checkin", headers=self.headers)
        body = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(body, dict)
        self.assertEqual(body["entries"], [])
        self.assertEqual(body["total"], 0)

    def test_get_history_returns_saved_entries_newest_first(self):
        self.client.post(
            "/api/checkin",
            data=json.dumps({"words": ["Calm"], "moodScore": 50, "moodLabel": "Okay"}),
            headers=self.headers,
        )
        time.sleep(0.02)
        self.client.post(
            "/api/checkin",
            data=json.dumps({"words": ["Focused", "Grateful"], "moodScore": 80, "moodLabel": "Great"}),
            headers=self.headers,
        )

        history_res = self.client.get("/api/checkin?limit=1", headers=self.headers)
        history = history_res.get_json()
        self.assertEqual(history_res.status_code, 200)
        self.assertEqual(history["total"], 2)
        self.assertEqual(history["hasMore"], True)
        self.assertEqual(len(history["entries"]), 1)
        self.assertEqual(history["entries"][0]["moodLabel"], "Great")

    def test_get_history_is_user_scoped(self):
        user_b_client = app.test_client()
        user_b = f"test_user_reflection_{uuid.uuid4().hex}@example.com"
        self._authenticate(user_b_client, user_b)

        self.client.post(
            "/api/checkin",
            data=json.dumps({"words": ["Hopeful"], "moodScore": 65, "moodLabel": "Good"}),
            headers=self.headers,
        )
        user_b_client.post(
            "/api/checkin",
            data=json.dumps({"words": ["Tired"], "moodScore": 30, "moodLabel": "Low"}),
            headers=self.headers,
        )

        history_a = self.client.get("/api/checkin", headers=self.headers).get_json()
        history_b = user_b_client.get("/api/checkin", headers=self.headers).get_json()
        entries_a = history_a["entries"] if isinstance(history_a, dict) else history_a
        entries_b = history_b["entries"] if isinstance(history_b, dict) else history_b
        self.assertEqual(len(entries_a), 1)
        self.assertEqual(len(entries_b), 1)
        self.assertEqual(entries_a[0]["words"], ["Hopeful"])
        self.assertEqual(entries_b[0]["words"], ["Tired"])


if __name__ == "__main__":
    unittest.main()