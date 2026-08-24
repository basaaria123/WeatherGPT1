# -*- coding: utf-8 -*-
"""Numeric grounding check.

Generated prose is scanned for measurement claims — a number attached to a
weather unit — and each one is matched against the values actually returned by
the provider. A claim that matches nothing is a fabrication, and the chat
engine responds by discarding the generated text in favour of the deterministic
template, which cannot hallucinate.

Only unit-bearing numbers are checked, on purpose. "24 hours", "12 noon" and
"100" in "76 out of 100" are not weather measurements, and treating them as
claims would produce constant false rejections without catching anything real.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Native digits map to ASCII before parsing, so a Hindi or Telugu answer is
# checked as strictly as an English one.
_DIGIT_MAP = {}
for _base, _script in ((0x0966, "devanagari"), (0x09E6, "bengali"), (0x0C66, "telugu")):
    for _i in range(10):
        _DIGIT_MAP[chr(_base + _i)] = str(_i)

# unit token -> canonical family
_UNIT_FAMILIES: dict[str, str] = {
    "mm": "precip", "millimetre": "precip", "millimetres": "precip", "millimeter": "precip",
    "मिमी": "precip", "मि.मी.": "precip", "మి.మీ.": "precip", "মিমি": "precip", "মি.মি.": "precip",
    "c": "temp", "°c": "temp", "celsius": "temp", "degree": "temp", "degrees": "temp",
    "km/h": "wind", "kmph": "wind", "km/hr": "wind", "kph": "wind",
    "किमी/घंटा": "wind", "कि.मी./घंटा": "wind", "किमी/तास": "wind",
    "కి.మీ./గంట": "wind", "কিমি/ঘণ্টা": "wind", "কি.মি./ঘণ্টা": "wind",
    "%": "percent", "percent": "percent", "per cent": "percent",
}

# Tolerances per family, generous enough for honest rounding, tight enough to
# catch a number that was made up.
_TOLERANCE: dict[str, float] = {"precip": 1.0, "temp": 0.6, "wind": 2.0, "percent": 2.0}

_UNIT_ALTERNATION = "|".join(
    sorted((re.escape(u) for u in _UNIT_FAMILIES), key=len, reverse=True)
)
_CLAIM_RE = re.compile(rf"(\d+(?:[.,]\d+)?)\s*({_UNIT_ALTERNATION})", re.IGNORECASE | re.UNICODE)


def normalise_digits(text: str) -> str:
    return "".join(_DIGIT_MAP.get(ch, ch) for ch in text or "")


def _walk_numbers(node: Any) -> Iterable[tuple[str, float]]:
    """Yield every (key, numeric value) pair anywhere in the payload."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from _walk_numbers(value)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                yield str(key), float(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_numbers(item)


def _family_for_key(key: str) -> str | None:
    key = key.lower()
    if "precipitation" in key or key.endswith("_mm") or "rain" in key:
        return "precip"
    if "temperature" in key or key.endswith("_c") or "feels" in key:
        return "temp"
    if "wind" in key or "gust" in key:
        return "wind"
    if key.endswith("_pct") or "probability" in key or "humidity" in key or "cover" in key:
        return "percent"
    return None


def allowed_values(weather_data: dict[str, Any]) -> dict[str, set[float]]:
    """Collect the permissible values per unit family from the real response."""
    buckets: dict[str, set[float]] = {"precip": set(), "temp": set(), "wind": set(), "percent": set()}
    for key, value in _walk_numbers(weather_data):
        family = _family_for_key(key)
        if family:
            buckets[family].add(round(value, 2))
    # Derived aggregates the answer may legitimately quote.
    for family in buckets:
        extras = set()
        for value in buckets[family]:
            extras.add(round(value))
            extras.add(round(value, 1))
        buckets[family] |= extras
    return buckets


def _matches(value: float, family: str, allowed: set[float]) -> bool:
    tolerance = _TOLERANCE.get(family, 1.0)
    return any(abs(value - candidate) <= tolerance for candidate in allowed)


def verify_numbers(text: str, weather_data: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    """Check every measurement claim in ``text``.

    Returns ``(ok, checked, rejected)`` where ``checked`` and ``rejected`` are
    human-readable claim strings such as ``"260.9 mm"``.
    """
    if not text:
        return True, [], []
    buckets = allowed_values(weather_data)
    normalised = normalise_digits(text)

    checked: list[str] = []
    rejected: list[str] = []
    for match in _CLAIM_RE.finditer(normalised):
        raw_value, raw_unit = match.group(1), match.group(2)
        family = _UNIT_FAMILIES.get(raw_unit.lower())
        if family is None:
            continue
        try:
            value = float(raw_value.replace(",", "."))
        except ValueError:
            continue
        claim = f"{raw_value} {raw_unit}"
        checked.append(claim)
        allowed = buckets.get(family) or set()
        if not allowed:
            # Nothing of this kind was supplied, so nothing of this kind may be claimed.
            rejected.append(claim)
        elif not _matches(value, family, allowed):
            rejected.append(claim)
    return (not rejected), checked, rejected
