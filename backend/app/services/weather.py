"""Weather data access.

Two providers sit behind one interface:

* ``OpenMeteoProvider`` — the real, production path. No API key needed.
* ``FixtureProvider``  — deterministic offline snapshots for dev/CI where the
  network is unavailable. Selected only by ``WEATHER_DATA_MODE=fixture``.

Every response carries ``source`` ("live" | "fixture") so nothing simulated can
be presented as live data further up the stack.

The normalised shapes returned here (``current`` / ``hourly`` / ``daily``) are
provider-agnostic on purpose: swapping in a GFS/WRF feed from an IMD or NOAA
mirror means writing a new provider, not touching the routes or risk engine.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import math
import re
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import DATA_DIR, get_settings
from . import wmo

log = logging.getLogger("weathergpt.weather")


class WeatherError(RuntimeError):
    """Raised when weather data cannot be obtained. Message is user-safe."""


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float
    admin1: str | None = None
    country: str | None = "India"
    timezone: str | None = "Asia/Kolkata"

    @property
    def label(self) -> str:
        if self.admin1 and self.admin1.lower() != self.name.lower():
            return f"{self.name}, {self.admin1}"
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WeatherBundle:
    location: Location
    current: dict[str, Any]
    hourly: list[dict[str, Any]]
    daily: list[dict[str, Any]]
    source: str
    fetched_at: str
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Gazetteer (offline geocoding fallback + risk-map tracked locations)
# ---------------------------------------------------------------------------
_GAZETTEER: list[dict[str, Any]] | None = None


def _gazetteer() -> list[dict[str, Any]]:
    global _GAZETTEER
    if _GAZETTEER is None:
        path = DATA_DIR / "gazetteer.json"
        try:
            _GAZETTEER = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - packaging error
            log.error("gazetteer unreadable: %s", exc)
            _GAZETTEER = []
    return _GAZETTEER


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def gazetteer_locations() -> list[Location]:
    return [_entry_to_location(e) for e in _gazetteer()]


def _entry_to_location(entry: dict[str, Any]) -> Location:
    return Location(
        name=entry["name"],
        latitude=float(entry["latitude"]),
        longitude=float(entry["longitude"]),
        admin1=entry.get("admin1"),
        timezone=entry.get("timezone", "Asia/Kolkata"),
    )


def native_lookup(query: str) -> Location | None:
    """Match a place written in Devanagari/Telugu/Bengali/Assamese script.

    ``_normalise`` strips non-ASCII, so native names need their own pass. Longest
    name first, so "New Delhi" wins over a shorter substring of it.
    """
    raw = (query or "").strip()
    if not raw:
        return None
    candidates: list[tuple[str, dict[str, Any]]] = []
    for entry in _gazetteer():
        for native in entry.get("native", []):
            candidates.append((native, entry))
    for native, entry in sorted(candidates, key=lambda pair: -len(pair[0])):
        if native in raw:
            return _entry_to_location(entry)
    return None


def nearest_location(latitude: float, longitude: float) -> Location | None:
    """Closest gazetteer entry to a coordinate.

    Open-Meteo's geocoder is forward-only, so a device coordinate is resolved to
    the nearest place the app actually covers. The caller is expected to present
    it as the nearest known city, not as the user's exact position.
    """
    entries = _gazetteer()
    if not entries:
        return None

    def distance_km(entry: dict[str, Any]) -> float:
        # Equirectangular approximation: accurate enough at city separation and
        # far cheaper than haversine over a few dozen candidates.
        lat1, lon1 = math.radians(latitude), math.radians(longitude)
        lat2, lon2 = math.radians(float(entry["latitude"])), math.radians(float(entry["longitude"]))
        x = (lon2 - lon1) * math.cos((lat1 + lat2) / 2)
        y = lat2 - lat1
        return math.sqrt(x * x + y * y) * 6371.0

    best = min(entries, key=distance_km)
    return Location(
        name=best["name"],
        latitude=float(best["latitude"]),
        longitude=float(best["longitude"]),
        admin1=best.get("admin1"),
        timezone=best.get("timezone", "Asia/Kolkata"),
    )


def gazetteer_lookup(query: str, cutoff: float = 0.72) -> Location | None:
    """Offline geocoding with misspelling tolerance ('Vijaywada' -> Vijayawada)
    and native-script support ('గువాహటిలో' -> Guwahati).

    City names always outrank state names, so "Puri, Odisha" resolves to Puri
    and not to whichever city happens to represent Odisha. A bare state name
    still falls back to its first listed city.
    """
    native = native_lookup(query)
    if native is not None:
        return native

    q = _normalise(query)
    if not q:
        return None

    cities: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}
    for entry in _gazetteer():
        cities.setdefault(_normalise(entry["name"]), entry)
        for alias in entry.get("aliases", []):
            cities.setdefault(_normalise(alias), entry)
        if entry.get("admin1"):
            states.setdefault(_normalise(entry["admin1"]), entry)

    def contained(index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        # Longest key first, so "Cherrapunji, Meghalaya" matches Cherrapunji.
        for key in sorted((k for k in index if len(k) >= 4), key=len, reverse=True):
            if key in q or q in key:
                return index[key]
        return None

    entry = (
        cities.get(q)
        or states.get(q)
        or contained(cities)
        or contained(states)
    )
    if entry is None:
        match = difflib.get_close_matches(q, list(cities), n=1, cutoff=cutoff)
        if match:
            entry = cities[match[0]]
    if entry is None:
        return None
    return _entry_to_location(entry)


# ---------------------------------------------------------------------------
# Tiny TTL cache — keeps demo clicking from hammering the upstream API
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()


def _cache_get(key: str) -> Any | None:
    ttl = get_settings().weather_cache_seconds
    with _cache_lock:
        hit = _cache.get(key)
        if hit and (time.time() - hit[0]) < ttl:
            return hit[1]
        if hit:
            _cache.pop(key, None)
    return None


def _cache_put(key: str, value: Any) -> None:
    with _cache_lock:
        _cache[key] = (time.time(), value)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------
# Open-Meteo (live)
# ---------------------------------------------------------------------------
CURRENT_FIELDS = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,"
    "weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
)
HOURLY_FIELDS = (
    "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,"
    "visibility,wind_speed_10m,wind_gusts_10m,cape"
)
DAILY_FIELDS = (
    "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,sunrise,sunset"
)


def _http_get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    try:
        with httpx.Client(timeout=settings.weather_timeout_seconds, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException as exc:
        raise WeatherError("The weather service is taking too long to respond. Please try again.") from exc
    except httpx.HTTPStatusError as exc:
        raise WeatherError(f"The weather service returned an error ({exc.response.status_code}).") from exc
    except httpx.HTTPError as exc:
        raise WeatherError("The weather service is unreachable right now.") from exc
    except json.JSONDecodeError as exc:
        raise WeatherError("The weather service returned an unreadable response.") from exc


def _geocode_live(query: str) -> Location | None:
    settings = get_settings()
    payload = _http_get(
        settings.open_meteo_geocode_url,
        {"name": query.strip(), "count": 5, "language": "en", "format": "json"},
    )
    results = payload.get("results") or []
    if not results:
        return None
    # Prefer an Indian match when one exists — the product's primary audience.
    best = next((r for r in results if r.get("country_code") == "IN"), results[0])
    return Location(
        name=best.get("name", query),
        latitude=float(best["latitude"]),
        longitude=float(best["longitude"]),
        admin1=best.get("admin1"),
        country=best.get("country"),
        timezone=best.get("timezone", "Asia/Kolkata"),
    )


def geocode(query: str) -> Location | None:
    """Resolve a place name to coordinates.

    Live mode tries Open-Meteo first and falls back to the bundled gazetteer if
    the network fails, so a geocoder outage degrades instead of breaking.
    """
    if not query or not query.strip():
        return None
    key = f"geo:{_normalise(query)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached or None

    settings = get_settings()
    result: Location | None = None
    if not settings.use_fixtures:
        try:
            result = _geocode_live(query)
        except WeatherError as exc:
            log.warning("live geocoding failed for %r (%s); using gazetteer", query, exc)
    if result is None:
        result = gazetteer_lookup(query)

    _cache_put(key, result or False)
    return result


def _series(block: dict[str, Any], key: str) -> list[Any]:
    values = block.get(key)
    return list(values) if isinstance(values, list) else []


def _at(values: list[Any], index: int) -> Any:
    if 0 <= index < len(values):
        value = values[index]
        return value if value is not None else None
    return None


def _normalise_openmeteo(location: Location, payload: dict[str, Any]) -> WeatherBundle:
    cur = payload.get("current") or {}
    hourly_block = payload.get("hourly") or {}
    daily_block = payload.get("daily") or {}

    times = _series(hourly_block, "time")
    # Align the hourly window to "now" rather than to midnight.
    now_iso = cur.get("time")
    start = 0
    if now_iso and now_iso in times:
        start = times.index(now_iso)
    elif times:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for idx, t in enumerate(times):
            try:
                if datetime.fromisoformat(t) >= now - timedelta(hours=1):
                    start = idx
                    break
            except ValueError:
                continue

    hourly: list[dict[str, Any]] = []
    for i in range(start, min(start + 48, len(times))):
        code = _at(_series(hourly_block, "weather_code"), i)
        visibility_m = _at(_series(hourly_block, "visibility"), i)
        hourly.append(
            {
                "time": times[i],
                "temperature_c": _at(_series(hourly_block, "temperature_2m"), i),
                "humidity_pct": _at(_series(hourly_block, "relative_humidity_2m"), i),
                "precipitation_probability_pct": _at(_series(hourly_block, "precipitation_probability"), i),
                "precipitation_mm": _at(_series(hourly_block, "precipitation"), i),
                "wind_speed_kmh": _at(_series(hourly_block, "wind_speed_10m"), i),
                "wind_gust_kmh": _at(_series(hourly_block, "wind_gusts_10m"), i),
                "cape": _at(_series(hourly_block, "cape"), i),
                "visibility_km": round(visibility_m / 1000.0, 1) if isinstance(visibility_m, (int, float)) else None,
                "weather_code": code,
                "condition": wmo.describe(code),
            }
        )

    daily: list[dict[str, Any]] = []
    dtimes = _series(daily_block, "time")
    for i, day in enumerate(dtimes[:7]):
        code = _at(_series(daily_block, "weather_code"), i)
        daily.append(
            {
                "date": day,
                "temp_max_c": _at(_series(daily_block, "temperature_2m_max"), i),
                "temp_min_c": _at(_series(daily_block, "temperature_2m_min"), i),
                "precipitation_sum_mm": _at(_series(daily_block, "precipitation_sum"), i),
                "precipitation_probability_pct": _at(_series(daily_block, "precipitation_probability_max"), i),
                "wind_speed_max_kmh": _at(_series(daily_block, "wind_speed_10m_max"), i),
                "wind_gust_max_kmh": _at(_series(daily_block, "wind_gusts_10m_max"), i),
                "sunrise": _at(_series(daily_block, "sunrise"), i),
                "sunset": _at(_series(daily_block, "sunset"), i),
                "weather_code": code,
                "condition": wmo.describe(code),
            }
        )

    code = cur.get("weather_code")
    current = {
        "temperature_c": cur.get("temperature_2m"),
        "apparent_temperature_c": cur.get("apparent_temperature"),
        "humidity_pct": cur.get("relative_humidity_2m"),
        "precipitation_mm": cur.get("precipitation"),
        "wind_speed_kmh": cur.get("wind_speed_10m"),
        "wind_gust_kmh": cur.get("wind_gusts_10m"),
        "wind_direction_deg": cur.get("wind_direction_10m"),
        "pressure_hpa": cur.get("pressure_msl"),
        "cloud_cover_pct": cur.get("cloud_cover"),
        "weather_code": code,
        "condition": wmo.describe(code),
        "is_day": bool(cur.get("is_day")) if cur.get("is_day") is not None else None,
        "observed_at": cur.get("time"),
        # Nowcast probability/visibility come from the aligned first hourly step.
        "precipitation_probability_pct": hourly[0]["precipitation_probability_pct"] if hourly else None,
        "visibility_km": hourly[0]["visibility_km"] if hourly else None,
    }

    return WeatherBundle(
        location=location,
        current=current,
        hourly=hourly,
        daily=daily,
        source="live",
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        raw=payload,
    )


# ---------------------------------------------------------------------------
# Fixture provider (offline / CI only)
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, dict[str, Any]] = {
    "calm": {"base_temp": 29.0, "rain_mm": 0.0, "prob": 8, "wind": 11.0, "gust": 18.0, "code": 1, "humidity": 54},
    "cloudy": {"base_temp": 28.0, "rain_mm": 0.2, "prob": 35, "wind": 15.0, "gust": 24.0, "code": 3, "humidity": 68},
    "rain": {"base_temp": 26.0, "rain_mm": 6.5, "prob": 82, "wind": 22.0, "gust": 38.0, "code": 63, "humidity": 88},
    "storm": {"base_temp": 25.0, "rain_mm": 6.0, "prob": 93, "wind": 33.0, "gust": 58.0, "code": 95, "humidity": 92},
    "flood": {"base_temp": 24.5, "rain_mm": 29.0, "prob": 97, "wind": 34.0, "gust": 58.0, "code": 82, "humidity": 96},
    "heat": {"base_temp": 43.0, "rain_mm": 0.0, "prob": 2, "wind": 13.0, "gust": 21.0, "code": 0, "humidity": 22},
    "wind": {"base_temp": 27.0, "rain_mm": 1.0, "prob": 40, "wind": 68.0, "gust": 96.0, "code": 3, "humidity": 70},
    "fog": {"base_temp": 14.0, "rain_mm": 0.0, "prob": 10, "wind": 6.0, "gust": 10.0, "code": 45, "humidity": 95},
}

_SCENARIO_ORDER = ("calm", "cloudy", "rain", "storm", "flood", "heat", "wind", "fog")

# Locations pinned to a scenario so the offline demo is stable and legible.
_PINNED: dict[str, str] = {
    "guwahati": "flood",
    "dibrugarh": "flood",
    "silchar": "flood",
    "cherrapunji": "flood",
    "mumbai": "storm",
    "chennai": "rain",
    "kochi": "rain",
    "jaisalmer": "heat",
    "bikaner": "heat",
    "jodhpur": "heat",
    "ratnagiri": "wind",
    "puri": "wind",
    "paradip": "wind",
    "new delhi": "fog",
    "shillong": "rain",
    "patna": "storm",
    "vijayawada": "cloudy",
    "bengaluru": "calm",
    "hyderabad": "calm",
}


def _scenario_for(location: Location) -> str:
    import os

    forced = os.getenv("WEATHER_FIXTURE_SCENARIO", "").strip().lower()
    if forced in SCENARIOS:
        return forced
    pinned = _PINNED.get(location.name.lower())
    if pinned:
        return pinned
    digest = hashlib.sha256(f"{location.name}|{round(location.latitude,2)}".encode()).digest()
    return _SCENARIO_ORDER[digest[0] % len(_SCENARIO_ORDER)]


def _local_now(location: Location) -> datetime:
    """Current time at the location, as a naive timestamp.

    Open-Meteo returns hourly times already in the location's timezone and
    without an offset suffix; the fixture provider has to match that exactly, or
    the offline demo shows hours that disagree with the user's own clock.
    """
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(location.timezone or "Asia/Kolkata")
    except Exception:  # noqa: BLE001 - unknown tz name, fall back to UTC
        tz = timezone.utc
    return datetime.now(tz).replace(tzinfo=None, minute=0, second=0, microsecond=0)


def _fixture_bundle(location: Location) -> WeatherBundle:
    """Deterministic synthetic weather. Never reachable in live mode."""
    scenario = _scenario_for(location)
    spec = SCENARIOS[scenario]
    now = _local_now(location)

    hourly: list[dict[str, Any]] = []
    for h in range(48):
        t = now + timedelta(hours=h)
        # Smooth diurnal temperature curve peaking mid-afternoon.
        diurnal = -math.cos((t.hour - 3) / 24.0 * 2 * math.pi) * 3.2
        decay = max(0.25, 1.0 - h * 0.018)  # events ease off over the window
        rain = round(spec["rain_mm"] * decay * (0.55 + 0.45 * math.sin(h / 3.0)) ** 2, 2)
        rain = max(0.0, rain)
        wind = round(spec["wind"] * (0.85 + 0.15 * math.sin(h / 5.0)) * decay + 4, 1)
        hourly.append(
            {
                "time": t.strftime("%Y-%m-%dT%H:00"),
                "temperature_c": round(spec["base_temp"] + diurnal, 1),
                "humidity_pct": spec["humidity"],
                "precipitation_probability_pct": int(max(0, min(100, spec["prob"] * decay))),
                "precipitation_mm": rain,
                "wind_speed_kmh": wind,
                "wind_gust_kmh": round(wind * 1.55, 1),
                "cape": 2400 if spec["code"] in wmo.THUNDER_CODES else 320,
                "visibility_km": 1.0 if spec["code"] in wmo.FOG_CODES else 12.0,
                "weather_code": spec["code"],
                "condition": wmo.describe(spec["code"]),
            }
        )

    daily: list[dict[str, Any]] = []
    for d in range(7):
        day = (now + timedelta(days=d)).date()
        window = hourly[d * 6 : d * 6 + 24] or hourly[:24]
        temps = [x["temperature_c"] for x in window]
        daily.append(
            {
                "date": day.isoformat(),
                "temp_max_c": round(max(temps) + 1.5, 1),
                "temp_min_c": round(min(temps) - 2.0, 1),
                "precipitation_sum_mm": round(sum(x["precipitation_mm"] for x in window), 1),
                "precipitation_probability_pct": max(x["precipitation_probability_pct"] for x in window),
                "wind_speed_max_kmh": max(x["wind_speed_kmh"] for x in window),
                "wind_gust_max_kmh": max(x["wind_gust_kmh"] for x in window),
                "sunrise": f"{day.isoformat()}T05:52",
                "sunset": f"{day.isoformat()}T18:24",
                "weather_code": spec["code"],
                "condition": wmo.describe(spec["code"]),
            }
        )

    first = hourly[0]
    apparent = first["temperature_c"] + (2.6 if spec["humidity"] > 80 else 1.1)
    if scenario == "heat":
        apparent = first["temperature_c"] + 4.2
    current = {
        "temperature_c": first["temperature_c"],
        "apparent_temperature_c": round(apparent, 1),
        "humidity_pct": float(spec["humidity"]),
        "precipitation_mm": first["precipitation_mm"],
        "precipitation_probability_pct": first["precipitation_probability_pct"],
        "wind_speed_kmh": first["wind_speed_kmh"],
        "wind_gust_kmh": first["wind_gust_kmh"],
        "wind_direction_deg": 225.0,
        "pressure_hpa": 996.0 if scenario in {"storm", "flood"} else 1008.0,
        "cloud_cover_pct": 95.0 if spec["code"] >= 51 else 30.0,
        "visibility_km": first["visibility_km"],
        "weather_code": spec["code"],
        "condition": wmo.describe(spec["code"]),
        "is_day": True,
        "observed_at": first["time"],
    }

    return WeatherBundle(
        location=location,
        current=current,
        hourly=hourly,
        daily=daily,
        source="fixture",
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        raw={"fixture_scenario": scenario, "note": "SIMULATED DATA - offline fixture provider"},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def fetch_weather(location: Location) -> WeatherBundle:
    """Fetch current + 48h hourly + 7d daily for a location."""
    settings = get_settings()
    key = f"wx:{settings.weather_data_mode}:{round(location.latitude,3)}:{round(location.longitude,3)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    if settings.use_fixtures:
        bundle = _fixture_bundle(location)
    else:
        payload = _http_get(
            settings.open_meteo_forecast_url,
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "current": CURRENT_FIELDS,
                "hourly": HOURLY_FIELDS,
                "daily": DAILY_FIELDS,
                "timezone": location.timezone or "auto",
                "forecast_days": 7,
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
                "temperature_unit": "celsius",
            },
        )
        if not payload.get("current"):
            raise WeatherError("The weather service returned no current conditions for that location.")
        bundle = _normalise_openmeteo(location, payload)

    _cache_put(key, bundle)
    return bundle


def fetch_archive(location: Location, start: date, end: date) -> dict[str, Any]:
    """Daily historical archive for climate-trend analysis."""
    settings = get_settings()
    key = f"arch:{settings.weather_data_mode}:{location.latitude}:{location.longitude}:{start}:{end}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    if settings.use_fixtures:
        payload = _fixture_archive(location, start, end)
    else:
        payload = _http_get(
            settings.open_meteo_archive_url,
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum",
                "timezone": location.timezone or "auto",
            },
        )
    _cache_put(key, payload)
    return payload


def _fixture_archive(location: Location, start: date, end: date) -> dict[str, Any]:
    """Deterministic pseudo-archive with a mild warming/wetting signal."""
    times: list[str] = []
    tmax: list[float] = []
    tmin: list[float] = []
    tmean: list[float] = []
    precip: list[float] = []
    cursor = start
    seed = int(hashlib.sha256(f"{location.name}".encode()).hexdigest()[:8], 16)
    while cursor <= end:
        doy = cursor.timetuple().tm_yday
        monsoon = max(0.0, math.sin((doy - 150) / 215.0 * math.pi))  # Jun-Sep hump
        wiggle = ((seed + doy * 7 + cursor.year * 13) % 100) / 100.0
        base = 27.0 + 6.0 * math.sin((doy - 100) / 365.0 * 2 * math.pi)
        warming = (cursor.year - 2015) * 0.06
        times.append(cursor.isoformat())
        tmax.append(round(base + 5.0 + warming + wiggle * 2, 1))
        tmin.append(round(base - 5.0 + warming + wiggle, 1))
        tmean.append(round(base + warming + wiggle, 1))
        precip.append(round(monsoon * 16.0 * wiggle * (1 + (cursor.year - 2015) * 0.01), 1))
        cursor += timedelta(days=1)
    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "daily": {
            "time": times,
            "temperature_2m_max": tmax,
            "temperature_2m_min": tmin,
            "temperature_2m_mean": tmean,
            "precipitation_sum": precip,
        },
        "fixture": True,
    }


def next_hours(bundle: WeatherBundle, count: int = 24) -> list[dict[str, Any]]:
    return bundle.hourly[:count]


def precipitation_next(bundle: WeatherBundle, hours: int = 24) -> float:
    return round(sum(float(h.get("precipitation_mm") or 0.0) for h in bundle.hourly[:hours]), 1)


def max_in_window(bundle: WeatherBundle, key: str, hours: int = 24) -> float:
    values = [float(h[key]) for h in bundle.hourly[:hours] if isinstance(h.get(key), (int, float))]
    return round(max(values), 1) if values else 0.0
