import sqlite3
from pathlib import Path
from typing import Optional

from config.settings import settings


class TicketStorage:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or settings.app.db_path
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    ticket TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(message_id)
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    def is_processed(self, message_id: str) -> bool:
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT 1 FROM processed_emails WHERE message_id = ? LIMIT 1",
                (message_id,),
            )
            return cur.fetchone() is not None
        finally:
            conn.close()

    def mark_processed(self, message_id: str, ticket: Optional[str]) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_emails (message_id, ticket)
                VALUES (?, ?)
                """,
                (message_id, ticket),
            )
            conn.commit()
        finally:
            conn.close()
    
    def count_processed_today(self) -> int:
        conn = self._get_conn()
        try:
            cur = conn.execute(
                """
                SELECT COUNT(*)
                FROM processed_emails
                WHERE date(created_at, 'localtime') = date('now', 'localtime')
                """
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()

