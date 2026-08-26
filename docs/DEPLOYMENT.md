# Deploying WeatherGPT

## Read this first

WeatherGPT has three components that expect a **long-lived process**:

| Component | Needs |
|---|---|
| Alert scheduler (APScheduler) | A process that stays alive between requests |
| `/ws/alerts` WebSocket | A connection held open across requests |
| SQLite alert store | A writable disk that persists |

Serverless platforms provide none of these. The app detects a serverless runtime
and degrades cleanly rather than failing — but you should choose deliberately:

| | **Split deploy** *(recommended)* | **All-Vercel** |
|---|---|---|
| Frontend | Vercel | Vercel |
| Backend | Render / Railway / Fly.io | Vercel functions |
| Chat, weather, forecast, risk map | ✅ | ✅ |
| Alerts stored and retrievable | ✅ | ⚠️ ephemeral |
| Live alert push | ✅ WebSocket | ⚠️ polling |
| Scheduled scans | ✅ every 30 min | ⚠️ cron, daily on Hobby |
| Server-side voice input | ✅ Whisper | ❌ browser only |
| Effort | Two deploys | One deploy |

**For the SIH demo, all-Vercel is fine** — every headline feature in
`DEMO_SCRIPT.md` works, and the alert step uses a manual scan anyway. For
anything resembling real use, split it.

---

## Option A — All-Vercel (single deploy)

`vercel.json` in the repo root already declares both services and the routing:
`/api/*` → FastAPI, everything else → the Vite build.

The backend service sets `"entrypoint": "main.py"`, resolved relative to its
`root`. Vercel's Python runtime requires this explicitly once it detects
FastAPI — without it the build fails with *"must specify an entrypoint for
runtime python"*. `backend/main.py` re-exports the ASGI app from
`backend/app/main.py`; keep it if you move things around.

### 1. Import the repo

Vercel detects `frontend` (Vite) and `backend` (FastAPI). The committed
`vercel.json` supplies the multi-service config it asks for.

### 2. Set environment variables

Project → Settings → Environment Variables:

| Variable | Value | Why |
|---|---|---|
| `GEMINI_API_KEY` | your key | Without it, answers use the templated fallback |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Optional. Larger flash models return 503 under load |
| `LLM_PROVIDER` | `gemini` | Optional. `auto` also works; `anthropic` selects the other provider |
| `ELEVENLABS_API_KEY` | your key | Server-side speech-to-text without shipping Whisper's weights |
| `ANTHROPIC_API_KEY` | optional | The alternative provider |
| `WEATHER_DATA_MODE` | `live` | The default; set explicitly so it is visible |
| `TWILIO_ACCOUNT_SID` / `_AUTH_TOKEN` / `_FROM_NUMBER` | optional | Omit and alerts log instead of texting |

You do **not** need to set `SCHEDULER_ENABLED`, `WEATHERGPT_DB` or
`API_MOUNT_PREFIX` — the app detects the serverless runtime and adjusts:
the in-process scheduler is disabled, the database moves to `/tmp`, and the API
is served at both `/chat` and `/api/chat` so it works whether or not the
platform strips the prefix.

`CORS_*` is irrelevant here: the rewrite makes both services same-origin.

### 3. Deploy, then verify

```bash
curl -s https://<your-app>.vercel.app/api/health | python3 -m json.tool
```

Expect:

```json
{
  "status": "ok",
  "data_source": "live",
  "llm": { "available": true },
  "alerts": { "scheduler_enabled": false, "websockets_supported": false },
  "runtime": { "serverless": true }
}
```

`scheduler_enabled: false` and `websockets_supported: false` are **correct** on
Vercel. The frontend reads them from `/config` and switches the alert feed to
polling — the status dot in the header turns blue and reads "Alerts updating
periodically" rather than pretending to be live.

### 4. Seed the alert feed

The cron in `vercel.json` runs daily (`0 1 * * *`), because **Vercel's Hobby plan
rejects sub-daily schedules at deploy time**. Daily is too slow for real alerting.

- **On Pro:** change the schedule to `0 */6 * * *` (every six hours).
- **On Hobby:** leave it daily and drive scans from outside, e.g. a GitHub
  Actions workflow on a schedule, or any external cron service, hitting
  `POST https://<your-app>.vercel.app/api/alerts/scan`.

For a demo, just run it by hand — this is what the demo script does:

```bash
curl -X POST https://<your-app>.vercel.app/api/alerts/scan
```

### What is degraded, precisely

- **Alerts do not persist.** SQLite lives in `/tmp`, which is per-instance and
  short-lived, so an alert created by one invocation may be invisible to the
  next. To fix properly, point the store at a managed database — the schema in
  `backend/app/db.py` maps 1:1 onto PostgreSQL.
- **No WebSocket push.** The client polls `/api/alerts` instead. Alerts still
  arrive; the latency is the poll interval rather than instant.
- **No server-side transcription.** `faster-whisper` is in
  `requirements-voice.txt`, deliberately excluded from the deployed bundle
  because CTranslate2 and onnxruntime exceed serverless size limits. Voice input
  still works in Chrome via the browser's own speech recognition, which the
  frontend sends as `client_transcript`. `/health` reports
  `transcription: false` so the UI stays honest about it.

---

## Option B — Split deploy (full functionality)

### Backend on Render

`render.yaml` is not committed — this is a five-field form:

| Field | Value |
|---|---|
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance type | Any paid tier (free tiers sleep, which stops the scheduler) |

Environment:

```
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
WEATHER_DATA_MODE=live
WEATHERGPT_DB=/var/data/weathergpt.db     # attach a persistent disk
CORS_ORIGINS=https://<your-frontend>.vercel.app
SCHEDULER_ENABLED=true
ALERT_INTERVAL_MINUTES=30
```

Add `pip install -r requirements-voice.txt` to the build command if you want
server-side Whisper. The first request then downloads the model, so warm it
once after deploy. With `ELEVENLABS_API_KEY` set you do not need it: Scribe is
tried first and needs nothing on disk, which is what makes voice input work on
a serverless host at all.

### Frontend on Vercel

Delete `vercel.json` (or keep the repo and set the project root to `frontend`),
then set:

```
VITE_API_BASE=https://<your-backend>.onrender.com
```

The client uses that for both HTTP and WebSocket URLs, so `/ws/alerts` upgrades
to `wss://` automatically. Make sure `CORS_ORIGINS` on the backend names the
exact Vercel domain — cross-origin is real in this topology, unlike Option A.

Verify:

```bash
curl -s https://<your-backend>.onrender.com/health | python3 -m json.tool
# expect scheduler_enabled: true, websockets_supported: true
```

---

## Docker (any host)

```dockerfile
FROM python:3.11-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
ENV WEATHERGPT_DB=/data/weathergpt.db
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Mount a volume at `/data` so alerts survive restarts.

---

## Post-deploy checklist

```bash
BASE=https://<your-app>.vercel.app/api      # or your backend origin

curl -s $BASE/health | python3 -m json.tool          # capabilities
curl -s "$BASE/weather/current?location=Guwahati"    # live provider reachable
curl -s -X POST $BASE/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"Will it rain in Guwahati today?"}'   # end-to-end
curl -s -X POST $BASE/alerts/scan                    # seed alerts
```

Then open the app and confirm:

- [ ] `data_source` is `live` and **no SIMULATED badge** appears in the header
- [ ] A chat answer returns with `verification.verified: true`
- [ ] The header status dot is green (WebSocket) or blue (polling) — not grey
- [ ] The risk map draws markers and its tiles load
- [ ] Switching to తెలుగు changes both the UI and the assistant's answers

If the SIMULATED badge appears in production, `WEATHER_DATA_MODE` is set to
`fixture` somewhere. Fixture data is never served in live mode, so the badge
means the environment variable is wrong, not that the data is suspect.
