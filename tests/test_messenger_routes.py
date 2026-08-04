import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, "/workspaces/Website")

sys.path.insert(0, "/workspaces/Website/ArunCode_package/ArunCode")
import app as app_module


class MessengerRouteTests(unittest.TestCase):
    def test_message_route_serves_messenger_page(self):
        client = app_module.app.test_client()
        response = client.get("/message")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ArunCode_Message", response.data)

    def test_message_page_keeps_sidebar_visible_on_tablets(self):
        html = Path("/workspaces/Website/ArunCode_package/ArunCode/static/message.html").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 900px)", html)
        self.assertNotIn(".sidebar{display:none}", html)

    def test_registration_checks_persisted_users_file(self):
        temp_users_path = "/tmp/aruncode-test-users.json"
        with open(temp_users_path, "w", encoding="utf-8") as handle:
            json.dump({"ArunC": {"email": "arun@example.com", "password": "x", "pin": "", "role": "user"}}, handle)

        original_users_file = app_module.USERS_FILE
        original_users = app_module.USERS.copy()
        app_module.USERS_FILE = temp_users_path
        app_module.USERS = {}
        self.addCleanup(lambda: setattr(app_module, "USERS_FILE", original_users_file))
        self.addCleanup(lambda: setattr(app_module, "USERS", original_users))

        client = app_module.app.test_client()
        response = client.post(
            "/api/register",
            json={"username": "ArunC", "email": "new@example.com", "password": "secret123"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("taken", response.get_json()["error"].lower())

        os.remove(temp_users_path)


if __name__ == "__main__":
    unittest.main()
