# -*- coding: utf-8 -*-
"""Who is asking. One list, read by everything that varies by role.

Before this module the answer to "which roles exist?" was spelled out in five
places — the card builders in ``role_intel``, three parallel dictionaries beside
them for icon, heading and note, the action tables in ``advisory``, and a
separate list in the frontend. Adding a role meant finding all of them, and
missing one meant a role that half-existed.

A ``Role`` is only *description*. It says which measurements this reader cares
about first, which hazards they need shouted at them, and which of their own
cards are worth offering to the assistant as a question. It scores nothing,
fetches nothing and translates nothing: the sentence keys here are looked up in
``i18n`` at render time, in the reader's language.

`metrics` is ordered, and the order is the whole point — a driver is told
visibility before temperature because that is the number that decides their
morning, and a farmer is told rainfall before wind for the same reason. The keys
match the fields of ``schemas.CurrentWeatherOut``, so a client can look each one
up in the reading it already has rather than being sent the number twice.

`ask` pairs one of the role's own card ids with an English question. The chip a
reader taps is labelled with that card's *translated* title, so the offer is in
their language; the question travels to the assistant in English because that is
what the assistant's context is written in, and the answer comes back in the
reader's language the same way every other answer does.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    key: str
    icon: str
    heading_key: str
    # Ordered: the first metric is the one this reader looks at first.
    metrics: tuple[str, ...]
    # Hazards to raise above the rest of the list for this reader. An empty
    # tuple means "no reordering" — every hazard matters equally to them.
    alert_hazards: tuple[str, ...] = ()
    # (card id, English question) — offered as a chip labelled with that card.
    ask: tuple[tuple[str, str], ...] = ()
    # A disclosure, where the app cannot fully answer this role's real question.
    note_key: str = ""
    # Roles whose decisions are about *when*, so an hour-by-hour strip earns
    # its space on their screen.
    timing: bool = False


_TEMP = ("temperature_c", "apparent_temperature_c")
_RAIN = ("precipitation_mm", "precipitation_probability_pct")
_WIND = ("wind_speed_kmh", "wind_gust_kmh", "wind_direction_deg")


ROLES: dict[str, Role] = {
    "general": Role(
        key="general", icon="🌤️", heading_key="ri_heading_general",
        metrics=_TEMP + _RAIN + ("wind_speed_kmh", "humidity_pct"),
        ask=(
            ('outdoor', 'Is it a good day to be outdoors?'),
            ('umbrella', 'Do I need an umbrella today?'),
            ('hazards', 'What is the main weather risk tonight?'),
        ),
    ),
    "farmer": Role(
        key="farmer", icon="🌾", heading_key="ri_heading_farmer",
        metrics=_RAIN + ("humidity_pct",) + _WIND[:2] + _TEMP,
        alert_hazards=("Heavy Rainfall", "Lightning/Storm", "Strong Wind", "Extreme Heat"),
        ask=(
            ('field_advisory', 'Is today suitable for field work and spraying?'),
            ('irrigation', 'Should I irrigate today, given the rainfall forecast?'),
            ('crop_risk', 'What is the disease risk for my crop in these conditions?'),
        ),
    ),
    "marine": Role(
        # The brief's key. "Fisherman" is who mostly uses it, but a harbour
        # pilot and a ferry operator ask the same questions, and the corpus has
        # always called this reading "Marine intelligence" — the sentence keys
        # below predate the rename and already say so.
        key="marine", icon="🎣", heading_key="ri_heading_fisherman",
        metrics=_WIND + ("visibility_km", "pressure_hpa") + _RAIN,
        alert_hazards=("Strong Wind", "Lightning/Storm", "Heavy Rainfall"),
        ask=(
            ('fishing_conditions', 'Is it safe to go out, based on the wind and visibility you can measure?'),
            ('wind', 'What are the wind speed and gusts doing over the next 24 hours?'),
            ('visibility', 'How is visibility at sea right now?'),
        ),
        # The one role whose real question this app cannot fully answer: no
        # provider wired into it returns wave height, swell, tide or current.
        note_key="ri_note_marine",
        timing=True,
    ),
    "driver": Role(
        key="driver", icon="🚗", heading_key="ri_heading_driver",
        metrics=("visibility_km",) + _RAIN + _WIND[:2] + _TEMP[:1],
        alert_hazards=("Heavy Rainfall", "Flood Risk", "Strong Wind"),
        ask=(
            ('road_visibility', 'How is visibility for driving, and when does it improve?'),
            ('road_surface', 'Is there a waterlogging risk on the roads today?'),
            ('departure', 'When is the safest time to drive today?'),
        ),
        timing=True,
    ),
    "outdoor_worker": Role(
        key="outdoor_worker", icon="🦺", heading_key="ri_heading_outdoor_worker",
        metrics=_TEMP + ("humidity_pct",) + _WIND[:2] + _RAIN,
        alert_hazards=("Extreme Heat", "Lightning/Storm", "Strong Wind", "Heavy Rainfall"),
        ask=(
            ('work_window', 'Which hours are safest to work outdoors today?'),
            ('heat_stress', 'How much heat stress should I expect working outdoors today?'),
            ('lightning', 'Is it safe to work in the open with this storm risk?'),
        ),
        timing=True,
    ),
    "student": Role(
        key="student", icon="🎓", heading_key="ri_heading_student",
        metrics=_RAIN + _TEMP + ("wind_speed_kmh", "visibility_km"),
        alert_hazards=("Heavy Rainfall", "Lightning/Storm", "Extreme Heat"),
        ask=(
            ('college_commute', 'What should I expect on the way to and from college today?'),
            ('campus', 'Is it safe to be outdoors on campus right now?'),
            ('lightning_safety', 'Should I avoid exposed areas because of lightning?'),
        ),
        timing=True,
    ),
    "caregiver": Role(
        key="caregiver", icon="👨‍👩‍👧", heading_key="ri_heading_caregiver",
        metrics=_TEMP + ("humidity_pct",) + _RAIN + ("wind_speed_kmh",),
        alert_hazards=("Extreme Heat", "Heavy Rainfall", "Lightning/Storm"),
        ask=(
            ('vulnerable', 'What should I watch for in vulnerable people in these conditions?'),
            ('prepare', 'What should the household have ready?'),
            ('exposure', 'Should the people I care for stay indoors today?'),
        ),
    ),
}

DEFAULT_ROLE = "general"

# Keys that are a role under another name. Stored preferences, older clients and
# the eight releases that shipped `fisherman` all keep working: the alias is
# resolved here rather than migrated away, so nobody's saved choice is quietly
# changed into a different reading.
ALIASES: dict[str, str] = {
    "fisherman": "marine",
    # Eight readings left the selector. They are aliased rather than deleted,
    # because a stored preference is a choice somebody made and a key this build
    # no longer knows would silently become "general" — the same reading, but
    # arrived at by accident rather than by mapping.
    #
    # Each goes to the nearest kept reading: the commuter and the urban traveller
    # are a driver by another name, the household and the officials are all
    # asking the community question, and the rest — a traveller, a researcher, a
    # pilot, an event planner — have no specialist reading here any more and get
    # the everyday one.
    "commuter": "driver",
    "urban": "driver",
    "household": "caregiver",
    "government": "caregiver",
    "disaster_manager": "caregiver",
    "traveler": "general",
    "researcher": "general",
    "aviation": "general",
    "event_planner": "general",
}


def get(role: str | None) -> Role:
    """The named role, or the general reading. Never raises on an unknown key.

    An unknown role is a client sending a key this build does not have — an old
    tab, a typo in a URL. The general reading is true for everybody, so it is
    the honest thing to fall back to.
    """
    key = (role or DEFAULT_ROLE).strip().lower()
    key = ALIASES.get(key, key)
    return ROLES.get(key, ROLES[DEFAULT_ROLE])


def known(role: str | None) -> bool:
    key = (role or "").strip().lower()
    return ALIASES.get(key, key) in ROLES


def keys() -> tuple[str, ...]:
    return tuple(ROLES)
