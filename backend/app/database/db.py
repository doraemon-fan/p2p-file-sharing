import sqlite3
import os
import json
from typing import List, Dict, Any, Optional

DB_PATH = os.path.abspath("peershare.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_history (
            id TEXT PRIMARY KEY,
            filename TEXT,
            direction TEXT, -- 'upload' or 'download'
            file_size INTEGER,
            peer_address TEXT,
            sha256 TEXT,
            status TEXT, -- 'completed', 'failed', 'interrupted'
            duration REAL,
            average_speed REAL,
            timestamp REAL
        )
    """)
    conn.commit()
    conn.close()

def log_transfer(
    transfer_id: str,
    filename: str,
    direction: str,
    file_size: int,
    peer_address: str,
    sha256: str,
    status: str,
    duration: float,
    average_speed: float,
    timestamp: float
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transfer_history (id, filename, direction, file_size, peer_address, sha256, status, duration, average_speed, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (transfer_id, filename, direction, file_size, peer_address, sha256, status, duration, average_speed, timestamp))
    conn.commit()
    conn.close()

def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transfer_history ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

init_db()
