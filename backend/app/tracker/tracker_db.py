import sqlite3
import os
import time
from typing import List, Dict, Any, Optional

TRACKER_DB_PATH = os.path.abspath("tracker.db")

def init_tracker_db(db_path: str = TRACKER_DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Peers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS peers (
            peer_id TEXT PRIMARY KEY,
            peer_name TEXT,
            host TEXT,
            port INTEGER,
            last_heartbeat REAL,
            status TEXT DEFAULT 'online'
        )
    """)

    # Shared files catalog table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shared_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            filename TEXT,
            file_size INTEGER,
            sha256 TEXT,
            peer_id TEXT,
            announced_at REAL,
            UNIQUE(file_id, peer_id),
            FOREIGN KEY (peer_id) REFERENCES peers (peer_id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

class TrackerDatabase:
    def __init__(self, db_path: str = TRACKER_DB_PATH):
        self.db_path = db_path
        init_tracker_db(self.db_path)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def register_or_update_peer(self, peer_id: str, peer_name: str, host: str, port: int) -> Dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.time()
        cursor.execute("""
            INSERT INTO peers (peer_id, peer_name, host, port, last_heartbeat, status)
            VALUES (?, ?, ?, ?, ?, 'online')
            ON CONFLICT(peer_id) DO UPDATE SET
                peer_name=excluded.peer_name,
                host=excluded.host,
                port=excluded.port,
                last_heartbeat=excluded.last_heartbeat,
                status='online'
        """, (peer_id, peer_name, host, port, now))
        conn.commit()
        conn.close()
        return {
            "peer_id": peer_id,
            "peer_name": peer_name,
            "host": host,
            "port": port,
            "last_heartbeat": now,
            "status": "online"
        }

    def heartbeat(self, peer_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.time()
        cursor.execute("""
            UPDATE peers SET last_heartbeat = ?, status = 'online'
            WHERE peer_id = ?
        """, (now, peer_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def purge_expired_peers(self, timeout_seconds: float = 60.0) -> int:
        """Mark peers as offline or delete them if inactive beyond timeout."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cutoff = time.time() - timeout_seconds
        
        # Remove files announced by expired peers
        cursor.execute("""
            DELETE FROM shared_files WHERE peer_id IN (
                SELECT peer_id FROM peers WHERE last_heartbeat < ?
            )
        """, (cutoff,))

        # Remove the expired peers
        cursor.execute("DELETE FROM peers WHERE last_heartbeat < ?", (cutoff,))
        purged = cursor.rowcount
        conn.commit()
        conn.close()
        return purged

    def get_all_peers(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM peers ORDER BY last_heartbeat DESC")
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return result

    def announce_file(self, peer_id: str, file_id: str, filename: str, file_size: int, sha256: str) -> Dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.time()
        cursor.execute("""
            INSERT INTO shared_files (file_id, filename, file_size, sha256, peer_id, announced_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_id, peer_id) DO UPDATE SET
                filename=excluded.filename,
                file_size=excluded.file_size,
                sha256=excluded.sha256,
                announced_at=excluded.announced_at
        """, (file_id, filename, file_size, sha256, peer_id, now))
        conn.commit()
        conn.close()
        return {
            "file_id": file_id,
            "filename": filename,
            "file_size": file_size,
            "sha256": sha256,
            "peer_id": peer_id,
            "announced_at": now
        }

    def search_files(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        if query:
            pattern = f"%{query}%"
            cursor.execute("""
                SELECT sf.*, p.peer_name, p.host, p.port, p.status as peer_status
                FROM shared_files sf
                JOIN peers p ON sf.peer_id = p.peer_id
                WHERE sf.filename LIKE ? OR sf.sha256 LIKE ?
                ORDER BY sf.announced_at DESC
            """, (pattern, pattern))
        else:
            cursor.execute("""
                SELECT sf.*, p.peer_name, p.host, p.port, p.status as peer_status
                FROM shared_files sf
                JOIN peers p ON sf.peer_id = p.peer_id
                ORDER BY sf.announced_at DESC
            """)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return result

    def get_file_peers(self, file_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.peer_id, p.peer_name, p.host, p.port, p.status, sf.file_id, sf.filename, sf.file_size, sf.sha256
            FROM shared_files sf
            JOIN peers p ON sf.peer_id = p.peer_id
            WHERE sf.file_id = ?
        """, (file_id,))
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return result

    def remove_peer(self, peer_id: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM shared_files WHERE peer_id = ?", (peer_id,))
        cursor.execute("DELETE FROM peers WHERE peer_id = ?", (peer_id,))
        conn.commit()
        conn.close()
