import json
import unittest
from server import app

class ThreeWordReflectionTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.headers = {
            "Content-Type": "application/json",
            "X-Username": "test_user_reflection"
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


if __name__ == "__main__":
    unittest.main()