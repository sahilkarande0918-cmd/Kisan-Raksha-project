"""Overview — live 3D relief map + KPI cards (clickable → Districts page)."""
import plotly.express as px
import streamlit as st

from dashboard import ui
from mcp_server.tools.common import districts


def chart_2d(df):
    fig = px.choropleth_map(
        df, geojson=ui.load_geojson(), locations="geo_name",
        featureidkey="properties.dtname", color="fsi",
        color_continuous_scale=["#2e7d32", "#fdd835", "#ef6c00", "#b71c1c"],
        range_color=(0, 100), hover_name="district",
        hover_data={"geo_name": False, "fsi": ":.1f", "level": True, "crop": True},
        labels={"fsi": "FSI"},
        map_style="carto-positron", zoom=5.4, center={"lat": 19.9, "lon": 77.5}, opacity=0.8)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=540,
                      coloraxis_colorbar_title="FSI")
    return fig


@st.fragment(run_every=ui.REFRESH_SECONDS)
def body() -> None:
    with st.spinner("Pulling live signals for 16 districts…"):
        df, fetched_at = ui.live_frame()
    if df.empty:
        st.info("No signal sources reachable and no cache yet — check connectivity and refresh.")
        return

    n_total = len(districts())
    n_live = int((df.source == "live").sum())
    n_cached = len(df) - n_live
    n_missing = n_total - len(df)
    parts = [f"{n_live} live"] + ([f"{n_cached} cached"] if n_cached else []) \
        + ([f"{n_missing} awaiting first fetch"] if n_missing else [])
    st.markdown(
        f"<span class='live-badge'><span class='live-dot'></span>"
        f"LIVE · {' · '.join(parts)} of {n_total} districts · updated {fetched_at}</span>",
        unsafe_allow_html=True)
    st.markdown("")

    n_crit = int((df.fsi > 75).sum())
    hi = df.loc[df.fsi.idxmax()]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<a class="kcard clickable d1" href="districts" target="_self">
            <div class="klabel">Districts monitored</div>
            <div class="kvalue">{len(df)}</div>
            <div class="ksub">Vidarbha + Marathwada</div></a>""", unsafe_allow_html=True)
    with c2:
        crit_col = "#c62828" if n_crit else "#1b5e20"
        st.markdown(f"""<div class="kcard d2">
            <div class="klabel">Critical (FSI &gt; 75)</div>
            <div class="kvalue" style="color:{crit_col}">{n_crit}</div>
            <div class="ksub">{'⚠️ alerts active' if n_crit else 'no active alerts'}</div></div>""",
            unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="kcard d3">
            <div class="klabel">Mean FSI</div>
            <div class="kvalue">{df.fsi.mean():.1f}</div>
            <div class="ksub">across monitored districts</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<a class="kcard clickable d4" href="districts?district={hi['district']}" target="_self">
            <div class="klabel">Highest stress</div>
            <div class="kvalue">{hi['fsi']:.1f}</div>
            <div class="ksub">{hi['district']} · {hi['level']}</div></a>""", unsafe_allow_html=True)
    st.markdown("")

    left, right = st.columns([3, 2])
    with left:
        if st.session_state.get("view_3d", True):
            st.pydeck_chart(ui.deck_3d(df), height=540)
            st.caption("Column height & colour = FSI · hover for evidence · drag to rotate")
        else:
            st.plotly_chart(chart_2d(df), use_container_width=True)
    with right:
        crit = df[df.fsi > 75].sort_values("fsi", ascending=False)
        if len(crit):
            st.markdown(f"### ⚠️ Critical districts <span class='crit-badge'>{len(crit)} active</span>",
                        unsafe_allow_html=True)
            st.dataframe(crit[["district", "region", "crop", "fsi", "rain_deficit_%", "price_gap_%"]],
                         hide_index=True, use_container_width=True)
        else:
            st.markdown("### Critical districts")
            st.success("No district above the critical threshold (75).")
        st.markdown("### Top stress right now")
        st.dataframe(
            df.sort_values("fsi", ascending=False).head(8)[["district", "region", "fsi", "level", "source"]],
            hide_index=True, use_container_width=True, height=250)


def render() -> None:
    ui.hero("🌾 KisaanRaksha — Farmer Financial Stress Index",
            "Live early-warning command centre · rainfall (Open-Meteo) · mandi vs MSP (Agmarknet) · NDVI (NASA MODIS)")
    with st.sidebar:
        st.toggle("3D relief map", value=True, key="view_3d",
                  help="Column height = FSI. Drag to rotate, scroll to zoom.")
        if st.button("🔄 Refresh live data now", use_container_width=True):
            ui.live_frame.clear()
            st.rerun()
        st.divider()
        st.markdown("**FSI legend**  \n> 75 CRITICAL · 55-75 HIGH  \n35-55 MODERATE · < 35 LOW")
        st.caption(f"Auto-refreshes every {ui.REFRESH_SECONDS // 60} min · offline-first cache fallback")
    body()
