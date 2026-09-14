# -*- coding: utf-8 -*-
"""Who is asking. One table, read by everything that varies by role.

Before this module the answer to "which roles exist?" was spelled out in five
places — the card builders in ``role_intel``, three parallel dictionaries beside
them for icon, heading and note, the action tables in ``advisory``, and a
separate list in the frontend. Adding a role meant finding all of them, and
missing one meant a role that half-existed.

A ``Role`` is only *description*. It says which measurements this reader cares
about first, which hazards they need shouted at them, which readings make up
their panel and which of those are worth offering to the assistant as a
question. It scores nothing, fetches nothing and translates nothing: the
sentence keys here are looked up in ``i18n`` at render time, in the reader's
language.

THE ONE IDEA THIS FILE EXISTS TO ENFORCE. The weather is the same for everybody.
Twelve readers standing in the same street get the same temperature, the same
wind, the same hazard and the same risk score — the dashboard above this panel
is identical for all of them, and it must stay identical or the product is
lying. What changes is which of those numbers is read first, what the reader
calls the thing they are deciding, and what they should do about it. Every field
below is one of those three, and none of them can change a measurement.

    metrics    ordered, and the order is the whole point — a driver is told
               visibility before temperature because that is the number that
               decides their morning. Keys match ``schemas.CurrentWeatherOut``.
    impacts    which "Your Weather Impact" sectors this reader is shown, first
               one first. A view, not a permission: every sector is scored the
               same way for everybody, and the ones left out are the ones that
               were never about this reader.
    factors    what their insight line leads with.
    horizon_h  how far ahead they are actually planning.
    cards      their Role Intelligence panel, as (card id, reading, title key,
               icon). `reading` names a shared measurement reading in
               ``role_intel``; the title and icon rename it into this reader's
               vocabulary. Two roles can share a reading and call it different
               things, which is right — a visibility verdict is the same verdict
               whoever reads it, but "Road visibility" in front of a pilot is a
               card written for somebody else.
    ask        (card id, English question) — offered as a chip labelled with
               that card's *translated* title, so a Tamil reader is offered a
               Tamil chip without a new string being translated. The question
               travels in English because that is what the assistant's context
               is written in.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# (card id, reading, title key, icon). An empty title key or icon keeps the
# reading's own, which is what happens when a role calls a thing by its
# ordinary name.
CardSpec = tuple[str, str, str, str]


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
    # "Your Weather Impact" sectors, in this reader's order.
    impacts: tuple[str, ...] = ()
    # What their insight line leads with.
    factors: tuple[str, ...] = ("rain", "wind", "heat", "visibility")
    # How far ahead this reader is planning, in hours.
    horizon_h: int = 12
    # The Role Intelligence panel.
    cards: tuple[CardSpec, ...] = field(default_factory=tuple)


_TEMP = ("temperature_c", "apparent_temperature_c")
_RAIN = ("precipitation_mm", "precipitation_probability_pct")
_WIND = ("wind_speed_kmh", "wind_gust_kmh", "wind_direction_deg")
_VIS = ("visibility_km",)


ROLES: dict[str, Role] = {
    # -----------------------------------------------------------------------
    # The default. Everyday weather, and nothing about anybody's occupation.
    #
    # This reading used to be given the farming and fishing impact sectors,
    # which is how a reader who had told the product nothing about themselves
    # came to be shown "Farming — Caution". Not a bug in the scoring: the
    # sector list said to show it. A reader with no stated role has no stated
    # occupation either, and the honest reading is the one anybody can use.
    # -----------------------------------------------------------------------
    "general": Role(
        key="general", icon="🌤️", heading_key="ri_heading_general",
        metrics=_TEMP + _RAIN + ("wind_speed_kmh", "humidity_pct"),
        impacts=("everyday", "outdoor", "travel"),
        factors=("rain", "wind", "heat", "visibility"),
        cards=(
            ("umbrella", "umbrella", "", ""),
            ("comfort", "comfort", "", ""),
            ("outdoor", "outdoor", "", ""),
            ("hazards", "hazards", "", ""),
        ),
        ask=(
            ("outdoor", "Is it a good day to be outdoors?"),
            ("umbrella", "Do I need an umbrella today?"),
            ("hazards", "What is the main weather risk tonight?"),
        ),
    ),

    # --- 1. Farmer ---------------------------------------------------------
    "farmer": Role(
        key="farmer", icon="🌾", heading_key="ri_heading_farmer",
        metrics=_RAIN + ("humidity_pct",) + _WIND[:2] + _TEMP,
        alert_hazards=("Heavy Rainfall", "Lightning/Storm", "Strong Wind", "Extreme Heat"),
        impacts=("farming", "outdoor", "travel"),
        factors=("rain", "heat", "wind", "visibility"),
        timing=True,
        cards=(
            ("rain_impact", "rain_impact", "", ""),
            ("irrigation", "irrigation", "", ""),
            ("crop_risk", "crop_risk", "", ""),
            ("field_advisory", "field_advisory", "", ""),
            # "Best field work window" — the same daylight search the outdoor
            # worker's window uses, under the name a farmer would use for it.
            ("work_window", "work_window", "ri_field_window_title", "🌤️"),
        ),
        ask=(
            ("crop_risk", "What is the disease risk for my crop in these conditions?"),
            ("irrigation", "Should I irrigate today, given the rainfall forecast?"),
            ("field_advisory", "Is today suitable for field work and spraying?"),
        ),
    ),

    # --- 2. Marine / fisherman --------------------------------------------
    "marine": Role(
        # The brief's key. "Fisherman" is who mostly uses it, but a harbour
        # pilot and a ferry operator ask the same questions, and the corpus has
        # always called this reading "Marine intelligence".
        key="marine", icon="🎣", heading_key="ri_heading_fisherman",
        metrics=_WIND + _VIS + ("pressure_hpa",) + _RAIN,
        alert_hazards=("Strong Wind", "Lightning/Storm", "Heavy Rainfall"),
        impacts=("fishing", "outdoor", "travel"),
        factors=("wind", "rain", "visibility", "heat"),
        timing=True,
        cards=(
            ("fishing_conditions", "fishing_conditions", "", ""),
            ("wind", "wind", "ri_marine_wind_title", "🌬️"),
            ("storm_risk", "storm_risk", "", ""),
            ("visibility", "visibility", "", ""),
            ("departure", "departure", "ri_fishing_window_title", "🎣"),
        ),
        ask=(
            ("fishing_conditions", "Is it safe to go out, based on the wind and visibility you can measure?"),
            ("wind", "What are the wind speed and gusts doing over the next 24 hours?"),
            ("departure", "When is the best window to go out today?"),
        ),
        # The one role whose real question this app cannot fully answer: no
        # provider wired into it returns wave height, swell, tide or current.
        note_key="ri_note_marine",
    ),

    # --- 3. Aviation professional -----------------------------------------
    "aviation": Role(
        key="aviation", icon="✈️", heading_key="ri_heading_aviation",
        metrics=_VIS + _WIND + ("cloud_cover_pct",) + _RAIN,
        alert_hazards=("Lightning/Storm", "Strong Wind", "Heavy Rainfall"),
        # NOT the travel sector. Its detail sentence is "Rain may slow traffic
        # and reduce visibility", which is a road sentence on a pilot's screen —
        # and it made this reading's impact panel identical to the driver's in
        # all eight scenarios. What weather does to an aviation professional is
        # done to people on an apron and to the day around them.
        impacts=("outdoor", "everyday"),
        factors=("visibility", "wind", "rain", "heat"),
        # A shorter planning window than a driver's, which is also what stops
        # the two of them closing on the same "rain is unlikely over the next
        # eight hours" sentence.
        horizon_h=6,
        cards=(
            ("flight_conditions", "flight_conditions", "", ""),
            ("visibility", "visibility", "", ""),
            ("crosswind", "crosswind", "", ""),
            ("convective", "storm_risk", "ri_convective_title", "⛈️"),
            ("cloud", "cloud", "", ""),
        ),
        ask=(
            ("flight_conditions", "What do the current conditions mean for flight operations?"),
            ("visibility", "How are visibility and wind right now and over the next few hours?"),
            ("convective", "What is the thunderstorm risk in this area?"),
        ),
        # The disclosure that matters most in this product: an interpretation of
        # a public forecast is not aviation weather information and is not a
        # clearance. Saying so is not a disclaimer bolted on, it is the reading.
        note_key="ri_note_aviation",
    ),

    # --- 4. Disaster response manager -------------------------------------
    "disaster": Role(
        key="disaster", icon="🚨", heading_key="ri_heading_disaster",
        metrics=_RAIN + _WIND[:2] + _VIS + _TEMP[:1],
        alert_hazards=("Flood Risk", "Heavy Rainfall", "Lightning/Storm", "Strong Wind", "Extreme Heat"),
        impacts=("household", "travel", "outdoor"),
        factors=("rain", "wind", "visibility", "heat"),
        cards=(
            ("hazard_status", "hazards", "ri_hazard_status_title", "🚨"),
            ("impact_area", "impact_area", "", ""),
            ("escalation", "escalation", "", ""),
            ("response_priority", "response_priority", "", ""),
            ("official_status", "official_status", "", ""),
        ),
        ask=(
            ("escalation", "Is the weather risk increasing over the next few hours?"),
            ("hazard_status", "What hazards are developing in this area right now?"),
            ("response_priority", "What should responders prioritise in these conditions?"),
        ),
        note_key="ri_note_disaster",
    ),

    # --- 5. Government / smart city planner --------------------------------
    "smart_city": Role(
        key="smart_city", icon="🏙️", heading_key="ri_heading_smart_city",
        metrics=_RAIN + _WIND[:2] + _VIS + _TEMP,
        alert_hazards=("Flood Risk", "Heavy Rainfall", "Strong Wind", "Extreme Heat"),
        impacts=("travel", "household", "outdoor"),
        factors=("rain", "wind", "heat", "visibility"),
        cards=(
            ("urban_risk", "urban_risk", "", ""),
            ("waterlogging", "waterlogging", "", ""),
            ("mobility", "commute_risk", "ri_mobility_title", "🚦"),
            ("infrastructure", "infrastructure", "", ""),
            ("municipal_prep", "municipal_prep", "", ""),
        ),
        ask=(
            ("waterlogging", "What is the urban flood and waterlogging risk today?"),
            ("mobility", "How will these conditions affect city traffic and mobility?"),
            ("infrastructure", "Which infrastructure is most exposed in these conditions?"),
        ),
    ),

    # --- 6. Researcher / climate analyst -----------------------------------
    "researcher": Role(
        key="researcher", icon="🔬", heading_key="ri_heading_researcher",
        metrics=_TEMP + ("humidity_pct", "pressure_hpa") + _RAIN + _WIND[:2],
        alert_hazards=(),
        # Two rather than the everyday reading's three: with `travel` it was
        # byte-identical to `general` in every scenario, and a climate analyst
        # is not being advised about their commute.
        impacts=("everyday", "outdoor"),
        factors=("rain", "heat", "wind", "visibility"),
        cards=(
            ("anomaly", "anomaly", "", ""),
            ("trend", "trend", "", ""),
            ("historical", "historical", "", ""),
            ("forecast_data", "forecast_data", "", ""),
            ("indicators", "indicators", "", ""),
        ),
        ask=(
            ("historical", "How does this compare with the historical record for this place?"),
            ("trend", "What is the temperature and rainfall trend here?"),
            ("indicators", "What are the key weather indicators right now?"),
        ),
        note_key="ri_note_researcher",
    ),

    # --- 7. Student --------------------------------------------------------
    "student": Role(
        key="student", icon="🎓", heading_key="ri_heading_student",
        metrics=_RAIN + _TEMP + ("wind_speed_kmh",) + _VIS,
        alert_hazards=("Heavy Rainfall", "Lightning/Storm", "Extreme Heat"),
        impacts=("travel", "outdoor", "household"),
        factors=("rain", "visibility", "wind", "heat"),
        horizon_h=8,
        timing=True,
        cards=(
            ("campus", "campus", "ri_campus_title", "🎓"),
            ("college_commute", "commute_risk", "ri_college_title", "🎒"),
            ("outdoor_activity", "umbrella", "ri_outdoor_activity_title", "🏃"),
            ("lightning_safety", "storm_risk", "ri_lightning_safety_title", "⚡"),
            ("departure", "departure", "ri_move_window_title", "🕗"),
        ),
        ask=(
            ("college_commute", "What should I expect on the way to and from college today?"),
            ("campus", "Is it safe to be outdoors on campus right now?"),
            ("lightning_safety", "Should I avoid exposed areas because of lightning?"),
        ),
    ),

    # --- 8. Driver / commuter ----------------------------------------------
    "driver": Role(
        key="driver", icon="🚗", heading_key="ri_heading_driver",
        metrics=_VIS + _RAIN + _WIND[:2] + _TEMP[:1],
        alert_hazards=("Heavy Rainfall", "Flood Risk", "Strong Wind"),
        impacts=("travel", "outdoor"),
        factors=("visibility", "rain", "wind", "heat"),
        horizon_h=8,
        timing=True,
        cards=(
            ("road_visibility", "road_visibility", "", ""),
            ("road_surface", "road_surface", "", ""),
            ("crosswind", "crosswind", "", ""),
            ("commute_risk", "commute_risk", "", ""),
            ("departure", "departure", "", ""),
        ),
        ask=(
            ("road_visibility", "How is visibility for driving, and when does it improve?"),
            ("road_surface", "Is there a waterlogging risk on the roads today?"),
            ("departure", "When is the safest time to drive today?"),
        ),
    ),

    # --- 9. Outdoor worker -------------------------------------------------
    "outdoor_worker": Role(
        key="outdoor_worker", icon="🦺", heading_key="ri_heading_outdoor_worker",
        metrics=_TEMP + ("humidity_pct",) + _WIND[:2] + _RAIN,
        alert_hazards=("Extreme Heat", "Lightning/Storm", "Strong Wind", "Heavy Rainfall"),
        impacts=("outdoor", "travel", "household"),
        factors=("heat", "rain", "wind", "visibility"),
        timing=True,
        cards=(
            # The outdoor-suitability verdict under the name a site uses for it.
            # NOT the caregiver's `exposure` card: that one's detail line is
            # about people who move slowly, which is a sentence for somebody
            # else's screen.
            ("worksite_risk", "worksite", "ri_worksite_title", "🦺"),
            ("heat_stress", "heat_stress", "", ""),
            ("lightning", "lightning", "", ""),
            ("wind_exposure", "wind", "ri_wind_exposure_title", "💨"),
            ("work_window", "work_window", "", ""),
        ),
        ask=(
            ("work_window", "Which hours are safest to work outdoors today?"),
            ("heat_stress", "How much heat stress should I expect working outdoors today?"),
            ("lightning", "Is it safe to work in the open with this storm risk?"),
        ),
    ),

    # --- 10. Household -----------------------------------------------------
    "household": Role(
        key="household", icon="🏠", heading_key="ri_heading_household",
        metrics=_TEMP + ("humidity_pct",) + _RAIN + ("wind_speed_kmh",),
        alert_hazards=("Heavy Rainfall", "Extreme Heat", "Lightning/Storm", "Flood Risk"),
        impacts=("household", "everyday", "outdoor"),
        factors=("rain", "heat", "wind", "visibility"),
        cards=(
            ("home_comfort", "comfort", "ri_home_comfort_title", "🏠"),
            ("rain_outlook", "umbrella", "ri_rain_outlook_title", "🌧️"),
            ("prepare", "prepare", "", ""),
            ("home_exposure", "home_outdoor", "ri_home_exposure_title", "🚪"),
            ("evening", "evening", "ri_evening_title", "🌙"),
        ),
        ask=(
            ("prepare", "What should the household have ready for these conditions?"),
            ("evening", "Will the weather affect my evening?"),
            ("rain_outlook", "Should I keep weather-sensitive things indoors today?"),
        ),
    ),

    # --- 11. Traveler ------------------------------------------------------
    "traveler": Role(
        key="traveler", icon="🧳", heading_key="ri_heading_traveler",
        metrics=_VIS + _RAIN + _TEMP + _WIND[:2],
        alert_hazards=("Heavy Rainfall", "Lightning/Storm", "Strong Wind", "Flood Risk"),
        impacts=("travel", "outdoor", "everyday"),
        factors=("rain", "visibility", "wind", "heat"),
        timing=True,
        cards=(
            ("travel_conditions", "trip_outdoor", "ri_travel_cond_title", "🧳"),
            ("journey_risk", "commute_risk", "ri_journey_title", "🛣️"),
            ("visibility", "visibility", "", ""),
            ("rain_timing", "umbrella", "ri_rain_timing_title", "🌦️"),
            ("departure", "departure", "ri_departure_window_title", "🕗"),
        ),
        ask=(
            ("journey_risk", "Should I travel today, given these conditions?"),
            ("departure", "When should I leave to avoid the worst of the weather?"),
            ("rain_timing", "Will the weather disrupt my trip?"),
        ),
    ),

    # --- 12. Community / caregiver -----------------------------------------
    "caregiver": Role(
        key="caregiver", icon="👨‍👩‍👧", heading_key="ri_heading_caregiver",
        metrics=_TEMP + ("humidity_pct",) + _RAIN + ("wind_speed_kmh",),
        alert_hazards=("Extreme Heat", "Heavy Rainfall", "Lightning/Storm"),
        impacts=("outdoor", "household", "travel"),
        factors=("heat", "rain", "wind", "visibility"),
        cards=(
            ("vulnerable", "vulnerable", "", ""),
            ("exposure", "exposure", "", ""),
            ("prepare", "prepare", "", ""),
            ("home_rain", "home_rain", "", ""),
            ("community", "community", "ri_community_title", "🤝"),
        ),
        ask=(
            ("vulnerable", "What should I watch for in vulnerable people in these conditions?"),
            ("prepare", "What should the household have ready?"),
            ("exposure", "Should the people I care for stay indoors today?"),
        ),
    ),
}

DEFAULT_ROLE = "general"

# The order the selector and the onboarding grid present. The professions in
# the brief's order, then the everyday reading last — it is the default, not a
# profession, and putting it first implies the twelve below it are variations
# on it rather than readings of their own.
ORDER: tuple[str, ...] = (
    "farmer", "marine", "aviation", "disaster", "smart_city", "researcher",
    "student", "driver", "outdoor_worker", "household", "traveler", "caregiver",
    "general",
)

# Keys that are a role under another name. Stored preferences and older clients
# keep working: the alias is resolved here rather than migrated away, so nobody's
# saved choice is quietly changed into a different reading.
#
# `government`, `disaster_manager`, `traveler`, `researcher`, `aviation` and
# `household` were aliases in the seven-role build and are readings of their own
# again — they are gone from this table because they are now real keys.
ALIASES: dict[str, str] = {
    "fisherman": "marine",
    "commuter": "driver",
    "urban": "driver",
    "government": "smart_city",
    "disaster_manager": "disaster",
    "climate_analyst": "researcher",
    # Never had a reading of its own, and the brief does not ask for one. An
    # event planner is deciding whether an outdoor event can go ahead, which is
    # the traveller's question about a fixed place.
    "event_planner": "traveler",
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
    """Every role, in the order a selector should present them."""
    return ORDER
