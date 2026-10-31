"""
Tests for Phase 1 P2P File Transfer Protocol and Implementation.
Covers:
- TCP connection establishment
- Metadata & file-size transmission
- Small, medium, and empty (0-byte) files
- Large binary files with high throughput
- SHA-256 integrity verification
- Safe filename sanitization (preventing directory traversal)
- Overwrite avoidance (collision numbering)
- Interrupted connection handling & cleanup
"""

import os
import sys
import time
import shutil
import socket
import threading
import unittest
import hashlib

# Ensure backend is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.networking import FileSender, FileReceiver, calculate_file_hash, sanitize_filename

TEST_PORT = 6123
TEMP_DIR = os.path.join(BASE_DIR, "temp_test_data")
DOWNLOADS_DIR = os.path.join(TEMP_DIR, "downloads")

class TestPhase1Networking(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.makedirs(TEMP_DIR, exist_ok=True)
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)

    def setUp(self):
        # Clean downloads dir between tests
        for f in os.listdir(DOWNLOADS_DIR):
            p = os.path.join(DOWNLOADS_DIR, f)
            if os.path.isfile(p):
                os.remove(p)

    def _transfer_file_helper(self, src_file: str, port: int = TEST_PORT):
        receiver = FileReceiver(host="127.0.0.1", port=port, destination_dir=DOWNLOADS_DIR)
        receiver.start_listening()

        rec_result = {}
        rec_error = []

        def run_receiver():
            try:
                rec_result["data"] = receiver.accept_one_file(timeout=5.0)
            except Exception as e:
                rec_error.append(e)
            finally:
                receiver.stop()

        t = threading.Thread(target=run_receiver)
        t.start()
        time.sleep(0.05)

        sender = FileSender(host="127.0.0.1", port=port)
        send_result = sender.send_file(src_file)

        t.join(timeout=5.0)

        if rec_error:
            raise rec_error[0]

        return send_result, rec_result.get("data")

    def test_small_text_file(self):
        """Test sending a small text file."""
        src = os.path.join(TEMP_DIR, "sample.txt")
        content = b"P2P Transfer Test Content - " + os.urandom(128)
        with open(src, "wb") as f:
            f.write(content)

        send_res, rec_res = self._transfer_file_helper(src, port=6124)
        
        self.assertEqual(send_res["sha256"], rec_res["sha256"])
        self.assertEqual(os.path.getsize(rec_res["file_path"]), len(content))
        with open(rec_res["file_path"], "rb") as f:
            self.assertEqual(f.read(), content)

    def test_empty_file(self):
        """Test sending an empty (0-byte) file."""
        src = os.path.join(TEMP_DIR, "empty.bin")
        with open(src, "wb") as f:
            pass

        send_res, rec_res = self._transfer_file_helper(src, port=6125)

        self.assertEqual(send_res["file_size"], 0)
        self.assertEqual(rec_res["file_size"], 0)
        self.assertEqual(os.path.getsize(rec_res["file_path"]), 0)
        self.assertEqual(send_res["sha256"], rec_res["sha256"])

    def test_medium_binary_file_with_sha256(self):
        """Test sending a 5MB random binary file with strict SHA-256 verification."""
        src = os.path.join(TEMP_DIR, "binary_5mb.bin")
        chunk_pattern = os.urandom(64 * 1024)
        with open(src, "wb") as f:
            for _ in range(80):  # 5 MB
                f.write(chunk_pattern)

        expected_hash = calculate_file_hash(src)
        send_res, rec_res = self._transfer_file_helper(src, port=6126)

        self.assertEqual(rec_res["sha256"], expected_hash)
        self.assertEqual(send_res["sha256"], expected_hash)
        self.assertEqual(os.path.getsize(rec_res["file_path"]), 5 * 1024 * 1024)

    def test_safe_filename_sanitization(self):
        """Test that directory traversal attacks or unsafe characters in filenames are sanitized."""
        self.assertEqual(sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("..\\..\\Windows\\System32\\calc.exe"), "calc.exe")
        self.assertEqual(sanitize_filename("invalid:name*?.txt"), "invalid_name__.txt")
        self.assertEqual(sanitize_filename(""), "unnamed_transfer")

    def test_overwrite_avoidance(self):
        """Test that sending the same file twice does not overwrite the existing file."""
        src = os.path.join(TEMP_DIR, "doc.txt")
        with open(src, "wb") as f:
            f.write(b"Version 1")

        send1, rec1 = self._transfer_file_helper(src, port=6127)
        self.assertTrue(os.path.exists(rec1["file_path"]))
        self.assertEqual(os.path.basename(rec1["file_path"]), "doc.txt")

        # Send again
        send2, rec2 = self._transfer_file_helper(src, port=6128)
        self.assertTrue(os.path.exists(rec2["file_path"]))
        self.assertEqual(os.path.basename(rec2["file_path"]), "doc (1).txt")
        self.assertTrue(os.path.exists(rec1["file_path"]))

    def test_interrupted_transfer_cleanup(self):
        """Test that if a sender aborts midway, the .part file is purged and no corrupt file is retained."""
        src = os.path.join(TEMP_DIR, "to_abort.bin")
        with open(src, "wb") as f:
            f.write(b"X" * 1024 * 1024)  # 1 MB

        receiver = FileReceiver(host="127.0.0.1", port=6129, destination_dir=DOWNLOADS_DIR)
        receiver.start_listening()

        rec_error = []

        def run_receiver():
            try:
                receiver.accept_one_file(timeout=3.0)
            except Exception as e:
                rec_error.append(e)
            finally:
                receiver.stop()

        t = threading.Thread(target=run_receiver)
        t.start()
        time.sleep(0.05)

        # Intentionally connect, send metadata claiming 1MB, but send only 100 bytes and close
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 6129))
        from app.networking.protocol import send_json
        send_json(s, {"filename": "to_abort.bin", "size": 1024 * 1024, "sha256": "fakehash"})
        s.sendall(b"partial byte stream")
        s.close()

        t.join(timeout=3.0)
        self.assertTrue(len(rec_error) > 0)
        self.assertIsInstance(rec_error[0], ConnectionError)

        # Verify no .part file or corrupt file remains
        files_in_downloads = os.listdir(DOWNLOADS_DIR)
        self.assertEqual(len(files_in_downloads), 0)

if __name__ == "__main__":
    unittest.main()
