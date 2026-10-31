import os
import time
import socket
import threading
import queue
from typing import List, Dict, Any, Optional, Set, Callable
from app.networking.protocol import (
    send_json,
    receive_json,
    send_frame,
    receive_frame,
    get_unique_destination_path
)
from app.transfer.chunk_manager import (
    FileManifest,
    write_chunk,
    verify_chunk,
    verify_whole_file
)
from app.transfer.session import ResumableDownloadSession
from app.transfer.chunk_protocol import ChunkP2PProtocol

class PeerEndpoint:
    """Represents a candidate peer in the swarm offering the requested file."""
    def __init__(self, peer_id: str, host: str, port: int, peer_name: str = ""):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.peer_name = peer_name
        self.chunks_downloaded = 0
        self.bytes_downloaded = 0
        self.active_connections = 0
        self.failed_requests = 0
        self.is_alive = True
        self.last_latency = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "peer_name": self.peer_name,
            "host": self.host,
            "port": self.port,
            "chunks_downloaded": self.chunks_downloaded,
            "bytes_downloaded": self.bytes_downloaded,
            "failed_requests": self.failed_requests,
            "is_alive": self.is_alive
        }

class SwarmDownloadManager:
    """
    Coordinates multi-peer concurrent swarming downloads:
    1. Obtains file manifest from available peer.
    2. Maintains a shared work-queue of missing chunks.
    3. Spawns concurrent worker threads across all participating peers.
    4. Detects disconnected or slow peers, re-enqueues unfinished chunks to remaining peers.
    5. Validates received chunk SHA-256 hashes.
    6. Reconstructs file in sparse part file.
    7. Verifies final whole-file SHA-256 integrity and atomically commits to disk.
    """
    def __init__(
        self,
        file_identifier: str,
        peers: List[Dict[str, Any]],
        downloads_dir: str = "downloads",
        max_workers_per_peer: int = 1,
        timeout: float = 120.0
    ):
        self.file_identifier = file_identifier
        self.downloads_dir = downloads_dir
        self.peers = [
            PeerEndpoint(
                peer_id=p["peer_id"],
                host=p["host"],
                port=p.get("chunk_port", p.get("port", 5002)),
                peer_name=p.get("peer_name", p["peer_id"])
            )
            for p in peers
        ]
        self.max_workers_per_peer = max_workers_per_peer
        self.timeout = timeout
        self.manifest: Optional[FileManifest] = None
        self.session: Optional[ResumableDownloadSession] = None
        self.chunk_queue: queue.Queue = queue.Queue()
        self.active = False
        self.lock = threading.Lock()
        self.start_time = 0.0
        # Event set when download is fully done (session.is_complete()) or aborted
        self._done_event = threading.Event()

    def _fetch_manifest_from_swarm(self) -> FileManifest:
        """Query peers until one provides the file manifest."""
        errors = []
        for p in self.peers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((p.host, p.port))
                send_json(sock, {
                    "type": ChunkP2PProtocol.MSG_GET_MANIFEST,
                    "file_identifier": self.file_identifier
                })
                resp = receive_json(sock)
                sock.close()
                if resp.get("type") == ChunkP2PProtocol.MSG_MANIFEST:
                    return FileManifest.from_dict(resp["manifest"])
            except Exception as e:
                errors.append(f"{p.peer_id} ({p.host}:{p.port}): {e}")

        raise RuntimeError(f"Could not fetch manifest from any peer in swarm: {'; '.join(errors)}")

    def _all_peers_dead(self) -> bool:
        return all(not p.is_alive for p in self.peers)

    def start_download(
        self,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        self.start_time = time.time()
        self.manifest = self._fetch_manifest_from_swarm()

        target_path = os.path.join(self.downloads_dir, self.manifest.filename)
        self.session = ResumableDownloadSession(target_path, self.manifest)

        # Enqueue missing chunks
        missing_chunks = sorted(list(self.session.get_missing_chunks()))
        for c_idx in missing_chunks:
            self.chunk_queue.put(c_idx)

        self.active = True
        self._done_event.clear()
        workers = []

        # Launch workers for each peer
        for peer in self.peers:
            for _ in range(self.max_workers_per_peer):
                t = threading.Thread(
                    target=self._peer_worker_loop,
                    args=(peer, progress_callback),
                    daemon=True
                )
                workers.append(t)
                t.start()

        # Wait for completion, all-peers-dead, or timeout
        deadline = time.time() + self.timeout
        while True:
            # Check if session is complete
            with self.lock:
                done = self.session.is_complete()
            if done:
                break

            # Check if all peers are dead (no worker can make progress)
            if self._all_peers_dead():
                self.active = False
                break

            # Overall timeout guard
            if time.time() > deadline:
                self.active = False
                break

            time.sleep(0.05)

        self.active = False

        # Wait for worker threads to finish (with timeout)
        for t in workers:
            t.join(timeout=2.0)

        # Whole-file integrity check
        if not self.session.is_complete():
            raise RuntimeError(
                f"Swarm download incomplete: {len(self.session.get_missing_chunks())} chunks remaining"
            )

        if not verify_whole_file(self.session.part_path, self.manifest.file_sha256):
            raise ValueError("Swarm reconstructed file SHA-256 verification failed!")

        # Commit .part to final file
        final_path = target_path
        if os.path.exists(target_path):
            final_path = get_unique_destination_path(self.downloads_dir, self.manifest.filename)
        os.rename(self.session.part_path, final_path)
        self.session.cleanup_state()

        elapsed = max(time.time() - self.start_time, 0.001)
        return {
            "status": "success",
            "filename": self.manifest.filename,
            "saved_to": final_path,
            "file_size": self.manifest.file_size,
            "total_chunks": self.manifest.total_chunks,
            "sha256": self.manifest.file_sha256,
            "duration": elapsed,
            "average_speed_mbps": (self.manifest.file_size / elapsed) / (1024 * 1024),
            "participating_peers": [p.to_dict() for p in self.peers]
        }

    def _peer_worker_loop(
        self,
        peer: PeerEndpoint,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]]
    ):
        sock = None
        while self.active:
            # Exit early if session already complete
            with self.lock:
                if self.session and self.session.is_complete():
                    break

            try:
                # Try to get chunk from queue without blocking indefinitely
                try:
                    chunk_idx = self.chunk_queue.get(timeout=0.3)
                except queue.Empty:
                    # Queue is empty — check if we're done or should keep waiting
                    with self.lock:
                        if self.session and self.session.is_complete():
                            break
                    # Not complete, keep looping (another peer may re-enqueue)
                    continue

                # Double-check if this chunk was already completed by another worker
                with self.lock:
                    already_done = (
                        self.session is not None
                        and chunk_idx not in self.session.get_missing_chunks()
                    )
                if already_done:
                    # No actual work needed; just mark done
                    self.chunk_queue.task_done()
                    continue

                # Ensure connection
                if sock is None:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        sock.settimeout(5.0)
                        sock.connect((peer.host, peer.port))
                    except Exception as conn_err:
                        # Connection failed — re-enqueue and increment failure count
                        sock = None
                        peer.failed_requests += 1
                        self.chunk_queue.task_done()
                        if peer.failed_requests >= 3:
                            peer.is_alive = False
                            # Put chunk back for other workers; drain remaining from queue too
                            self.chunk_queue.put(chunk_idx)
                            break
                        self.chunk_queue.put(chunk_idx)
                        time.sleep(0.2)
                        continue

                # Request chunk
                t0 = time.time()
                send_json(sock, {
                    "type": ChunkP2PProtocol.MSG_GET_CHUNK,
                    "file_identifier": self.file_identifier,
                    "chunk_index": chunk_idx
                })

                header = receive_json(sock)
                if header.get("type") == ChunkP2PProtocol.MSG_ERROR:
                    raise ValueError(header.get("error", "Peer error"))

                chunk_bytes = receive_frame(sock)
                chunk_info = self.manifest.chunks[chunk_idx]

                # Verify SHA-256 of received chunk
                if not verify_chunk(chunk_bytes, chunk_info.sha256):
                    raise ValueError(f"Chunk {chunk_idx} checksum failed from {peer.peer_id}")

                # Sparse write with thread safety
                with self.lock:
                    write_chunk(self.session.part_path, chunk_info.offset, chunk_bytes)
                    self.session.mark_chunk_completed(chunk_idx)
                    peer.chunks_downloaded += 1
                    peer.bytes_downloaded += len(chunk_bytes)
                    peer.last_latency = time.time() - t0

                self.chunk_queue.task_done()

                if progress_callback:
                    info = self.get_swarm_status()
                    progress_callback(info)

            except Exception as e:
                # If error occurred with chunk, re-enqueue for other peers to pick up!
                peer.failed_requests += 1
                try:
                    if sock:
                        sock.close()
                except Exception:
                    pass
                sock = None

                # Re-enqueue chunk
                self.chunk_queue.task_done()
                self.chunk_queue.put(chunk_idx)

                # If peer is repeatedly failing, mark dead and stop this worker
                if peer.failed_requests >= 3:
                    peer.is_alive = False
                    break
                time.sleep(0.2)

        if sock:
            try:
                sock.close()
            except Exception:
                pass

    def get_swarm_status(self) -> Dict[str, Any]:
        with self.lock:
            prog = self.session.get_progress_info() if self.session else {}
            elapsed = max(time.time() - self.start_time, 0.001)
            downloaded = prog.get("downloaded_bytes", 0)
            return {
                "file_identifier": self.file_identifier,
                "progress_percent": prog.get("progress_percent", 0.0),
                "completed_chunks": prog.get("completed_chunks", 0),
                "total_chunks": prog.get("total_chunks", 0),
                "downloaded_bytes": downloaded,
                "total_bytes": prog.get("total_bytes", 0),
                "speed_bytes_sec": downloaded / elapsed,
                "peers": [p.to_dict() for p in self.peers]
            }
