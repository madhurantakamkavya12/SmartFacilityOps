import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from energy_agent import energy_agent
from database import DEFAULT_DB_PATH, load_energy_data


st.set_page_config(
    page_title="FacilityOps | Energy Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #191a1b;
        --muted: #777b7d;
        --line: #e7e8e7;
        --paper: #eaf2f1;
        --surface: #ffffff;
        --soft: #f2f3f2;
        --orange: #ffb83f;
        --orange-ink: #8a5810;
        --teal: #078c88;
        --green: #58a66b;
        --red: #e05e58;
    }
    html, body, [class*="css"] {
        font-family: Inter, "Segoe UI", Arial, sans-serif;
        color: var(--ink);
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(145deg, #edf2f1 0%, #dfeeed 100%);
        color: var(--ink);
    }
    [data-testid="stHeader"] { background: rgba(234, 242, 241, .94); }
    [data-testid="stMainBlockContainer"] {
        max-width: 1480px;
        padding: 1.25rem 2rem 2.4rem;
        background: #fff;
        border-radius: 22px;
        margin-top: 1rem;
        margin-bottom: 2rem;
        box-shadow: 0 18px 55px rgba(31, 70, 72, .13);
    }
    #MainMenu, footer { visibility: hidden; }
    h1, h2, h3 { color: var(--ink) !important; font-family: Inter, "Segoe UI", Arial, sans-serif; }
    h1 { font-size: clamp(1.55rem, 2.3vw, 2rem) !important; letter-spacing: -.045em; margin-bottom: .15rem !important; }
    h2 { letter-spacing: -.035em; }
    p, label, [data-testid="stMarkdownContainer"] { color: var(--ink); }
    [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p { color: var(--ink) !important; }
    [data-testid="stTabs"] [role="tablist"] {
        gap: 7px;
        border-bottom: 1px solid var(--line);
        margin: 6px 0 18px;
    }
    [data-testid="stTabs"] button[role="tab"] {
        color: #73777a !important;
        font-size: .84rem;
        font-weight: 600;
        border-radius: 999px;
        padding: 8px 16px;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        background: #191a1b !important;
        color: #fff !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line) !important;
        border-radius: 13px !important;
        background: #f4f4f3;
    }
    [data-testid="stExpander"] {
        border-color: var(--line);
        background: #fff;
        border-radius: 11px;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p { color: var(--ink) !important; }
    [data-testid="stDataFrame"] { color: #25292b !important; }
    [data-testid="stDataFrame"] * { color: #25292b !important; }
    [data-testid="stDownloadButton"] button {
        background: var(--orange) !important;
        color: #1f1b14 !important;
        border: 0 !important;
        border-radius: 999px !important;
        padding: .55rem 1rem !important;
        font-size: .83rem !important;
        font-weight: 700 !important;
        box-shadow: 0 3px 9px rgba(177, 120, 29, .17);
    }
    [data-testid="stDownloadButton"] button:hover { background: #f5a91f !important; }
    .topbar { display:flex; align-items:center; gap:9px; margin:0 0 18px; color:#232526; }
    .brand-mark {
        width:28px; height:28px; display:grid; place-items:center;
        border-radius:50%; background:var(--orange); color:#29251d;
        font-size:17px; font-weight:800;
    }
    .brand-name { font-weight:750; font-size:.91rem; letter-spacing:-.02em; }
    .brand-divider { height:19px; width:1px; background:#d9dddc; margin:0 4px; }
    .brand-section { color:#777b7d; font-size:.8rem; }
    .page-subtitle { color:var(--muted); font-size:.84rem; margin:0 0 13px; }
    .period-chip {
        display:inline-block; border:1px solid #e5e6e5; border-radius:999px;
        background:#f5f5f4; color:#3c4041; padding:8px 11px;
        font-size:.73rem; font-weight:600; text-align:center;
    }
    .eyebrow { color:#73777a; font-size:.65rem; font-weight:700; letter-spacing:.105em; text-transform:uppercase; }
    .kpi-card {
        min-height:91px; padding:11px 13px 9px; border-right:1px solid #ededec;
    }
    .kpi-label { color:#777b7d; font-size:.69rem; line-height:1.3; font-weight:550; }
    .kpi-value { color:#191a1b; font-size:clamp(1.38rem, 2vw, 1.85rem); line-height:1.18; letter-spacing:-.06em; font-weight:650; margin:6px 0 4px; white-space:nowrap; }
    .kpi-value small { font-size:.48em; letter-spacing:-.015em; font-weight:500; color:#64696b; }
    .kpi-note { color:#73777a; font-size:.65rem; line-height:1.35; }
    .delta-up { color:var(--green); font-weight:700; }
    .delta-warn { color:var(--red); font-weight:700; }
    .section-head { color:#222526; font-size:.98rem; font-weight:700; letter-spacing:-.025em; margin:0 0 2px; }
    .section-note { color:#838789; font-size:.72rem; margin:0 0 12px; }
    .soft-panel { background:#f1f2f1; border:1px solid #eceeed; border-radius:12px; padding:15px 16px 10px; }
    .breakdown-panel { background:#ffcf79; border:1px solid #f7c66d; border-radius:12px; padding:14px 15px 13px; }
    .breakdown-title { color:#29251d; font-size:.86rem; font-weight:700; margin-bottom:2px; }
    .breakdown-note { color:#6c593b; font-size:.66rem; }
    .breakdown-row { display:flex; justify-content:space-between; gap:8px; color:#39352c; font-size:.69rem; padding:4px 0; border-bottom:1px solid rgba(93,72,37,.12); }
    .breakdown-row:last-child { border-bottom:0; }
    .donut { width:132px; height:132px; border-radius:50%; margin:12px auto 14px; position:relative; }
    .donut:after { content:''; position:absolute; inset:27px; background:#ffcf79; border-radius:50%; }
    .donut-center { position:absolute; z-index:1; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column; color:#29251d; font-size:1.08rem; font-weight:750; }
    .donut-center small { color:#6c593b; font-size:.58rem; font-weight:500; }
    .review-box { border-left:3px solid #edae42; background:#fff8e9; border-radius:0 9px 9px 0; padding:10px 12px; color:#66512d; font-size:.77rem; line-height:1.45; }
    .recommendation-card {
        display:flex; gap:11px; min-height:94px; padding:13px;
        border:1px solid #e9eae9; border-radius:11px; background:#fafaf9;
    }
    .recommendation-number { flex:0 0 28px; width:28px; height:28px; display:grid; place-items:center; background:#ffce73; color:#352710; border-radius:50%; font-size:.7rem; font-weight:800; }
    .recommendation-text { color:#45494b; font-size:.78rem; line-height:1.45; }
    .footer-note { color:#8a8f90; font-size:.67rem; text-align:center; border-top:1px solid #eceeed; margin-top:23px; padding-top:13px; }
    @media (max-width: 760px) {
        [data-testid="stMainBlockContainer"] { padding:1rem .85rem 1.6rem; margin-top:.4rem; }
        .kpi-card { border-right:0; border-bottom:1px solid #ededec; }
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
database_file = DEFAULT_DB_PATH

timezone = "Asia/Kolkata"
period_start = pd.Timestamp("2013-07-13 00:00:00", tz=timezone)
period_end = pd.Timestamp("2013-08-04 23:59:00", tz=timezone)

if not processed_file.exists():
    st.error(f"Processed energy data not found: {processed_file}")
    st.stop()
if not forecast_file.exists():
    st.error(f"Forecast file not found: {forecast_file}")
    st.stop()
if not database_file.exists():
    st.error(
        f"SQL database not found: {database_file}. "
        "From the project root, run `python .\\src\\setup_database.py` to create and populate it."
    )
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
def run_energy_agent(csv_path, file_modified_time, sql_readings):
    """Run the LangGraph workflow using readings loaded from SQL."""
    return energy_agent.invoke(
        {
            "data_path": csv_path,
            "data": sql_readings,
            "metrics": {},
            "recommendations": [],
        }
    )


def build_html_report(metrics, recommendations, forecast_frame, water_profile):
    """Create a self-contained HTML report that can also be printed to PDF."""
    safe_recommendations = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in recommendations
    )
    forecast_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row.timestamp.strftime('%d %b %Y, %H:%M'))}</td>"
        f"<td>{row.forecast_power_W:,.1f} W</td>"
        f"<td>{row.forecast_energy_kWh:.3f} kWh</td>"
        "</tr>"
        for row in forecast_frame.itertuples(index=False)
    )
    water_section = "<p>Water signal profile is not available.</p>"
    if water_profile:
        water_section = (
            "<p><b>Rows profiled:</b> "
            f"{water_profile['row_count']:,} &nbsp; · &nbsp; "
            f"<b>Rows passing checks:</b> {water_profile['valid_row_count']:,} &nbsp; · &nbsp; "
            f"<b>Rows flagged:</b> {water_profile['invalid_row_count']:,}</p>"
            "<p>Water litres are not estimated because the stream requires validated pulse calibration and false-signal handling.</p>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FacilityOps Energy Report</title>
<style>
body{{margin:0;background:#edf3f2;color:#202223;font:15px/1.55 Inter,'Segoe UI',Arial,sans-serif}}
main{{max-width:920px;margin:32px auto;background:#fff;padding:42px 48px;border-radius:18px;box-shadow:0 12px 36px #25494a20}}
.brand{{font-size:12px;letter-spacing:.13em;text-transform:uppercase;color:#777;font-weight:700}}
h1{{font-size:32px;letter-spacing:-.05em;margin:8px 0 2px}} .sub{{color:#777;margin-top:0}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:24px 0}}
.stat{{padding:13px;background:#f3f4f3;border-radius:10px}} .label{{font-size:11px;color:#777;text-transform:uppercase}}
.value{{font-size:23px;font-weight:700;letter-spacing:-.04em}} section{{margin-top:25px}}
h2{{font-size:18px;margin-bottom:7px}} .note{{color:#777;font-size:13px}}
.callout{{background:#fff6e5;border-left:3px solid #ffb83f;padding:12px 15px;border-radius:0 8px 8px 0}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:8px;border-bottom:1px solid #e8e9e8;text-align:left}}th{{background:#f3f4f3}}
button{{background:#ffb83f;border:0;border-radius:20px;padding:9px 15px;font-weight:700;cursor:pointer}}
@media print{{body{{background:#fff}}main{{margin:0 auto;box-shadow:none;padding:20px}}button{{display:none}}}}
</style></head><body><main>
<div class="brand">⚡ FacilityOps · Milestone 1</div><h1>Energy analytics report</h1>
<p class="sub">iAWE New Delhi residential dataset · {html.escape(metrics['period'])} · India time</p>
<button onclick="window.print()">Print / Save as PDF</button>
<div class="stats">
<div class="stat"><div class="label">Mains energy</div><div class="value">{metrics['mains_energy_kwh']:,.2f} kWh</div></div>
<div class="stat"><div class="label">Both ACs</div><div class="value">{metrics['ac_energy_kwh']:,.2f} kWh</div></div>
<div class="stat"><div class="label">AC share</div><div class="value">{metrics['ac_share_percent']:.1f}%</div></div>
<div class="stat"><div class="label">Mains coverage</div><div class="value">{metrics['coverage_percent']:.1f}%</div></div>
</div>
<section><h2>Load and data quality</h2><p>Peak mains power was {metrics['peak_power_w']:,.1f} W at {html.escape(metrics['peak_datetime'])} (India time). {metrics['anomaly_count']:,} minutes ({metrics['anomaly_percent']:.2f}%) had AC power above combined mains power; these are review flags, not confirmed faults.</p>
<div class="callout">Energy values describe this one-home dataset. Recommendations use transparent starter rules and have not been validated against labelled anomalies.</div></section>
<section><h2>Agent recommendations</h2><ul>{safe_recommendations}</ul></section>
<section><h2>Next-day hourly baseline</h2><p class="note">A same-hour historical average for August 5, 2013. This is a baseline forecast, not a validated machine-learning prediction.</p>
<table><thead><tr><th>India time</th><th>Average power</th><th>Hourly energy</th></tr></thead><tbody>{forecast_rows}</tbody></table></section>
<section><h2>Water meter signal quality</h2>{water_section}</section>
<p class="note">Generated from the FacilityOps Milestone 1 prototype. Water record counts are not litres; no per-meter pulse conversion is claimed.</p>
</main></body></html>"""


data = load_energy_data(database_file)
forecast = load_csv(str(forecast_file))
data = (
    data.sort_values("timestamp")
    .set_index("timestamp")
    .reindex(pd.date_range(start=period_start, end=period_end, freq="1min"))
    .rename_axis("timestamp")
    .reset_index()
)
agent_result = run_energy_agent(
    str(processed_file), database_file.stat().st_mtime, data
)
metrics = agent_result["metrics"]
recommendations = agent_result["recommendations"]
water_profile = None
if water_profile_file.exists():
    with water_profile_file.open(encoding="utf-8") as profile_stream:
        water_profile = json.load(profile_stream)

report_html = build_html_report(metrics, recommendations, forecast, water_profile)

brand_col, spacer_col, report_col = st.columns([3, 4, 1.5], vertical_alignment="center")
with brand_col:
    st.markdown(
        '<div class="topbar"><span class="brand-mark">ϟ</span>'
        '<span class="brand-name">FacilityOps</span><span class="brand-divider"></span>'
        '<span class="brand-section">Energy intelligence</span></div>',
        unsafe_allow_html=True,
    )
with report_col:
    st.download_button(
        "Generate report  ↓",
        data=report_html.encode("utf-8"),
        file_name="facilityops_energy_report.html",
        mime="text/html",
        type="primary",
        use_container_width=True,
        help="Download a report of these metrics and the hourly baseline. Open it in a browser to print or save as PDF.",
    )

title_col, period_col = st.columns([3, 1.5], vertical_alignment="bottom")
with title_col:
    st.title("Energy analytics")
    st.markdown(
        '<div class="page-subtitle">Consumption trends, metered HVAC share, and operational data quality.</div>',
        unsafe_allow_html=True,
    )
with period_col:
    st.markdown(
        '<div class="period-chip">▦ &nbsp; 13 Jul — 04 Aug 2013 &nbsp;⌄</div>',
        unsafe_allow_html=True,
    )

energy_tab, water_tab = st.tabs(["Analytics", "Water quality"])

with energy_tab:
    st.markdown('<div class="eyebrow">Period overview</div>', unsafe_allow_html=True)
    kpis = st.columns(5, gap="small")
    kpi_items = [
        ("Total consumption", f"{metrics['mains_energy_kwh']:,.2f}<small> kWh</small>", "Recorded mains energy", "#191a1b"),
        ("AC submeter total", f"{metrics['ac_energy_kwh']:,.2f}<small> kWh</small>", f"{metrics['ac_share_percent']:.1f}% of mains", "#191a1b"),
        ("Peak load", f"{metrics['peak_power_w'] / 1000:.2f}<small> kW</small>", f"{metrics['peak_datetime']} · India", "#191a1b"),
        ("Meter coverage", f"{metrics['coverage_percent']:.1f}<small>%</small>", f"{metrics['missing_minutes']:,} minutes missing", "#191a1b"),
        ("Review flags", f"{metrics['anomaly_count']:,}<small> min</small>", f"{metrics['anomaly_percent']:.2f}% of recorded minutes", "#191a1b"),
    ]
    for column, (label, value, note, accent) in zip(kpis, kpi_items):
        column.markdown(
            f'<div class="kpi-card" style="--kpi-accent:{accent}">'
            f'<div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>'
            f'<div class="kpi-note">{html.escape(note)}</div></div>',
            unsafe_allow_html=True,
        )

    if metrics["anomaly_count"] > 0:
        st.markdown(
            '<div class="review-box" style="margin:10px 0 14px">'
            f'<b>{metrics["anomaly_count"]:,} minutes need a data consistency review.</b> '
            'AC power exceeds combined mains during these readings; this rule flags them for inspection, '
            'not as confirmed faults.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    trend_col, breakdown_col = st.columns([3.2, 1.05], gap="medium")

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
            x=history["timestamp"], y=history["power_W"],
            name="Observed hourly average", mode="lines",
            line={"color": "#85898b", "width": 2.2},
            hovertemplate="%{x|%d %b, %H:%M}<br>%{y:,.0f} W<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=forecast_points["timestamp"], y=forecast_points["power_W"],
            name="Next-day baseline", mode="lines+markers",
            line={"color": "#f5ad38", "width": 2.7},
            marker={"size": 6, "color": "#f5ad38"},
            hovertemplate="%{x|%d %b, %H:%M}<br>%{y:,.0f} W<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white", height=360,
        margin={"l": 10, "r": 10, "t": 35, "b": 8},
        paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="#f1f2f1",
        font={"family": "Inter, Segoe UI, Arial, sans-serif", "color": "#5c6163", "size": 10},
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.12, "x": 0, "font": {"color": "#595e60", "size": 10}, "bgcolor": "rgba(255,255,255,0)"},
        yaxis_title="Average power (W)", xaxis_title=None,
    )
    if not forecast_points.empty:
        figure.add_vline(x=forecast_points["timestamp"].min(), line_width=1, line_dash="dot", line_color="#a9abad")
    figure.update_xaxes(showgrid=False, zeroline=False, tickfont={"color": "#74797b", "size": 9})
    figure.update_yaxes(gridcolor="#dedfdd", zeroline=False, tickfont={"color": "#74797b", "size": 9}, title_font={"color": "#515658", "size": 10})

    with trend_col.container(border=True):
        st.markdown('<div class="section-head">Consumption trends</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-note">Observed hourly power across the analysis window and the following day baseline.</div>', unsafe_allow_html=True)
        st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})

    with breakdown_col.container(border=True):
        other_mains_kwh = max(0.0, metrics["mains_energy_kwh"] - metrics["ac_energy_kwh"])
        st.markdown(
            '<div class="breakdown-panel">'
            '<div class="breakdown-title">Meter breakdown</div>'
            '<div class="breakdown-note">Share of recorded mains energy</div>'
            f'<div class="donut" style="background:conic-gradient(#282b2d 0 {metrics["ac_share_percent"]:.1f}%, #fff0d1 {metrics["ac_share_percent"]:.1f}% 100%)">'
            f'<div class="donut-center">{metrics["ac_share_percent"]:.1f}%<small>AC share</small></div></div>'
            '<div class="breakdown-row"><span>Both AC submeters</span>'
            f'<b>{metrics["ac_energy_kwh"]:,.2f} kWh</b></div>'
            '<div class="breakdown-row"><span>Remaining mains*</span>'
            f'<b>{other_mains_kwh:,.2f} kWh</b></div>'
            '<div class="section-note" style="margin:8px 2px 0">'
            '*Calculated as mains minus the two AC readings.</div></div>',
            unsafe_allow_html=True,
        )

    with st.expander("View all 24 forecast hours"):
        forecast_table = forecast.copy()
        forecast_table["forecast_power_W"] = forecast_table["forecast_power_W"].round(1)
        forecast_table["forecast_energy_kWh"] = forecast_table["forecast_energy_kWh"].round(3)
        st.dataframe(forecast_table, hide_index=True, width="stretch")

    st.markdown('<div class="section-head" style="margin-top:17px">Operational recommendations</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-note">Transparent starter rules · prompts for staff review</div>', unsafe_allow_html=True)
    recommendation_columns = st.columns(min(3, len(recommendations)))
    for index, recommendation in enumerate(recommendations):
        recommendation_columns[index % len(recommendation_columns)].markdown(
            '<div class="recommendation-card">'
            f'<div class="recommendation-number">{index + 1:02d}</div>'
            f'<div class="recommendation-text">{html.escape(str(recommendation))}</div></div>',
            unsafe_allow_html=True,
        )

with water_tab:
    st.markdown('<div class="section-head">Water meter quality</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-note">This view profiles the water stream as a signal feed; it does not convert events to litres.</div>', unsafe_allow_html=True)
    if not water_profile:
        st.info("Water profile not found. Run `python .\\src\\profile_water.py` to create it.")
    else:
        total_rows = water_profile["row_count"]
        valid_rows = water_profile["valid_row_count"]
        pass_rate = valid_rows / total_rows * 100 if total_rows else 0
        water_kpis = st.columns(3)
        water_values = [
            ("Records profiled", f"{total_rows:,}", "Raw meter records"),
            ("Passed format checks", f"{pass_rate:.4f}%", f"{valid_rows:,} records"),
            ("Flagged for review", f"{water_profile['invalid_row_count']:,}", "Timestamp, state, or meter ID"),
        ]
        for column, (label, value, note) in zip(water_kpis, water_values):
            column.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{value}</div><div class="kpi-note">{html.escape(note)}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="review-box" style="margin:12px 0">'
            '<b>Water volume is not estimated.</b> Repeated state records, false pulses, '
            'and uncertain meter calibration make raw record counts unsuitable as litres.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="section-note">Validated timestamp range: '
            f'{html.escape(str(water_profile["timestamp_start_india"]))} to '
            f'{html.escape(str(water_profile["timestamp_end_india"]))} (India time).</div>',
            unsafe_allow_html=True,
        )
        audit_col1, audit_col2 = st.columns([1, 1.5], gap="medium")
        meter_table = pd.DataFrame(
            [{"Meter ID": meter_id, "Records": count} for meter_id, count in water_profile["meter_record_counts"].items()]
        )
        state_table = pd.DataFrame(
            [{"State": f"State {state}", "Records": count} for state, count in water_profile["state_record_counts"].items()]
        )
        with audit_col1.container(border=True):
            st.markdown('<div class="section-head">Records by meter</div>', unsafe_allow_html=True)
            st.dataframe(meter_table, hide_index=True, width="stretch")
        state_figure = go.Figure(
            go.Bar(
                x=state_table["Records"], y=state_table["State"], orientation="h",
                marker_color=["#b9c4c3", "#f2b64d"],
                text=[f"{value:,}" for value in state_table["Records"]], textposition="outside",
                hovertemplate="%{y}<br>%{x:,} records<extra></extra>",
            )
        )
        state_figure.update_layout(
            template="plotly_white", height=220,
            margin={"l": 8, "r": 60, "t": 8, "b": 12},
            paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="#f1f2f1",
            font={"family": "Inter, Segoe UI, Arial, sans-serif", "color": "#52585a", "size": 11},
            xaxis={"showgrid": False, "showticklabels": False, "zeroline": False},
            yaxis={"showgrid": False, "title": None}, showlegend=False,
        )
        with audit_col2.container(border=True):
            st.markdown('<div class="section-head">Reported state records</div>', unsafe_allow_html=True)
            st.plotly_chart(state_figure, width="stretch", config={"displayModeBar": False})
        with st.expander("Example rows flagged for review"):
            st.dataframe(pd.DataFrame(water_profile["invalid_examples"]), hide_index=True, width="stretch")

st.markdown(
    '<div class="footer-note">FACILITYOPS · ENERGY INTELLIGENCE · PROTOTYPE ANALYTICS FOR THE iAWE RESIDENTIAL DATASET</div>',
    unsafe_allow_html=True,
)
