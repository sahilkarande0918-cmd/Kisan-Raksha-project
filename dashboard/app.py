"""KisaanRaksha officer dashboard — live 3D FSI relief map (Streamlit + deck.gl).

Run:  streamlit run dashboard/app.py
Live 2026 signals (Open-Meteo · Agmarknet · NASA MODIS), fetched in parallel,
auto-refreshed every 10 minutes; offline cache is the automatic fallback.
Column height & colour = Financial Stress Index.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.tools.common import DATA_DIR, OFFLINE_CACHE_PATH, districts  # noqa: E402
from mcp_server.tools.fsi import compute_fsi  # noqa: E402

REFRESH_SECONDS = 600  # live signals re-pulled every 10 minutes

GEO_ALIAS = {
    "Beed": "Bid",
    "Buldhana": "Buldana",
    "Chhatrapati Sambhajinagar": "Aurangabad",
    "Dharashiv": "Osmanabad",
}

st.set_page_config(page_title="KisaanRaksha — FSI Dashboard", page_icon="🌾", layout="wide")

# ---------- agriculture light theme + gentle background motion ----------
st.markdown("""
<style>
  .block-container { padding-top: 1.1rem; }
  h1 { letter-spacing: -0.5px; color: #1b5e20; }

  /* soft drifting green fields in the background — slow and subtle */
  .stApp::before, .stApp::after {
      content: ""; position: fixed; z-index: 0; pointer-events: none;
      border-radius: 50%; filter: blur(90px); opacity: .16;
  }
  .stApp::before {
      width: 46vw; height: 46vw; background: #66bb6a;
      top: -14vw; right: -10vw; animation: drift1 26s ease-in-out infinite;
  }
  .stApp::after {
      width: 38vw; height: 38vw; background: #9ccc65;
      bottom: -12vw; left: -8vw; animation: drift2 32s ease-in-out infinite;
  }
  @keyframes drift1 { 0%,100% {transform: translate(0,0);} 50% {transform: translate(-6vw, 4vh);} }
  @keyframes drift2 { 0%,100% {transform: translate(0,0);} 50% {transform: translate(5vw, -4vh);} }

  [data-testid="stMetric"] {
      background: #ffffff;
      border: 1px solid #dcedc8; border-left: 5px solid #2e7d32;
      border-radius: 14px; padding: 14px 18px;
      box-shadow: 0 2px 10px rgba(46,125,50,.08);
      transition: box-shadow .3s ease, transform .3s ease;
  }
  [data-testid="stMetric"]:hover {
      box-shadow: 0 6px 18px rgba(46,125,50,.16); transform: translateY(-2px);
  }
  [data-testid="stMetricValue"] { font-weight: 700; color: #1b5e20; }

  .live-badge {
      display:inline-block; padding:3px 12px; border-radius:12px;
      background:#e8f5e9; color:#2e7d32; font-weight:600; font-size:.85rem;
      border:1px solid #a5d6a7;
  }
  .live-dot {
      display:inline-block; width:8px; height:8px; border-radius:50%;
      background:#2e7d32; margin-right:6px;
      animation: livepulse 2s ease-in-out infinite;
  }
  @keyframes livepulse { 0%,100% {opacity:1;} 50% {opacity:.35;} }

  .crit-badge {
      display:inline-block; padding:2px 10px; border-radius:10px;
      background:#ffebee; color:#c62828; font-weight:600;
      border:1px solid #ef9a9a;
      animation: livepulse 2.4s ease-in-out infinite;
  }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_geojson() -> dict:
    with open(DATA_DIR / "maharashtra_districts.geojson", encoding="utf-8") as f:
        return json.load(f)


def cached_fsi() -> dict:
    if OFFLINE_CACHE_PATH.exists():
        with open(OFFLINE_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f).get("fsi", {})
    return {}


def _row(d: dict, r: dict, crop: str, source: str) -> dict:
    sig = r.get("signals", {})
    return {
        "district": d["name"],
        "geo_name": GEO_ALIAS.get(d["name"], d["name"]),
        "region": d["region"],
        "crop": r.get("crop", crop),
        "fsi": r["fsi"],
        "level": r.get("level", ""),
        "rain_deficit_%": sig.get("drought", {}).get("deficit_pct"),
        "price_gap_%": sig.get("price", {}).get("gap_below_msp_pct"),
        "ndvi": sig.get("ndvi", {}).get("latest_ndvi"),
        "source": source,
    }


@st.cache_data(ttl=REFRESH_SECONDS - 30, show_spinner=False)
def live_frame() -> tuple[pd.DataFrame, str]:
    """Fetch live FSI for all districts in parallel; cache fallback per district."""
    dist_list = districts()
    fallback = cached_fsi()

    def fetch(d, retries=1):
        crop = d["major_crops"][0]
        for _ in range(retries + 1):
            try:
                r = compute_fsi(d["name"], crop)
                if r.get("fsi") is not None:
                    return _row(d, r, crop, "cached" if r.get("cached") else "live")
            except Exception:
                continue
        c = fallback.get(f"{d['name']}:{crop}")
        return _row(d, c, crop, "cached") if c and c.get("fsi") is not None else None

    # modest parallelism — NASA/data.gov.in throttle aggressive fan-out
    with ThreadPoolExecutor(max_workers=5) as ex:
        rows = [r for r in ex.map(fetch, dist_list) if r]
    return pd.DataFrame(rows), datetime.now().strftime("%d %b %Y, %H:%M:%S")


def fsi_rgb(fsi: float) -> list[int]:
    stops = [(0, (46, 125, 50)), (40, (253, 216, 53)), (70, (239, 108, 0)), (100, (183, 28, 28))]
    for (x1, c1), (x2, c2) in zip(stops, stops[1:]):
        if fsi <= x2:
            t = (fsi - x1) / (x2 - x1)
            return [round(a + (b - a) * t) for a, b in zip(c1, c2)]
    return list(stops[-1][1])


def deck_3d(df: pd.DataFrame) -> pdk.Deck:
    geo = load_geojson()
    by_name = df.set_index("geo_name")
    features = []
    for f in geo["features"]:
        name = f["properties"].get("dtname")
        props = {"dtname": name}
        if name in by_name.index:
            row = by_name.loc[name]
            rgb = fsi_rgb(float(row["fsi"]))
            props.update({
                "district": row["district"], "fsi": float(row["fsi"]),
                "level": row["level"], "crop": row["crop"],
                "deficit": row["rain_deficit_%"], "gap": row["price_gap_%"],
                "elev": max(float(row["fsi"]), 3) * 280,
                "fill": rgb + [225],
                "monitored": True,
            })
        else:
            props.update({"district": name, "fsi": 0, "level": "—", "crop": "—",
                          "deficit": "—", "gap": "—", "elev": 0,
                          "fill": [205, 215, 205, 90], "monitored": False})
        features.append({"type": "Feature", "geometry": f["geometry"], "properties": props})

    layer = pdk.Layer(
        "GeoJsonLayer",
        {"type": "FeatureCollection", "features": features},
        pickable=True, stroked=True, filled=True, extruded=True,
        get_elevation="properties.elev",
        get_fill_color="properties.fill",
        get_line_color=[27, 94, 32, 60],
        line_width_min_pixels=1,
        transitions={"getElevation": 900},  # one smooth rise — nothing more
    )
    tooltip = {
        "html": "<b>{district}</b><br/>"
                "FSI: <b>{fsi}</b> ({level})<br/>"
                "Crop: {crop} · Rain deficit: {deficit}%<br/>"
                "Price below MSP: {gap}%",
        "style": {"backgroundColor": "#ffffff", "color": "#1b2e1f",
                  "border": "1px solid #2e7d32", "borderRadius": "8px",
                  "fontSize": "13px"},
    }
    view = pdk.ViewState(latitude=20.4, longitude=77.6, zoom=5.5, pitch=45, bearing=-12)
    return pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip,
                    map_provider="carto", map_style="light")


def chart_2d(df: pd.DataFrame):
    fig = px.choropleth_map(
        df, geojson=load_geojson(), locations="geo_name",
        featureidkey="properties.dtname", color="fsi",
        color_continuous_scale=["#2e7d32", "#fdd835", "#ef6c00", "#b71c1c"],
        range_color=(0, 100), hover_name="district",
        hover_data={"geo_name": False, "fsi": ":.1f", "level": True,
                    "crop": True, "rain_deficit_%": True, "price_gap_%": True},
        labels={"fsi": "FSI"},
        map_style="carto-positron", zoom=5.4, center={"lat": 19.9, "lon": 77.5},
        opacity=0.8)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=560,
                      coloraxis_colorbar_title="FSI")
    return fig


st.title("🌾 KisaanRaksha — Farmer Financial Stress Index")
st.caption("Live early-warning relief map for district officers · Vidarbha + Marathwada · "
           "signals: rainfall (Open-Meteo) · mandi vs MSP (Agmarknet) · NDVI (NASA MODIS)")

with st.sidebar:
    st.header("Display")
    view_3d = st.toggle("3D relief map", value=True,
                        help="Column height = FSI. Drag to rotate, scroll to zoom.")
    if st.button("🔄 Refresh live data now", use_container_width=True):
        live_frame.clear()
        st.rerun()
    st.divider()
    st.markdown("**FSI legend**  \n> 75 CRITICAL · 55-75 HIGH  \n35-55 MODERATE · < 35 LOW")
    st.divider()
    st.caption(f"Signals auto-refresh every {REFRESH_SECONDS // 60} minutes. "
               "If a source is unreachable, the last cached value is shown "
               "(offline-first design).")


@st.fragment(run_every=REFRESH_SECONDS)
def dashboard_body() -> None:
    with st.spinner("Pulling live signals for 16 districts…"):
        df, fetched_at = live_frame()
    if df.empty:
        st.info("No signal sources reachable and no cache yet — check connectivity and refresh.")
        return

    n_total = len(districts())
    n_live = int((df.source == "live").sum())
    n_cached = len(df) - n_live
    n_missing = n_total - len(df)
    parts = [f"{n_live} live"]
    if n_cached:
        parts.append(f"{n_cached} cached")
    if n_missing:
        parts.append(f"{n_missing} awaiting first fetch")
    st.markdown(
        f"<span class='live-badge'><span class='live-dot'></span>"
        f"LIVE · {' · '.join(parts)} of {n_total} districts · updated {fetched_at}</span>",
        unsafe_allow_html=True)
    st.markdown("")

    n_crit = int((df.fsi > 75).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Districts monitored", len(df))
    c2.metric("Critical (FSI > 75)", n_crit, delta="alerts active" if n_crit else "none",
              delta_color="inverse" if n_crit else "off")
    c3.metric("Mean FSI", f"{df.fsi.mean():.1f}")
    c4.metric("Highest stress", f"{df.fsi.max():.1f}", delta=df.loc[df.fsi.idxmax(), "district"],
              delta_color="off")
    st.markdown("")

    left, right = st.columns([3, 2])
    with left:
        if view_3d:
            st.pydeck_chart(deck_3d(df), height=560)
            st.caption("Column height & colour = FSI · hover for evidence · drag to rotate")
        else:
            st.plotly_chart(chart_2d(df), use_container_width=True)

    with right:
        crit = df[df.fsi > 75].sort_values("fsi", ascending=False)
        if len(crit):
            st.markdown(f"### ⚠️ Critical districts &nbsp;<span class='crit-badge'>{len(crit)} active</span>",
                        unsafe_allow_html=True)
            st.dataframe(
                crit[["district", "region", "crop", "fsi", "rain_deficit_%", "price_gap_%", "ndvi"]],
                hide_index=True, use_container_width=True)
        else:
            st.markdown("### Critical districts")
            st.success("No district above the critical threshold (75).")
        st.markdown("### All districts")
        st.dataframe(
            df.sort_values("fsi", ascending=False)[["district", "region", "fsi", "level", "source"]],
            hide_index=True, use_container_width=True, height=250)


dashboard_body()
