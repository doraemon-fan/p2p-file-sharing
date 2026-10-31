import os
import json
import time
from typing import Set, Dict, Any, Optional
from .chunk_manager import FileManifest

class ResumableDownloadSession:
    """
    Tracks state of an ongoing chunked download:
    - Maintains the FileManifest
    - Tracks completed chunk indices
    - Persists progress to a session state file (<file>.state)
    - Supports resuming from previously verified chunks
    """
    def __init__(self, destination_path: str, manifest: FileManifest):
        self.destination_path = destination_path
        self.part_path = destination_path + ".part"
        self.state_path = destination_path + ".state"
        self.manifest = manifest
        self.completed_chunks: Set[int] = set()
        self.failed_chunks: Set[int] = set()
        self.start_time = time.time()
        self._load_state()

    def _load_state(self):
        """Load session progress if an interrupted transfer state exists."""
        if os.path.exists(self.state_path) and os.path.exists(self.part_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("file_sha256") == self.manifest.file_sha256:
                        self.completed_chunks = set(data.get("completed_chunks", []))
            except Exception:
                self.completed_chunks = set()

    def save_state(self):
        """Persist state to disk for crash resilience."""
        data = {
            "file_id": self.manifest.file_id,
            "filename": self.manifest.filename,
            "file_size": self.manifest.file_size,
            "file_sha256": self.manifest.file_sha256,
            "completed_chunks": list(self.completed_chunks),
            "total_chunks": self.manifest.total_chunks,
            "timestamp": time.time()
        }
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def mark_chunk_completed(self, chunk_index: int):
        self.completed_chunks.add(chunk_index)
        if chunk_index in self.failed_chunks:
            self.failed_chunks.remove(chunk_index)
        self.save_state()

    def mark_chunk_failed(self, chunk_index: int):
        self.failed_chunks.add(chunk_index)

    def get_missing_chunks(self) -> Set[int]:
        all_indices = set(range(self.manifest.total_chunks))
        return all_indices - self.completed_chunks

    def is_complete(self) -> bool:
        return len(self.completed_chunks) == self.manifest.total_chunks

    def cleanup_state(self):
        """Clean up .state file once download is fully completed and committed."""
        if os.path.exists(self.state_path):
            try:
                os.remove(self.state_path)
            except Exception:
                pass

    def get_progress_info(self) -> Dict[str, Any]:
        total = self.manifest.total_chunks
        completed = len(self.completed_chunks)
        percent = (completed / total * 100) if total > 0 else 100.0
        
        # Calculate downloaded bytes
        downloaded_bytes = sum(self.manifest.chunks[i].size for i in self.completed_chunks if i < len(self.manifest.chunks))
        
        return {
            "filename": self.manifest.filename,
            "total_chunks": total,
            "completed_chunks": completed,
            "missing_chunks": len(self.get_missing_chunks()),
            "progress_percent": percent,
            "downloaded_bytes": downloaded_bytes,
            "total_bytes": self.manifest.file_size,
            "is_complete": self.is_complete()
        }
