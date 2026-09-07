# -*- coding: utf-8 -*-
"""Can this app actually answer in the languages it offers?

A missing key is invisible in production: every accessor falls back to English,
so a half-translated language ships as a language that quietly answers in
English behind a translated name. That is the specific failure these tests
exist to prevent, and it is why the pack loader raises at import rather than
letting the fallback do its work.
"""

from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("WEATHER_DATA_MODE", "fixture")

from app.schemas import SUPPORTED_LANGUAGES
from app.services import advisory, i18n, langs, risk_engine, role_intel
from app.services.langs import invented_placeholders, validate

PACK_CODES = sorted(i18n._PACKS)
ALL_LANGS = sorted(i18n.LANGUAGES)


def test_there_are_packs_to_check():
    assert PACK_CODES, "no language packs were discovered"


@pytest.mark.parametrize("code", PACK_CODES)
def test_pack_is_complete(code):
    """The loader already refused an incomplete pack at import — this says so."""
    validate(code, i18n._PACKS[code], i18n._REFERENCE)


@pytest.mark.parametrize("code", PACK_CODES)
def test_pack_invents_no_placeholder(code):
    """A slot nothing fills raises KeyError in front of the reader."""
    assert invented_placeholders(i18n._PACKS[code], i18n._REFERENCE) == []


def test_offered_languages_are_the_answerable_ones():
    """/config is what the language picker believes."""
    assert set(SUPPORTED_LANGUAGES) == set(i18n.LANGUAGES)


@pytest.mark.parametrize("lang", ALL_LANGS)
def test_every_sentence_renders_in_every_language(lang):
    """No key falls through to English, and none renders with a hole in it."""
    english = i18n.SENTENCES["en"]
    table = i18n.SENTENCES[lang]
    missing = sorted(set(english) - set(table))
    assert not missing, f"{lang}: {missing[:8]}"
    if lang == "en":
        return
    same = [k for k, v in table.items() if v == english[k] and len(v) > 24]
    assert not same, f"{lang}: untranslated {same[:8]}"


@pytest.mark.parametrize("lang", ALL_LANGS)
def test_every_table_covers_every_language(lang):
    for name in ("CONDITIONS", "HAZARD_NAMES", "RISK_LEVELS", "DRIVERS", "DAYS",
                 "IMPACT_CATEGORIES", "IMPACT_STATUS"):
        table = getattr(i18n, name)
        assert lang in table, f"{name}: {lang}"
        assert set(table[lang]) == set(table["en"]), f"{name}: {lang}"
    assert lang in i18n.TERMINATORS
    for hazard, table in i18n.HAZARD_ACTIONS.items():
        assert len(table[lang]) == len(table["en"]), f"{hazard}: {lang}"
    for profile, families in i18n.PROFILE_ACTIONS.items():
        for family, table in families.items():
            assert table.get(lang), f"action {profile}/{family}: {lang}"
            assert i18n.PROFILE_REASONS[profile][family].get(lang), f"reason {profile}/{family}: {lang}"


@pytest.mark.parametrize("lang", ALL_LANGS)
def test_a_whole_answer_comes_back_in_the_reader_s_language(lang):
    """End to end: the advisory, the impact cards and the role panel together.

    Latin letters are the tell — outside English, a Latin run longer than a unit
    symbol means an English sentence leaked through the fallback.
    """
    from app.services import weather

    os.environ["WEATHER_FIXTURE_SCENARIO"] = "rain"
    weather.clear_cache()
    location = weather.gazetteer_lookup("Chennai")
    assert location is not None
    bundle = weather.fetch_weather(location)
    risk = risk_engine.assess(bundle)

    blob = " ".join(
        [
            advisory.smart_explanation(bundle, risk, lang),
            *(c.detail for c in advisory.impact_cards(bundle, risk, lang, "farmer")),
            *(a["action"] for a in advisory.build_advisory(risk, "farmer", lang, bundle=bundle)["actions"]),
            *(
                f"{c['title']} {c['headline']} {c['detail']}"
                for c in role_intel.build(bundle, risk, "caregiver", lang)["cards"]
            ),
        ]
    )
    assert blob.strip()
    if lang == "en":
        return
    # "km/h", "mm", "hPa" and the like are fine, and so is the place name — the
    # gazetteer carries it in Latin script and it arrives through a slot. A
    # five-letter Latin word that is neither is an English sentence.
    allowed = {"weathergpt"} | {w.lower() for w in re.findall(r"[A-Za-z]+", bundle.location.label)}
    leaked = [w for w in re.findall(r"[A-Za-z]{5,}", blob) if w.lower() not in allowed]
    assert not leaked, f"{lang}: English leaked through — {sorted(set(leaked))[:8]}"
