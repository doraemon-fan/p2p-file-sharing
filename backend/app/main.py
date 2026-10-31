import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import config
from app.transfer.manager import transfer_manager
from app.api.routes import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start receiver socket daemon on startup
    transfer_manager.start_receiver_daemon()
    print(f"PeerShare background receiver listening on port {config.p2p_port}...")
    yield
    # Cleanup on shutdown
    transfer_manager.stop()
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

@app.get("/")
def root():
    return {"app": "PeerShare", "status": "running", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.api_port, reload=False)
