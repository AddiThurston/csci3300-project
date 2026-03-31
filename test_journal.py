import json
import time
import unittest
import uuid
from unittest.mock import MagicMock, patch


# ── Mock Redis before importing the app ───────────────────────────────────────
# server.py connects to Redis at import time, so we patch it before the import.
mock_redis = MagicMock()
patch("upstash_redis.Redis", return_value=mock_redis).start()

from server import app  # noqa: E402  (import after patch)


class JournalTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.username = f"test_user_journal_{uuid.uuid4().hex}"
        self.headers = {
            "Content-Type": "application/json",
            "X-Username": self.username,
        }
        # Each test gets its own clean in-memory store keyed by Redis hash key.
        # { "journal:<username>": { entry_id: json_string, ... } }
        self._store: dict = {}
        self._setup_redis_mock()

    def _setup_redis_mock(self):
        """Wire the shared mock_redis to our per-test in-memory store."""

        def hset(key, field, value):
            self._store.setdefault(key, {})[field] = value

        def hgetall(key):
            return dict(self._store.get(key, {}))

        def hdel(key, field):
            self._store.get(key, {}).pop(field, None)

        mock_redis.hset.side_effect = hset
        mock_redis.hgetall.side_effect = hgetall
        mock_redis.hdel.side_effect = hdel

    # ------------------------------------------------------------------ POST

    def test_valid_entry(self):
        """201 returned; echoes title, content, id, and timestamp."""
        payload = {"title": "My Day", "content": "Today was great."}
        res = self.client.post("/api/entries",
            data=json.dumps(payload), headers=self.headers)

        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["title"], "My Day")
        self.assertEqual(data["content"], "Today was great.")
        self.assertIn("id", data)
        self.assertIn("timestamp", data)

    def test_entry_title_defaults_to_untitled(self):
        """Omitting title should create the entry with title 'Untitled'."""
        payload = {"content": "No title here."}
        res = self.client.post("/api/entries",
            data=json.dumps(payload), headers=self.headers)

        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["title"], "Untitled")
        self.assertEqual(data["content"], "No title here.")

    def test_empty_title_defaults_to_untitled(self):
        """An empty/blank title should also default to 'Untitled'."""
        payload = {"title": "", "content": "No title."}
        res = self.client.post("/api/entries",
            data=json.dumps(payload), headers=self.headers)

        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["title"], "Untitled")

    def test_missing_content_rejected(self):
        """An entry with no content field should be rejected with 400."""
        payload = {"title": "Empty"}
        res = self.client.post("/api/entries",
            data=json.dumps(payload), headers=self.headers)

        self.assertEqual(res.status_code, 400)

    def test_blank_content_rejected(self):
        """An entry whose content is whitespace-only should be rejected with 400."""
        payload = {"title": "Blank", "content": "   "}
        res = self.client.post("/api/entries",
            data=json.dumps(payload), headers=self.headers)

        self.assertEqual(res.status_code, 400)

    def test_post_requires_username(self):
        """Missing X-Username header should return 401."""
        payload = {"content": "No auth."}
        res = self.client.post("/api/entries",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"})

        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Username required")

    # ------------------------------------------------------------------ GET

    def test_get_requires_username(self):
        """Missing X-Username header should return 401."""
        res = self.client.get("/api/entries")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "Username required")

    def test_get_empty_for_new_user(self):
        """A brand-new user should get an empty list."""
        res = self.client.get("/api/entries", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), [])

    def test_get_returns_saved_entries_newest_first(self):
        """Entries should be returned sorted newest-first."""
        self.client.post("/api/entries",
            data=json.dumps({"title": "First", "content": "Entry one."}),
            headers=self.headers)
        time.sleep(0.02)   # ensure distinct ms timestamps
        self.client.post("/api/entries",
            data=json.dumps({"title": "Second", "content": "Entry two."}),
            headers=self.headers)

        res = self.client.get("/api/entries", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        entries = res.get_json()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["title"], "Second")
        self.assertEqual(entries[1]["title"], "First")

    def test_get_is_user_scoped(self):
        """Each user only sees their own entries."""
        user_b_headers = {
            "Content-Type": "application/json",
            "X-Username": f"test_user_journal_{uuid.uuid4().hex}",
        }

        self.client.post("/api/entries",
            data=json.dumps({"title": "A", "content": "User A entry."}),
            headers=self.headers)
        self.client.post("/api/entries",
            data=json.dumps({"title": "B", "content": "User B entry."}),
            headers=user_b_headers)

        entries_a = self.client.get("/api/entries", headers=self.headers).get_json()
        entries_b = self.client.get("/api/entries", headers=user_b_headers).get_json()

        self.assertEqual(len(entries_a), 1)
        self.assertEqual(len(entries_b), 1)
        self.assertEqual(entries_a[0]["title"], "A")
        self.assertEqual(entries_b[0]["title"], "B")

    # ------------------------------------------------------------------ DELETE

    def test_delete_requires_username(self):
        """Missing X-Username header should return 401."""
        res = self.client.delete("/api/entries/some-id",
            headers={"Content-Type": "application/json"})
        self.assertEqual(res.status_code, 401)

    def test_delete_removes_entry(self):
        """After deletion the entry should not appear in GET."""
        res = self.client.post("/api/entries",
            data=json.dumps({"title": "Gone", "content": "Delete me."}),
            headers=self.headers)
        entry_id = res.get_json()["id"]

        del_res = self.client.delete(f"/api/entries/{entry_id}",
            headers=self.headers)
        self.assertEqual(del_res.status_code, 200)

        entries = self.client.get("/api/entries", headers=self.headers).get_json()
        self.assertEqual(entries, [])

    def test_delete_nonexistent_entry_returns_200(self):
        """Server silently succeeds on deleting a non-existent id (hdel is a no-op)."""
        res = self.client.delete(f"/api/entries/{uuid.uuid4()}",
            headers=self.headers)
        self.assertEqual(res.status_code, 200)

    def test_delete_only_removes_target_entry(self):
        """Deleting one entry leaves the other intact."""
        res_a = self.client.post("/api/entries",
            data=json.dumps({"title": "Keep", "content": "Stay here."}),
            headers=self.headers)
        time.sleep(0.02)
        res_b = self.client.post("/api/entries",
            data=json.dumps({"title": "Remove", "content": "Delete me."}),
            headers=self.headers)

        self.client.delete(f"/api/entries/{res_b.get_json()['id']}",
            headers=self.headers)

        entries = self.client.get("/api/entries", headers=self.headers).get_json()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "Keep")


if __name__ == "__main__":
    unittest.main()