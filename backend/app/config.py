"""Central configuration for WeatherGPT.

Every tunable lives here and is sourced from the environment so the same code
runs in a hackathon demo, in CI, and against a production NWP feed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FIXTURE_DIR = DATA_DIR / "fixtures"


def _load_dotenv() -> None:
    """Read ``backend/.env`` into the environment, if it exists.

    Deliberately not python-dotenv: this is a dozen lines and the project keeps
    its dependency list short enough to fit a serverless bundle. Real
    environment variables always win, so a value set in the Vercel dashboard is
    never shadowed by a file left in a developer's checkout.
    """
    path = BASE_DIR.parent / ".env"
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


_load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _is_serverless() -> bool:
    """True on Vercel, AWS Lambda and similar function runtimes."""
    return any(
        os.getenv(name)
        for name in ("VERCEL", "AWS_LAMBDA_FUNCTION_NAME", "FUNCTIONS_WORKER_RUNTIME", "K_SERVICE")
    )


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # --- Anthropic / LLM ---------------------------------------------------
    # Which provider answers. "auto" prefers Gemini when its key is present,
    # then Anthropic; either way the rules-based path stays underneath both.
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "auto").strip().lower())
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "").strip())
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip())
    gemini_api_key: str = field(
        default_factory=lambda: (
            os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        ).strip()
    )
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip())
    gemini_api_base: str = field(
        default_factory=lambda: os.getenv(
            "GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta"
        ).strip().rstrip("/")
    )
    llm_timeout_seconds: float = field(default_factory=lambda: _env_float("LLM_TIMEOUT_SECONDS", 25.0))
    llm_max_retries: int = field(default_factory=lambda: _env_int("LLM_MAX_RETRIES", 1))
    llm_enabled: bool = field(default_factory=lambda: _env_bool("LLM_ENABLED", True))

    # --- Weather data source ----------------------------------------------
    # "live"    -> real Open-Meteo HTTP calls (default, the production path)
    # "fixture" -> deterministic bundled snapshots, for offline dev/CI only.
    weather_data_mode: str = field(default_factory=lambda: os.getenv("WEATHER_DATA_MODE", "live").strip().lower())
    open_meteo_forecast_url: str = field(
        default_factory=lambda: os.getenv("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
    )
    open_meteo_archive_url: str = field(
        default_factory=lambda: os.getenv("OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive")
    )
    open_meteo_geocode_url: str = field(
        default_factory=lambda: os.getenv("OPEN_METEO_GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search")
    )
    weather_timeout_seconds: float = field(default_factory=lambda: _env_float("WEATHER_TIMEOUT_SECONDS", 12.0))
    weather_cache_seconds: int = field(default_factory=lambda: _env_int("WEATHER_CACHE_SECONDS", 600))

    # --- Persistence -------------------------------------------------------
    # On a serverless host the project directory is read-only, so fall back to
    # /tmp. That storage is per-instance and short-lived — see docs/DEPLOYMENT.md.
    db_path: str = field(
        default_factory=lambda: os.getenv(
            "WEATHERGPT_DB",
            "/tmp/weathergpt.db" if _is_serverless() else str(BASE_DIR.parent / "weathergpt.db"),
        )
    )

    # --- Alert scheduler ---------------------------------------------------
    alert_interval_minutes: int = field(default_factory=lambda: _env_int("ALERT_INTERVAL_MINUTES", 30))
    # An in-process scheduler cannot run on a serverless host: there is no
    # long-lived process to hold it. Use a platform cron against /alerts/scan.
    scheduler_enabled: bool = field(
        default_factory=lambda: _env_bool("SCHEDULER_ENABLED", not _is_serverless())
    )
    alert_min_risk_score: int = field(default_factory=lambda: _env_int("ALERT_MIN_RISK_SCORE", 61))
    alert_dedup_hours: int = field(default_factory=lambda: _env_int("ALERT_DEDUP_HOURS", 6))

    # --- Twilio SMS --------------------------------------------------------
    twilio_account_sid: str = field(default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID", "").strip())
    twilio_auth_token: str = field(default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN", "").strip())
    twilio_from_number: str = field(default_factory=lambda: os.getenv("TWILIO_FROM_NUMBER", "").strip())

    # --- Speech ------------------------------------------------------------
    # Hosted speech-to-text. Tried ahead of Whisper when a key is present, and
    # it needs no model download, which is what makes voice work on serverless.
    elevenlabs_api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", "").strip())
    elevenlabs_stt_model: str = field(
        default_factory=lambda: os.getenv("ELEVENLABS_STT_MODEL", "scribe_v1").strip()
    )
    # Its own budget rather than a multiple of the weather timeout: a demo can
    # afford to wait for a transcription, but not to wait twice for one that is
    # never coming back.
    elevenlabs_timeout_seconds: float = field(
        default_factory=lambda: _env_float("ELEVENLABS_TIMEOUT_SECONDS", 30.0)
    )
    elevenlabs_api_base: str = field(
        default_factory=lambda: os.getenv("ELEVENLABS_API_BASE", "https://api.elevenlabs.io").strip().rstrip("/")
    )
    whisper_model: str = field(default_factory=lambda: os.getenv("WHISPER_MODEL", "base").strip())
    whisper_device: str = field(default_factory=lambda: os.getenv("WHISPER_DEVICE", "cpu").strip())
    max_audio_bytes: int = field(default_factory=lambda: _env_int("MAX_AUDIO_BYTES", 20 * 1024 * 1024))
    max_audio_seconds: int = field(default_factory=lambda: _env_int("MAX_AUDIO_SECONDS", 120))
    tts_enabled: bool = field(default_factory=lambda: _env_bool("TTS_ENABLED", True))

    # --- HTTP / CORS -------------------------------------------------------
    cors_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "CORS_ORIGINS",
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
            ],
        )
    )
    cors_allow_all: bool = field(default_factory=lambda: _env_bool("CORS_ALLOW_ALL", False))

    # --- Deployment --------------------------------------------------------
    # Routers are served at the root *and* under this prefix, so the API works
    # whether or not the platform strips the prefix before forwarding.
    api_mount_prefix: str = field(default_factory=lambda: os.getenv("API_MOUNT_PREFIX", "/api").strip())
    serverless: bool = field(default_factory=lambda: _is_serverless())

    # --- Behaviour ---------------------------------------------------------
    max_query_chars: int = field(default_factory=lambda: _env_int("MAX_QUERY_CHARS", 1200))
    session_ttl_seconds: int = field(default_factory=lambda: _env_int("SESSION_TTL_SECONDS", 60 * 60 * 6))
    max_session_turns: int = field(default_factory=lambda: _env_int("MAX_SESSION_TURNS", 12))

    @property
    def use_fixtures(self) -> bool:
        return self.weather_data_mode == "fixture"

    @property
    def twilio_configured(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number)

    @property
    def websockets_supported(self) -> bool:
        """Serverless functions cannot hold a socket open across invocations."""
        return not self.serverless

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_enabled and self.active_llm_provider)

    @property
    def active_llm_provider(self) -> str:
        """Which provider a call would actually use: "gemini", "anthropic" or ""."""
        if not self.llm_enabled:
            return ""
        if self.llm_provider == "gemini":
            return "gemini" if self.gemini_api_key else ""
        if self.llm_provider == "anthropic":
            return "anthropic" if self.anthropic_api_key else ""
        # auto
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "anthropic"
        return ""

    @property
    def active_llm_model(self) -> str:
        provider = self.active_llm_provider
        if provider == "gemini":
            return self.gemini_model
        if provider == "anthropic":
            return self.anthropic_model
        return ""


_settings: Settings | None = None


def get_settings() -> Settings:
    """Process-wide settings singleton (re-readable in tests via reset_settings)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Drop the cached settings so a test can re-read a mutated environment."""
    global _settings
    _settings = None
