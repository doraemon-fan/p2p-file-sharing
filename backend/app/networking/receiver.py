import os
import socket
import time
import hashlib
from typing import Optional, Callable, Dict, Any
from .protocol import (
    DEFAULT_BUFFER_SIZE,
    receive_json,
    send_json,
    get_unique_destination_path
)

class FileReceiver:
    """
    Robust receiver that listens on TCP, receives file metadata, streams chunks
    into a temporary .part file, calculates SHA-256 on the fly, verifies integrity,
    and atomically commits the file to disk without accidental overwrites.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5000, destination_dir: str = "downloads"):
        self.host = host
        self.port = port
        self.destination_dir = destination_dir
        self.is_running = False
        self._server_socket: Optional[socket.socket] = None

    def start_listening(self) -> None:
        """Bind and start listening on socket."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self.is_running = True

    def stop(self) -> None:
        """Stop listening and close socket."""
        self.is_running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

    def accept_one_file(
        self,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Accept a single incoming connection, receive one file, verify integrity,
        send ACK, and return transfer summary.
        """
        if not self._server_socket:
            self.start_listening()

        if timeout:
            self._server_socket.settimeout(timeout)

        connection, address = self._server_socket.accept()
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        part_path = None
        target_path = None

        try:
            # 1. Receive metadata
            metadata = receive_json(connection)
            filename = metadata.get("filename", "unnamed_transfer")
            file_size = int(metadata.get("size", 0))
            expected_sha256 = metadata.get("sha256")

            # 2. Determine safe destination path
            target_path = get_unique_destination_path(self.destination_dir, filename)
            part_path = target_path + ".part"

            # 3. Stream chunks into .part file and calculate SHA-256 simultaneously
            hasher = hashlib.sha256()
            received = 0
            start_time = time.time()
            last_progress_time = start_time

            with open(part_path, "wb") as f:
                while received < file_size:
                    remaining = file_size - received
                    chunk_size = min(DEFAULT_BUFFER_SIZE, remaining)
                    chunk = connection.recv(chunk_size)
                    if not chunk:
                        raise ConnectionError("Connection closed prematurely by sender")

                    f.write(chunk)
                    hasher.update(chunk)
                    received += len(chunk)

                    now = time.time()
                    if progress_callback and (now - last_progress_time >= 0.05 or received == file_size):
                        elapsed = max(now - start_time, 0.0001)
                        speed = received / elapsed
                        progress_callback(received, file_size, speed)
                        last_progress_time = now

            # 4. Integrity check
            calculated_sha256 = hasher.hexdigest()
            if expected_sha256 and calculated_sha256.lower() != expected_sha256.lower():
                # Hash mismatch! Remove partial corrupted file
                if os.path.exists(part_path):
                    os.remove(part_path)
                ack = {
                    "status": "error",
                    "message": "SHA-256 verification failed",
                    "expected": expected_sha256,
                    "actual": calculated_sha256
                }
                try:
                    send_json(connection, ack)
                except Exception:
                    pass
                raise ValueError(
                    f"Checksum mismatch! Expected {expected_sha256}, calculated {calculated_sha256}"
                )

            # 5. Atomic commit: rename .part to target_path
            if os.path.exists(target_path):
                # Extra guard against collision
                target_path = get_unique_destination_path(self.destination_dir, filename)
            os.rename(part_path, target_path)

            total_time = max(time.time() - start_time, 0.001)
            ack = {
                "status": "success",
                "message": "File verified and saved",
                "sha256": calculated_sha256,
                "saved_to": target_path
            }
            try:
                send_json(connection, ack)
            except Exception:
                pass

            return {
                "status": "success",
                "sender_address": address,
                "filename": os.path.basename(target_path),
                "file_path": target_path,
                "file_size": file_size,
                "sha256": calculated_sha256,
                "duration_seconds": total_time,
                "average_speed_mbps": (file_size / total_time) / (1024 * 1024)
            }

        except Exception as e:
            # Clean up .part file on interruption or failure
            if part_path and os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass
            raise e

        finally:
            try:
                connection.close()
            except Exception:
                pass
