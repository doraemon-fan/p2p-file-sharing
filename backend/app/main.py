import os
import sys
from pathlib import Path

# Ensure backend root is always on sys.path regardless of working directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import config
from app.transfer.manager import transfer_manager
from app.api.routes import router as api_router
from app.tracker import tracker_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start receiver socket daemon on startup
    transfer_manager.start_receiver_daemon()
    print(f"PeerShare background receiver listening on port {config.p2p_port}...")
    
    # Start tracker heartbeat & announcement background loop
    tracker_client.start_heartbeat_loop(interval=15.0)
    print(f"PeerShare connected to tracker at {config.tracker_url}...")
    
    yield
    # Cleanup on shutdown
    transfer_manager.stop()
    tracker_client.stop()
    print("PeerShare backend stopped.")

app = FastAPI(
    title="PeerShare Backend API",
    description="Local agent handling P2P TCP transfers, chunking, and tracker comms",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (Vite typically runs on 5173 or similar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(api_router)  # Also mount so /ws/transfers works without /api prefix

@app.get("/")
def root():
    return {"app": "PeerShare", "status": "running", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.api_port, reload=False)
