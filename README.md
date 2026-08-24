# WeatherGPT

**SIH26068 — Ministry of Earth Sciences / IMD · Disaster Management**

A conversational, multilingual, voice-enabled weather assistant that turns
forecast data into plain-language, actionable guidance for farmers, fishermen,
travellers and flood-prone communities across India.

```
        Open-Meteo (live)                    Anthropic (claude-sonnet-4-6)
               │                                          │
               ▼                                          ▼
        ┌──────────────┐                       ┌────────────────────┐
        │  Weather     │                       │  Structured        │
        │  provider    │                       │  extraction +      │
        └──────┬───────┘                       │  grounded writing  │
               │                               └─────────┬──────────┘
               ▼                                         │
     ╔═══════════════════════╗                           │
     ║  WEATHER RISK ENGINE  ║ ◄─────────────────────────┘
     ║  the only place risk  ║
     ║  is ever computed     ║
     ╚═══════╤═══════════════╝
             │  { risk_score, risk_level, detected_hazard }
   ┌─────────┼───────────┬──────────────┬───────────────┐
   ▼         ▼           ▼              ▼               ▼
 /chat    /alerts   24h timeline   India risk map   emergency mode
```

---

## Why it is built this way

**One risk engine.** Every feature that mentions risk calls
`app/services/risk_engine.py`. Nothing else computes a score. That is what makes
it impossible for the map to say *Moderate* while the alert says *Severe* for
the same place — there is no second implementation to drift.

**Answers cannot invent numbers.** Generated prose is scanned for measurement
claims and each one is checked against the values the provider actually
returned. A claim that matches nothing causes the whole answer to be discarded
in favour of a template built from real values. The fallback for a hallucination
is a correct answer, not an apology.

**Degradation is designed, not accidental.** No API key, no network, a failed
translation, a dead TTS service — each has a defined path. Quality drops;
availability does not. Whatever degraded is reported in the response's
`degraded` object rather than hidden.

**Multilingual all the way down.** Six languages end to end. Language detection
runs offline on the Unicode script, which is exact for Telugu and separates
Assamese from Bengali by two letters Bengali does not use. When the LLM is
unavailable the assistant answers from localised templates — it never silently
falls back to English.

---

## Quick start

Two terminals. Neither step needs an API key to run.

```bash
# ── Backend ───────────────────────────────────────────────
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env          # optional; every value has a default
python run.py                       # http://127.0.0.1:8000  ·  docs at /docs

# ── Frontend ──────────────────────────────────────────────
cd frontend
npm install
npm run dev                         # http://127.0.0.1:5173
```

The Vite dev server proxies `/api` (WebSockets included) to FastAPI, so local
development never depends on CORS configuration.

### Configuration

Everything is environment-driven; see [`.env.example`](.env.example). The values
that change behaviour most:

| Variable | Default | Effect |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(unset)* | Unset ⇒ rule-based understanding and templated answers |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Model used for extraction and writing |
| `WEATHER_DATA_MODE` | `live` | `fixture` serves deterministic offline data for dev/CI |
| `ALERT_INTERVAL_MINUTES` | `30` | Scan cadence for the single alert scheduler |
| `ALERT_MIN_RISK_SCORE` | `61` | The "High" band; the floor for raising an alert |
| `TWILIO_*` | *(unset)* | Unset ⇒ alerts log to the console instead of texting |

`WEATHER_DATA_MODE=fixture` is for offline development and tests. Fixture
responses are tagged `data_source: "fixture"` and the UI shows a **SIMULATED
DATA** badge at every breakpoint. Simulated data cannot appear in live mode.

---

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/chat` | Ask a question. Returns answer, explanation, actions, risk, impacts, raw data, verification |
| `POST` | `/voice-chat` | Same, from an audio upload (or a browser-supplied transcript) |
| `GET` | `/weather/current` | Current conditions plus risk and impact cards |
| `GET` | `/weather/timeline` | Next N hours, each with its own risk level |
| `GET` | `/weather/forecast` | 7-day forecast with per-day risk |
| `GET` | `/climate-trend` | Historical anomaly summary for the month so far |
| `GET` | `/risk` | Risk for one location |
| `GET` | `/risk-map` | Per-location risk for the India map |
| `GET` | `/alerts` | Active alerts, with localised hazard and severity labels |
| `POST` | `/alerts/subscribe` | Subscribe a location and hazard set |
| `POST` | `/alerts/scan` | Run the scan immediately (same job the scheduler runs) |
| `WS` | `/ws/alerts` | Live alert push; sends a snapshot on connect |
| `GET` | `/health`, `/config` | Capabilities, so the UI can hide what cannot work |
| `GET` | `/historical-events` | Reference events used for context comparisons |

Interactive documentation at `/docs`.

### The risk contract

Every risk-bearing response carries the same shape:

```json
{ "risk_score": 76, "risk_level": "High", "detected_hazard": "Heavy Rainfall" }
```

Bands: **0–30** Low · **31–60** Moderate · **61–80** High · **81–100** Severe.
Hazards: Heavy Rainfall, Flood Risk, Strong Wind, Extreme Heat, Lightning/Storm.

Thresholds follow IMD's published rainfall categories (7.6 / 35.6 / 64.5 /
115.6 / 204.5 mm per 24 h) and conventional wind and heat advisory breakpoints,
so the numbers mean something to a domain expert.

---

## Layout

```
backend/
  app/
    main.py              FastAPI app, CORS, the single alert scheduler
    config.py            All configuration, environment-driven
    schemas.py           Wire contract shared with the frontend
    db.py                SQLite (PostgreSQL is a driver swap)
    routes/              chat · weather · alerts · risk · meta
    services/
      risk_engine.py     ◄── the single source of truth for risk
      chat_engine.py     Orchestration: detect → understand → fetch → score → verify
      weather.py         Open-Meteo client + offline fixture provider
      llm.py             Anthropic, forced tool use, isolated failures
      verification.py    Numeric grounding check
      nlp_fallback.py    Rule-based understanding when the LLM is unavailable
      language.py        Offline script-based detection; translation
      i18n.py            Localised templates for all six languages
      advisory.py        Plain-language explanation, impacts, emergency briefs
      alerts.py          Scan job, WebSocket hub, Twilio
      climate.py         Historical anomaly analysis
      history.py         Threshold-matched historical comparisons
      memory.py          Multi-turn session memory
      speech.py          Whisper transcription, gTTS synthesis
  tests/                 101 tests: risk engine, eval harness, edge cases, API
frontend/
  src/
    App.jsx              Splash → landing → dashboard
    scene/               Three.js background that reacts to conditions
    components/          Dashboard panels
    api/client.js        Typed-ish client; every failure becomes a safe message
docs/DEMO_SCRIPT.md      Step-by-step live demo
```

---

## Tests

```bash
cd backend && python -m pytest tests/ -q
```

101 tests, no network required — they run against the fixture provider with the
LLM disabled, which means they exercise the degraded path by default. That is
deliberate: the degraded path is the one that must never break.

Coverage includes the risk-engine band boundaries and hazard discrimination, a
20-case eval harness (varied phrasing, misspellings, five languages, multi-turn
follow-ups, off-topic queries), the eight edge cases from the brief, and a
cross-feature invariant test asserting that `/chat`, `/risk`, `/risk-map` and
stored alerts report identical scores for the same location.

To evaluate the LLM path instead, export `ANTHROPIC_API_KEY` and unset
`LLM_ENABLED=false` in `tests/conftest.py`.

---

## Optional capabilities

Both are feature-detected at runtime and reported by `/health`; neither is
required for the app to start.

- **Voice input.** `faster-whisper` transcribes server side. The browser's own
  SpeechRecognition is used when available and sent as `client_transcript`, so
  voice still works on a deployment without the Whisper model installed.
- **Voice output.** gTTS, with an offline `pyttsx3` path when installed. If
  synthesis fails the text answer is still returned, with the reason in
  `degraded.tts_error`.

Assamese has no gTTS voice; the closest available voice is used and the
substitution is stated in the response rather than passed off silently.

---

## Swapping in a real NWP feed

`app/services/weather.py` normalises provider output into a provider-agnostic
shape before anything else sees it. Pointing at a GFS/WRF feed from an IMD or
NOAA mirror means writing one new provider class — the routes, the risk engine
and the frontend are untouched. The Open-Meteo endpoints are already
environment-overridable for a drop-in mirror.

---

## Limitations

- Impact guidance is general, not professional agricultural, medical or
  disaster-management advice. The disclaimer is shown in the UI.
- Historical comparisons convey scale only. Figures are approximate published
  estimates, each carrying its source note, and the wording never predicts
  recurrence.
- The gazetteer covers 85 major Indian locations for offline geocoding; live
  mode uses the full Open-Meteo geocoder and falls back to the gazetteer only
  if that is unreachable.
- SQLite suits a single-node deployment. The schema maps 1:1 onto PostgreSQL.
