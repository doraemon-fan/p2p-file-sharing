import os
import socket
import time
import threading
from typing import Dict, Any, Optional, Callable, Set
from app.networking.protocol import (
    send_json,
    receive_json,
    send_frame,
    receive_frame,
    get_unique_destination_path
)
from .chunk_manager import (
    FileManifest,
    generate_manifest,
    read_chunk,
    write_chunk,
    verify_chunk,
    verify_whole_file
)
from .session import ResumableDownloadSession

class ChunkP2PProtocol:
    """
    Message types exchanged between peers:
    1. 'GET_MANIFEST': {'type': 'GET_MANIFEST', 'file_identifier': str}
       -> returns manifest dict
    2. 'GET_CHUNK': {'type': 'GET_CHUNK', 'file_identifier': str, 'chunk_index': int}
       -> returns 4-byte index + raw chunk frame
    3. 'CHUNK_DATA': Header frame {'type': 'CHUNK_DATA', 'chunk_index': int, 'size': int, 'sha256': str} followed by chunk bytes frame
    """
    MSG_GET_MANIFEST = "GET_MANIFEST"
    MSG_MANIFEST = "MANIFEST"
    MSG_GET_CHUNK = "GET_CHUNK"
    MSG_CHUNK_DATA = "CHUNK_DATA"
    MSG_ERROR = "ERROR"

class ChunkPeerServer:
    """
    Daemon listening for chunk and manifest requests from other peers.
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 5001, shared_dir: str = "shared"):
        self.host = host
        self.port = port
        self.shared_dir = shared_dir
        self.is_running = False
        self._server_sock: Optional[socket.socket] = None
        self._manifest_cache: Dict[str, FileManifest] = {}

    def _find_file_path(self, identifier: str) -> Optional[str]:
        """Find file in shared directory by filename or hash prefix."""
        if not os.path.exists(self.shared_dir):
            return None
        for f in os.listdir(self.shared_dir):
            p = os.path.join(self.shared_dir, f)
            if os.path.isfile(p):
                if f == identifier or f.startswith(identifier):
                    return p
        return None

    def _get_or_create_manifest(self, file_path: str) -> FileManifest:
        if file_path not in self._manifest_cache:
            self._manifest_cache[file_path] = generate_manifest(file_path)
        return self._manifest_cache[file_path]

    def start(self):
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(10)
        self.is_running = True

        def accept_loop():
            while self.is_running:
                try:
                    conn, addr = self._server_sock.accept()
                    threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
                except Exception:
                    if not self.is_running:
                        break
                    time.sleep(0.1)

        threading.Thread(target=accept_loop, daemon=True).start()

    def _handle_client(self, conn: socket.socket, addr):
        try:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            while True:
                try:
                    msg = receive_json(conn)
                except Exception:
                    break

                msg_type = msg.get("type")
                file_id = msg.get("file_identifier")
                file_path = self._find_file_path(file_id)

                if not file_path:
                    send_json(conn, {"type": ChunkP2PProtocol.MSG_ERROR, "error": "File not found"})
                    continue

                if msg_type == ChunkP2PProtocol.MSG_GET_MANIFEST:
                    manifest = self._get_or_create_manifest(file_path)
                    send_json(conn, {
                        "type": ChunkP2PProtocol.MSG_MANIFEST,
                        "manifest": manifest.to_dict()
                    })

                elif msg_type == ChunkP2PProtocol.MSG_GET_CHUNK:
                    chunk_index = msg.get("chunk_index")
                    manifest = self._get_or_create_manifest(file_path)
                    if 0 <= chunk_index < manifest.total_chunks:
                        chunk_info = manifest.chunks[chunk_index]
                        data = read_chunk(file_path, chunk_info.offset, chunk_info.size)
                        
                        # Send chunk header frame
                        send_json(conn, {
                            "type": ChunkP2PProtocol.MSG_CHUNK_DATA,
                            "chunk_index": chunk_index,
                            "size": len(data),
                            "sha256": chunk_info.sha256
                        })
                        # Send payload frame
                        send_frame(conn, data)
                    else:
                        send_json(conn, {"type": ChunkP2PProtocol.MSG_ERROR, "error": "Invalid chunk index"})
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def stop(self):
        self.is_running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None

class ChunkClientDownloader:
    """
    Downloads a file from a peer using chunked, verifiable, and resumable transfers.
    """
    def __init__(self, peer_host: str, peer_port: int, downloads_dir: str = "downloads"):
        self.peer_host = peer_host
        self.peer_port = peer_port
        self.downloads_dir = downloads_dir

    def fetch_manifest(self, file_identifier: str) -> FileManifest:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.peer_host, self.peer_port))
        try:
            send_json(sock, {
                "type": ChunkP2PProtocol.MSG_GET_MANIFEST,
                "file_identifier": file_identifier
            })
            resp = receive_json(sock)
            if resp.get("type") == ChunkP2PProtocol.MSG_ERROR:
                raise ValueError(resp.get("error", "Failed to fetch manifest"))
            return FileManifest.from_dict(resp["manifest"])
        finally:
            sock.close()

    def download_file(
        self,
        file_identifier: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        max_chunk_retries: int = 3
    ) -> Dict[str, Any]:
        # 1. Fetch manifest
        manifest = self.fetch_manifest(file_identifier)
        
        # 2. Determine target destination and setup resumable session
        target_path = os.path.join(self.downloads_dir, manifest.filename)
        session = ResumableDownloadSession(target_path, manifest)

        # 3. Download missing chunks with automatic retries
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((self.peer_host, self.peer_port))

        try:
            missing = sorted(list(session.get_missing_chunks()))
            for chunk_idx in missing:
                retries = 0
                chunk_success = False

                while retries < max_chunk_retries and not chunk_success:
                    try:
                        # Request chunk
                        send_json(sock, {
                            "type": ChunkP2PProtocol.MSG_GET_CHUNK,
                            "file_identifier": file_identifier,
                            "chunk_index": chunk_idx
                        })

                        # Receive header and raw chunk frame
                        header = receive_json(sock)
                        if header.get("type") == ChunkP2PProtocol.MSG_ERROR:
                            raise ValueError(header.get("error"))

                        chunk_bytes = receive_frame(sock)

                        # Verify chunk hash
                        chunk_info = manifest.chunks[chunk_idx]
                        if not verify_chunk(chunk_bytes, chunk_info.sha256):
                            raise ValueError(f"Chunk {chunk_idx} checksum verification failed!")

                        # Write to sparse part file
                        write_chunk(session.part_path, chunk_info.offset, chunk_bytes)
                        session.mark_chunk_completed(chunk_idx)
                        chunk_success = True

                        if progress_callback:
                            progress_callback(session.get_progress_info())

                    except Exception as e:
                        retries += 1
                        session.mark_chunk_failed(chunk_idx)
                        if retries >= max_chunk_retries:
                            raise RuntimeError(f"Chunk {chunk_idx} failed after {retries} attempts: {e}")
                        time.sleep(0.1)

            # 4. Whole-file verification
            if not session.is_complete():
                raise RuntimeError("Download completed but not all chunks are present!")

            if not verify_whole_file(session.part_path, manifest.file_sha256):
                raise ValueError("Whole-file SHA-256 verification failed on reconstructed file!")

            # 5. Atomically commit part file to final destination
            if os.path.exists(target_path):
                # Unique target if duplicate
                target_path = get_unique_destination_path(self.downloads_dir, manifest.filename)
            os.rename(session.part_path, target_path)
            session.cleanup_state()

            return {
                "status": "success",
                "filename": manifest.filename,
                "saved_to": target_path,
                "file_size": manifest.file_size,
                "total_chunks": manifest.total_chunks,
                "sha256": manifest.file_sha256
            }

        finally:
            try:
                sock.close()
            except Exception:
                pass
