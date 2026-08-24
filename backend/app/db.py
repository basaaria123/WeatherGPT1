"""SQLite persistence.

Deliberately thin and dependency-free: the schema below maps 1:1 onto tables a
PostgreSQL migration would create, so the upgrade path is a driver swap plus
`AUTOINCREMENT` -> `SERIAL`, not a rewrite.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

from .config import get_settings

_lock = threading.Lock()
_initialised = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    location       TEXT    NOT NULL,
    latitude       REAL,
    longitude      REAL,
    alert_type     TEXT    NOT NULL,
    severity       TEXT    NOT NULL,
    risk_score     INTEGER NOT NULL DEFAULT 0,
    timestamp      TEXT    NOT NULL,
    message        TEXT    NOT NULL,
    actions        TEXT    NOT NULL DEFAULT '[]',
    comparison     TEXT,
    expires_at     TEXT,
    active         INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_alerts_location ON alerts(location);
CREATE INDEX IF NOT EXISTS idx_alerts_active   ON alerts(active, timestamp);

CREATE TABLE IF NOT EXISTS subscriptions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    location      TEXT    NOT NULL,
    latitude      REAL,
    longitude     REAL,
    hazard_types  TEXT    NOT NULL DEFAULT '[]',
    phone_number  TEXT,
    min_severity  TEXT    NOT NULL DEFAULT 'High',
    created_at    TEXT    NOT NULL,
    UNIQUE(location, phone_number)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    payload       TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    conn = sqlite3.connect(settings.db_path, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    global _initialised
    with _lock:
        conn = _connect()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()
        _initialised = True


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    if not _initialised:
        init_db()
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
def insert_alert(
    *,
    location: str,
    latitude: float | None,
    longitude: float | None,
    alert_type: str,
    severity: str,
    risk_score: int,
    message: str,
    actions: list[str],
    comparison: dict[str, Any] | None = None,
    ttl_hours: int = 12,
) -> int:
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO alerts
               (location, latitude, longitude, alert_type, severity, risk_score,
                timestamp, message, actions, comparison, expires_at, active)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                location,
                latitude,
                longitude,
                alert_type,
                severity,
                int(risk_score),
                now.isoformat(timespec="seconds"),
                message,
                json.dumps(actions, ensure_ascii=False),
                json.dumps(comparison, ensure_ascii=False) if comparison else None,
                (now + timedelta(hours=ttl_hours)).isoformat(timespec="seconds"),
            ),
        )
        return int(cur.lastrowid or 0)


def recent_alert_exists(location: str, alert_type: str, within_hours: int) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=within_hours)).isoformat(timespec="seconds")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM alerts WHERE location=? AND alert_type=? AND timestamp>=? LIMIT 1",
            (location, alert_type, cutoff),
        ).fetchone()
    return row is not None


def fetch_alerts(location: str | None = None, include_expired: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if location:
        clauses.append("LOWER(location) LIKE ?")
        params.append(f"%{location.strip().lower()}%")
    if not include_expired:
        clauses.append("(expires_at IS NULL OR expires_at >= ?)")
        params.append(utcnow_iso())
        clauses.append("active = 1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM alerts {where} ORDER BY datetime(timestamp) DESC LIMIT ?", params
        ).fetchall()
    return [_row_to_alert(r) for r in rows]


def _row_to_alert(row: sqlite3.Row) -> dict[str, Any]:
    try:
        actions = json.loads(row["actions"] or "[]")
    except (json.JSONDecodeError, TypeError):
        actions = []
    comparison = None
    if row["comparison"]:
        try:
            comparison = json.loads(row["comparison"])
        except json.JSONDecodeError:
            comparison = None
    return {
        "id": row["id"],
        "location": row["location"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "alert_type": row["alert_type"],
        "severity": row["severity"],
        "risk_score": row["risk_score"],
        "timestamp": row["timestamp"],
        "message": row["message"],
        "actions": actions,
        "historical_comparison": comparison,
        "active": bool(row["active"]),
    }


def deactivate_expired_alerts() -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE alerts SET active=0 WHERE active=1 AND expires_at IS NOT NULL AND expires_at < ?",
            (utcnow_iso(),),
        )
        return cur.rowcount


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------
def upsert_subscription(
    *,
    location: str,
    latitude: float | None,
    longitude: float | None,
    hazard_types: list[str],
    phone_number: str | None,
    min_severity: str,
) -> dict[str, Any]:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO subscriptions
                 (location, latitude, longitude, hazard_types, phone_number, min_severity, created_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(location, phone_number) DO UPDATE SET
                 hazard_types=excluded.hazard_types,
                 min_severity=excluded.min_severity,
                 latitude=excluded.latitude,
                 longitude=excluded.longitude""",
            (
                location,
                latitude,
                longitude,
                json.dumps(hazard_types, ensure_ascii=False),
                phone_number,
                min_severity,
                utcnow_iso(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE location=? AND phone_number IS ?",
            (location, phone_number),
        ).fetchone()
    return _row_to_subscription(row)


def _row_to_subscription(row: sqlite3.Row) -> dict[str, Any]:
    try:
        hazards = json.loads(row["hazard_types"] or "[]")
    except (json.JSONDecodeError, TypeError):
        hazards = []
    return {
        "id": row["id"],
        "location": row["location"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "hazard_types": hazards,
        "phone_number": row["phone_number"],
        "min_severity": row["min_severity"],
        "created_at": row["created_at"],
    }


def list_subscriptions() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM subscriptions ORDER BY id").fetchall()
    return [_row_to_subscription(r) for r in rows]


def delete_subscription(subscription_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM subscriptions WHERE id=?", (subscription_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def save_session(session_id: str, payload: dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, payload, updated_at) VALUES (?,?,?)
               ON CONFLICT(session_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at""",
            (session_id, json.dumps(payload, ensure_ascii=False), utcnow_iso()),
        )


def load_session(session_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT payload FROM sessions WHERE session_id=?", (session_id,)).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["payload"])
    except json.JSONDecodeError:
        return None


def purge_old_sessions(ttl_seconds: int) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)).isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE updated_at < ?", (cutoff,))
        return cur.rowcount
