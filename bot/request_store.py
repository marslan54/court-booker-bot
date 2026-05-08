import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class StoredBooking:
    job_id: str
    chat_id: int
    court_name: str
    start_time_iso: str
    status: str
    created_at_iso: str


class BookingRequestStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS booking_requests (
                    job_id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    court_name TEXT NOT NULL,
                    start_time_iso TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at_iso TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert(
        self,
        job_id: str,
        chat_id: int,
        court_name: str,
        start_time: datetime,
        status: str,
    ) -> None:
        now_iso = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO booking_requests(job_id, chat_id, court_name, start_time_iso, status, created_at_iso)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    chat_id=excluded.chat_id,
                    court_name=excluded.court_name,
                    start_time_iso=excluded.start_time_iso,
                    status=excluded.status
                """,
                (
                    job_id,
                    chat_id,
                    court_name,
                    start_time.isoformat(),
                    status,
                    now_iso,
                ),
            )
            conn.commit()

    def update_status(self, job_id: str, status: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE booking_requests SET status = ? WHERE job_id = ?",
                (status, job_id),
            )
            conn.commit()

    def list_for_chat(self, chat_id: int, limit: int = 10) -> list[StoredBooking]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT job_id, chat_id, court_name, start_time_iso, status, created_at_iso
                FROM booking_requests
                WHERE chat_id = ?
                ORDER BY created_at_iso DESC
                LIMIT ?
                """,
                (chat_id, limit),
            ).fetchall()
        return [StoredBooking(*row) for row in rows]
