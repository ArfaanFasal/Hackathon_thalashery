"""Chat persistence: MongoDB when MONGODB_URI is set, else SQLite (local fallback)."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover
    MongoClient = None  # type: ignore

_MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
_MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "civicsafe")
_CHAT_STORAGE = os.getenv("CHAT_STORAGE", "sqlite").strip().lower()
_SQLITE_PATH = Path(__file__).resolve().parents[1] / "data" / "civicsafe_chat.sqlite"

_mongo_client: Optional[Any] = None
_mongo_db_handle: Optional[Any] = None
_mongo_unavailable: bool = False


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _use_mongo() -> bool:
    return _CHAT_STORAGE == "mongodb" and bool(_MONGODB_URI) and MongoClient is not None


def _mongo_db() -> Optional[Any]:
    global _mongo_client, _mongo_db_handle, _mongo_unavailable
    if not _use_mongo() or _mongo_unavailable:
        return None
    if _mongo_db_handle is not None:
        return _mongo_db_handle
    try:
        _mongo_client = MongoClient(_MONGODB_URI, serverSelectionTimeoutMS=8000)
        _mongo_client.admin.command("ping")
        _mongo_db_handle = _mongo_client[_MONGO_DB_NAME]
        _mongo_db_handle.chat_sessions.create_index("updated_at")
        _mongo_db_handle.chat_messages.create_index("session_id")
        return _mongo_db_handle
    except Exception:
        _mongo_unavailable = True
        _mongo_db_handle = None
        _mongo_client = None
        return None


def _connect_sqlite() -> sqlite3.Connection:
    _SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_SQLITE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    if _mongo_db() is not None:
        return
    conn = _connect_sqlite()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                state_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            """
        )
        conn.commit()
    finally:
        conn.close()


def _default_state() -> Dict[str, Any]:
    return {
        "stage": "A",
        "parent": None,
        "domain_id": None,
        "item_id": None,
        "item_kind": None,
        "slots": {"description": "", "location": "", "urgency": "", "since_when": ""},
    }


def create_session() -> str:
    init_db()
    sid = f"sess_{uuid.uuid4().hex[:12]}"
    now = _utc_iso()
    db = _mongo_db()
    if db is not None:
        db.chat_sessions.insert_one(
            {"_id": sid, "created_at": now, "updated_at": now, "state": _default_state()}
        )
        return sid
    conn = _connect_sqlite()
    try:
        conn.execute(
            "INSERT INTO sessions (id, created_at, updated_at, state_json) VALUES (?, ?, ?, ?)",
            (sid, now, now, json.dumps(_default_state())),
        )
        conn.commit()
    finally:
        conn.close()
    return sid


def get_session(session_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    init_db()
    db = _mongo_db()
    if db is not None:
        doc = db.chat_sessions.find_one({"_id": session_id})
        if not doc:
            return None
        state = doc.get("state") or _default_state()
        return session_id, state
    conn = _connect_sqlite()
    try:
        row = conn.execute("SELECT state_json FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        return session_id, json.loads(row["state_json"])
    finally:
        conn.close()


def save_state(session_id: str, state: Dict[str, Any]) -> None:
    init_db()
    now = _utc_iso()
    db = _mongo_db()
    if db is not None:
        db.chat_sessions.update_one(
            {"_id": session_id},
            {"$set": {"state": state, "updated_at": now}},
        )
        return
    conn = _connect_sqlite()
    try:
        conn.execute(
            "UPDATE sessions SET state_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(state), now, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def append_message(session_id: str, role: str, content: str) -> None:
    init_db()
    now = _utc_iso()
    db = _mongo_db()
    if db is not None:
        db.chat_messages.insert_one({"session_id": session_id, "role": role, "content": content, "created_at": now})
        return
    conn = _connect_sqlite()
    try:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        conn.commit()
    finally:
        conn.close()


def list_messages(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    init_db()
    db = _mongo_db()
    if db is not None:
        cur = db.chat_messages.find({"session_id": session_id}).sort("created_at", 1).limit(limit)
        return [{"role": d["role"], "content": d["content"], "created_at": d["created_at"]} for d in cur]
    conn = _connect_sqlite()
    try:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in rows]
    finally:
        conn.close()


def storage_backend() -> str:
    return "mongodb" if _mongo_db() is not None else "sqlite"
