"""Shared UI system + data helpers for the KisaanRaksha dashboard."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.tools.common import DATA_DIR, OFFLINE_CACHE_PATH, districts  # noqa: E402
from mcp_server.tools.fsi import compute_fsi  # noqa: E402

REFRESH_SECONDS = 600

GEO_ALIAS = {
    "Beed": "Bid",
    "Buldhana": "Buldana",
    "Chhatrapati Sambhajinagar": "Aurangabad",
    "Dharashiv": "Osmanabad",
}

LEVEL_COLORS = {"CRITICAL": "#c62828", "HIGH": "#ef6c00", "MODERATE": "#f9a825", "LOW": "#2e7d32"}


# ---------------------------------------------------------------- styling ----
CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Sora', 'Segoe UI', sans-serif; }
  .block-container { padding-top: 1.0rem; max-width: 1250px; }
  h1, h2, h3 { letter-spacing: -0.5px; }

  /* ---------- animated field background ---------- */
  .stApp {
      background:
        radial-gradient(60vw 60vw at 110% -10%, rgba(129,199,132,.20), transparent 60%),
        radial-gradient(50vw 50vw at -10% 110%, rgba(174,213,129,.22), transparent 60%),
        linear-gradient(165deg, #f7fbf5 0%, #eef7ee 55%, #f2f8ec 100%);
  }
  .stApp::before, .stApp::after {
      content: ""; position: fixed; z-index: 0; pointer-events: none;
      border-radius: 50%; filter: blur(90px);
  }
  .stApp::before {
      width: 44vw; height: 44vw; background: #66bb6a; opacity:.14;
      top: -12vw; right: -10vw; animation: drift1 26s ease-in-out infinite;
  }
  .stApp::after {
      width: 36vw; height: 36vw; background: #c5e1a5; opacity:.20;
      bottom: -10vw; left: -8vw; animation: drift2 32s ease-in-out infinite;
  }
  @keyframes drift1 { 0%,100% {transform: translate(0,0) scale(1);} 50% {transform: translate(-6vw,4vh) scale(1.08);} }
  @keyframes drift2 { 0%,100% {transform: translate(0,0) scale(1);} 50% {transform: translate(5vw,-4vh) scale(1.06);} }

  /* ---------- hero ---------- */
  .hero {
      position: relative; overflow: hidden;
      background: linear-gradient(120deg, #1b5e20 0%, #2e7d32 45%, #43a047 80%);
      background-size: 200% 200%;
      animation: heroShift 14s ease infinite;
      border-radius: 20px; padding: 26px 32px 22px;
      box-shadow: 0 16px 40px rgba(27,94,32,.30);
      margin-bottom: 1.1rem;
  }
  @keyframes heroShift { 0%,100% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} }
  .hero h1 { color: #ffffff; margin: 0 0 4px; font-size: 1.9rem; font-weight: 800; }
  .hero p  { color: #dcedc8; margin: 0; font-size: .95rem; }
  .hero::after {
      content:""; position:absolute; inset:0;
      background: radial-gradient(50% 120% at 85% 10%, rgba(255,255,255,.18), transparent 60%);
      pointer-events:none;
  }

  /* ---------- glass cards + 3D tilt ---------- */
  .kcard {
      position: relative; display:block; text-decoration: none !important;
      background: rgba(255,255,255,.72);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(46,125,50,.22);
      border-radius: 16px; padding: 18px 20px 14px;
      box-shadow: 0 8px 24px rgba(27,94,32,.10);
      transition: transform .35s cubic-bezier(.2,.8,.3,1), box-shadow .35s ease, border-color .35s ease;
      transform-style: preserve-3d; will-change: transform;
      animation: fadeUp .6s ease both;
  }
  .kcard:hover {
      transform: perspective(900px) rotateX(3deg) rotateY(-3deg) translateY(-5px);
      box-shadow: 0 18px 42px rgba(27,94,32,.22);
      border-color: rgba(46,125,50,.55);
  }
  .kcard .klabel { font-size:.82rem; color:#4b6b50; font-weight:600; margin-bottom:2px; }
  .kcard .kvalue { font-size:2.0rem; font-weight:800; color:#1b5e20; line-height:1.15; }
  .kcard .ksub   { font-size:.8rem; color:#6b8a70; }
  .kcard.clickable::after {
      content:"→ view all"; position:absolute; right:14px; bottom:10px;
      font-size:.75rem; color:#2e7d32; font-weight:600; opacity:0;
      transition: opacity .3s ease;
  }
  .kcard.clickable:hover::after { opacity:1; }

  @keyframes fadeUp { from {opacity:0; transform: translateY(14px);} to {opacity:1; transform: translateY(0);} }
  .d1 { animation-delay:.05s; } .d2 { animation-delay:.12s; }
  .d3 { animation-delay:.19s; } .d4 { animation-delay:.26s; }

  /* ---------- district cards grid ---------- */
  .dgrid { display:grid; grid-template-columns: repeat(auto-fill, minmax(250px,1fr)); gap:14px; }
  .dcard {
      position:relative; display:block; text-decoration:none !important;
      background: rgba(255,255,255,.78); backdrop-filter: blur(10px);
      border:1px solid rgba(46,125,50,.18); border-left:6px solid var(--lvl,#2e7d32);
      border-radius:14px; padding:14px 16px;
      box-shadow:0 6px 18px rgba(27,94,32,.08);
      transition: transform .3s cubic-bezier(.2,.8,.3,1), box-shadow .3s ease;
      animation: fadeUp .5s ease both;
  }
  .dcard:hover { transform: perspective(700px) rotateX(2.5deg) translateY(-4px) scale(1.015);
                 box-shadow:0 14px 34px rgba(27,94,32,.20); }
  .dcard .dname { font-weight:700; color:#1b2e1f; font-size:1.02rem; }
  .dcard .dregion { font-size:.75rem; color:#6b8a70; }
  .dcard .dfsi { font-size:1.7rem; font-weight:800; color:var(--lvl,#2e7d32); }
  .dcard .dlevel {
      display:inline-block; padding:1px 10px; border-radius:9px; font-size:.72rem; font-weight:700;
      color:#fff; background:var(--lvl,#2e7d32);
  }
  .dcard .dsig { font-size:.76rem; color:#4b6b50; margin-top:6px; }

  /* ---------- badges ---------- */
  .live-badge {
      display:inline-block; padding:4px 14px; border-radius:12px;
      background:rgba(232,245,233,.9); color:#2e7d32; font-weight:600; font-size:.85rem;
      border:1px solid #a5d6a7; backdrop-filter: blur(6px);
  }
  .live-dot {
      display:inline-block; width:8px; height:8px; border-radius:50%;
      background:#2e7d32; margin-right:6px;
      animation: livepulse 2s ease-in-out infinite;
  }
  @keyframes livepulse { 0%,100% {opacity:1; box-shadow:0 0 0 0 rgba(46,125,50,.5);} 50% {opacity:.45; box-shadow:0 0 0 5px rgba(46,125,50,0);} }
  .crit-badge {
      display:inline-block; padding:2px 10px; border-radius:10px;
      background:#ffebee; color:#c62828; font-weight:700;
      border:1px solid #ef9a9a; animation: livepulse 2.4s ease-in-out infinite;
  }

  /* ---------- section panels ---------- */
  .panel {
      background: rgba(255,255,255,.66); backdrop-filter: blur(12px);
      border:1px solid rgba(46,125,50,.16); border-radius:18px;
      padding:22px 26px; margin-bottom:1rem;
      box-shadow:0 8px 26px rgba(27,94,32,.08);
      animation: fadeUp .6s ease both;
  }
  .panel h3 { margin-top:0; color:#1b5e20; }

  /* architecture flow */
  .flow { display:flex; align-items:stretch; gap:8px; flex-wrap:wrap; }
  .fbox {
      flex:1; min-width:130px; text-align:center;
      background:linear-gradient(160deg,#e8f5e9,#f1f8e9);
      border:1px solid #a5d6a7; border-radius:12px; padding:12px 8px;
      transition: transform .3s ease;
  }
  .fbox:hover { transform: translateY(-4px); }
  .fbox b { color:#1b5e20; font-size:.88rem; display:block; }
  .fbox span { color:#4b6b50; font-size:.72rem; }
  .farrow { align-self:center; color:#2e7d32; font-weight:800; font-size:1.2rem; }

  .sdg { display:inline-block; margin:3px; padding:6px 14px; border-radius:20px;
         background:linear-gradient(120deg,#1b5e20,#43a047); color:#fff; font-weight:600; font-size:.82rem;
         box-shadow:0 4px 12px rgba(27,94,32,.25); }

  [data-testid="stSidebarNav"] { display:none; }  /* we render our own nav via st.navigation */
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(f"""<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>""",
                unsafe_allow_html=True)


# ------------------------------------------------------------------- data ----
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
    """Live FSI for all districts, parallel with retry; cache fallback."""
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

    with ThreadPoolExecutor(max_workers=5) as ex:
        rows = [r for r in ex.map(fetch, dist_list) if r]
    return pd.DataFrame(rows), datetime.now().strftime("%d %b %Y, %H:%M:%S")


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def district_fsi(name: str, crop: str) -> dict:
    """Full FSI result for one district (detail page)."""
    try:
        r = compute_fsi(name, crop)
        if r.get("fsi") is not None:
            return r
    except Exception:
        pass
    return cached_fsi().get(f"{name}:{crop}") or {}


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
                "fill": rgb + [225], "monitored": True,
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
        transitions={"getElevation": 900},
    )
    tooltip = {
        "html": "<b>{district}</b><br/>FSI: <b>{fsi}</b> ({level})<br/>"
                "Crop: {crop} · Rain deficit: {deficit}%<br/>Price below MSP: {gap}%",
        "style": {"backgroundColor": "#ffffff", "color": "#1b2e1f",
                  "border": "1px solid #2e7d32", "borderRadius": "8px", "fontSize": "13px"},
    }
    view = pdk.ViewState(latitude=20.4, longitude=77.6, zoom=5.5, pitch=45, bearing=-12)
    return pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip,
                    map_provider="carto", map_style="light")
