"""
End-to-End integration test for FastAPI backend + TCP socket transfer + SQLite history
"""
import os
import sys
import time
import shutil
import unittest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.main import app
from app.config import config
from app.transfer.manager import transfer_manager
from app.database.db import get_history

TEST_SHARED = os.path.join(BASE_DIR, "test_shared")
TEST_DOWNLOADS = os.path.join(BASE_DIR, "test_downloads")

class TestBackendApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(TEST_SHARED, exist_ok=True)
        os.makedirs(TEST_DOWNLOADS, exist_ok=True)
        config.shared_dir = TEST_SHARED
        config.downloads_dir = TEST_DOWNLOADS
        config.p2p_port = 6188
        transfer_manager.start_receiver_daemon()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        transfer_manager.stop()
        shutil.rmtree(TEST_SHARED, ignore_errors=True)
        shutil.rmtree(TEST_DOWNLOADS, ignore_errors=True)

    def setUp(self):
        self.client = TestClient(app)

    def test_status_endpoint(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("peer_id", data)
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["p2p_port"], 6188)

    def test_send_and_receive_via_api(self):
        # Create a test file in shared dir
        test_file = os.path.join(TEST_SHARED, "api_test.txt")
        content = b"Integration test payload for P2P API with SHA-256"
        with open(test_file, "wb") as f:
            f.write(content)

        # Trigger send via API to our own receiver daemon
        send_req = {
            "file_path": test_file,
            "peer_host": "127.0.0.1",
            "peer_port": 6188
        }
        resp = self.client.post("/api/send", json=send_req)
        self.assertEqual(resp.status_code, 200)
        transfer_id = resp.json()["transfer_id"]
        self.assertTrue(transfer_id.startswith("send-"))

        # Wait for transfer completion
        completed = False
        for _ in range(30):
            time.sleep(0.1)
            history = get_history(limit=5)
            if any(h["filename"] == "api_test.txt" and h["status"] == "completed" for h in history):
                completed = True
                break

        self.assertTrue(completed, "Transfer did not complete in time")

        # Verify saved file in downloads
        downloaded_file = os.path.join(TEST_DOWNLOADS, "api_test.txt")
        self.assertTrue(os.path.exists(downloaded_file))
        with open(downloaded_file, "rb") as f:
            self.assertEqual(f.read(), content)

if __name__ == "__main__":
    unittest.main()
