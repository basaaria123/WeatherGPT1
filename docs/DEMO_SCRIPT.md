# WeatherGPT — Live Demo Script

**Total runtime: about 6 minutes.** Timings are generous; the whole script fits
in 5 minutes at pace.

---

## Before you start (5 minutes, off-camera)

```bash
# Terminal 1 — backend
cd backend
export ANTHROPIC_API_KEY=sk-ant-...        # optional; see note below
python run.py                              # http://127.0.0.1:8000

# Terminal 2 — frontend
cd frontend
npm run dev                                # http://127.0.0.1:5173
```

Then, in a third terminal, seed the alert feed so the map has content:

```bash
curl -X POST http://127.0.0.1:8000/alerts/scan
```

**Checklist before going live**

| Check | Command / action | Expect |
|---|---|---|
| Backend healthy | `curl -s localhost:8000/health` | `"status": "ok"` |
| Data source | same response | `"data_source": "live"` |
| LLM configured | same response | `"llm": {"available": true}` |
| Voice output | same response | `"synthesis": true` |
| Alerts present | `curl -s "localhost:8000/alerts" \| head` | `"count"` above 0 |

> **If `ANTHROPIC_API_KEY` is unset**, everything below still works. Answers come
> from the deterministic template path instead of generated prose — still
> multilingual, still grounded, still emergency-aware. Say so plainly if asked;
> it is a designed fallback, not a failure.

> **Voice input**: Chrome's built-in speech recognition drives the microphone
> button and needs no setup. Server-side Whisper is used instead when
> `faster-whisper` and its model are installed. Demo in Chrome.

Open `http://127.0.0.1:5173` in Chrome and **hard-refresh** so the splash plays.

---

## Step 1 — Splash and landing (0:00 – 0:35)

**Do:** Load the page. Say nothing for the first three seconds.

**On screen:** Cyan and teal particles converge from the edges and resolve into
the WeatherGPT wordmark, over a deep navy field. A thin rule sweeps left to
right. It fades directly into the landing page — no second loading screen.

**Say:**
> "WeatherGPT is a conversational weather assistant for India. The background
> you're seeing isn't decoration — it's rendering the live condition at the
> selected location. Right now that's drifting cloud."

**Point at the three cards:** Raw data → Understanding → Action.

> "That's the whole thesis. Forecast data goes in; a decision comes out."

---

## Step 2 — Into the dashboard (0:35 – 1:05)

**Do:** Click **Open the assistant**.

**On screen:** The landing fades up into the command center — temperature,
condition, feels-like, humidity, wind, gusts, rain chance, pressure, cloud
cover, visibility — with a risk pill top-right.

**Say:**
> "Every number here comes from the Open-Meteo API. If a field isn't in the
> response, we leave it out rather than printing 'N/A'. The risk score in the
> corner comes from one shared risk engine — remember that, it matters in a
> minute."

**Do:** Change location to **Guwahati** (click the location chip, type Guwahati).

---

## Step 3 — Emergency mode triggering (1:05 – 2:10)

**Do:** Type into the chat: `Will it rain in Guwahati today?`

**On screen:** A typing indicator, then an answer that is *not* a normal weather
readout. It leads with a warning, states what is happening, why it matters, and
what to do — with an action checklist underneath. The risk pill reads **Severe**.

**Say:**
> "Notice what happened. I asked an ordinary question, and it came back as an
> emergency briefing. I didn't ask for that, and the model didn't decide it —
> the risk engine measured rainfall accumulation and returned Severe, and
> Severe automatically switches the response into emergency mode: what's
> happening, why it matters, what to do. The model is not allowed to declare an
> emergency on its own."

**Do:** Scroll to the **Weather → Understanding → Action** panel.

**Say:**
> "Left column: the actual measurements. Middle: the plain-language reading.
> Right: what to do about it. Every number in the middle column is cross-checked
> against the left one before the answer is returned. If the model quotes a
> figure the API didn't produce, we throw the answer away and fall back to a
> template built from real values. A wrong number in a flood warning is worse
> than no number."

**Do:** Scroll to the **Historical context** panel.

**Say:**
> "And it recognises the scale — these conditions are in the range of the June
> 2025 Assam floods, which affected over 600,000 people. Read the wording
> carefully: it says this is a comparison of scale, *not* a prediction that it
> happens again. That framing is enforced in the backend, not left to the model."

---

## Step 4 — Voice, in a non-English language (2:10 – 3:10)

**Do:** Click the language chip and switch to **తెలుగు (Telugu)**.

**On screen:** The interface labels change immediately.

**Do:** Click the microphone. Say clearly in Telugu:

> **"గువాహటిలో వాతావరణం ఎలా ఉంది?"**
> *(What is the weather like in Guwahati?)*

**On screen:** The button pulses with a "Listening…" counter, the transcript
appears as your message, and the answer comes back **in Telugu** with a play
button for spoken audio.

**Do:** Press play so the room hears it.

**Say:**
> "Language detection runs offline on the script itself — Telugu has its own
> Unicode block, so that detection is exact. For Assamese versus Bengali we key
> off two letters Assamese uses and Bengali doesn't. No network round trip to
> guess the language."

**Do:** Now ask the follow-up, still in Telugu — this is the important one:

> **"మరి ఎల్లుండి?"**
> *(And the day after tomorrow?)*

**Say:**
> "I never said 'Guwahati' in that sentence. Session memory carried the location
> across a language boundary and across turns — the same memory the text chat
> uses. There is only one memory system."

---

## Step 5 — Alerts, push and the map (3:10 – 4:20)

**Do:** Switch back to **EN**. Point at the **Active alerts** panel.

**Say:**
> "These arrived over a WebSocket, not by polling. A scheduled job scans tracked
> locations every 30 minutes, scores each one with the same risk engine, and
> pushes anything that crosses the threshold."

**Do:** In your third terminal, run:

```bash
curl -X POST http://localhost:8000/alerts/scan
```

**On screen:** New alert cards slide in from the right with a brief flash. The
count in the panel header increases. *Nothing was refreshed.*

**Say:**
> "That fired from outside the browser. The page updated live."

**Do:** Click **View affected area** on the Guwahati alert.

**On screen:** The page scrolls to the India risk map and flies to Guwahati.
Markers are sized and coloured by risk score.

**Say:**
> "Same engine again. The alert says Severe, the map marker says Severe, the
> chat answer said Severe — because there is exactly one place in the codebase
> that computes risk. Nothing here can disagree with anything else here."

**Do:** Click a marker to show the popup — location, score, level, hazard.

> "And if Twilio credentials are configured, that same alert goes out as an SMS.
> Without them it logs to the console rather than failing."

---

## Step 6 — Raw bulletin vs. plain language (4:20 – 5:20)

**Do:** Click **Demo mode** at the bottom of the page.

**On screen:** Two panels side by side with an animated arrow between them.
Left: a technical bulletin — `T2M 27.6°C`, `PRCP/24H 260.9mm`, `FX10 51km/h`,
`RISK 100/100 SEVERE`. Right: WeatherGPT's answer and action list.

**Say:**
> "This is the problem we set out to solve. On the left is what forecast data
> actually looks like. On the right is the same response — the identical
> backend payload — turned into something a farmer in Barpeta can act on.
>
> Nothing on this screen is scripted. Both panels render from one API response.
> If we were running on simulated data, there'd be a SIMULATED badge on both
> this panel and the header — live mode never shows fixture data."

**Do:** Close the panel. Switch the profile chip from **General** to **Farmer**,
then re-ask `Will it rain in Guwahati today?`

**Say:**
> "Same measurements, same risk score — but the first action is now about
> draining fields and moving harvested grain. The profile changes what gets
> prioritised. It never invents a fact the data doesn't support: there's no
> sea-state or crop-stage feed behind this, so it won't pretend there is."

---

## Step 7 — Close (5:20 – 6:00)

**Say:**
> "Three things to take away.
>
> **One — it can't make numbers up.** Every figure in an answer is verified
> against the provider response before it reaches the user.
>
> **Two — it can't contradict itself.** One risk engine feeds chat, alerts, the
> timeline and the map.
>
> **Three — it stays up.** No Anthropic key, no network, a failed translation,
> a dead text-to-speech service — each has a defined fallback. Quality degrades;
> availability doesn't. For a disaster tool, that's the requirement."

---

## If something goes wrong on stage

| Symptom | What to do | What to say |
|---|---|---|
| Answers are terse/templated | Nothing — it's the fallback path | "That's the no-LLM fallback; it's designed to look like this." |
| Map tiles don't load | Nothing — markers still render | "Tiles are a CDN; the risk data is ours and it's still there." |
| Microphone does nothing | Type the question instead | "Voice input is the browser's; the pipeline behind it is the same." |
| No alerts in the panel | Re-run `curl -X POST .../alerts/scan` | "Let me trigger a scan." |
| Answer comes back in English after switching language | Ask again | Detection needs a few words to be confident. |

## Quick reference — endpoints touched during the demo

| Step | Endpoint |
|---|---|
| 2 | `GET /weather/current`, `GET /weather/timeline`, `GET /weather/forecast`, `GET /risk-map` |
| 3 | `POST /chat` |
| 4 | `POST /voice-chat` |
| 5 | `POST /alerts/scan`, `WS /ws/alerts`, `GET /alerts` |
| 6 | `POST /chat` (with `user_type`) |

---

# Depth-pass sequence — decision support

Run this after the core walkthrough. It lands the three features that separate
WeatherGPT from a weather app: **the same forecast producing different
decisions**, an interface that changes state under danger, and grounded
historical context.

Total: **~3 min 30 s**. The pause in step 2 is the point of the whole sequence —
do not rush it.

### Step 1 — A calm baseline (~25 s)

**Do:** Location → **Bengaluru**. Type *"What should I know today?"*

**On screen:** Plain answer. **No emergency banner, no advisory card, no
historical panel.** The dashboard looks exactly as it always does.

**Say:** *"Nothing is firing here, and that matters — these features are
additive. On a calm day the app gets out of the way."*

> Showing the silent state first is what makes the next step land. Skip it and
> the emergency looks like decoration rather than a state change.

### Step 2 — One forecast, five decisions (~60 s) ← **the moment**

**Do:** Location → **Guwahati**. Set persona to **Farmer**. Read the advisory
card. Then switch to **Fisherman** — advice changes without re-asking anything.
Now press **Compare all roles**.

**On screen:** The shared condition stated once at the top, then five cards:

| | |
|---|---|
| 🌾 Farmer | Drain standing water; move harvested grain to raised storage |
| 🎣 Fisherman | Do not venture out to sea; secure boat and nets on high ground |
| 🧳 Traveller | Expect waterlogging and delays; check road and rail before starting |
| 🚌 Commuter | Leave earlier; avoid underpasses that flood quickly |
| 🏠 General | Keep your phone charged; follow local advisories |

Each carries **why**. Shared flood safety appears once beneath, not five times.

**Say:** *"One weather fact. Five different decisions. And these come from a
rules table a domain expert can review — not from a model improvising disaster
advice."*

**Pause here for three seconds.** Let them read across the row.

> If a judge asks where the advice comes from, open
> `backend/app/services/i18n.py` — `HAZARD_ACTIONS` and `PROFILE_ACTIONS`. That
> answer is far stronger than "the model generated it."

### Step 3 — The interface changes state (~40 s)

**On screen (already active at Guwahati):** A pinned banner above everything —
severity as **icon + the word SEVERE**, hazard named, headline, then
**what is happening → why it matters → what to do now**, numbered. The
persona actions have moved *above* the conditions card. Nothing is hidden;
it is reordered.

**Say:** *"The trigger is the risk engine, never the interface. React cannot
talk itself into an emergency — if it could, the screen and the score could
disagree, and they would disagree in front of you."*

**Optional:** press **Dismiss**. A compact strip remains: *"Emergency conditions
still active."* A dismissed warning must never look like a resolved one.

### Step 4 — Emergency instructions aloud, in language (~30 s)

**Do:** Switch language to **తెలుగు**. Press **🔊 Listen to emergency
instructions**.

**On screen / audio:** Banner and instructions in Telugu; speech in a Telugu
voice. Roughly 30 seconds — short enough that someone frightened will hear it
out.

**Say:** *"Written for speech, not reading — no bullet symbols, no
'precipitation probability 87 percent'. And it never falls back to English."*

### Step 5 — Historical context, said out loud as similarity (~45 s)

**Do:** Switch back to **English**. Ask *"what precautions should I take?"*
Scroll to **Historical context** (below the answer and below any live alert —
never above them).

**On screen:**

```
Historical context                              100% similar
June 2025 Assam floods · Assam, Brahmaputra valley

Matched on
  24-hour rainfall               260.9mm  vs 90mm    100%
  72-hour rainfall accumulation  591mm    vs 220mm   100%

A pattern-similarity signal, not a prediction. Similar conditions do
not mean a similar outcome.
Source: Assam State Disaster Management Authority (ASDMA)
```

**Say — unprompted, this is important:** *"This is similarity, not prediction.
We show which dimensions matched and both values, so you can check it rather
than trust it. And the panel is styled unlike an alert on purpose — historical
context must never be mistaken for an active warning."*

> Saying the caveat before anyone asks is what makes a technical panel trust the
> rest of your claims.

### Step 6 — Clean exit (~20 s)

**Do:** Location → **Bengaluru**.

**On screen:** Banner gone, advisory gone, historical panel gone. Calm dashboard.

**Say:** *"Risk drops, the mode exits. It doesn't linger, and it never invents
an emergency that isn't in the data."*

---

## Forcing the severe state

The fixture provider pins Guwahati to a flood scenario, so step 2 works offline
with no setup:

```bash
WEATHER_DATA_MODE=fixture uvicorn app.main:app
```

A simulated emergency carries `is_simulated: true`, which renders an unmissable
**DEMO / SIMULATED DATA** badge *inside the banner*. It can never appear in live
mode — the flag comes from the data source, not from a UI toggle.

## Endpoints exercised

| Step | Endpoint |
|---|---|
| 1 | `GET /weather/current` |
| 2 | `GET /weather/current` (`user_type`), `GET /advisory/personas` |
| 3 | `GET /weather/current` → `emergency.active` |
| 4 | browser speech synthesis over `emergency.spoken_instructions` |
| 5 | `POST /chat` → `historical_similarity` |
| 6 | `GET /weather/current` → `emergency.active: false` |

## If something misbehaves

- **No emergency banner at Guwahati** — check `/weather/current` returns
  `emergency.active: true`. The frontend only mirrors it.
- **Compare panel empty** — `/advisory/personas?location=Guwahati` should list
  five personas.
- **No historical panel** — it appears once per session per event by design.
  Reload to show it again.
