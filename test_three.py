import json
import time
import unittest
import uuid

from server import app

class ThreeWordReflectionTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.username = f"test_user_reflection_{uuid.uuid4().hex}"
        self.headers = {
            "Content-Type": "application/json",
            "X-Username": self.username
        }

    # Check in with valid data
    def test_valid_checkin(self):
        payload = {
            "words": ["Happy", "Calm"],
            "moodScore": 70,
            "moodLabel": "Good"
        }

        res = self.client.post("/api/checkin",
            data=json.dumps(payload),
            headers=self.headers
        )

        self.assertEqual(res.status_code, 201)
        data = res.get_json()

        self.assertEqual(data["words"], ["Happy", "Calm"])
        self.assertEqual(data["moodScore"], 70)
        self.assertEqual(data["moodLabel"], "Good")

    # No words
    def test_no_words(self):
        payload = {
            "words": [],
            "moodScore": 50
        }

        res = self.client.post("/api/checkin",
            data=json.dumps(payload),
            headers=self.headers
        )

        self.assertEqual(res.status_code, 400)

    # More than 3 words
    def test_more_than_three_words(self):
        payload = {
            "words": ["Happy", "Calm", "Focused", "Extra"],
            "moodScore": 60
        }

        res = self.client.post("/api/checkin",
            data=json.dumps(payload),
            headers=self.headers
        )

        self.assertEqual(res.status_code, 400)

    # No mood slider
    def test_missing_mood_slider(self):
        payload = {
            "words": ["Happy"]
        }

        res = self.client.post("/api/checkin",
            data=json.dumps(payload),
            headers=self.headers
        )

        self.assertEqual(res.status_code, 400)

    # Missing user auth header for history fetch
    def test_get_history_requires_username(self):
        res = self.client.get("/api/checkin")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Username required")

    # New users should have no check-in history
    def test_get_history_empty_for_new_user(self):
        res = self.client.get("/api/checkin", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        # Future contract: history endpoint returns metadata envelope.
        self.assertIsInstance(body, dict)
        self.assertEqual(body["entries"], [])
        self.assertEqual(body["total"], 0)

    # GET history should return newest entries first
    def test_get_history_returns_saved_entries_newest_first(self):
        base_payload = {
            "words": ["Calm"],
            "moodScore": 50,
            "moodLabel": "Okay"
        }

        first = self.client.post(
            "/api/checkin",
            data=json.dumps(base_payload),
            headers=self.headers
        )
        # Ensure distinct timestamps so sort order is deterministic.
        time.sleep(0.02)
        second_payload = dict(base_payload)
        second_payload["words"] = ["Focused", "Grateful"]
        second_payload["moodScore"] = 80
        second_payload["moodLabel"] = "Great"
        second = self.client.post(
            "/api/checkin",
            data=json.dumps(second_payload),
            headers=self.headers
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

        # Future contract: UI can request only the latest N records.
        history_res = self.client.get("/api/checkin?limit=1", headers=self.headers)
        self.assertEqual(history_res.status_code, 200)
        history = history_res.get_json()
        self.assertIsInstance(history, dict)
        self.assertEqual(history["total"], 2)
        self.assertEqual(history["hasMore"], True)
        self.assertEqual(len(history["entries"]), 1)

        # Newest check-in appears first in API response.
        self.assertEqual(history["entries"][0]["moodLabel"], "Great")
        self.assertEqual(history["entries"][0]["words"], ["Focused", "Grateful"])

    # GET history should only return the current user's data
    def test_get_history_is_user_scoped(self):
        user_a_headers = dict(self.headers)
        user_b_headers = {
            "Content-Type": "application/json",
            "X-Username": f"test_user_reflection_{uuid.uuid4().hex}"
        }

        payload_a = {"words": ["Hopeful"], "moodScore": 65, "moodLabel": "Good"}
        payload_b = {"words": ["Tired"], "moodScore": 30, "moodLabel": "Low"}

        res_a = self.client.post("/api/checkin", data=json.dumps(payload_a), headers=user_a_headers)
        res_b = self.client.post("/api/checkin", data=json.dumps(payload_b), headers=user_b_headers)

        self.assertEqual(res_a.status_code, 201)
        self.assertEqual(res_b.status_code, 201)

        history_a = self.client.get("/api/checkin", headers=user_a_headers)
        history_b = self.client.get("/api/checkin", headers=user_b_headers)

        self.assertEqual(history_a.status_code, 200)
        self.assertEqual(history_b.status_code, 200)
        self.assertEqual(len(history_a.get_json()), 1)
        self.assertEqual(len(history_b.get_json()), 1)
        self.assertEqual(history_a.get_json()[0]["words"], ["Hopeful"])
        self.assertEqual(history_b.get_json()[0]["words"], ["Tired"])


if __name__ == "__main__":
    unittest.main()