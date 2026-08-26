"""Multi-turn session memory.

One store, used by text chat and voice chat alike — Role 3 explicitly must not
build a second memory system. Memory is what makes "what about tomorrow?" and
its Telugu equivalent "మరి ఎల్లుండి?" resolve against the previous turn's
location instead of asking the user to repeat themselves.

Backed by SQLite so a server restart mid-demo does not lose the thread, with an
in-process cache in front so the common path costs nothing.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from ..config import get_settings
from ..db import load_session, purge_old_sessions, save_session


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    text: str
    language: str = "en"
    intent: str | None = None
    location: str | None = None
    at: float = field(default_factory=time.time)


@dataclass
class SessionState:
    session_id: str
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    admin1: str | None = None
    user_type: str = "general"
    language: str = "en"
    response_mode: str = "normal"
    last_intent: str | None = None
    last_day_offset: int = 0
    # True when the user named this place out loud rather than it coming from
    # the dashboard selector. A follow-up continues the place they asked about.
    location_was_named: bool = False
    # Historical comparisons already surfaced in this conversation. A pattern
    # match is context, and context repeated every turn becomes noise.
    seen_events: list[str] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["turns"] = [asdict(t) if not isinstance(t, dict) else t for t in self.turns]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        turns = [Turn(**t) for t in data.get("turns", []) if isinstance(t, dict)]
        known = {f for f in cls.__dataclass_fields__ if f != "turns"}
        return cls(turns=turns, **{k: v for k, v in data.items() if k in known})

    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def recent(self, count: int = 6) -> list[Turn]:
        return self.turns[-count:]

    def transcript(self, count: int = 6) -> str:
        """Compact prior context for the LLM's extraction prompt."""
        lines = []
        for turn in self.recent(count):
            speaker = "User" if turn.role == "user" else "WeatherGPT"
            lines.append(f"{speaker}: {turn.text}")
        return "\n".join(lines)


_cache: dict[str, SessionState] = {}
_lock = threading.Lock()


def new_session_id() -> str:
    return uuid.uuid4().hex


def get_session(session_id: str | None) -> SessionState:
    """Load (or create) a session. Never returns None — a bad id starts fresh."""
    if not session_id:
        return SessionState(session_id=new_session_id())

    with _lock:
        cached = _cache.get(session_id)
    if cached is not None:
        return cached

    stored = load_session(session_id)
    state = SessionState.from_dict(stored) if stored else SessionState(session_id=session_id)
    state.session_id = session_id
    with _lock:
        _cache[session_id] = state
    return state


def persist(state: SessionState) -> None:
    settings = get_settings()
    state.updated_at = time.time()
    if len(state.turns) > settings.max_session_turns:
        state.turns = state.turns[-settings.max_session_turns :]
    with _lock:
        _cache[state.session_id] = state
    try:
        save_session(state.session_id, state.to_dict())
    except Exception:  # noqa: BLE001 - memory is a convenience, never fatal
        pass


def remember_turn(state: SessionState, role: str, text: str, **kwargs: Any) -> None:
    state.turns.append(Turn(role=role, text=text, **kwargs))


def set_location(state: SessionState, location: Any, *, named: bool | None = None) -> None:
    state.location_name = location.name
    state.admin1 = location.admin1
    state.latitude = location.latitude
    state.longitude = location.longitude
    if named is not None:
        state.location_was_named = named


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def housekeeping() -> int:
    """Drop sessions past their TTL. Called by the scheduler."""
    settings = get_settings()
    cutoff = time.time() - settings.session_ttl_seconds
    with _lock:
        stale = [sid for sid, st in _cache.items() if st.updated_at < cutoff]
        for sid in stale:
            _cache.pop(sid, None)
    try:
        return purge_old_sessions(settings.session_ttl_seconds)
    except Exception:  # noqa: BLE001
        return 0
