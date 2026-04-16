import json
import time
import unittest
import uuid
from unittest.mock import MagicMock, patch

mock_redis = MagicMock()
patch("upstash_redis.Redis", return_value=mock_redis).start()

from server import app

VALID_RESPONSES = {
    "mood": 4,
    "sleep": 3,
    "energy": 5,
    "calm": 2,
    "connection": 4,
    "motivation": 3,
    "focus": 4,
    "responsibilities": 5,
    "hope": 3,
    "anxiety_free": 2,
    "progress": 4,
    "physical": 3,
    "grounded": 4,
}


class QuestionnaireTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.username = f"test_user_q_{uuid.uuid4().hex}@example.com"
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

    def test_valid_submission(self):
        res = self.client.post(
            "/api/questionnaire",
            data=json.dumps({"responses": VALID_RESPONSES}),
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["responses"]["mood"], 4)
        self.assertIn("id", data)
        self.assertIn("timestamp", data)

    def test_requires_authentication(self):
        unauth = app.test_client()
        res = unauth.get("/api/questionnaire")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Authentication required")

    def test_incomplete_responses_rejected(self):
        incomplete = dict(list(VALID_RESPONSES.items())[:5])
        res = self.client.post(
            "/api/questionnaire",
            data=json.dumps({"responses": incomplete}),
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)

    def test_get_returns_saved_entries_newest_first(self):
        self.client.post(
            "/api/questionnaire",
            data=json.dumps({"responses": {**VALID_RESPONSES, "mood": 2}}),
            headers=self.headers,
        )
        time.sleep(0.02)
        self.client.post(
            "/api/questionnaire",
            data=json.dumps({"responses": {**VALID_RESPONSES, "mood": 5}}),
            headers=self.headers,
        )
        res = self.client.get("/api/questionnaire", headers=self.headers)
        entries = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["responses"]["mood"], 5)
        self.assertEqual(entries[1]["responses"]["mood"], 2)

    def test_get_is_user_scoped(self):
        user_b = f"test_user_q_{uuid.uuid4().hex}@example.com"
        user_b_client = app.test_client()
        self._authenticate(user_b_client, user_b)

        self.client.post(
            "/api/questionnaire",
            data=json.dumps({"responses": {**VALID_RESPONSES, "mood": 5}}),
            headers=self.headers,
        )
        user_b_client.post(
            "/api/questionnaire",
            data=json.dumps({"responses": {**VALID_RESPONSES, "mood": 1}}),
            headers=self.headers,
        )

        entries_a = self.client.get("/api/questionnaire", headers=self.headers).get_json()
        entries_b = user_b_client.get("/api/questionnaire", headers=self.headers).get_json()
        self.assertEqual(len(entries_a), 1)
        self.assertEqual(len(entries_b), 1)
        self.assertEqual(entries_a[0]["responses"]["mood"], 5)
        self.assertEqual(entries_b[0]["responses"]["mood"], 1)


if __name__ == "__main__":
    unittest.main()
