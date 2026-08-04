import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, "/workspaces/Website/ArunCode_package/ArunCode")
import app as app_module


class YoutubeRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_youtube_file = app_module.YOUTUBE_FILE
        self.youtube_path = os.path.join(self.temp_dir.name, "videos.json")
        app_module.YOUTUBE_FILE = self.youtube_path
        if os.path.exists(self.youtube_path):
            os.remove(self.youtube_path)

    def tearDown(self):
        app_module.YOUTUBE_FILE = self.original_youtube_file

    def test_youtube_page_serves(self):
        client = app_module.app.test_client()
        response = client.get("/youtube")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ArunCode_Youtube", response.data)

    def test_youtube_api_accepts_new_video(self):
        client = app_module.app.test_client()
        with client.session_transaction() as session:
            session["logged_in"] = True
            session["username"] = "ArunC"
            session["role"] = "admin"

        response = client.post(
            "/api/youtube/videos",
            json={
                "title": "Hello ArunCode",
                "description": "A first test video",
                "videoUrl": "",
                "thumbnailUrl": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["videos"]), 1)

    def test_youtube_normalizes_watch_urls_to_embed_urls(self):
        normalized = app_module.normalize_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(normalized, "https://www.youtube.com/embed/dQw4w9WgXcQ")

    def test_youtube_api_returns_json_for_unauthenticated_upload(self):
        client = app_module.app.test_client()
        response = client.post(
            "/api/youtube/videos",
            json={"title": "Guest upload", "description": ""},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])

    def test_youtube_upload_accepts_video_file(self):
        client = app_module.app.test_client()
        response = client.post(
            "/api/youtube/videos",
            data={
                "title": "ArunCode video",
                "description": "Created inside ArunCode",
                "video": (io.BytesIO(b"fake video bytes"), "demo.mp4"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["videos"][0]["videoUrl"].startswith("/uploads/videos/"))

    def test_youtube_comment_accepts_guest_comments(self):
        client = app_module.app.test_client()
        video_payload = client.post(
            "/api/youtube/videos",
            json={"title": "Guest video", "description": ""},
        )
        video_id = video_payload.get_json()["videos"][0]["id"]

        response = client.post(
            f"/api/youtube/videos/{video_id}/comment",
            json={"text": "Nice work!"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["video"]["comments"][-1]["text"], "Nice work!")


if __name__ == "__main__":
    unittest.main()
