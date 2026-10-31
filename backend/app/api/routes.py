import os
import shutil
import uuid
import time
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio

from app.config import config
from app.transfer.manager import transfer_manager, TransferState
from app.database.db import get_history, log_transfer
from app.networking import calculate_file_hash

router = APIRouter()

class SendRequest(BaseModel):
    file_path: Optional[str] = None
    peer_host: str
    peer_port: int

class SettingsUpdate(BaseModel):
    peer_name: Optional[str] = None
    downloads_dir: Optional[str] = None
    shared_dir: Optional[str] = None
    p2p_port: Optional[int] = None
    tracker_url: Optional[str] = None

@router.get("/status")
def get_status():
    return {
        "peer_id": config.peer_id,
        "peer_name": config.peer_name,
        "p2p_port": config.p2p_port,
        "status": "online",
        "downloads_dir": config.downloads_dir,
        "shared_dir": config.shared_dir,
        "total_uploaded": transfer_manager.total_uploaded,
        "total_downloaded": transfer_manager.total_downloaded,
        "active_transfers_count": len([t for t in transfer_manager.active_transfers.values() if t.status == "active"])
    }

@router.get("/transfers")
def get_transfers():
    return transfer_manager.get_transfers_snapshot()

@router.get("/history")
def get_transfer_history():
    return get_history()

@router.post("/send")
def initiate_send(req: SendRequest):
    if not req.file_path or not os.path.exists(req.file_path):
        raise HTTPException(status_code=400, detail="Specified file does not exist")
    try:
        transfer_id = transfer_manager.send_file_async(req.file_path, req.peer_host, req.peer_port)
        return {"status": "started", "transfer_id": transfer_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-and-send")
async def upload_and_send(
    peer_host: str = Form(...),
    peer_port: int = Form(...),
    file: UploadFile = File(...)
):
    """
    Accepts a file uploaded via browser drag-and-drop, saves to shared folder,
    and streams it directly to target peer.
    """
    os.makedirs(config.shared_dir, exist_ok=True)
    destination = os.path.join(config.shared_dir, file.filename)
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    transfer_id = transfer_manager.send_file_async(destination, peer_host, peer_port)
    return {"status": "started", "transfer_id": transfer_id, "file_path": destination}

@router.get("/shared-files")
def get_shared_files():
    files = []
    if os.path.exists(config.shared_dir):
        for fname in os.listdir(config.shared_dir):
            fpath = os.path.join(config.shared_dir, fname)
            if os.path.isfile(fpath):
                files.append({
                    "name": fname,
                    "path": fpath,
                    "size": os.path.getsize(fpath),
                    "modified": os.path.getmtime(fpath),
                    "status": "ready"
                })
    return files

@router.get("/downloaded-files")
def get_downloaded_files():
    files = []
    if os.path.exists(config.downloads_dir):
        for fname in os.listdir(config.downloads_dir):
            if fname.endswith(".part"):
                continue
            fpath = os.path.join(config.downloads_dir, fname)
            if os.path.isfile(fpath):
                files.append({
                    "name": fname,
                    "path": fpath,
                    "size": os.path.getsize(fpath),
                    "modified": os.path.getmtime(fpath)
                })
    return files

@router.get("/settings")
def get_settings():
    return config.model_dump()

@router.post("/settings")
def update_settings(updates: SettingsUpdate):
    from app.tracker import tracker_client
    tracker_url_changed = updates.tracker_url and updates.tracker_url != config.tracker_url

    if updates.peer_name:
        config.peer_name = updates.peer_name
    if updates.downloads_dir:
        config.downloads_dir = os.path.abspath(updates.downloads_dir)
        os.makedirs(config.downloads_dir, exist_ok=True)
    if updates.shared_dir:
        config.shared_dir = os.path.abspath(updates.shared_dir)
        os.makedirs(config.shared_dir, exist_ok=True)
    if updates.tracker_url:
        # This also re-registers immediately with the new tracker
        tracker_client.update_tracker_url(updates.tracker_url)

    return {"status": "updated", "config": config.model_dump()}


@router.get("/tracker/peers")
def get_tracker_peers():
    """Retrieve online peers from central tracker."""
    try:
        from app.tracker import tracker_client
        return {"peers": tracker_client.get_online_peers()}
    except Exception as e:
        return {"peers": [], "error": str(e)}

@router.get("/tracker/files")
def search_tracker_files(q: Optional[str] = None):
    """Search for shared files across all online peers via central tracker."""
    try:
        from app.tracker import tracker_client
        return {"files": tracker_client.search_files(q)}
    except Exception as e:
        return {"files": [], "error": str(e)}

@router.post("/tracker/announce")
def announce_shared_files_now():
    """Manually trigger broadcast of shared folder to tracker."""
    try:
        from app.tracker import tracker_client
        announced = tracker_client.announce_shared_directory()
        return {"status": "announced", "files": announced}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tracker/download")
def download_file_from_peer(
    peer_host: str = Form(...),
    peer_port: int = Form(...),
    file_path_or_name: str = Form(...)
):
    """
    Request download of a file discovered from tracker by connecting directly to the peer.
    """
    # Direct peer transfer initiation
    transfer_id = transfer_manager.send_file_async(file_path_or_name, peer_host, peer_port)
    return {"status": "started", "transfer_id": transfer_id}

@router.post("/chunks/download")
def download_chunked_file(
    peer_host: str = Form(...),
    peer_port: int = Form(...),
    file_identifier: str = Form(...)
):
    """
    Initiate Phase 3 chunked & resumable download from a peer.
    """
    from app.transfer.chunk_protocol import ChunkClientDownloader
    import threading

    transfer_id = f"chunk-{uuid.uuid4().hex[:8]}"
    state = TransferState(
        id=transfer_id,
        filename=file_identifier,
        direction="download",
        total_bytes=0,
        transferred_bytes=0,
        speed_bytes_sec=0,
        progress_percent=0,
        status="active",
        peer_address=f"{peer_host}:{peer_port}",
        start_time=time.time()
    )
    transfer_manager.active_transfers[transfer_id] = state

    def run_chunk_download():
        downloader = ChunkClientDownloader(
            peer_host=peer_host,
            peer_port=peer_port,
            downloads_dir=config.downloads_dir
        )

        def on_prog(info):
            state.transferred_bytes = info.get("downloaded_bytes", 0)
            state.total_bytes = info.get("total_bytes", 0)
            state.progress_percent = info.get("progress_percent", 0)
            elapsed = max(time.time() - state.start_time, 0.001)
            state.speed_bytes_sec = state.transferred_bytes / elapsed
            state.elapsed_time = elapsed
            transfer_manager.broadcast_sync()

        try:
            res = downloader.download_file(file_identifier, progress_callback=on_prog)
            state.status = "completed"
            state.sha256 = res.get("sha256")
            state.filename = res.get("filename")
            state.progress_percent = 100.0
            state.speed_bytes_sec = 0.0
            transfer_manager.total_downloaded += state.total_bytes
            log_transfer(
                transfer_id=transfer_id,
                filename=state.filename,
                direction="download",
                file_size=state.total_bytes,
                peer_address=state.peer_address,
                sha256=state.sha256 or "",
                status="completed",
                duration=time.time() - state.start_time,
                average_speed=state.speed_bytes_sec / (1024 * 1024),
                timestamp=time.time()
            )
        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            log_transfer(
                transfer_id=transfer_id,
                filename=state.filename,
                direction="download",
                file_size=state.total_bytes,
                peer_address=state.peer_address,
                sha256="",
                status="failed",
                duration=time.time() - state.start_time,
                average_speed=0.0,
                timestamp=time.time()
            )
        finally:
            transfer_manager.broadcast_sync()

    threading.Thread(target=run_chunk_download, daemon=True).start()
    return {"status": "started", "transfer_id": transfer_id}

@router.websocket("/ws/transfers")
async def websocket_transfers(websocket: WebSocket):
    await websocket.accept()
    queue = asyncio.Queue()
    transfer_manager.subscribe(queue)
    # Send initial state
    await websocket.send_json(transfer_manager.get_transfers_snapshot())
    try:
        while True:
            # Wait for either new updates or a periodic heartbeat
            try:
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(data)
            except asyncio.TimeoutError:
                # Send live snapshot periodically
                await websocket.send_json(transfer_manager.get_transfers_snapshot())
    except WebSocketDisconnect:
        transfer_manager.unsubscribe(queue)
    except Exception:
        transfer_manager.unsubscribe(queue)
