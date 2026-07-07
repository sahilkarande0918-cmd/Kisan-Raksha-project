"""KisaanRaksha — multi-page officer command centre (Streamlit).

Run:  streamlit run dashboard/app.py
Pages: Overview (live 3D relief map) · Districts (status board + detail) ·
Activity (agent log) · About. Live 2026 signals, 10-min auto-refresh,
offline-first cache fallback.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard import ui  # noqa: E402

st.set_page_config(page_title="KisaanRaksha — FSI Command Centre", page_icon="🌾",
                   layout="wide")
ui.inject_css()

pages = ui.build_pages()
nav = st.navigation(list(pages.values()))

ui.topbar(pages, active=getattr(nav, "url_path", "overview") or "overview")

with st.sidebar:
    st.markdown("### 🌾 KisaanRaksha")
    st.caption("Officer command centre")
    st.divider()

nav.run()
