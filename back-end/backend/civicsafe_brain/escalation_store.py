"""
In-memory rolling log of complaint signals by region + issue category for grouped escalation.

Plug a persistent store later without changing callers: keep record() / count_similar() API.
"""

from __future__ import annotations

import re
import threading
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

_lock = threading.Lock()
# (timestamp_utc, region_key, issue_key)
_events: List[Tuple[datetime, str, str]] = []

_PRUNE_HORIZON_DAYS = 14


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_region(region: str | None) -> str:
    if not region or not str(region).strip():
        return "unknown_region"
    s = str(region).strip().lower()
    s = re.sub(r"\s+", "_", s)
    return re.sub(r"[^a-z0-9_]+", "", s) or "unknown_region"


def normalize_issue(issue_category: str | None) -> str:
    if not issue_category or not str(issue_category).strip():
        return "general_public"
    s = re.sub(r"[^a-z0-9]+", "_", issue_category.lower().strip())
    return s.strip("_") or "general_public"


def _prune() -> None:
    cutoff = _utc_now() - timedelta(days=_PRUNE_HORIZON_DAYS)
    global _events
    _events = [e for e in _events if e[0] >= cutoff]


def record_signal(region: str | None, issue_category: str | None) -> None:
    """Append one complaint signal (call when a message is classified as a civic complaint)."""
    rk = normalize_region(region)
    ik = normalize_issue(issue_category)
    with _lock:
        _prune()
        _events.append((_utc_now(), rk, ik))


def count_similar(region: str | None, issue_category: str | None, *, days: float) -> int:
    """How many signals in the last `days` for same normalized region + issue (inclusive of recent)."""
    rk = normalize_region(region)
    ik = normalize_issue(issue_category)
    cutoff = _utc_now() - timedelta(days=days)
    with _lock:
        _prune()
        return sum(1 for ts, r, i in _events if ts >= cutoff and r == rk and i == ik)


def reset_for_tests() -> None:
    """Clear store (unit tests only)."""
    with _lock:
        global _events
        _events = []
