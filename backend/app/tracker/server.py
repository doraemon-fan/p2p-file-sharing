import os
import sys
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.tracker.tracker_db import TrackerDatabase

tracker_db = TrackerDatabase()

class PeerRegisterRequest(BaseModel):
    peer_id: str
    peer_name: str
    host: Optional[str] = None
    port: int

class HeartbeatRequest(BaseModel):
    peer_id: str

class AnnounceFileRequest(BaseModel):
    peer_id: str
    file_id: str
    filename: str
    file_size: int
    sha256: str

@asynccontextmanager
async def tracker_lifespan(app: FastAPI):
    # Background task to clean up expired peers (heartbeat timeout: 60s)
    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(20)
                purged = tracker_db.purge_expired_peers(timeout_seconds=45.0)
                if purged > 0:
                    print(f"[Tracker] Purged {purged} inactive peers and associated files")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Tracker] Error in cleanup loop: {e}")

    task = asyncio.create_task(cleanup_loop())
    print("[Tracker] Tracker server started and background peer reaper running...")
    yield
    task.cancel()
    print("[Tracker] Tracker server stopped.")

app = FastAPI(
    title="PeerShare Central Tracker Service",
    description="Coordinates peer registration, heartbeats, and file announcements without handling file data",
    version="1.0.0",
    lifespan=tracker_lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def tracker_root():
    return {
        "service": "PeerShare Tracker",
        "status": "online",
        "active_peers": len(tracker_db.get_all_peers())
    }

@app.post("/peers/register")
def register_peer(req: PeerRegisterRequest, request: Request):
    # Use explicit host or detect caller IP
    client_host = req.host or request.client.host
    if client_host in ("127.0.0.1", "localhost", "::1"):
        # If running locally, preserve loopback
        client_host = "127.0.0.1"
    
    peer = tracker_db.register_or_update_peer(
        peer_id=req.peer_id,
        peer_name=req.peer_name,
        host=client_host,
        port=req.port
    )
    return {"status": "registered", "peer": peer}

@app.post("/peers/heartbeat")
def peer_heartbeat(req: HeartbeatRequest):
    updated = tracker_db.heartbeat(req.peer_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Peer not registered or expired")
    return {"status": "ok", "peer_id": req.peer_id}

@app.get("/peers")
def list_peers():
    peers = tracker_db.get_all_peers()
    return {"peers": peers, "total": len(peers)}

@app.post("/files/announce")
def announce_file(req: AnnounceFileRequest):
    record = tracker_db.announce_file(
        peer_id=req.peer_id,
        file_id=req.file_id,
        filename=req.filename,
        file_size=req.file_size,
        sha256=req.sha256
    )
    return {"status": "announced", "file": record}

@app.get("/files/search")
def search_files(q: Optional[str] = Query(None, description="Search query")):
    results = tracker_db.search_files(q)
    return {"results": results, "total": len(results)}

@app.get("/files/{file_id}/peers")
def get_file_peers(file_id: str):
    peers = tracker_db.get_file_peers(file_id)
    if not peers:
        raise HTTPException(status_code=404, detail="No peers found possessing this file")
    return {"file_id": file_id, "peers": peers, "total": len(peers)}

def run_tracker(host: str = "0.0.0.0", port: int = 8001):
    uvicorn.run("app.tracker.server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    run_tracker()
