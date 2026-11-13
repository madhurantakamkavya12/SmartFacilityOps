import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from energy_agent import energy_agent


st.set_page_config(
    page_title="FacilityOps | Energy Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #172b3a;
        --muted: #6f8290;
        --line: #e5ebef;
        --teal: #087e78;
        --mint: #d9f3ec;
        --paper: #f4f7f8;
    }
    html, body, [class*="css"] { font-family: 'Segoe UI', Arial, sans-serif; }
    [data-testid="stAppViewContainer"] { background: var(--paper); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMainBlockContainer"] {
        max-width: 1480px;
        padding-top: 1.4rem;
        padding-bottom: 4rem;
    }
    #MainMenu, footer { visibility: hidden; }
    h1, h2, h3 {
        color: var(--ink) !important;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    h2 { letter-spacing: -0.025em; }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 18px 20px 16px;
        box-shadow: 0 5px 18px rgba(25, 56, 71, 0.035);
        min-height: 122px;
    }
    [data-testid="stMetricLabel"] p {
        color: var(--muted) !important;
        font-size: 0.82rem;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: var(--ink) !important;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-weight: 800;
        letter-spacing: -0.04em;
    }
    [data-testid="stWidgetLabel"] { color: var(--ink) !important; }
    [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span { color: #334b5a !important; }
    [data-testid="stDataFrame"] { color: #334b5a !important; }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p {
        color: var(--ink) !important;
    }
    [data-testid="stExpander"] {
        border-color: var(--line);
        background: #ffffff;
    }
    [data-testid="stTabs"] [role="tablist"] {
        gap: 10px;
        border-bottom: 1px solid var(--line);
    }
    [data-testid="stTabs"] button[role="tab"] {
        color: var(--muted) !important;
        font-weight: 600;
        padding: 12px 16px;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--teal) !important;
    }
    .hero {
        background: linear-gradient(115deg, #123446 0%, #145d63 64%, #158277 100%);
        color: #f7fffd;
        border-radius: 24px;
        padding: 30px 36px;
        margin: 0 0 24px 0;
        position: relative;
        overflow: hidden;
        box-shadow: 0 14px 34px rgba(20, 75, 83, 0.16);
    }
    .hero:after {
        content: '';
        position: absolute;
        right: -58px;
        top: -112px;
        width: 310px;
        height: 310px;
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 50%;
        box-shadow: 0 0 0 32px rgba(255,255,255,0.035), 0 0 0 68px rgba(255,255,255,0.025);
        z-index: 0;
        pointer-events: none;
    }
    .hero > * { position: relative; z-index: 1; }
    .hero-kicker {
        color: #a9e7d8;
        font-size: 0.73rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .hero-title {
        color: #ffffff;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: clamp(1.8rem, 3.1vw, 2.7rem);
        font-weight: 800;
        letter-spacing: -0.055em;
        line-height: 1.08;
        margin: 0 0 10px;
    }
    .hero-subtitle { color: #d2e7e7; font-size: 0.98rem; margin: 0; }
    .hero-meta {
        display: flex;
        gap: 9px;
        flex-wrap: wrap;
        margin-top: 22px;
    }
    .hero-chip {
        border: 1px solid rgba(232,255,249,0.22);
        border-radius: 999px;
        color: #e2f5f1;
        background: rgba(255,255,255,0.08);
        padding: 6px 11px;
        font-size: 0.76rem;
        font-weight: 600;
    }
    .section-eyebrow {
        color: var(--teal);
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin: 5px 0 3px;
    }
    .section-note { color: var(--muted); font-size: 0.9rem; margin-bottom: 14px; }
    .recommendation-card {
        display: flex;
        gap: 14px;
        height: 100%;
        min-height: 126px;
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 16px;
        background: #fff;
        box-shadow: 0 5px 18px rgba(25, 56, 71, 0.035);
    }
    .recommendation-number {
        flex: 0 0 34px;
        width: 34px;
        height: 34px;
        display: grid;
        place-items: center;
        color: #076b67;
        background: var(--mint);
        border-radius: 11px;
        font-size: 0.78rem;
        font-weight: 800;
    }
    .recommendation-text { color: #334b5a; font-size: 0.91rem; line-height: 1.55; }
    .panel {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 19px 21px;
        box-shadow: 0 5px 18px rgba(25, 56, 71, 0.035);
    }
    .status-note {
        border-left: 4px solid #dc9b33;
        border-radius: 0 12px 12px 0;
        background: #fff8e9;
        color: #624b27;
        padding: 13px 16px;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

project_folder = Path(__file__).resolve().parents[1]
processed_folder = project_folder / "data" / "processed"
processed_file = processed_folder / "energy_2013-07-13_to_2013-08-04_1min.csv"
forecast_file = processed_folder / "energy_forecast_2013-08-05.csv"
water_profile_file = processed_folder / "water_signal_profile.json"

timezone = "Asia/Kolkata"
period_start = pd.Timestamp("2013-07-13 00:00:00", tz=timezone)
period_end = pd.Timestamp("2013-08-04 23:59:00", tz=timezone)

st.markdown(
    """
    <section class="hero">
      <div class="hero-kicker">FacilityOps · Milestone 01</div>
      <div class="hero-title">Energy Intelligence</div>
      <p class="hero-subtitle">A clear view of consumption, system signals, and operational opportunities.</p>
      <div class="hero-meta">
        <span class="hero-chip">iAWE residential dataset</span>
        <span class="hero-chip">13 Jul — 04 Aug 2013</span>
        <span class="hero-chip">India time · 1 min readings</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

if not processed_file.exists():
    st.error(f"Processed energy data not found: {processed_file}")
    st.stop()
if not forecast_file.exists():
    st.error(f"Forecast file not found: {forecast_file}")
    st.stop()


@st.cache_data
def load_csv(csv_path):
    """Load a processed CSV and convert its timestamps to India time."""
    frame = pd.read_csv(csv_path)
    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"], utc=True
    ).dt.tz_convert(timezone)
    return frame


@st.cache_data
def run_energy_agent(csv_path, file_modified_time):
    """Run the LangGraph workflow; file time refreshes the cache."""
    return energy_agent.invoke(
        {
            "data_path": csv_path,
            "metrics": {},
            "recommendations": [],
        }
    )


data = load_csv(str(processed_file))
forecast = load_csv(str(forecast_file))
data = (
    data.sort_values("timestamp")
    .set_index("timestamp")
    .reindex(
        pd.date_range(
            start=period_start,
            end=period_end,
            freq="1min",
        )
    )
    .rename_axis("timestamp")
    .reset_index()
)
agent_result = run_energy_agent(
    str(processed_file),
    processed_file.stat().st_mtime,
)
metrics = agent_result["metrics"]

energy_tab, water_tab = st.tabs(["Energy overview", "Water signal quality"])

with energy_tab:
    st.markdown('<div class="section-eyebrow">Period summary</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-note">Recorded consumption and data coverage for the selected period.</div>',
        unsafe_allow_html=True,
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Mains energy", f"{metrics['mains_energy_kwh']:,.2f} kWh")
    kpi2.metric("Both ACs", f"{metrics['ac_energy_kwh']:,.2f} kWh")
    kpi3.metric("AC share", f"{metrics['ac_share_percent']:.1f}%")
    kpi4.metric("Mains coverage", f"{metrics['coverage_percent']:.1f}%")

    st.caption(
        "Energy totals cover recorded minutes. Missing AC readings are treated as off; "
        "missing mains minutes remain missing."
    )

    if metrics["anomaly_count"] > 0:
        st.warning(
            f"Data quality review: {metrics['anomaly_count']:,} minutes "
            f"({metrics['anomaly_percent']:.2f}%) show AC power above combined mains power. "
            "These readings are flagged for review, not treated as confirmed faults."
        )

    st.markdown('<div class="section-eyebrow">Agent briefing</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-note">Rule-based recommendations based on the observed data.</div>',
        unsafe_allow_html=True,
    )
    recommendations = agent_result["recommendations"]
    if recommendations:
        rec_columns = st.columns(min(len(recommendations), 3))
        for index, recommendation in enumerate(recommendations):
            safe_recommendation = html.escape(str(recommendation))
            rec_columns[index % len(rec_columns)].markdown(
                f'<div class="recommendation-card">'
                f'<div class="recommendation-number">{index + 1:02d}</div>'
                f'<div class="recommendation-text">{safe_recommendation}</div>'
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-eyebrow">Load profile</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-note">Hourly observed power alongside the next-day baseline forecast.</div>',
        unsafe_allow_html=True,
    )

    mains_by_minute = data.set_index("timestamp")["total_mains_W"]
    historical_hourly = mains_by_minute.resample("1h").mean()
    hourly_reading_count = mains_by_minute.resample("1h").count()
    historical_hourly[hourly_reading_count < 48] = float("nan")
    history = historical_hourly.rename("power_W").reset_index()
    forecast_points = forecast[["timestamp", "forecast_power_W"]].rename(
        columns={"forecast_power_W": "power_W"}
    )

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history["timestamp"],
            y=history["power_W"],
            name="Observed hourly average",
            mode="lines",
            line={"color": "#087e78", "width": 2.4},
            hovertemplate="%{x|%d %b, %H:%M}<br>%{y:,.0f} W<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_points["timestamp"],
            y=forecast_points["power_W"],
            name="Next-day baseline forecast",
            mode="lines+markers",
            line={"color": "#e69b46", "width": 2.4, "dash": "dash"},
            marker={"size": 5},
            hovertemplate="%{x|%d %b, %H:%M}<br>%{y:,.0f} W<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white",
        height=430,
        margin={"l": 8, "r": 12, "t": 28, "b": 8},
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#ffffff",
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#496070", "size": 12},
        hovermode="x unified",
        legend={
            "orientation": "h",
            "y": 1.08,
            "x": 0,
            "font": {"color": "#496070"},
            "bgcolor": "rgba(255,255,255,0)",
        },
        yaxis_title="Average power (W)",
        xaxis_title=None,
    )
    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
        tickfont={"color": "#607584"},
        title_font={"color": "#334b5a"},
    )
    figure.update_yaxes(
        gridcolor="#e8eef1",
        zeroline=False,
        tickfont={"color": "#607584"},
        title_font={"color": "#334b5a"},
    )
    with st.container(border=True):
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displayModeBar": False},
        )

    with st.expander("View all 24 forecast hours"):
        forecast_table = forecast.copy()
        forecast_table["forecast_power_W"] = forecast_table["forecast_power_W"].round(1)
        forecast_table["forecast_energy_kWh"] = forecast_table[
            "forecast_energy_kWh"
        ].round(3)
        st.dataframe(forecast_table, hide_index=True, width="stretch")

with water_tab:
    st.markdown('<div class="section-eyebrow">Water meter data audit</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-note">Signal integrity summary for the raw water-meter feed.</div>',
        unsafe_allow_html=True,
    )

    if not water_profile_file.exists():
        st.info(
            "Water profile not found. Run "
            "`.\\.venv\\Scripts\\python.exe .\\src\\profile_water.py` "
            "to create it."
        )
    else:
        with water_profile_file.open(encoding="utf-8") as profile_stream:
            water_profile = json.load(profile_stream)

        total_rows = water_profile["row_count"]
        valid_rows = water_profile["valid_row_count"]
        pass_rate = valid_rows / total_rows * 100 if total_rows else 0
        water_kpi1, water_kpi2, water_kpi3 = st.columns(3)
        water_kpi1.metric("Rows profiled", f"{total_rows:,}")
        water_kpi2.metric("Format pass rate", f"{pass_rate:.4f}%")
        water_kpi3.metric(
            "Rows for review", f"{water_profile['invalid_row_count']:,}"
        )

        st.markdown(
            '<div class="status-note"><strong>Volume is not estimated.</strong> '
            "Repeated state records and uncertain pulse calibration make record counts "
            "unsuitable as litres. This profile is kept separate from energy totals.</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"Validated timestamp span: {water_profile['timestamp_start_india']} to "
            f"{water_profile['timestamp_end_india']} (India time)."
        )

        audit_col1, audit_col2 = st.columns([1, 1.4])
        meter_table = pd.DataFrame(
            [
                {"Meter ID": meter_id, "Records": count}
                for meter_id, count in water_profile["meter_record_counts"].items()
            ]
        )
        with audit_col1.container(border=True):
            st.subheader("Records by meter")
            st.dataframe(meter_table, hide_index=True, width="stretch")

        state_table = pd.DataFrame(
            [
                {"Reported state": f"State {state}", "Record count": count}
                for state, count in water_profile["state_record_counts"].items()
            ]
        )
        state_figure = go.Figure(
            go.Bar(
                x=state_table["Record count"],
                y=state_table["Reported state"],
                orientation="h",
                marker_color=["#a9c6c3", "#087e78"],
                text=[f"{value:,}" for value in state_table["Record count"]],
                textposition="outside",
                hovertemplate="%{y}<br>%{x:,} records<extra></extra>",
            )
        )
        state_figure.update_layout(
            template="plotly_white",
            height=220,
            margin={"l": 8, "r": 72, "t": 12, "b": 12},
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="#ffffff",
            font={"family": "Segoe UI, Arial, sans-serif", "color": "#496070", "size": 12},
            xaxis={"showgrid": False, "showticklabels": False, "zeroline": False},
            yaxis={"showgrid": False, "title": None},
            showlegend=False,
        )
        with audit_col2.container(border=True):
            st.subheader("Reported state records")
            st.plotly_chart(
                state_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

        with st.expander("Example rows flagged for review"):
            st.dataframe(
                pd.DataFrame(water_profile["invalid_examples"]),
                hide_index=True,
                width="stretch",
            )

st.markdown(
    '<div style="color:#82929c;font-size:.75rem;text-align:center;padding-top:28px">'
    "FacilityOps Energy Intelligence · Prototype analytics for the iAWE residential dataset"
    "</div>",
    unsafe_allow_html=True,
)
