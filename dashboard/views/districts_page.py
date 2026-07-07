"""Districts — full status grid; click a card for the officer detail view."""
import plotly.graph_objects as go
import streamlit as st

from alerts.whatsapp import format_officer_alert
from dashboard import ui
from mcp_server.tools.common import crop_calendar, districts, find_district

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def gauge(fsi: float, level: str) -> go.Figure:
    color = ui.LEVEL_COLORS.get(level, "#2e7d32")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=fsi,
        number={"font": {"size": 44, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.28},
            "steps": [
                {"range": [0, 35], "color": "#e8f5e9"},
                {"range": [35, 55], "color": "#fff9c4"},
                {"range": [55, 75], "color": "#ffe0b2"},
                {"range": [75, 100], "color": "#ffcdd2"},
            ],
            "threshold": {"line": {"color": "#c62828", "width": 3}, "value": 75},
        },
    ))
    fig.update_layout(height=240, margin=dict(l=24, r=24, t=18, b=6),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def month_strip(window: dict, color: str) -> str:
    s, e = window["start_month"], window["end_month"]
    active = {m for m in range(1, 13)
              if (s <= m <= e) if s <= e} if s <= e else {m for m in range(1, 13) if m >= s or m <= e}
    cells = "".join(
        f"<span style='display:inline-block;width:32px;text-align:center;padding:3px 0;"
        f"border-radius:6px;margin:1px;font-size:.68rem;font-weight:600;"
        f"background:{color if m in active else '#eef2ee'};"
        f"color:{'#fff' if m in active else '#8aa08e'}'>{MONTHS[m-1]}</span>"
        for m in range(1, 13))
    return cells


def detail(name: str) -> None:
    d = find_district(name)
    if not d:
        st.error(f"Unknown district: {name}")
        return
    if st.button("← All districts"):
        st.query_params.clear()
        st.rerun()

    crop = d["major_crops"][0]
    with st.spinner(f"Live signals for {d['name']}…"):
        r = ui.district_fsi(d["name"], crop)
    if not r.get("fsi"):
        st.warning("No live data or cache for this district yet.")
        return
    sig = r.get("signals", {})
    level = r.get("level", "LOW")
    color = ui.LEVEL_COLORS.get(level, "#2e7d32")

    ui.hero(f"{d['name']} · {d['region']}",
            f"Primary crop: {crop} · {len(d['talukas'])} talukas monitored · data: "
            + ("offline cache" if r.get("cached") else "live"))

    left, right = st.columns([2, 3])
    with left:
        st.markdown(f"<div class='panel' style='text-align:center'>"
                    f"<div class='klabel'>FINANCIAL STRESS INDEX</div>"
                    f"<span class='dlevel' style='--lvl:{color}'>{level}</span></div>",
                    unsafe_allow_html=True)
        st.plotly_chart(gauge(r["fsi"], level), use_container_width=True)
    with right:
        st.markdown("<div class='panel'><h3>Signal evidence</h3></div>", unsafe_allow_html=True)
        drought = sig.get("drought", {})
        price = sig.get("price", {})
        ndvi = sig.get("ndvi", {})
        rows = [
            ("🌧️ Rainfall deficit (30-day vs 5-yr)", drought.get("value", 0),
             f"{drought.get('deficit_pct', '—')}% deficit"),
            ("💰 Price below MSP", price.get("value", 0),
             f"₹{price.get('market_price', '—')}/qtl vs MSP ₹{price.get('msp', '—')} "
             f"({price.get('gap_below_msp_pct', '—')}% gap)"),
            ("🛰️ Vegetation stress (NDVI)", ndvi.get("value", 0),
             f"latest NDVI {ndvi.get('latest_ndvi', '—')}"),
            ("📅 Loan repayment proximity", sig.get("repayment_proximity", 0),
             "window " + ("ACTIVE" if sig.get("repayment_proximity", 0) >= 1 else
                          "approaching" if sig.get("repayment_proximity", 0) > 0 else "not current")),
        ]
        for label, val, caption in rows:
            st.markdown(f"**{label}**  —  {caption}")
            st.progress(min(max(float(val or 0), 0.0), 1.0))

    cal = crop_calendar()["crops"]
    st.markdown("<div class='panel'><h3>Crop calendar & officer context</h3></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        for ckey in d["major_crops"]:
            if ckey not in cal:
                continue
            info = cal[ckey]
            st.markdown(f"**{ckey.title()}** ({info['name_mr']}) · MSP ₹{info['msp_rs_per_quintal']}/qtl")
            st.markdown("Sowing " + month_strip(info["sowing"], "#43a047"), unsafe_allow_html=True)
            st.markdown("Harvest " + month_strip(info["harvest"], "#f9a825"), unsafe_allow_html=True)
            st.markdown("Loan due " + month_strip(info["loan_repayment_window"], "#c62828"),
                        unsafe_allow_html=True)
            st.markdown("")
    with c2:
        st.markdown(f"**Talukas ({len(d['talukas'])})**")
        st.markdown(" ".join(
            f"<span style='display:inline-block;background:#e8f5e9;border:1px solid #a5d6a7;"
            f"border-radius:12px;padding:3px 12px;margin:2px;font-size:.8rem;color:#1b5e20'>{t}</span>"
            for t in d["talukas"]), unsafe_allow_html=True)
        st.markdown("")
        with st.expander("📋 Officer alert text (copy for records)"):
            st.code(format_officer_alert(r), language=None)


def grid() -> None:
    ui.hero("📍 All districts — live status board",
            "Every monitored district with its current FSI, level and key signals. Click a card for the full officer view.")
    with st.spinner("Pulling live signals…"):
        df, fetched_at = ui.live_frame()
    if df.empty:
        st.info("No data yet — visit the Overview page first or check connectivity.")
        return
    st.markdown(f"<span class='live-badge'><span class='live-dot'></span>"
                f"updated {fetched_at}</span>", unsafe_allow_html=True)
    st.markdown("")

    q = st.text_input("🔍 Search district", placeholder="e.g. Amravati")
    region = st.radio("Region", ["All", "Vidarbha", "Marathwada"], horizontal=True)
    view = df.sort_values("fsi", ascending=False)
    if q:
        view = view[view.district.str.contains(q, case=False)]
    if region != "All":
        view = view[view.region == region]

    cards = ""
    for i, row in enumerate(view.itertuples()):
        color = ui.LEVEL_COLORS.get(row.level, "#2e7d32")
        cards += f"""<a class="dcard" style="--lvl:{color}; animation-delay:{min(i*0.05, 0.6)}s"
              href="districts?district={row.district}" target="_self">
            <div style="display:flex;justify-content:space-between;align-items:baseline">
              <div><div class="dname">{row.district}</div>
                   <div class="dregion">{row.region} · {row.crop}</div></div>
              <div class="dfsi">{row.fsi:.0f}</div>
            </div>
            <span class="dlevel">{row.level}</span>
            <div class="dsig">🌧️ deficit {row._7}% &nbsp; 💰 MSP gap {row._8}% &nbsp; 🛰️ NDVI {row.ndvi}</div>
        </a>"""
    st.markdown(f"<div class='dgrid'>{cards}</div>", unsafe_allow_html=True)


def render() -> None:
    sel = st.query_params.get("district")
    if sel:
        detail(sel)
    else:
        grid()
