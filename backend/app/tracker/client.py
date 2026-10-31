import time
import threading
import requests
import os
from typing import Dict, Any, List, Optional
from app.config import config
from app.networking import calculate_file_hash

class TrackerClient:
    """
    Client agent running inside peer node to interact with the central tracker:
    - Registers peer identity and listening TCP port
    - Sends periodic heartbeats
    - Automatically announces files in shared folder
    - Queries for online peers and file searches
    """
    def __init__(self, tracker_url: str = None):
        self.tracker_url = tracker_url or config.tracker_url
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None

    def register(self) -> Dict[str, Any]:
        url = f"{self.tracker_url}/peers/register"
        payload = {
            "peer_id": config.peer_id,
            "peer_name": config.peer_name,
            "port": config.p2p_port
        }
        res = requests.post(url, json=payload, timeout=5.0)
        res.raise_for_status()
        return res.json()

    def send_heartbeat(self) -> bool:
        url = f"{self.tracker_url}/peers/heartbeat"
        payload = {"peer_id": config.peer_id}
        res = requests.post(url, json=payload, timeout=3.0)
        return res.status_code == 200

    def start_heartbeat_loop(self, interval: float = 15.0):
        if self._running:
            return
        self._running = True

        def loop():
            # Initial registration attempt
            try:
                self.register()
                self.announce_shared_directory()
            except Exception as e:
                print(f"[TrackerClient] Initial tracker registration warning: {e}")

            while self._running:
                time.sleep(interval)
                try:
                    self.send_heartbeat()
                except Exception:
                    # Retry register if heartbeat failed (e.g. tracker restarted)
                    try:
                        self.register()
                    except Exception:
                        pass

        self._heartbeat_thread = threading.Thread(target=loop, daemon=True)
        self._heartbeat_thread.start()

    def stop(self):
        self._running = False

    def announce_shared_directory(self) -> List[Dict[str, Any]]:
        """Announce all files currently in shared_dir to the tracker."""
        announced = []
        if not os.path.exists(config.shared_dir):
            return announced

        for fname in os.listdir(config.shared_dir):
            fpath = os.path.join(config.shared_dir, fname)
            if os.path.isfile(fpath):
                file_size = os.path.getsize(fpath)
                file_hash = calculate_file_hash(fpath)
                file_id = f"{file_hash[:16]}"
                try:
                    res = requests.post(
                        f"{self.tracker_url}/files/announce",
                        json={
                            "peer_id": config.peer_id,
                            "file_id": file_id,
                            "filename": fname,
                            "file_size": file_size,
                            "sha256": file_hash
                        },
                        timeout=5.0
                    )
                    if res.status_code == 200:
                        announced.append(res.json()["file"])
                except Exception as e:
                    print(f"[TrackerClient] Failed to announce {fname}: {e}")
        return announced

    def get_online_peers(self) -> List[Dict[str, Any]]:
        url = f"{self.tracker_url}/peers"
        res = requests.get(url, timeout=5.0)
        res.raise_for_status()
        return res.json().get("peers", [])

    def search_files(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        url = f"{self.tracker_url}/files/search"
        params = {"q": query} if query else {}
        res = requests.get(url, params=params, timeout=5.0)
        res.raise_for_status()
        return res.json().get("results", [])

tracker_client = TrackerClient()
