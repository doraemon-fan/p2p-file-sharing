import os
import socket
import time
import hashlib
from typing import Optional, Callable, Dict, Any
from .protocol import (
    DEFAULT_BUFFER_SIZE,
    send_json,
    calculate_file_hash,
    receive_json
)

class FileSender:
    """
    Robust sender for transmitting files directly to a receiver over TCP.
    Supports progress callback, SHA-256 verification, and response handshakes.
    """

    def __init__(self, host: str, port: int, buffer_size: int = DEFAULT_BUFFER_SIZE):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size

    def send_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, int, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Send a file to the configured host and port.
        progress_callback receives (bytes_sent, total_bytes, speed_bytes_per_sec).
        Returns receiver confirmation and transmission stats.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        # 1. Calculate SHA-256 integrity hash before sending
        sha256_hash = calculate_file_hash(file_path, self.buffer_size)

        metadata = {
            "filename": filename,
            "size": file_size,
            "sha256": sha256_hash,
            "timestamp": time.time()
        }

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        try:
            client_socket.connect((self.host, self.port))

            # 2. Send metadata header
            send_json(client_socket, metadata)

            # 3. Stream file chunks
            bytes_sent = 0
            start_time = time.time()
            last_progress_time = start_time

            with open(file_path, "rb") as f:
                while bytes_sent < file_size:
                    chunk = f.read(self.buffer_size)
                    if not chunk:
                        break
                    client_socket.sendall(chunk)
                    bytes_sent += len(chunk)

                    now = time.time()
                    if progress_callback and (now - last_progress_time >= 0.05 or bytes_sent == file_size):
                        elapsed = max(now - start_time, 0.0001)
                        speed = bytes_sent / elapsed
                        progress_callback(bytes_sent, file_size, speed)
                        last_progress_time = now

            # 4. Wait for receiver verification acknowledgment
            response = {}
            try:
                # If receiver sends an ACK frame
                client_socket.settimeout(10.0)
                response = receive_json(client_socket)
            except Exception:
                # Fallback if peer closes without ack
                response = {"status": "completed_unacknowledged"}

            total_time = max(time.time() - start_time, 0.001)
            return {
                "status": "success",
                "filename": filename,
                "file_size": file_size,
                "sha256": sha256_hash,
                "duration_seconds": total_time,
                "average_speed_mbps": (file_size / total_time) / (1024 * 1024),
                "receiver_ack": response
            }

        finally:
            try:
                client_socket.close()
            except Exception:
                pass
