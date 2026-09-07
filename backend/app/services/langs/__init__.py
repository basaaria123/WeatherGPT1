# -*- coding: utf-8 -*-
"""Languages added after the original six.

The first six (en, hi, te, bn, mr, as) are written inline in ``i18n.py``, one
language column per string. That reads well at six and stops reading at twelve,
so every language added since lives here instead: one module, one language, the
whole of it in one place a reviewer or a native speaker can read end to end.

A pack is merged into the same tables ``i18n`` already serves, so nothing
downstream knows the difference — ``sentence()``, ``profile_action()`` and the
rest are unchanged.

The important part is ``validate``. A missing key would not raise anywhere: the
accessors all fall back to English, so a half-translated language would ship as
a language that silently answers in English — exactly the failure this file
exists to end. So a pack that does not carry every key the English corpus has
fails at import, loudly, before anything can be served from it.
"""

from __future__ import annotations

from typing import Any

# Every section a pack must fill, and the shape it must fill it with.
#   flat   -> {key: str}
#   list   -> {key: [str, ...]}
#   nested -> {key: {inner: str}}
SECTIONS: dict[str, str] = {
    "conditions": "flat",
    "hazards": "flat",
    "levels": "flat",
    "sentences": "flat",
    "role_sentences": "flat",
    "drivers": "flat",
    "days": "flat",
    "impact_categories": "flat",
    "impact_status": "flat",
    "hazard_actions": "list",
    "profile_actions": "nested",
    "profile_reasons": "nested",
}


class PackError(ImportError):
    """A language pack that cannot be served honestly."""


def validate(code: str, pack: dict[str, Any], reference: dict[str, Any]) -> None:
    """Refuse a pack that would answer in English behind a translated label."""
    problems: list[str] = []

    if not isinstance(pack.get("terminator"), str) or not pack["terminator"]:
        problems.append("terminator: missing")

    for section, shape in SECTIONS.items():
        want = reference.get(section) or {}
        got = pack.get(section)
        if not isinstance(got, dict):
            problems.append(f"{section}: missing")
            continue

        missing = sorted(set(want) - set(got))
        unknown = sorted(set(got) - set(want))
        if missing:
            problems.append(f"{section}: missing {missing[:6]}{'…' if len(missing) > 6 else ''}")
        if unknown:
            problems.append(f"{section}: unknown {unknown[:6]}{'…' if len(unknown) > 6 else ''}")

        for key in sorted(set(want) & set(got)):
            value, expected = got[key], want[key]
            if shape == "list":
                if not isinstance(value, list) or len(value) != len(expected):
                    problems.append(f"{section}.{key}: expected {len(expected)} lines")
            elif shape == "nested":
                inner_missing = sorted(set(expected) - set(value if isinstance(value, dict) else {}))
                if inner_missing:
                    problems.append(f"{section}.{key}: missing {inner_missing}")
            elif not isinstance(value, str) or not value.strip():
                problems.append(f"{section}.{key}: empty")

    if problems:
        raise PackError(f"language pack '{code}' is incomplete: " + "; ".join(problems))


def invented_placeholders(pack: dict[str, Any], reference: dict[str, Any]) -> list[str]:
    """Templates carrying a ``{slot}`` English does not fill.

    Only extras are an error. Dropping one is a translator's call and often the
    right one — Hindi and Telugu both drop the ``{verb}``/``{noun}`` agreement
    slots from ``alert_some``, because neither language needs them — whereas a
    slot nothing fills raises KeyError in front of the reader.
    """
    import re

    slots = lambda text: set(re.findall(r"\{(\w+)\}", text))  # noqa: E731
    bad: list[str] = []
    for section in ("sentences", "role_sentences", "drivers", "days"):
        want, got = reference.get(section) or {}, pack.get(section) or {}
        for key in set(want) & set(got):
            extra = slots(got[key]) - slots(want[key])
            if extra:
                bad.append(f"{section}.{key}: {sorted(extra)}")
    return sorted(bad)


def load() -> dict[str, dict[str, Any]]:
    """Every pack in this package, keyed by language code.

    Discovered rather than listed, so adding a language is adding one file —
    the module name is the language code.
    """
    import importlib
    import pkgutil

    packs: dict[str, dict[str, Any]] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        pack = getattr(module, "PACK", None)
        if isinstance(pack, dict):
            packs[info.name] = pack
    return packs
