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

    def _get_lan_ip(self) -> str:
        """
        Detect the machine's own LAN IP by opening a UDP socket toward the tracker host.
        This doesn't actually send any data — it just finds which local interface
        the OS would route through to reach the tracker. Falls back to 127.0.0.1.
        """
        import socket
        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.tracker_url)
            tracker_host = parsed.hostname or "8.8.8.8"
            tracker_port = parsed.port or 80
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(1.0)
                s.connect((tracker_host, tracker_port))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def register(self) -> Dict[str, Any]:
        url = f"{self.tracker_url}/peers/register"
        own_ip = self._get_lan_ip()
        payload = {
            "peer_id": config.peer_id,
            "peer_name": config.peer_name,
            "host": own_ip,          # always send our real LAN IP explicitly
            "port": config.p2p_port
        }
        res = requests.post(url, json=payload, timeout=5.0)
        res.raise_for_status()
        print(f"[TrackerClient] Registered as '{config.peer_name}' ({config.peer_id}) "
              f"at {own_ip}:{config.p2p_port} → tracker {self.tracker_url}")
        return res.json()

    def send_heartbeat(self) -> bool:
        url = f"{self.tracker_url}/peers/heartbeat"
        payload = {"peer_id": config.peer_id}
        res = requests.post(url, json=payload, timeout=3.0)
        return res.status_code == 200

    def update_tracker_url(self, new_url: str):
        """Change tracker URL at runtime and immediately re-register + re-announce."""
        self.tracker_url = new_url
        config.tracker_url = new_url
        try:
            self.register()
            self.announce_shared_directory()
            print(f"[TrackerClient] Re-registered with new tracker: {new_url}")
        except Exception as e:
            print(f"[TrackerClient] Re-registration warning after URL change: {e}")

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
