import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, "/workspaces/Website/ArunCode_package/ArunCode")
import app as app_module


class EmailStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_emails_file = app_module.EMAILS_FILE
        self.emails_path = os.path.join(self.temp_dir.name, "emails.json")
        app_module.EMAILS_FILE = self.emails_path
        with open(self.emails_path, "w", encoding="utf-8"):
            pass

    def tearDown(self):
        app_module.EMAILS_FILE = self.original_emails_file

    def test_empty_email_file_returns_empty_list(self):
        self.assertEqual(app_module.load_emails(), [])

    def test_saving_emails_writes_json(self):
        app_module.save_emails([{"id": 1, "subject": "Hi"}])
        with open(self.emails_path, "r", encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), [{"id": 1, "subject": "Hi"}])

    def test_resolve_recipient_accepts_username_alias(self):
        resolved = app_module.resolve_recipient(
            "ArunC@literate-enigma-x5gww6xpxvw6fpvv6-5000.app.github.dev"
        )
        self.assertEqual(resolved["to_user"], "ArunC")
        self.assertEqual(resolved["to_addr"], "chandrasekarana@student.rcdsb.on.ca")

    def test_registering_new_user_allows_alias_resolution(self):
        original_users_file = app_module.USERS_FILE
        original_users = app_module.USERS.copy()
        temp_users_path = os.path.join(self.temp_dir.name, "users.json")
        app_module.USERS_FILE = temp_users_path
        app_module.USERS = {}
        app_module.save_users(app_module.USERS)
        self.addCleanup(lambda: setattr(app_module, "USERS_FILE", original_users_file))
        self.addCleanup(lambda: setattr(app_module, "USERS", original_users))

        client = app_module.app.test_client()
        response = client.post(
            "/api/register",
            json={"username": "Mina", "email": "mina@example.com", "password": "secret123"},
        )

        self.assertEqual(response.status_code, 200)
        resolved = app_module.resolve_recipient("Mina@literate-enigma-x5gww6xpxvw6fpvv6-5000.app.github.dev")
        self.assertEqual(resolved["to_user"], "Mina")
        self.assertEqual(resolved["to_addr"], "mina@example.com")


if __name__ == "__main__":
    unittest.main()
