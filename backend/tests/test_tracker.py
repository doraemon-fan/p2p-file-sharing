"""
Tests for Phase 2 Central Tracker Service & Peer Discovery:
- Peer registration
- Heartbeat keeping peer online
- Automatic reaper of expired peers
- File announcements with SHA-256
- File search by query
- Querying peers by file_id
"""
import os
import sys
import time
import shutil
import unittest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.tracker.server import app as tracker_app
from app.tracker.tracker_db import TrackerDatabase, TRACKER_DB_PATH

TEST_DB_PATH = os.path.join(BASE_DIR, "test_tracker.db")

class TestTrackerService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        # Use isolated test database
        cls.db = TrackerDatabase(TEST_DB_PATH)
        # Point tracker server db to test db
        import app.tracker.server as srv
        srv.tracker_db = cls.db
        cls.client = TestClient(tracker_app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_peer_registration_and_list(self):
        # Register Peer A
        payload = {
            "peer_id": "peer-alpha",
            "peer_name": "Alpha Node",
            "host": "192.168.1.100",
            "port": 5001
        }
        res = self.client.post("/peers/register", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "registered")

        # Register Peer B
        self.client.post("/peers/register", json={
            "peer_id": "peer-beta",
            "peer_name": "Beta Node",
            "host": "192.168.1.101",
            "port": 5002
        })

        # List peers
        list_res = self.client.get("/peers")
        self.assertEqual(list_res.status_code, 200)
        peers = list_res.json()["peers"]
        peer_ids = [p["peer_id"] for p in peers]
        self.assertIn("peer-alpha", peer_ids)
        self.assertIn("peer-beta", peer_ids)

    def test_heartbeat_and_expiration(self):
        # Ensure Peer A is registered
        self.client.post("/peers/register", json={
            "peer_id": "peer-alpha",
            "peer_name": "Alpha Node",
            "host": "192.168.1.100",
            "port": 5001
        })
        self.client.post("/peers/register", json={
            "peer_id": "peer-beta",
            "peer_name": "Beta Node",
            "host": "192.168.1.101",
            "port": 5002
        })

        # Heartbeat for Peer A succeeds
        res = self.client.post("/peers/heartbeat", json={"peer_id": "peer-alpha"})
        self.assertEqual(res.status_code, 200)

        # Heartbeat for nonexistent peer fails
        res_fail = self.client.post("/peers/heartbeat", json={"peer_id": "peer-ghost"})
        self.assertEqual(res_fail.status_code, 404)

        # Send heartbeat to Alpha
        self.client.post("/peers/heartbeat", json={"peer_id": "peer-alpha"})

        # Wait so Beta is older than 0.6s
        time.sleep(0.6)

        # Refresh Alpha's heartbeat so it is fresh (<0.1s)
        self.client.post("/peers/heartbeat", json={"peer_id": "peer-alpha"})
        
        # Beta (inactive for >0.6s) will be purged with timeout=0.4s, while Alpha remains fresh
        purged = self.db.purge_expired_peers(timeout_seconds=0.4)
        self.assertGreaterEqual(purged, 1)

        peers_after = self.client.get("/peers").json()["peers"]
        peer_ids = [p["peer_id"] for p in peers_after]
        self.assertIn("peer-alpha", peer_ids)
        self.assertNotIn("peer-beta", peer_ids)

    def test_file_announcement_and_search(self):
        # Register seeder
        self.client.post("/peers/register", json={
            "peer_id": "peer-seeder",
            "peer_name": "Seeder 1",
            "host": "10.0.0.5",
            "port": 5005
        })

        # Announce an ISO file
        file_payload = {
            "peer_id": "peer-seeder",
            "file_id": "hash-arch-2026",
            "filename": "archlinux-2026.iso",
            "file_size": 1200000000,
            "sha256": "abcdef1234567890abcdef1234567890"
        }
        res = self.client.post("/files/announce", json=file_payload)
        self.assertEqual(res.status_code, 200)

        # Search for "archlinux"
        search_res = self.client.get("/files/search?q=archlinux")
        self.assertEqual(search_res.status_code, 200)
        results = search_res.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "archlinux-2026.iso")
        self.assertEqual(results[0]["peer_name"], "Seeder 1")

        # Query peers by file_id
        peers_res = self.client.get("/files/hash-arch-2026/peers")
        self.assertEqual(peers_res.status_code, 200)
        self.assertEqual(peers_res.json()["peers"][0]["peer_id"], "peer-seeder")

if __name__ == "__main__":
    unittest.main()
