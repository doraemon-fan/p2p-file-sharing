import os
import time
import uuid
import threading
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from app.config import config
from app.networking import FileSender, FileReceiver, calculate_file_hash
from app.database.db import log_transfer

class TransferState(BaseModel):
    id: str
    filename: str
    direction: str  # 'upload' or 'download'
    total_bytes: int
    transferred_bytes: int
    speed_bytes_sec: float
    progress_percent: float
    status: str  # 'pending', 'active', 'completed', 'failed'
    peer_address: str
    sha256: Optional[str] = None
    error: Optional[str] = None
    start_time: float
    elapsed_time: float = 0.0

class TransferManager:
    """
    Coordinates active transfers, background receiver server, and WebSocket notifications.
    """
    def __init__(self):
        self.active_transfers: Dict[str, TransferState] = {}
        self.receiver_server: Optional[FileReceiver] = None
        self.receiver_thread: Optional[threading.Thread] = None
        self._running = False
        self._ws_subscribers: List[asyncio.Queue] = []
        self.total_uploaded = 0
        self.total_downloaded = 0

    def start_receiver_daemon(self):
        if self._running:
            return
        self._running = True
        self.receiver_server = FileReceiver(
            host="0.0.0.0",
            port=config.p2p_port,
            destination_dir=config.downloads_dir
        )
        self.receiver_server.start_listening()

        def listen_loop():
            while self._running:
                try:
                    transfer_id = f"recv-{uuid.uuid4().hex[:8]}"
                    # Prepare state
                    state = TransferState(
                        id=transfer_id,
                        filename="Incoming file...",
                        direction="download",
                        total_bytes=0,
                        transferred_bytes=0,
                        speed_bytes_sec=0,
                        progress_percent=0,
                        status="active",
                        peer_address="Waiting for connection",
                        start_time=time.time()
                    )
                    self.active_transfers[transfer_id] = state

                    def progress_cb(rec, total, speed):
                        state.transferred_bytes = rec
                        state.total_bytes = total
                        state.speed_bytes_sec = speed
                        state.progress_percent = (rec / total * 100) if total > 0 else 100
                        state.elapsed_time = time.time() - state.start_time
                        self.broadcast_sync()

                    result = self.receiver_server.accept_one_file(progress_callback=progress_cb)
                    
                    # Update completed state
                    state.filename = result["filename"]
                    state.status = "completed"
                    state.sha256 = result["sha256"]
                    state.peer_address = f"{result['sender_address'][0]}:{result['sender_address'][1]}"
                    state.progress_percent = 100.0
                    state.speed_bytes_sec = 0.0
                    state.elapsed_time = result["duration_seconds"]
                    self.total_downloaded += result["file_size"]

                    log_transfer(
                        transfer_id=transfer_id,
                        filename=result["filename"],
                        direction="download",
                        file_size=result["file_size"],
                        peer_address=state.peer_address,
                        sha256=result["sha256"],
                        status="completed",
                        duration=result["duration_seconds"],
                        average_speed=result["average_speed_mbps"],
                        timestamp=time.time()
                    )
                    self.broadcast_sync()

                except Exception as e:
                    if not self._running:
                        break
                    time.sleep(0.5)

        self.receiver_thread = threading.Thread(target=listen_loop, daemon=True)
        self.receiver_thread.start()

    def send_file_async(self, file_path: str, peer_host: str, peer_port: int) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        transfer_id = f"send-{uuid.uuid4().hex[:8]}"

        state = TransferState(
            id=transfer_id,
            filename=filename,
            direction="upload",
            total_bytes=file_size,
            transferred_bytes=0,
            speed_bytes_sec=0,
            progress_percent=0,
            status="active",
            peer_address=f"{peer_host}:{peer_port}",
            start_time=time.time()
        )
        self.active_transfers[transfer_id] = state

        def run_sender():
            sender = FileSender(host=peer_host, port=peer_port)

            def progress_cb(sent, total, speed):
                state.transferred_bytes = sent
                state.total_bytes = total
                state.speed_bytes_sec = speed
                state.progress_percent = (sent / total * 100) if total > 0 else 100
                state.elapsed_time = time.time() - state.start_time
                self.broadcast_sync()

            try:
                result = sender.send_file(file_path, progress_callback=progress_cb)
                state.status = "completed"
                state.sha256 = result["sha256"]
                state.progress_percent = 100.0
                state.speed_bytes_sec = 0.0
                state.elapsed_time = result["duration_seconds"]
                self.total_uploaded += file_size

                log_transfer(
                    transfer_id=transfer_id,
                    filename=filename,
                    direction="upload",
                    file_size=file_size,
                    peer_address=state.peer_address,
                    sha256=result["sha256"],
                    status="completed",
                    duration=result["duration_seconds"],
                    average_speed=result["average_speed_mbps"],
                    timestamp=time.time()
                )
            except Exception as e:
                state.status = "failed"
                state.error = str(e)
                log_transfer(
                    transfer_id=transfer_id,
                    filename=filename,
                    direction="upload",
                    file_size=file_size,
                    peer_address=state.peer_address,
                    sha256="",
                    status="failed",
                    duration=time.time() - state.start_time,
                    average_speed=0.0,
                    timestamp=time.time()
                )
            finally:
                self.broadcast_sync()

        thread = threading.Thread(target=run_sender, daemon=True)
        thread.start()
        return transfer_id

    def subscribe(self, q: asyncio.Queue):
        self._ws_subscribers.append(q)

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._ws_subscribers:
            self._ws_subscribers.remove(q)

    def broadcast_sync(self):
        # Notify WebSocket queues if any active asyncio loops
        data = self.get_transfers_snapshot()
        for q in list(self._ws_subscribers):
            try:
                q.put_nowait(data)
            except Exception:
                pass

    def get_transfers_snapshot(self) -> List[Dict[str, Any]]:
        return [state.model_dump() for state in self.active_transfers.values()]

    def stop(self):
        self._running = False
        if self.receiver_server:
            self.receiver_server.stop()

transfer_manager = TransferManager()
