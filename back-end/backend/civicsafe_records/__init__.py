"""Persistent storage for complaint / request / scam / service records (SQLite)."""

from .store import fetch_all_records, init_records_db, persist_record

__all__ = ["init_records_db", "persist_record", "fetch_all_records"]
