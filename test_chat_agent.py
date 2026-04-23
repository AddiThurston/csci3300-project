import json
import unittest
import uuid
from unittest.mock import MagicMock, patch

# Contract tests for the future Gemini Flash 2.5 chatbot.
# These tests intentionally define the expected API and prompt-building behavior
# before the implementation exists.
mock_redis = MagicMock()
patch("upstash_redis.Redis", return_value=mock_redis).start()

import server

app = server.app

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


class ChatAgentContractTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.username = f"test_user_chat_{uuid.uuid4().hex}@example.com"
        self.headers = {"Content-Type": "application/json"}
        self._store = {}
        self._setup_redis_mock()
        self._authenticate(self.client, self.username)

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

    def _authenticate(self, client, username):
        with client.session_transaction() as sess:
            sess["user"] = {"sub": f"sub-{username}", "email": username}

    def _save_record(self, bucket, record, username=None):
        owner = username or self.username
        self._store.setdefault(f"{bucket}:{owner}", {})[record["id"]] = json.dumps(record)

    def _journal_entry(self, entry_id, title, content, timestamp, username=None):
        self._save_record(
            "journal",
            {
                "id": entry_id,
                "title": title,
                "content": content,
                "timestamp": timestamp,
            },
            username=username,
        )

    def _checkin(self, entry_id, mood_score, mood_label, words, timestamp, username=None):
        self._save_record(
            "checkin",
            {
                "id": entry_id,
                "words": words,
                "moodScore": mood_score,
                "moodLabel": mood_label,
                "timestamp": timestamp,
            },
            username=username,
        )

    def _questionnaire(self, entry_id, responses, timestamp, username=None):
        self._save_record(
            "questionnaire",
            {
                "id": entry_id,
                "responses": responses,
                "timestamp": timestamp,
            },
            username=username,
        )

    def test_requires_authentication(self):
        unauthenticated_client = app.test_client()

        response = unauthenticated_client.post(
            "/api/gemini",
            data=json.dumps({"message": "What trends do you see?"}),
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Authentication required")

    def test_rejects_missing_or_blank_message(self):
        response = self.client.post(
            "/api/gemini",
            data=json.dumps({"message": "   "}),
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "message is required")

    def test_builds_gemini_prompt_from_entries_and_trends(self):
        self._journal_entry("j1", "Midterms", "I felt overwhelmed studying for exams.", 1000)
        self._journal_entry("j2", "Recovery", "I felt more grounded after taking a walk.", 2000)

        for index, mood_score in enumerate([35, 38, 40, 42, 45, 47, 49, 62, 64, 66, 68, 70, 72, 74], start=1):
            self._checkin(
                f"c{index}",
                mood_score,
                "Good" if mood_score >= 60 else "Low",
                ["calm", "hopeful"] if mood_score >= 60 else ["stressed", "tired"],
                10_000 + index,
            )

        self._questionnaire("q1", VALID_RESPONSES, 3000)

        ai_client = MagicMock()
        ai_client.models.generate_content.return_value = MagicMock(
            text="Your recent check-ins are improving, and calm is becoming more common."
        )

        with patch.object(server, "client", ai_client, create=True), patch.object(
            server, "MODEL_NAME", "gemini-2.5-flash", create=True
        ):
            response = self.client.post(
                "/api/gemini",
                data=json.dumps({"message": "What patterns do you notice this week?"}),
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["reply"],
            "Your recent check-ins are improving, and calm is becoming more common.",
        )

        call = ai_client.models.generate_content.call_args
        self.assertIsNotNone(call)
        self.assertEqual(call.kwargs["model"], "gemini-2.5-flash")

        prompt = call.kwargs["contents"]
        self.assertIn("User Question:", prompt)
        self.assertIn("Date Context:", prompt)
        self.assertIn("Journal Entries:", prompt)
        self.assertIn("Check-In History:", prompt)
        self.assertIn("Questionnaire Responses:", prompt)
        self.assertIn("What patterns do you notice this week?", prompt)
        self.assertIn("I felt overwhelmed studying for exams.", prompt)
        self.assertIn("I felt more grounded after taking a walk.", prompt)
        self.assertIn("Use the timestamps below to reason about chronology", prompt)
        self.assertIn("Journal window:", prompt)
        self.assertIn("Most recent journal entry:", prompt)
        self.assertIn("Check-in window:", prompt)
        self.assertIn("Questionnaire window:", prompt)
        self.assertIn("1970-01-01 00:00:01 UTC", prompt)
        self.assertIn("1970-01-01 00:00:02 UTC", prompt)
        self.assertIn("Improving", prompt)
        self.assertIn("calm", prompt.lower())
        self.assertIn("mood", prompt.lower())
        self.assertNotIn("canvas", prompt.lower())

    def test_prompt_uses_only_authenticated_users_data(self):
        other_user = f"test_user_chat_{uuid.uuid4().hex}@example.com"
        self._journal_entry("mine", "My Entry", "This is my journal entry.", 1000)
        self._journal_entry(
            "theirs",
            "Other Entry",
            "This belongs to another user and must never be sent.",
            2000,
            username=other_user,
        )
        self._checkin("mine-checkin", 67, "Good", ["steady"], 3000)
        self._checkin("their-checkin", 5, "Low", ["private"], 4000, username=other_user)

        ai_client = MagicMock()
        ai_client.models.generate_content.return_value = MagicMock(text="Scoped correctly.")

        with patch.object(server, "client", ai_client, create=True), patch.object(
            server, "MODEL_NAME", "gemini-2.5-flash", create=True
        ):
            response = self.client.post(
                "/api/gemini",
                data=json.dumps({"message": "Summarize my data only."}),
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        prompt = ai_client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("This is my journal entry.", prompt)
        self.assertIn("steady", prompt)
        self.assertNotIn("This belongs to another user and must never be sent.", prompt)
        self.assertNotIn("private", prompt)

    def test_accepts_supplied_checkin_and_questionnaire_drafts(self):
        ai_client = MagicMock()
        ai_client.models.generate_content.return_value = MagicMock(text="Draft context included.")

        supplied_checkins = [
            {
                "words": ["anxious", "tired"],
                "moodScore": 28,
                "moodLabel": "Low",
                "timestamp": 4_000,
            }
        ]
        supplied_questionnaires = [
            {
                "responses": {
                    "mood": 2,
                    "sleep": 1,
                    "energy": 2,
                    "focus": 2,
                },
                "timestamp": 5_000,
            }
        ]

        with patch.object(server, "client", ai_client, create=True), patch.object(
            server, "MODEL_NAME", "gemini-2.5-flash", create=True
        ):
            response = self.client.post(
                "/api/gemini",
                data=json.dumps(
                    {
                        "message": "What stands out in the draft answers I have right now?",
                        "checkins": supplied_checkins,
                        "questionnaires": supplied_questionnaires,
                    }
                ),
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        prompt = ai_client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("anxious", prompt.lower())
        self.assertIn("tired", prompt.lower())
        self.assertIn("Recent questionnaire responses", prompt)
        self.assertIn("Mood: 2", prompt)
        self.assertIn("Sleep: 1", prompt)
        self.assertIn("What stands out in the draft answers I have right now?", prompt)

    def test_handles_missing_history_with_clear_placeholders(self):
        ai_client = MagicMock()
        ai_client.models.generate_content.return_value = MagicMock(
            text="I do not have enough history yet, but I can still answer general questions."
        )

        with patch.object(server, "client", ai_client, create=True), patch.object(
            server, "MODEL_NAME", "gemini-2.5-flash", create=True
        ):
            response = self.client.post(
                "/api/gemini",
                data=json.dumps({"message": "What can you tell me so far?"}),
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        prompt = ai_client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("No journal entries available.", prompt)
        self.assertIn("No check-ins available.", prompt)
        self.assertIn("No questionnaire responses available.", prompt)

    def test_returns_upstream_error_when_gemini_fails(self):
        self._journal_entry("j1", "Today", "I had a hard day.", 1000)

        ai_client = MagicMock()
        ai_client.models.generate_content.side_effect = RuntimeError("Gemini unavailable")

        with patch.object(server, "client", ai_client, create=True), patch.object(
            server, "MODEL_NAME", "gemini-2.5-flash", create=True
        ):
            response = self.client.post(
                "/api/gemini",
                data=json.dumps({"message": "Help me understand my recent mood."}),
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["error"], "Chat service unavailable")


if __name__ == "__main__":
    unittest.main()
