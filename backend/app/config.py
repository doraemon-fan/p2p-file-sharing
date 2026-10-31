import os
import uuid
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    peer_id: str = Field(default_factory=lambda: f"peer-{uuid.uuid4().hex[:8]}")
    peer_name: str = "Peer-Local"
    p2p_port: int = 5000
    api_port: int = 8000
    downloads_dir: str = os.path.abspath("downloads")
    shared_dir: str = os.path.abspath("shared")
    tracker_url: str = "http://127.0.0.1:8001"

config = AppConfig()
os.makedirs(config.downloads_dir, exist_ok=True)
os.makedirs(config.shared_dir, exist_ok=True)
