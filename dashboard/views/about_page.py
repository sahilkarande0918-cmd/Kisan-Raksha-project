"""About — mission, architecture, responsible AI, data sources, team."""
import json

import streamlit as st

from dashboard import ui
from mcp_server.tools.common import MODEL_DIR


def render() -> None:
    ui.hero("🌾 About KisaanRaksha",
            "Farmer Financial Distress Early Warning System · Hack4Humanity 2026 · Track C — AI for Societal Good")

    st.markdown("""<div class="panel">
      <h3>Why this exists</h3>
      <p>Maharashtra loses a farmer to suicide every <b>3 hours</b>. In 2024, <b>2,706 farmers</b>
      died in Vidarbha and Marathwada alone — and every rupee of state response was <i>reactive</i>:
      compensation after a death. Yet the crisis pattern is measurable months in advance —
      a failed monsoon, prices collapsing below MSP, and the loan repayment deadline arriving at once.</p>
      <p><b>KisaanRaksha watches those signals continuously and warns officers before the crisis peaks,
      not after.</b> Farmers reach it in Marathi voice on WhatsApp; it answers with grounded numbers
      and drafts their PMFBY insurance claim automatically.</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="panel">
      <h3>How it works</h3>
      <div class="flow">
        <div class="fbox"><b>👨‍🌾 Farmer</b><span>WhatsApp Marathi voice note</span></div>
        <div class="farrow">→</div>
        <div class="fbox"><b>🎙️ ASR</b><span>Whisper large-v3 · AI4Bharat offline option</span></div>
        <div class="farrow">→</div>
        <div class="fbox"><b>🤖 LLM Agent</b><span>tool-calling loop, no bare answers</span></div>
        <div class="farrow">→</div>
        <div class="fbox"><b>🧰 MCP Server</b><span>7 role-scoped tools</span></div>
        <div class="farrow">→</div>
        <div class="fbox"><b>🛰️ Grounded data</b><span>Open-Meteo · Agmarknet · NASA MODIS</span></div>
      </div>
      <p style="margin-top:14px">Four live signals — rainfall deficit, mandi price vs MSP, satellite NDVI and
      loan-repayment proximity — feed a LightGBM model that produces the
      <b>Financial Stress Index (0–100)</b> per district. FSI &gt; 75 automatically alerts the duty
      agriculture officer on WhatsApp with the full evidence and the farmer's callback number.</p>
    </div>""", unsafe_allow_html=True)

    # responsible AI panel with real Fairlearn numbers
    gates_html = ""
    try:
        rep = json.loads((MODEL_DIR / "fairlearn_report.json").read_text())
        for gate, ok in rep.get("gates", {}).items():
            icon = "✅" if ok else "❌"
            gates_html += f"<li>{icon} <code>{gate}</code></li>"
    except Exception:
        gates_html = "<li>run <code>model/fairlearn_report.py</code> to regenerate</li>"
    st.markdown(f"""<div class="panel">
      <h3>Responsible AI</h3>
      <ul>
        <li>🔒 <b>No raw farmer PII stored</b> — farmers are keyed by hashed WhatsApp IDs; training data is synthetic.</li>
        <li>⚖️ <b>Fairlearn bias audit</b> on every retrain — false-negative-rate parity across regions and crops:</li>
        <ul>{gates_html}</ul>
        <li>🧭 FSI is an <b>officer-attention tool</b>, never an automated eligibility or denial decision.</li>
        <li>📡 <b>Offline-first</b>: every signal falls back to the last cached value in low-connectivity deployments.</li>
      </ul>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="panel">
      <h3>Data sources — all public / keyless / free</h3>
      <ul>
        <li>🌧️ <a href="https://open-meteo.com">Open-Meteo ERA5 archive</a> — rainfall, CC-BY 4.0, keyless</li>
        <li>💰 <a href="https://data.gov.in">Agmarknet via data.gov.in</a> — daily mandi prices, Ministry of Agriculture</li>
        <li>🛰️ <a href="https://modis.ornl.gov">NASA MODIS MOD13Q1</a> — NDVI via ORNL Subsets API, keyless</li>
        <li>🌾 MSP 2025-26 — CACP, Ministry of Agriculture</li>
        <li>🗺️ District boundaries — datta07/INDIAN-SHAPEFILES (GeoJSON)</li>
        <li>📊 Custom synthetic training dataset (13,644 rows) — flagged for IEEE Dataport publication</li>
      </ul>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="panel" style="text-align:center">
      <h3>Aligned to the UN Sustainable Development Goals</h3>
      <span class="sdg">SDG 2 · Zero Hunger</span>
      <span class="sdg">SDG 3 · Good Health & Well-Being</span>
      <span class="sdg">SDG 10 · Reduced Inequalities</span>
      <p style="margin-top:16px;color:#4b6b50">Team: Sahil Karande · [Teammate] &nbsp;·&nbsp;
      <a href="https://github.com/sahilkarande0918-cmd/Kisan-Raksha-project">GitHub repository</a><br/>
      <i>"Technology must serve humanity — KisaanRaksha points it at the farmer the system forgot."</i></p>
    </div>""", unsafe_allow_html=True)
