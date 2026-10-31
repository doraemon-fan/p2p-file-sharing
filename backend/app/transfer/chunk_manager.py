import os
import math
import json
import hashlib
from typing import List, Dict, Any, Optional

DEFAULT_CHUNK_SIZE = 512 * 1024  # 512 KB logical chunks

class ChunkInfo:
    def __init__(self, index: int, offset: int, size: int, sha256: str):
        self.index = index
        self.offset = offset
        self.size = size
        self.sha256 = sha256

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "offset": self.offset,
            "size": self.size,
            "sha256": self.sha256
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ChunkInfo":
        return cls(
            index=d["index"],
            offset=d["offset"],
            size=d["size"],
            sha256=d["sha256"]
        )

class FileManifest:
    def __init__(
        self,
        file_id: str,
        filename: str,
        file_size: int,
        chunk_size: int,
        total_chunks: int,
        file_sha256: str,
        chunks: List[ChunkInfo]
    ):
        self.file_id = file_id
        self.filename = filename
        self.file_size = file_size
        self.chunk_size = chunk_size
        self.total_chunks = total_chunks
        self.file_sha256 = file_sha256
        self.chunks = chunks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "chunk_size": self.chunk_size,
            "total_chunks": self.total_chunks,
            "file_sha256": self.file_sha256,
            "chunks": [c.to_dict() for c in self.chunks]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileManifest":
        chunks = [ChunkInfo.from_dict(c) for c in data["chunks"]]
        return cls(
            file_id=data["file_id"],
            filename=data["filename"],
            file_size=data["file_size"],
            chunk_size=data["chunk_size"],
            total_chunks=data["total_chunks"],
            file_sha256=data["file_sha256"],
            chunks=chunks
        )

def generate_manifest(file_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> FileManifest:
    """
    Create a logical manifest dividing a file into fixed-size chunks,
    calculating individual SHA-256 for each chunk and the whole-file SHA-256.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    filename = os.path.basename(file_path)
    whole_hasher = hashlib.sha256()

    total_chunks = math.ceil(file_size / chunk_size) if file_size > 0 else 1
    chunks: List[ChunkInfo] = []

    with open(file_path, "rb") as f:
        for idx in range(total_chunks):
            offset = idx * chunk_size
            data = f.read(chunk_size)
            chunk_len = len(data)

            whole_hasher.update(data)
            chunk_hash = hashlib.sha256(data).hexdigest()

            chunks.append(ChunkInfo(
                index=idx,
                offset=offset,
                size=chunk_len,
                sha256=chunk_hash
            ))

    file_sha256 = whole_hasher.hexdigest()
    file_id = f"{file_sha256[:16]}"

    return FileManifest(
        file_id=file_id,
        filename=filename,
        file_size=file_size,
        chunk_size=chunk_size,
        total_chunks=len(chunks),
        file_sha256=file_sha256,
        chunks=chunks
    )

def read_chunk(file_path: str, offset: int, size: int) -> bytes:
    """Read a specific chunk slice directly from disk."""
    with open(file_path, "rb") as f:
        f.seek(offset)
        return f.read(size)

def write_chunk(file_path: str, offset: int, data: bytes) -> None:
    """Write chunk bytes into target file at offset (creating sparse file if needed)."""
    # Open in r+b if exists, else wb
    mode = "r+b" if os.path.exists(file_path) else "wb"
    with open(file_path, mode) as f:
        f.seek(offset)
        f.write(data)

def verify_chunk(data: bytes, expected_hash: str) -> bool:
    """Verify integrity of a single chunk."""
    return hashlib.sha256(data).hexdigest().lower() == expected_hash.lower()

def verify_whole_file(file_path: str, expected_hash: str) -> bool:
    """Verify completed reconstructed file matches expected SHA-256."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            buf = f.read(64 * 1024)
            if not buf:
                break
            hasher.update(buf)
    return hasher.hexdigest().lower() == expected_hash.lower()
