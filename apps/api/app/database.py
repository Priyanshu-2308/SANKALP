"""SQLite database layer for single-use approval tokens and trip audit logging.

Design Principles:
- Uses Python's standard library sqlite3 (zero external database dependencies).
- WAL (Write-Ahead Logging) mode enabled for high concurrency and resilience.
- Atomic single-use token verification: guarantees no token can be reused.
- Clean audit log trail of all user approvals.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator, Optional
from sankalp_engine.models import IST

DEFAULT_DB_PATH = Path("data/sankalp.sqlite3")


class Database:
    """Manages SQLite storage for SANKALP tokens and audit logs."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an active SQLite connection with row factory."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and foreign keys for high reliability
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create tables and indices if they do not exist."""
        with self.get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS approval_tokens (
                        token TEXT PRIMARY KEY,
                        itinerary_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        is_used INTEGER NOT NULL DEFAULT 0,
                        used_at TEXT
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_tokens_expires 
                    ON approval_tokens(expires_at, is_used);
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trip_audit_log (
                        trip_id TEXT PRIMARY KEY,
                        approval_token TEXT NOT NULL,
                        itinerary_id TEXT NOT NULL,
                        origin_id TEXT NOT NULL,
                        destination_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        total_fare_paise INTEGER NOT NULL,
                        p_ontime REAL NOT NULL,
                        created_at TEXT NOT NULL,
                        itinerary_json TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_trip_created 
                    ON trip_audit_log(created_at);
                    """
                )

    def create_approval_token(self, itinerary_id: str, ttl_minutes: int = 15) -> str:
        """Issue a cryptographically secure single-use token with short TTL."""
        token = f"tok_{secrets.token_urlsafe(32)}"
        now = datetime.now(IST)
        expires_at = now + timedelta(minutes=ttl_minutes)

        with self.get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO approval_tokens (token, itinerary_id, created_at, expires_at, is_used)
                    VALUES (?, ?, ?, ?, 0);
                    """,
                    (token, itinerary_id, now.isoformat(), expires_at.isoformat()),
                )
        return token

    def verify_and_redeem_token(self, token: str, itinerary_id: str) -> bool:
        """Atomically verify and redeem a token.
        
        Returns True if the token was valid, unused, and within its TTL.
        Returns False if the token was already redeemed, expired, or invalid.
        """
        now = datetime.now(IST).isoformat()
        with self.get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE approval_tokens
                    SET is_used = 1, used_at = ?
                    WHERE token = ? 
                      AND itinerary_id = ? 
                      AND is_used = 0 
                      AND expires_at > ?;
                    """,
                    (now, token, itinerary_id, now),
                )
                # If rowcount == 1, token was atomically redeemed. If 0, redemption failed.
                return cursor.rowcount == 1

    def record_trip_approval(
        self,
        approval_token: str,
        itinerary_id: str,
        origin_id: str,
        destination_id: str,
        total_fare_paise: int,
        p_ontime: float,
        itinerary_data: dict[str, Any],
        action: str = "APPROVED",
    ) -> str:
        """Record an approved journey into the audit log."""
        trip_id = f"trip_{secrets.token_hex(8)}"
        now = datetime.now(IST).isoformat()
        itinerary_str = json.dumps(itinerary_data)

        with self.get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO trip_audit_log (
                        trip_id, approval_token, itinerary_id, origin_id, 
                        destination_id, action, total_fare_paise, p_ontime, 
                        created_at, itinerary_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        trip_id,
                        approval_token,
                        itinerary_id,
                        origin_id,
                        destination_id,
                        action,
                        total_fare_paise,
                        p_ontime,
                        now,
                        itinerary_str,
                    ),
                )
        return trip_id

    def get_trip(self, trip_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a trip and its full itinerary by trip ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM trip_audit_log WHERE trip_id = ?;", (trip_id,)
            ).fetchone()
            if not row:
                return None
            return {
                "trip_id": row["trip_id"],
                "approval_token": row["approval_token"],
                "itinerary_id": row["itinerary_id"],
                "origin_id": row["origin_id"],
                "destination_id": row["destination_id"],
                "action": row["action"],
                "total_fare_paise": row["total_fare_paise"],
                "p_ontime": row["p_ontime"],
                "created_at": row["created_at"],
                "itinerary": json.loads(row["itinerary_json"]),
            }

    def list_audit_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent audit logs."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT trip_id, action, origin_id, destination_id, total_fare_paise, p_ontime, created_at
                FROM trip_audit_log
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
