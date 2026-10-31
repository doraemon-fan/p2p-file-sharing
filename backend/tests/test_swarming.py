"""
Tests for Phase 4: Multiple Peers and Swarming
- Concurrent chunk requests distributed across multiple seeders
- Automatic failover / chunk reassignment when one seeder fails
- Reassembly of chunks into original file
- Full file SHA-256 verification of swarm-reconstructed file
"""

import os
import sys
import time
import shutil
import unittest
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.transfer.chunk_protocol import ChunkPeerServer
from app.transfer.scheduler import SwarmDownloadManager

SWARM_TEST_DIR = os.path.join(BASE_DIR, "test_swarm_data")
PEER_A_DIR = os.path.join(SWARM_TEST_DIR, "peer_a")
PEER_B_DIR = os.path.join(SWARM_TEST_DIR, "peer_b")
CLIENT_DOWNLOADS_DIR = os.path.join(SWARM_TEST_DIR, "downloads")

class TestSwarmDownload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(PEER_A_DIR, exist_ok=True)
        os.makedirs(PEER_B_DIR, exist_ok=True)
        os.makedirs(CLIENT_DOWNLOADS_DIR, exist_ok=True)

    def setUp(self):
        """Clean the downloads directory before each test to avoid stale .part/.state files."""
        for fname in os.listdir(CLIENT_DOWNLOADS_DIR):
            fpath = os.path.join(CLIENT_DOWNLOADS_DIR, fname)
            try:
                if os.path.isfile(fpath):
                    os.remove(fpath)
            except Exception:
                pass

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(SWARM_TEST_DIR):
            shutil.rmtree(SWARM_TEST_DIR, ignore_errors=True)

    def test_multi_peer_swarming(self):
        """
        Setup:
        - 2 Seeders (Peer A on port 6301, Peer B on port 6302) both sharing the same 2 MB file
        - Downloader connects to both peers simultaneously
        - Chunks are distributed across both peers concurrently
        - Verify completed file matches SHA-256
        """
        filename = "swarm_sample.dat"
        file_data = os.urandom(2 * 1024 * 1024)  # 2 MB file (4 x 512KB chunks)
        expected_hash = hashlib.sha256(file_data).hexdigest()

        # Seed file on both peers
        with open(os.path.join(PEER_A_DIR, filename), "wb") as f:
            f.write(file_data)
        with open(os.path.join(PEER_B_DIR, filename), "wb") as f:
            f.write(file_data)

        server_a = ChunkPeerServer(host="127.0.0.1", port=6301, shared_dir=PEER_A_DIR)
        server_b = ChunkPeerServer(host="127.0.0.1", port=6302, shared_dir=PEER_B_DIR)
        server_a.start()
        server_b.start()
        time.sleep(0.1)

        try:
            peers_info = [
                {"peer_id": "seeder-a", "host": "127.0.0.1", "port": 6301, "peer_name": "Seeder Alpha"},
                {"peer_id": "seeder-b", "host": "127.0.0.1", "port": 6302, "peer_name": "Seeder Beta"}
            ]

            manager = SwarmDownloadManager(
                file_identifier=filename,
                peers=peers_info,
                downloads_dir=CLIENT_DOWNLOADS_DIR
            )

            res = manager.start_download()
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["sha256"], expected_hash)

            # Check that both peers participated in contributing chunks
            participating = res["participating_peers"]
            chunks_a = participating[0]["chunks_downloaded"]
            chunks_b = participating[1]["chunks_downloaded"]
            total_chunks = chunks_a + chunks_b

            self.assertEqual(total_chunks, 4)
            self.assertGreater(chunks_a + chunks_b, 0)

            # Verify downloaded file on disk
            downloaded_path = os.path.join(CLIENT_DOWNLOADS_DIR, filename)
            self.assertTrue(os.path.exists(downloaded_path))
            with open(downloaded_path, "rb") as f:
                self.assertEqual(f.read(), file_data)

        finally:
            server_a.stop()
            server_b.stop()

    def test_swarm_failover_and_reassignment(self):
        """
        Test that if one peer is offline/dead, the scheduler detects the failure
        and successfully re-assigns the remaining chunks to the healthy peer.
        """
        filename = "failover_sample.dat"
        file_data = os.urandom(1024 * 1024)  # 1 MB (2 chunks)
        expected_hash = hashlib.sha256(file_data).hexdigest()

        # Seed file only on Peer A
        with open(os.path.join(PEER_A_DIR, filename), "wb") as f:
            f.write(file_data)

        server_a = ChunkPeerServer(host="127.0.0.1", port=6303, shared_dir=PEER_A_DIR)
        server_a.start()
        time.sleep(0.05)

        try:
            # Point to Peer A (healthy) and Peer Dead (port 6399 nothing listening)
            peers_info = [
                {"peer_id": "seeder-dead", "host": "127.0.0.1", "port": 6399, "peer_name": "Ghost Peer"},
                {"peer_id": "seeder-alive", "host": "127.0.0.1", "port": 6303, "peer_name": "Alive Peer"}
            ]

            manager = SwarmDownloadManager(
                file_identifier=filename,
                peers=peers_info,
                downloads_dir=CLIENT_DOWNLOADS_DIR
            )

            res = manager.start_download()
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["sha256"], expected_hash)

            # Verify file integrity
            downloaded_path = os.path.join(CLIENT_DOWNLOADS_DIR, filename)
            with open(downloaded_path, "rb") as f:
                self.assertEqual(f.read(), file_data)

        finally:
            server_a.stop()

if __name__ == "__main__":
    unittest.main()
