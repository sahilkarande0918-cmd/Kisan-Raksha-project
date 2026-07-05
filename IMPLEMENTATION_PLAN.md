# KisaanRaksha — Phased Implementation Plan

**Farmer Financial Distress Early Warning System — Maharashtra**
Hack4Humanity 2026 · Track C (AI for Societal Good) · Team of 2

---

## Timeline anchors

| Milestone | Date | What must exist |
|---|---|---|
| **Round 1 submission** | **July 15, 2026** | Solution doc + 3-min pitch video + GitHub repo (working MVP skeleton) |
| **Round 2 finale** | **August 8, 2026** | 12-hour in-person build → polished live WhatsApp demo |
| Merge point | Hour 8 of finale | Person 2's `compute_fsi()` wrapped as MCP tool by Person 1 |

**Strategy:** Round 1 = a *demonstrably working end-to-end thin slice* (real datasets, real MCP tools, real WhatsApp message), not a full product. Round 2 = harden, integrate live, rehearse the demo. Judges reward a working pipeline over a broad-but-fake one.

---

## Phase 0 — Foundations & Scaffolding
**Goal:** Repo runs on this one laptop; skeleton compiles; secrets managed.
**Owner:** shared (single-machine build — teammate works via GitHub, not a second local setup)

- [ ] `git init`, push `kisaanraksha` to GitHub under [sahilkarande0918-cmd](https://github.com/sahilkarande0918-cmd) (private until submission).
- [ ] Create full folder tree from brief (`mcp_server/`, `agent/`, `api/`, `asr/`, `alerts/`, `model/`, `dashboard/`, `data/`, `dataset/`).
- [ ] `requirements.txt` + `python -m venv` (Python 3.11). Pin: `fastmcp`, `fastapi`, `uvicorn`, `lightgbm`, `scikit-learn`, `fairlearn`, `pandas`, `requests`, `python-dotenv`, `google-generativeai`, `twilio`, `streamlit`, `plotly`.
- [ ] `.env.example` + `.gitignore` (never commit `.env`, `*.pkl` optional, `__pycache__`).
- [ ] `README.md` stub with architecture diagram + data-source citations.
- [ ] Decide: contract between the two halves = **`compute_fsi(district: str) -> dict`** returning `{fsi: float, signals: {...}, confidence: float}`.

**Exit criteria:** `uvicorn` and `streamlit` both launch empty apps without error on this machine.

---

## Phase 1 — Grounded Data Layer & Synthetic Dataset
**Goal:** Real India-specific data flowing; custom dataset built (bonus points).
**Owner:** Person 2 (data pipeline) + Person 1 (static JSON)

- [ ] `data/maharashtra_districts.json` — districts + talukas + lat/lon (focus: Vidarbha + Marathwada).
- [ ] `data/crop_calendar.json` — sowing/harvest/repayment windows per district × crop (cotton, soybean, tur).
- [ ] `weather.py` — OpenWeatherMap: 30-day rainfall deficit → drought signal (0–1).
- [ ] `mandi.py` — Agmarknet (data.gov.in API): crop price vs MSP % gap.
- [ ] `ndvi.py` — ISRO Bhuvan / MODIS NDVI pull (or cached tiles if API friction).
- [ ] **`dataset/maharashtra_ag_stress_dataset.csv`** — synthetic-but-grounded: ~2,000 rows (taluka × month × 4 signals × labeled stress). Document generation method for IEEE Dataport handoff. **No real farmer PII.**

**Exit criteria:** Each signal function returns a real value for "Amravati" from a live source; dataset CSV loads in pandas with no nulls.

---

## Phase 2 — FSI Model + Fairlearn Bias Report
**Goal:** `compute_fsi()` works; bias report exists (non-negotiable per rubric §8.3).
**Owner:** Person 2

- [ ] `model/train_fsi.py` — LightGBM regressor/classifier on the synthetic dataset → FSI 0–100.
- [ ] Save `model/risk_model.pkl`.
- [ ] `tools/fsi.py` — loads model, exposes `compute_fsi(district)` per the agreed contract; FSI > 75 = critical.
- [ ] `model/fairlearn_report.py` — sensitive feature = district group (e.g., Vidarbha vs rest); output demographic parity / equalized-odds metrics → save `fairlearn_report.html/json`.
- [ ] Link the bias report in README.

**Exit criteria:** `compute_fsi("Amravati")` returns a plausible score; Fairlearn report renders and is committed.

---

## Phase 3 — KisaanRaksha MCP Server (6 tools)
**Goal:** No bare LLM calls — every capability is a role-scoped MCP tool.
**Owner:** Person 1

- [ ] `mcp_server/server.py` — FastMCP server registering all 6 tools.
- [ ] `query_weather_signal(district)` → wraps `weather.py`.
- [ ] `query_mandi_prices(crop, taluka)` → wraps `mandi.py`.
- [ ] `compute_fsi(district)` → wraps Person 2's model (the merge point).
- [ ] `get_farmer_history(phone)` → SQLite (`tools/memory.py`).
- [ ] `send_officer_alert(taluka, fsi, details)` → Twilio (`alerts/whatsapp.py`).
- [ ] `draft_pmfby_claim(farmer, district)` → Gemini, output in **Marathi** (`tools/claim_draft.py`).

**Exit criteria:** MCP server lists all 6 tools; each is individually callable and returns structured JSON.

---

## Phase 4 — Agent Orchestrator (Gemini)
**Goal:** LLM agent chains tools: weather → mandi → NDVI → FSI → alert/claim.
**Owner:** Person 1

- [ ] `agent/orchestrator.py` — Gemini free tier as orchestrator that *calls MCP tools* (not a wrapper).
- [ ] System prompt encodes the decision flow + FSI>75 → trigger `send_officer_alert`.
- [ ] Structured memory: reads/writes `get_farmer_history` each turn.

**Exit criteria:** Given a text query ("cotton, Amravati, poor rains"), agent produces the FSI, decides on alert, and drafts a claim — all via tool calls, logged.

---

## Phase 5 — WhatsApp + Marathi ASR Pipeline (the demo moment)
**Goal:** Real Marathi voice note on a real phone → transcribed → agent → reply.
**Owner:** Person 1 (Twilio/webhook) + Person 2 (ASR)

- [ ] `asr/marathi_asr.py` — AI4Bharat IndicASR (IndicWav2Vec): Marathi audio → text.
- [ ] `api/webhook.py` — FastAPI Twilio Sandbox webhook: receive voice note → ASR → orchestrator → reply.
- [ ] `alerts/whatsapp.py` — Twilio sender (officer alert + farmer claim letter).
- [ ] Expose local server via `ngrok` for Twilio callback during dev/demo.

**Exit criteria:** Send a Marathi voice note to the sandbox number → receive an auto-drafted PMFBY claim reply in Marathi.

---

## Phase 6 — Streamlit Dashboard
**Goal:** District-officer FSI heatmap updating live.
**Owner:** Person 2

- [ ] `dashboard/app.py` — Maharashtra FSI choropleth (Plotly + district GeoJSON).
- [ ] Table of critical talukas (FSI > 75) with drivers (drought days, price gap, farmers in repayment window).
- [ ] Reads from SQLite / cache so it reflects the same state the agent sees.

**Exit criteria:** Dashboard shows a colored heatmap; clicking Amravati shows the alert breakdown from the demo script.

---

## Phase 7 — Offline-First & Memory Hardening
**Goal:** Rubric requirements: offline fallback + structured memory.
**Owner:** shared

- [ ] `data/offline_cache.json` — last-known FSI per district; tools fall back to cache when APIs fail.
- [ ] Wrap every external API call in try/except → cache → graceful degradation banner.
- [ ] SQLite schema finalized: farmer sessions, transcripts, prior FSI, claims filed.

**Exit criteria:** Pull the network — pipeline still returns cached FSI and the dashboard still renders.

---

## Phase 8 — Round 1 Deliverables (due July 15)
**Goal:** Submit doc + video + repo.
**Owner:** shared

- [ ] **Solution doc** (6 sections from brief): cover/SDGs → problem (every-3-hours, 2,706 in 2024) → architecture diagram → methodology (4 signals + FSI formula + MCP tools + Fairlearn) → impact metrics → deployment pathway (Krishi Vibhag/NGO handoff, offline, low-bandwidth).
- [ ] **3-min pitch video** — screen-record the live WhatsApp demo (Phase 5) as the climax.
- [ ] **README** — data sources cited, bias report linked, run instructions.
- [ ] Tag `v1.0-round1` release.

**Exit criteria:** All three artifacts submitted before deadline; repo reproducible from README.

---

## Phase 9 — Round 2 Finale Integration & Live Demo (Aug 8, 12h)
**Goal:** Polished, rehearsed, live on a real phone.
**Owner:** shared — merge at hour 8

- [ ] Hours 0–4: both harden their halves against the agreed contract.
- [ ] Hours 4–8: integrate — Person 1 wraps Person 2's final `compute_fsi()`.
- [ ] Hours 8–10: full dress rehearsal of the 6-step demo script end-to-end.
- [ ] Hours 10–12: fallback plan (cached demo path if live APIs/Twilio flake), deploy to Railway or keep localhost+ngrok, buffer.

**Exit criteria:** The 6-step demo runs twice in a row without intervention.

---

## Dependency graph (build order)

```
Phase 0 ─┬─> Phase 1 ──> Phase 2 (FSI+Fairlearn) ─┐
         │                                        ├─> Phase 3 (MCP) ──> Phase 4 (Agent) ──> Phase 5 (WhatsApp+ASR)
         └─> (static JSON)                         │
                                                   └─> Phase 6 (Dashboard)
Phase 7 (offline/memory) runs alongside 3–6
Phase 8 (Round 1 docs) after 5 works end-to-end
Phase 9 = finale
```

## Rubric coverage check (need 60/100 to qualify)

| Requirement | Satisfied by |
|---|---|
| No bare LLM calls → MCP wrapper | Phase 3 |
| India-specific datasets | Phase 1 |
| Fairlearn bias output | Phase 2 |
| Offline-first cache | Phase 7 |
| Structured memory | Phase 3 (`get_farmer_history`) + 7 |
| Role-scoped agentic pipeline | Phase 3 + 4 |
| Custom dataset (bonus) | Phase 1 |
| Live demo | Phase 5 + 9 |

---

## Credentials & accounts needed (gather before Phase 0/1)

**Cost policy: no credit card entered anywhere, ever.** Every service below is chosen because it has a genuinely free tier that does *not* require billing setup. Where the "obvious" choice (OpenWeatherMap One Call 3.0) now demands a card even for its free quota, we swap to a card-free alternative instead — same signal, zero risk of accidental charges.

| # | Credential | Used in | How to get it | Card required? | Cost |
|---|---|---|---|---|---|
| 1 | **GitHub** repo access | Phase 0 | Repo under [sahilkarande0918-cmd](https://github.com/sahilkarande0918-cmd) — confirm name + public/private | No | Free |
| 2 | ~~OpenWeatherMap~~ → **Open-Meteo** (no key needed at all) | `weather.py` | Nothing to sign up for — public REST API, includes historical rainfall archive | No | Free, unlimited for non-commercial use |
| 3 | **data.gov.in API key** (Agmarknet mandi prices) | `mandi.py` | Register at data.gov.in → generate API key | No | Free |
| 4 | **ISRO Bhuvan** (WMS layers) | `ndvi.py` | Keyless public WMS/thematic layers | No | Free |
| 4b | *(fallback only if Bhuvan access is flaky)* NASA Earthdata login | `ndvi.py` | Free registration at urs.earthdata.nasa.gov for MODIS via AppEEARS | No | Free |
| 5 | **Google Gemini API key** | `orchestrator.py`, `claim_draft.py` | Google AI Studio (aistudio.google.com) → free tier key | No (free tier) | Free — but rate-limited (~15 requests/min on Gemini Flash); code must throttle/retry, not upgrade |
| 6 | **Twilio Account SID + Auth Token + WhatsApp Sandbox number** | `webhook.py`, `whatsapp.py` | Twilio free trial, enable WhatsApp Sandbox | Yes (Twilio requires phone verification, not a charged card) | Uses trial credit only (~$15); sandbox demo traffic costs fractions of a cent/msg — trial credit covers the whole hackathon |
| 7 | **ngrok authtoken** | Local webhook dev | Free ngrok account | No | Free |
| 8 | **Hugging Face token** (optional) | `marathi_asr.py` (AI4Bharat IndicASR) | Only needed if the specific IndicWav2Vec checkpoint is gated; else public download | No | Free |

Nothing else is required — LightGBM, Fairlearn, SQLite, Streamlit all run fully local/offline, zero API cost.

**Only genuine cost exposure:** Twilio trial credit. As long as demo/testing volume stays low (a handful of messages per test run), $15 trial credit lasts through both Round 1 and the Round 2 finale. I'll log Twilio calls so you can watch remaining balance.

## Recommended near-term order for Sahil (Person 1)
1. Phase 0 scaffolding (unblocks everyone).
2. Phase 3 MCP server with **stubbed** `compute_fsi` (returns fake score) so Phases 4–5 proceed before Person 2's model lands.
3. Phase 4 orchestrator, then Phase 5 WhatsApp — this is the winning demo, prioritize it.
4. Swap the stub for Person 2's real model at the merge point.
