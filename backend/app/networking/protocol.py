import os
import re
import socket
import json
import hashlib
from typing import Dict, Any, Tuple

DEFAULT_BUFFER_SIZE = 64 * 1024  # 64 KB buffer for high-throughput TCP streaming

def receive_exactly(connection: socket.socket, number_of_bytes: int) -> bytes:
    """
    Reliably receive exactly number_of_bytes from a socket.
    Raises ConnectionError if connection closes prematurely.
    """
    data = bytearray()
    while len(data) < number_of_bytes:
        chunk = connection.recv(number_of_bytes - len(data))
        if not chunk:
            raise ConnectionError(
                f"Connection closed early: expected {number_of_bytes} bytes, got {len(data)}"
            )
        data.extend(chunk)
    return bytes(data)

def send_frame(connection: socket.socket, payload: bytes) -> None:
    """
    Send a 4-byte big-endian length-prefixed frame.
    """
    length_bytes = len(payload).to_bytes(4, byteorder="big")
    connection.sendall(length_bytes)
    if payload:
        connection.sendall(payload)

def receive_frame(connection: socket.socket) -> bytes:
    """
    Receive a 4-byte big-endian length-prefixed frame.
    """
    length_bytes = receive_exactly(connection, 4)
    length = int.from_bytes(length_bytes, byteorder="big")
    if length == 0:
        return b""
    return receive_exactly(connection, length)

def send_json(connection: socket.socket, data: Dict[str, Any]) -> None:
    """
    Serialize dictionary to JSON and transmit as a length-prefixed frame.
    """
    json_bytes = json.dumps(data).encode("utf-8")
    send_frame(connection, json_bytes)

def receive_json(connection: socket.socket) -> Dict[str, Any]:
    """
    Receive length-prefixed frame and deserialize from JSON.
    """
    json_bytes = receive_frame(connection)
    return json.loads(json_bytes.decode("utf-8"))

def calculate_file_hash(file_path: str, buffer_size: int = DEFAULT_BUFFER_SIZE) -> str:
    """
    Compute SHA-256 hash of a file on disk without loading entire file in memory.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(buffer_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def sanitize_filename(filename: str) -> str:
    """
    Strip path traversal components (e.g., ../, /etc, C:\\) and unsafe characters.
    """
    # Extract only the base name
    clean_name = os.path.basename(filename)
    # Remove control characters and non-printable or forbidden filesystem chars
    clean_name = re.sub(r'[\\/*?:"<>|]', '_', clean_name)
    clean_name = clean_name.strip('. ')
    if not clean_name:
        clean_name = "unnamed_transfer"
    return clean_name

def get_unique_destination_path(destination_dir: str, filename: str) -> str:
    """
    Return a collision-free file path in destination_dir to prevent accidental overwrites.
    Appends (1), (2), etc. if the file already exists.
    """
    clean_filename = sanitize_filename(filename)
    os.makedirs(destination_dir, exist_ok=True)
    base, ext = os.path.splitext(clean_filename)
    
    candidate = os.path.join(destination_dir, clean_filename)
    counter = 1
    while os.path.exists(candidate) or os.path.exists(candidate + ".part"):
        candidate = os.path.join(destination_dir, f"{base} ({counter}){ext}")
        counter += 1
    return candidate
