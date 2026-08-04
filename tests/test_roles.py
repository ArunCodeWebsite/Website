import importlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, "/workspaces/Website/ArunCode_package/ArunCode")
import app as app_module


class RoleTests(unittest.TestCase):
    def test_users_file_is_resolved_from_the_app_directory(self):
        original_cwd = os.getcwd()
        os.chdir(tempfile.gettempdir())
        self.addCleanup(os.chdir, original_cwd)

        reloaded = importlib.reload(app_module)
        self.assertTrue(reloaded.USERS_FILE.startswith(reloaded.BASE_DIR))
        self.assertTrue(os.path.exists(reloaded.USERS_FILE))

    def test_student_role_is_saved_for_new_users(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        original_users_file = app_module.USERS_FILE
        original_users = app_module.USERS.copy()
        temp_users_path = os.path.join(temp_dir.name, "users.json")
        app_module.USERS_FILE = temp_users_path
        app_module.USERS = {}
        app_module.save_users(app_module.USERS)
        self.addCleanup(lambda: setattr(app_module, "USERS_FILE", original_users_file))
        self.addCleanup(lambda: setattr(app_module, "USERS", original_users))

        client = app_module.app.test_client()
        response = client.post(
            "/api/register",
            json={"username": "StudentUser", "email": "student@example.com", "password": "secret123", "role": "Student"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(app_module.USERS["StudentUser"]["role"], "student")


if __name__ == "__main__":
    unittest.main()
