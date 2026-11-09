"""SQLite-backed interview session store for VoiceHire.

Replaces the in-memory ``SESSIONS`` dict in ``app.main``: interview sessions
now survive a server restart. One table, one JSON blob per session — the
session dict is already JSON-shaped (plan, answers, index, follow-ups), so
no schema migration is needed if fields are added later.

- Path: ``VOICEHIRE_SESSION_DB`` env var, else ``voicehire_sessions.db``
  next to this package's parent (``backend/``). The file is runtime state:
  it is gitignored and never committed.
- Thread-safe: FastAPI runs sync endpoints in a thread pool, so all access
  goes through one lock and short-lived connections.
- The store is deliberately boring: no ORM, no migrations, no network.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

_LOCK = threading.Lock()


def _db_path() -> Path:
    override = os.environ.get("VOICEHIRE_SESSION_DB")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "voicehire_sessions.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "  id TEXT PRIMARY KEY,"
        "  data TEXT NOT NULL,"
        "  updated_at REAL NOT NULL"
        ")"
    )
    conn.commit()
    return conn


def get_session(session_id: str) -> dict | None:
    """Load a session dict by id, or None if it does not exist."""
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT data FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        finally:
            conn.close()
    return json.loads(row[0]) if row else None


def save_session(session: dict) -> None:
    """Insert or replace a session dict (upsert by id)."""
    import time

    payload = json.dumps(session)
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO sessions (id, data, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET data = excluded.data,"
                " updated_at = excluded.updated_at",
                (session["id"], payload, time.time()),
            )
            conn.commit()
        finally:
            conn.close()


def delete_session(session_id: str) -> bool:
    """Delete a session. Returns True if a row was removed."""
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
