import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio

from app.config import config
from app.transfer.manager import transfer_manager
from app.database.db import get_history
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
    if updates.peer_name:
        config.peer_name = updates.peer_name
    if updates.downloads_dir:
        config.downloads_dir = os.path.abspath(updates.downloads_dir)
        os.makedirs(config.downloads_dir, exist_ok=True)
    if updates.shared_dir:
        config.shared_dir = os.path.abspath(updates.shared_dir)
        os.makedirs(config.shared_dir, exist_ok=True)
    if updates.tracker_url:
        config.tracker_url = updates.tracker_url
    return {"status": "updated", "config": config.model_dump()}

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
