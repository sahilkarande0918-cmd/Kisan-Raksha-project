# 🌾 KisaanRaksha — Farmer Financial Distress Early Warning System

**Hack4Humanity 2026 · Track C (AI for Societal Good) · SDG 2, 3, 10**

Maharashtra loses a farmer every 3 hours. 2,706 farmer deaths in Vidarbha + Marathwada in 2024 alone — and the government response is 100% reactive: compensation only after death. KisaanRaksha flips this: an AI agent that **predicts financial crisis before it happens**, alerts officers proactively, and helps farmers file PMFBY insurance claims **in Marathi over WhatsApp voice**.

## Architecture

```
Farmer (WhatsApp Marathi voice)
    ↓
Twilio Sandbox → FastAPI webhook (api/webhook.py)
    ↓
Marathi ASR (asr/marathi_asr.py — Whisper large-v3 / AI4Bharat)
    ↓
LLM Agent orchestrator (agent/orchestrator.py)
    ↓ calls MCP tools ↓
┌──────────────────────────────────────────┐
│    KisaanRaksha MCP Server (FastMCP)     │
│  • query_weather_signal(district)        │
│  • query_mandi_prices(crop, district)    │
│  • query_ndvi_signal(district)           │
│  • compute_fsi() → LightGBM model        │
│  • get_farmer_history() → SQLite         │
│  • send_officer_alert() → Twilio         │
│  • draft_pmfby_claim() → LLM (Marathi)   │
└──────────────────────────────────────────┘
    ↓ grounded data layer ↓
Open-Meteo ERA5 · Agmarknet (data.gov.in) · NASA MODIS MOD13Q1 (ORNL)
    ↓
Streamlit dashboard (dashboard/app.py) — district FSI heatmap
```

**No bare LLM calls** — every fact the agent states comes from an MCP tool grounded in a real dataset. **Offline-first** — every signal falls back to `data/offline_cache.json` when connectivity drops. **Structured memory** — farmer sessions persist in SQLite keyed by hashed phone number (no raw PII).

## The Financial Stress Index (FSI)

| Signal | Source | Measures |
|---|---|---|
| Drought | Open-Meteo ERA5 archive | 30-day rainfall deficit vs 5-yr baseline |
| Price | Agmarknet via data.gov.in | mandi modal price vs MSP gap |
| Crop health | NASA MODIS MOD13Q1 NDVI | actual vegetation stress from satellite |
| Repayment proximity | crop calendar (CACP MSP data) | days to loan-due window |

A LightGBM model (trained on `dataset/maharashtra_ag_stress_dataset.csv`, 13,644 rows) combines the four signals → **FSI 0–100 per district**. FSI > 75 = critical → officer WhatsApp alert fires automatically.

- Model metrics: MAE 3.75, R² 0.94, critical-alert recall 0.78 on **held-out talukas** ([model/training_metrics.json](model/training_metrics.json))
- **Fairness audit (Fairlearn):** false-negative-rate and MAE parity across region (Vidarbha/Marathwada) and crop groups — all gates pass. See [model/fairlearn_report.md](model/fairlearn_report.md).

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in keys (see below)

python dataset/build_dataset.py    # regenerate synthetic dataset
python model/train_fsi.py          # train FSI model
python model/fairlearn_report.py   # bias audit

python -m mcp_server.tools.fsi Amravati cotton   # live FSI, one district
python agent/orchestrator.py                     # full agent turn (Marathi demo)

streamlit run dashboard/app.py                   # officer dashboard
uvicorn api.webhook:app --port 8000              # WhatsApp webhook
ngrok http 8000                                  # expose → Twilio sandbox
```

Set the Twilio sandbox inbound webhook to `https://<ngrok-url>/whatsapp`.

## Credentials (.env)

All free tier, no credit card: `DATA_GOV_IN_API_KEY` (data.gov.in), `GROQ_API_KEY` / `GEMINI_API_KEY` (LLM + Whisper ASR), `TWILIO_*` (WhatsApp sandbox), `OFFICER_WHATSAPP_TO` (alert destination), optional `HF_TOKEN` (AI4Bharat local ASR) and `EARTHDATA_BEARER_TOKEN`. Open-Meteo and NASA ORNL MODIS need **no key at all**.

## Demo mode

Live signals reflect today's reality (which may be calm). To demonstrate the critical-alert path, every tool accepts `simulate_crisis=true`, which replays the documented **Oct–Nov 2024 Vidarbha stress pattern** (68% rain deficit, cotton 18% below MSP, failed NDVI) — always visibly labeled `SIMULATION`. A WhatsApp message containing "demo"/"चाचणी" triggers it end-to-end.

## Data sources (all public / synthetic)

- [Open-Meteo](https://open-meteo.com) ERA5 rainfall archive (CC-BY 4.0, keyless)
- [Agmarknet daily mandi prices](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi) — Ministry of Agriculture, data.gov.in
- [NASA MODIS MOD13Q1 NDVI](https://modis.ornl.gov) via ORNL Subsets API (keyless)
- MSP 2025-26: CACP / Ministry of Agriculture
- District boundaries GeoJSON: [datta07/INDIAN-SHAPEFILES](https://github.com/datta07/INDIAN-SHAPEFILES)
- Training data: **synthetic, no real farmer PII** — generation methodology in [dataset/README.md](dataset/README.md) (candidate for IEEE Dataport)

## Repo map

```
mcp_server/   FastMCP server + tool implementations (weather, mandi, ndvi, fsi, memory, claim_draft)
agent/        LLM tool-calling orchestrator
api/          FastAPI Twilio WhatsApp webhook
asr/          Marathi speech-to-text
alerts/       Twilio WhatsApp sender + officer alert formatting
model/        LightGBM training, saved model, Fairlearn bias report
dashboard/    Streamlit FSI heatmap for district officers
data/         districts, crop calendar, GeoJSON, offline cache, SQLite DB
dataset/      synthetic dataset + builder (IEEE Dataport candidate)
```

## Team

Built for Hack4Humanity 2026 (IEEE JCTS + SIGHT + BRAIN Foundation, Pune).
