"""WMO 4677 weather-code helpers.

Open-Meteo reports conditions as WMO codes; every human-readable condition
string and every UI scene key in the app derives from this one table.
"""

from __future__ import annotations

# code -> (label, scene). `scene` drives the animated 3D background in the UI.
WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Clear sky", "clear"),
    1: ("Mainly clear", "clear"),
    2: ("Partly cloudy", "cloudy"),
    3: ("Overcast", "cloudy"),
    45: ("Fog", "fog"),
    48: ("Depositing rime fog", "fog"),
    51: ("Light drizzle", "rain"),
    53: ("Moderate drizzle", "rain"),
    55: ("Dense drizzle", "rain"),
    56: ("Light freezing drizzle", "rain"),
    57: ("Dense freezing drizzle", "rain"),
    61: ("Slight rain", "rain"),
    63: ("Moderate rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Light freezing rain", "rain"),
    67: ("Heavy freezing rain", "rain"),
    71: ("Slight snowfall", "snow"),
    73: ("Moderate snowfall", "snow"),
    75: ("Heavy snowfall", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Slight rain showers", "rain"),
    81: ("Moderate rain showers", "rain"),
    82: ("Violent rain showers", "storm"),
    85: ("Slight snow showers", "snow"),
    86: ("Heavy snow showers", "snow"),
    95: ("Thunderstorm", "storm"),
    96: ("Thunderstorm with slight hail", "storm"),
    99: ("Thunderstorm with heavy hail", "storm"),
}

THUNDER_CODES = frozenset({95, 96, 99})
HEAVY_RAIN_CODES = frozenset({65, 67, 82})
RAIN_CODES = frozenset({51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82})
FOG_CODES = frozenset({45, 48})


def describe(code: int | None) -> str:
    """Human label for a WMO code; 'Unknown' rather than a guess when unmapped."""
    if code is None:
        return "Unknown"
    return WMO_CODES.get(int(code), ("Unknown", "clear"))[0]


def scene_for(code: int | None) -> str:
    """UI scene key ('clear' | 'cloudy' | 'rain' | 'storm' | 'fog' | 'snow')."""
    if code is None:
        return "clear"
    return WMO_CODES.get(int(code), ("Unknown", "clear"))[1]


def is_thunder(code: int | None) -> bool:
    return code is not None and int(code) in THUNDER_CODES


def is_rain(code: int | None) -> bool:
    return code is not None and int(code) in RAIN_CODES
