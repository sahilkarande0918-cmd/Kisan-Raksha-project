"""Activity — farmer interactions, alerts and PMFBY claims from SQLite memory."""
import json
import sqlite3

import pandas as pd
import streamlit as st

from dashboard import ui
from mcp_server.tools.common import DB_PATH


def load_activity() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()
    with sqlite3.connect(DB_PATH) as c:
        inter = pd.read_sql_query(
            "SELECT ts, farmer_id, district, crop, fsi, fsi_level, actions "
            "FROM interactions ORDER BY id DESC LIMIT 200", c)
        claims = pd.read_sql_query(
            "SELECT ts, farmer_id, district, crop, status, claim_text "
            "FROM claims ORDER BY id DESC LIMIT 100", c)
    return inter, claims


def render() -> None:
    ui.hero("📞 Field activity — WhatsApp agent log",
            "Every farmer interaction, alert and drafted PMFBY claim · farmers identified only by hashed IDs (no raw PII)")
    inter, claims = load_activity()
    if inter.empty and claims.empty:
        st.info("No farmer interactions logged yet — the WhatsApp agent writes here as farmers message in.")
        return

    n_alerts = int(inter["actions"].fillna("").str.contains("send_officer_alert").sum()) if not inter.empty else 0
    n_crit = int((inter["fsi_level"] == "CRITICAL").sum()) if not inter.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    for col, cls, label, value, sub in (
        (c1, "d1", "Farmer interactions", len(inter), "last 200 shown"),
        (c2, "d2", "Officer alerts sent", n_alerts, "auto-triggered at FSI > 75"),
        (c3, "d3", "Critical events", n_crit, "conversations at CRITICAL"),
        (c4, "d4", "PMFBY claims drafted", len(claims), "in Marathi, evidence-grounded"),
    ):
        with col:
            st.markdown(f"""<div class="kcard {cls}">
                <div class="klabel">{label}</div><div class="kvalue">{value}</div>
                <div class="ksub">{sub}</div></div>""", unsafe_allow_html=True)
    st.markdown("")

    tab1, tab2 = st.tabs(["🗨️ Interactions", "📄 PMFBY claims"])
    with tab1:
        if inter.empty:
            st.info("No interactions yet.")
        else:
            show = inter.copy()
            show["actions"] = show["actions"].apply(
                lambda a: ", ".join(json.loads(a)) if a else "")
            show["farmer_id"] = show["farmer_id"].str.slice(0, 8) + "…"
            st.dataframe(show.rename(columns={
                "ts": "time (UTC)", "farmer_id": "farmer (hashed)", "fsi_level": "level"}),
                hide_index=True, use_container_width=True, height=420)
    with tab2:
        if claims.empty:
            st.info("No claims drafted yet.")
        else:
            for row in claims.itertuples():
                with st.expander(f"📄 {row.district} · {row.crop} · {row.ts} · {row.status}"):
                    st.text(row.claim_text)
