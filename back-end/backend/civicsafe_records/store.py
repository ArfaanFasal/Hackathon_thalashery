from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "civicsafe_records.sqlite"


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_records_db() -> None:
    conn = _connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS civic_records (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                allocation_bucket TEXT,
                domain_id TEXT,
                domain_title TEXT,
                item_id TEXT,
                item_title TEXT,
                raw_json TEXT NOT NULL,
                processed_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_civic_records_type ON civic_records(type);
            CREATE INDEX IF NOT EXISTS idx_civic_records_bucket ON civic_records(allocation_bucket);
            CREATE INDEX IF NOT EXISTS idx_civic_records_domain ON civic_records(domain_id);
            """
        )
        conn.commit()
    finally:
        conn.close()


def persist_record(
    record_id: str,
    record_type: str,
    created_at: datetime,
    raw_input: Dict[str, Any],
    processed_output: Dict[str, Any],
    *,
    allocation_bucket: str | None = None,
    domain_id: str | None = None,
    domain_title: str | None = None,
    item_id: str | None = None,
    item_title: str | None = None,
) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO civic_records
            (id, type, created_at, allocation_bucket, domain_id, domain_title, item_id, item_title, raw_json, processed_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                record_type,
                created_at.isoformat(),
                allocation_bucket,
                domain_id,
                domain_title,
                item_id,
                item_title,
                json.dumps(raw_input, default=str),
                json.dumps(processed_output, default=str),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def fetch_all_records() -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, type, created_at, allocation_bucket, domain_id, domain_title, item_id, item_title, raw_json, processed_json FROM civic_records ORDER BY created_at ASC"
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "type": r["type"],
                    "created_at": r["created_at"],
                    "allocation_bucket": r["allocation_bucket"],
                    "domain_id": r["domain_id"],
                    "domain_title": r["domain_title"],
                    "item_id": r["item_id"],
                    "item_title": r["item_title"],
                    "raw_json": r["raw_json"],
                    "processed_json": r["processed_json"],
                }
            )
        return out
    finally:
        conn.close()
