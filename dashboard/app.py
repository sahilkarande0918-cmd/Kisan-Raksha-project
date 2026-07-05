"""KisaanRaksha officer dashboard — Maharashtra FSI heatmap (Streamlit).

Run:  streamlit run dashboard/app.py
Data: offline cache (last computed FSI per district) — refresh pulls live
signals; demo mode paints the documented 2024-style crisis scenario.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.tools.common import DATA_DIR, OFFLINE_CACHE_PATH, districts  # noqa: E402
from mcp_server.tools.fsi import compute_fsi  # noqa: E402

# our district names -> GeoJSON dtname
GEO_ALIAS = {
    "Beed": "Bid",
    "Buldhana": "Buldana",
    "Chhatrapati Sambhajinagar": "Aurangabad",
    "Dharashiv": "Osmanabad",
}

st.set_page_config(page_title="KisaanRaksha — FSI Dashboard", page_icon="🌾", layout="wide")
st.title("🌾 KisaanRaksha — Farmer Financial Stress Index")
st.caption("Early-warning heatmap for district officers · Vidarbha + Marathwada · "
           "signals: rainfall (Open-Meteo) · mandi vs MSP (Agmarknet) · NDVI (NASA MODIS)")


@st.cache_data(show_spinner=False)
def load_geojson() -> dict:
    with open(DATA_DIR / "maharashtra_districts.geojson", encoding="utf-8") as f:
        return json.load(f)


def cached_fsi() -> dict:
    if OFFLINE_CACHE_PATH.exists():
        with open(OFFLINE_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f).get("fsi", {})
    return {}


def fsi_frame(mode: str) -> pd.DataFrame:
    rows = []
    cache = cached_fsi()
    progress = st.progress(0.0, text="Computing FSI…") if mode != "cache" else None
    dist_list = districts()
    for i, d in enumerate(dist_list):
        crop = d["major_crops"][0]
        if mode == "demo":
            r = compute_fsi(d["name"], crop, simulate_crisis=True)
        elif mode == "live":
            r = compute_fsi(d["name"], crop)
        else:
            r = cache.get(f"{d['name']}:{crop}") or cache.get(f"{d['name']}:cotton") or {}
        if progress:
            progress.progress((i + 1) / len(dist_list), text=f"Computing FSI… {d['name']}")
        if r.get("fsi") is not None:
            sig = r.get("signals", {})
            rows.append({
                "district": d["name"],
                "geo_name": GEO_ALIAS.get(d["name"], d["name"]),
                "region": d["region"],
                "crop": r.get("crop", crop),
                "fsi": r["fsi"],
                "level": r.get("level", ""),
                "rain_deficit_%": sig.get("drought", {}).get("deficit_pct"),
                "price_gap_%": sig.get("price", {}).get("gap_below_msp_pct"),
                "ndvi": sig.get("ndvi", {}).get("latest_ndvi"),
                "as_of": r.get("cached_at", "live"),
            })
    if progress:
        progress.empty()
    return pd.DataFrame(rows)


with st.sidebar:
    st.header("Data source")
    mode = st.radio("Mode", ["cache", "live", "demo"], format_func={
        "cache": "🗂️ Offline cache (last known)",
        "live": "📡 Live signals (slow, ~1 min)",
        "demo": "🎭 Demo: simulated 2024 crisis",
    }.get)
    if mode == "demo":
        st.warning("SIMULATION — replays the Oct-Nov 2024 Vidarbha stress pattern. Not live data.")
    st.divider()
    st.markdown("**FSI legend**  \n> 75 CRITICAL · 55-75 HIGH  \n35-55 MODERATE · < 35 LOW")

df = fsi_frame(mode)
if df.empty:
    st.info("No FSI values yet — run once in **live** or **demo** mode to populate the cache.")
    st.stop()

left, right = st.columns([3, 2])
with left:
    fig = px.choropleth_map(
        df, geojson=load_geojson(), locations="geo_name",
        featureidkey="properties.dtname", color="fsi",
        color_continuous_scale=["#2e7d32", "#fdd835", "#ef6c00", "#b71c1c"],
        range_color=(0, 100), hover_name="district",
        hover_data={"geo_name": False, "fsi": ":.1f", "level": True,
                    "crop": True, "rain_deficit_%": True, "price_gap_%": True},
        labels={"fsi": "FSI"},
        map_style="carto-darkmatter", zoom=5.4, center={"lat": 19.9, "lon": 77.5},
        opacity=0.75)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=520,
                      coloraxis_colorbar_title="FSI")
    st.plotly_chart(fig, use_container_width=True)

with right:
    crit = df[df.fsi > 75].sort_values("fsi", ascending=False)
    st.subheader(f"⚠️ Critical districts: {len(crit)}")
    if len(crit):
        st.dataframe(
            crit[["district", "region", "crop", "fsi", "rain_deficit_%", "price_gap_%", "ndvi"]],
            hide_index=True, use_container_width=True)
    else:
        st.success("No district above the critical threshold (75).")
    st.subheader("All districts")
    st.dataframe(
        df.sort_values("fsi", ascending=False)[["district", "region", "fsi", "level", "as_of"]],
        hide_index=True, use_container_width=True, height=260)

st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Districts monitored", len(df))
c2.metric("Critical (FSI > 75)", int((df.fsi > 75).sum()))
c3.metric("Mean FSI", f"{df.fsi.mean():.1f}")
c4.metric("Max FSI", f"{df.fsi.max():.1f} — {df.loc[df.fsi.idxmax(), 'district']}")
