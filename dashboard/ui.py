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
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

  /* ---------- typography system ----------
     Sora        -> display / headings
     Inter       -> body, UI, labels
     Space Grotesk -> numbers, metrics, data                    */
  html, body, [class*="css"], .stApp, p, li, label, input, textarea {
      font-family: 'Inter', 'Segoe UI', sans-serif;
  }
  /* light base so a page load never flashes to black */
  html, body, #root, [data-testid="stAppViewContainer"] { background-color: #eef7ee; }
  h1, h2, h3, h4, .hero h1, .brand, .dname,
  [data-testid="stMarkdownContainer"] h1,
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h3 {
      font-family: 'Sora', 'Segoe UI', sans-serif !important;
      letter-spacing: -0.6px;
  }
  .kvalue, .dfsi, [data-testid="stMetricValue"] {
      font-family: 'Space Grotesk', monospace !important;
      font-feature-settings: 'tnum';
  }
  .block-container { padding-top: 4.4rem; max-width: 1250px; }

  /* ---------- layered mesh background (gives the glass something to blur) -- */
  .stApp {
      background:
        radial-gradient(55vw 55vw at 112% -8%,  rgba(102,187,106,.34), transparent 62%),
        radial-gradient(48vw 48vw at -12% 108%, rgba(174,213,129,.38), transparent 60%),
        radial-gradient(34vw 34vw at 84% 82%,   rgba(38,166,154,.16),  transparent 60%),
        radial-gradient(30vw 30vw at 12% 18%,   rgba(255,241,118,.18), transparent 58%),
        linear-gradient(160deg, #f2faf0 0%, #e4f3e4 48%, #edf7e4 100%);
  }
  .stApp::before, .stApp::after {
      content: ""; position: fixed; z-index: 0; pointer-events: none;
      border-radius: 50%; filter: blur(70px);
      will-change: transform; transform: translateZ(0);
      backface-visibility: hidden;
  }
  .stApp::before {
      width: 44vw; height: 44vw; background: radial-gradient(circle, #4caf50, #81c784);
      opacity:.24; top: -12vw; right: -10vw; animation: drift1 30s ease-in-out infinite;
  }
  .stApp::after {
      width: 38vw; height: 38vw; background: radial-gradient(circle, #aed581, #dcedc8);
      opacity:.30; bottom: -10vw; left: -8vw; animation: drift2 36s ease-in-out infinite;
  }
  @media (prefers-reduced-motion: reduce) {
      .stApp::before, .stApp::after, .hero { animation: none !important; }
  }
  @keyframes drift1 { 0%,100% {transform: translate(0,0) scale(1);} 50% {transform: translate(-7vw,5vh) scale(1.10);} }
  @keyframes drift2 { 0%,100% {transform: translate(0,0) scale(1);} 50% {transform: translate(6vw,-5vh) scale(1.07);} }

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

  /* ---------- green glassmorphism recipe ---------- */
  .kcard {
      position: relative; display:block; text-decoration: none !important;
      background: linear-gradient(135deg, rgba(255,255,255,.62) 0%, rgba(232,245,233,.44) 55%, rgba(200,230,201,.36) 100%);
      backdrop-filter: blur(11px); -webkit-backdrop-filter: blur(11px);
      border: 1px solid rgba(255,255,255,.65);
      border-top: 1.5px solid rgba(255,255,255,.9);
      border-radius: 18px; padding: 18px 20px 14px;
      box-shadow: 0 8px 26px rgba(27,94,32,.14), inset 0 1px 0 rgba(255,255,255,.6);
      transition: transform .3s cubic-bezier(.2,.8,.3,1), box-shadow .3s ease, border-color .3s ease;
      will-change: transform; transform: translateZ(0);
      animation: fadeUp .5s ease both;
      overflow: hidden;
  }
  .kcard::before {
      content:""; position:absolute; top:0; left:-70%; width:50%; height:100%;
      background: linear-gradient(105deg, transparent, rgba(255,255,255,.45), transparent);
      transform: skewX(-20deg); transition: left .6s ease;
  }
  .kcard:hover::before { left: 130%; }
  .kcard:hover {
      transform: perspective(900px) rotateX(3deg) rotateY(-3deg) translateY(-5px);
      box-shadow: 0 20px 48px rgba(27,94,32,.26), inset 0 1px 0 rgba(255,255,255,.7);
      border-color: rgba(165,214,167,.95);
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
      background: linear-gradient(135deg, rgba(255,255,255,.66) 0%, rgba(232,245,233,.46) 100%);
      backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
      border:1px solid rgba(255,255,255,.6); border-left:6px solid var(--lvl,#2e7d32);
      border-top: 1.5px solid rgba(255,255,255,.85);
      border-radius:16px; padding:14px 16px;
      box-shadow:0 6px 20px rgba(27,94,32,.12), inset 0 1px 0 rgba(255,255,255,.55);
      transition: transform .28s cubic-bezier(.2,.8,.3,1), box-shadow .28s ease;
      will-change: transform; transform: translateZ(0);
      animation: fadeUp .45s ease both;
  }
  .dcard:hover { transform: perspective(700px) rotateX(2.5deg) translateY(-4px) scale(1.015);
                 box-shadow:0 16px 40px rgba(27,94,32,.26), inset 0 1px 0 rgba(255,255,255,.65); }
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

  /* ---------- section panels (green glass) ---------- */
  .panel {
      background: linear-gradient(150deg, rgba(255,255,255,.60) 0%, rgba(232,245,233,.42) 60%, rgba(220,237,200,.36) 100%);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border:1px solid rgba(255,255,255,.62);
      border-top: 1.5px solid rgba(255,255,255,.88);
      border-radius:20px;
      padding:22px 26px; margin-bottom:1rem;
      box-shadow:0 10px 28px rgba(27,94,32,.12), inset 0 1px 0 rgba(255,255,255,.55);
      will-change: transform; transform: translateZ(0);
      animation: fadeUp .5s ease both;
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

  [data-testid="stSidebarNav"] { display:none; }  /* we render our own nav via the topbar */

  /* ---------- smooth scrolling ---------- */
  html { scroll-behavior: smooth; }
  [data-testid="stMain"], section.main, .stApp { scroll-behavior: smooth; }

  /* ---------- sticky glass top navigation bar (native page links) ---------- */
  [data-testid="stHeader"] { background: rgba(247,251,245,.65); backdrop-filter: blur(8px); }
  .st-key-topbar {
      position: sticky; top: .4rem; z-index: 1000;
      background: linear-gradient(120deg, rgba(255,255,255,.72) 0%, rgba(232,245,233,.58) 100%);
      backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
      border: 1px solid rgba(255,255,255,.75);
      border-top: 1.5px solid rgba(255,255,255,.95);
      border-radius: 16px;
      padding: 6px 16px; margin-bottom: 16px;
      box-shadow: 0 8px 24px rgba(27,94,32,.16);
      transform: translateZ(0);   /* promote to its own GPU layer */
  }
  .st-key-topbar [data-testid="stHorizontalBlock"] { gap: .4rem; }
  .brandwrap { font-family:'Sora',sans-serif; font-weight:800; color:#1b5e20;
               font-size:1.08rem; white-space:nowrap; }
  /* pill styling for native page links */
  .st-key-topbar [data-testid="stPageLink"] a {
      border-radius: 11px; padding: 7px 8px; justify-content: center;
      transition: background .2s ease, transform .2s ease, box-shadow .2s ease;
  }
  .st-key-topbar [data-testid="stPageLink"] a p { font-weight: 600; color:#2f5136; }
  .st-key-topbar [data-testid="stPageLink"] a:hover {
      background: #e2f2e2 !important; transform: translateY(-1px);
  }
  /* active page link (Streamlit marks it aria-current) */
  .st-key-topbar [data-testid="stPageLink"] a[aria-current="page"] {
      background: linear-gradient(120deg, #1b5e20, #43a047) !important;
      box-shadow: 0 4px 12px rgba(27,94,32,.30);
  }
  .st-key-topbar [data-testid="stPageLink"] a[aria-current="page"] p { color: #fff !important; }

  /* ---------- skeleton shimmer (themed loading state) ---------- */
  .skwrap { display:grid; grid-template-columns: repeat(4,1fr); gap:14px; margin:8px 0 18px; }
  .sk {
      height: 92px; border-radius: 16px;
      background: linear-gradient(100deg, rgba(232,245,233,.55) 30%, rgba(255,255,255,.85) 50%, rgba(232,245,233,.55) 70%);
      background-size: 200% 100%;
      border: 1px solid rgba(165,214,167,.5);
      animation: shimmer 1.3s ease-in-out infinite;
  }
  .sk.tall { height: 300px; }
  @keyframes shimmer { 0% {background-position: 180% 0;} 100% {background-position: -180% 0;} }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def build_pages() -> dict:
    """Create the page objects once; shared by st.navigation and the topbar."""
    from dashboard.views import about_page, activity_page, districts_page, overview
    return {
        "overview": st.Page(overview.render, title="Home", icon="🗺️",
                            url_path="overview", default=True),
        "districts": st.Page(districts_page.render, title="Districts", icon="📍",
                             url_path="districts"),
        "activity": st.Page(activity_page.render, title="Field activity", icon="📞",
                            url_path="activity"),
        "about": st.Page(about_page.render, title="About", icon="🌾", url_path="about"),
    }


def topbar(pages: dict, active: str = "overview") -> None:
    """Sticky navigation bar using native page links (instant, no page reload)."""
    with st.container(key="topbar"):
        c = st.columns([2.4, 1, 1.15, 1.5, 1], vertical_alignment="center")
        c[0].markdown("<div class='brandwrap'>🌾&nbsp;<b>KisaanRaksha</b></div>",
                      unsafe_allow_html=True)
        c[1].page_link(pages["overview"], label="Home", icon="🗺️")
        c[2].page_link(pages["districts"], label="Districts", icon="📍")
        c[3].page_link(pages["activity"], label="Field activity", icon="📞")
        c[4].page_link(pages["about"], label="About", icon="🌾")
    # Streamlit marks the active link only with an unstable hashed class, so we
    # drive the active pill from the page we already know is current.
    col = {"overview": 2, "districts": 3, "activity": 4, "about": 5}.get(active, 2)
    st.markdown(
        f"<style>"
        f".st-key-topbar [data-testid='stColumn']:nth-child({col}) [data-testid='stPageLink'] a"
        f"{{background:linear-gradient(120deg,#1b5e20,#43a047)!important;"
        f"box-shadow:0 4px 12px rgba(27,94,32,.30);}}"
        f".st-key-topbar [data-testid='stColumn']:nth-child({col}) [data-testid='stPageLink'] a p"
        f"{{color:#ffffff!important;}}</style>",
        unsafe_allow_html=True)


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
