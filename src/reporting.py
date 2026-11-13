"""HTML report generation for the Milestone 1 dashboard."""

import html

import pandas as pd


def build_html_report(
    metrics: dict,
    recommendations: list[dict[str, str]],
    forecast_frame: pd.DataFrame,
    water_profile: dict | None,
    alerts: pd.DataFrame | None = None,
    forecast_evaluation: dict | None = None,
    source_record_count: int | None = None,
) -> str:
    """Build a self-contained report from current SQL-backed results."""
    recommendation_items = []
    for item in recommendations:
        if isinstance(item, dict):
            recommendation_items.append(
                "<article class='recommendation'>"
                f"<div class='priority'>{html.escape(str(item.get('priority', 'Review')))} priority</div>"
                f"<h3>{html.escape(str(item.get('issue', 'Recommendation')))}</h3>"
                f"<p>{html.escape(str(item.get('reason', '')))}</p>"
                f"<p><b>Evidence:</b> {html.escape(str(item.get('evidence', '')))}</p>"
                f"<p><b>Suggested action:</b> {html.escape(str(item.get('action', '')))}</p>"
                "</article>"
            )
        else:
            recommendation_items.append(
                f"<li>{html.escape(str(item))}</li>"
            )
    recommendations_html = "".join(recommendation_items) or "<p>No recommendations are available.</p>"

    forecast_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row.timestamp.strftime('%d %b %Y, %H:%M'))}</td>"
        f"<td>{row.forecast_power_W:,.1f} W</td>"
        f"<td>{row.forecast_energy_kWh:.3f} kWh</td>"
        "</tr>"
        for row in forecast_frame.itertuples(index=False)
    )
    if not forecast_rows:
        forecast_rows = "<tr><td colspan='3'>No forecast hours are available.</td></tr>"

    alert_total = len(alerts) if alerts is not None else metrics.get("anomaly_count", 0)
    alert_rows = ""
    if alerts is not None and not alerts.empty:
        for row in alerts.head(10).itertuples(index=False):
            alert_rows += (
                "<tr>"
                f"<td>{html.escape(str(row.created_at))}</td>"
                f"<td>{html.escape(str(row.severity))}</td>"
                f"<td>{html.escape(str(row.details))}</td>"
                "</tr>"
            )
    if not alert_rows:
        alert_rows = "<tr><td colspan='3'>No stored review alerts.</td></tr>"

    water_section = "<p>Water signal profile is not available.</p>"
    if water_profile:
        water_section = (
            "<p><b>Rows profiled:</b> "
            f"{water_profile['row_count']:,} &nbsp; · &nbsp; "
            f"<b>Rows passing checks:</b> {water_profile['valid_row_count']:,} &nbsp; · &nbsp; "
            f"<b>Rows flagged:</b> {water_profile['invalid_row_count']:,}</p>"
            "<p>Water litres are not estimated because the stream requires validated pulse calibration and false-signal handling.</p>"
        )

    if forecast_evaluation:
        evaluation_section = (
            f"<p>Chronological holdout: {html.escape(str(forecast_evaluation.get('holdout_date', '')))}; "
            f"{int(forecast_evaluation.get('hours_evaluated', 0))} valid hours. "
            f"MAE {float(forecast_evaluation.get('mae_kW', float('nan'))):.3f} kW; "
            f"RMSE {float(forecast_evaluation.get('rmse_kW', float('nan'))):.3f} kW.</p>"
        )
    else:
        evaluation_section = "<p>Forecast holdout evaluation is not available.</p>"

    source_count_line = (
        f"SQLite source rows: {source_record_count:,}. "
        if source_record_count is not None
        else ""
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
h2{{font-size:18px;margin-bottom:7px}} h3{{font-size:15px;margin:3px 0}} .note{{color:#777;font-size:13px}}
.callout{{background:#fff6e5;border-left:3px solid #ffb83f;padding:12px 15px;border-radius:0 8px 8px 0}}
.recommendation{{border:1px solid #e8e9e8;border-radius:9px;padding:10px 14px;margin:8px 0}}
.priority{{font-size:11px;color:#795514;text-transform:uppercase;font-weight:700}}
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
<section><h2>Load and data quality</h2><p>{source_count_line}Peak mains power was {metrics['peak_power_w']:,.1f} W at {html.escape(metrics['peak_datetime'])} (India time). {metrics['anomaly_count']:,} minutes ({metrics['anomaly_percent']:.2f}%) had AC power above combined mains power; these are rule-based review flags, not confirmed faults.</p>
<div class="callout">No labelled anomaly examples are available, so anomaly accuracy cannot be calculated. Do not interpret the number of rule flags as model accuracy or proven energy savings.</div></section>
<section><h2>Stored review alerts ({alert_total:,})</h2><table><thead><tr><th>Time</th><th>Severity</th><th>Explanation</th></tr></thead><tbody>{alert_rows}</tbody></table></section>
<section><h2>Agent recommendations</h2>{recommendations_html}</section>
<section><h2>Next-day hourly baseline</h2><p class="note">A same-hour historical average for August 5, 2013. This is a baseline forecast, not a trained machine-learning model.</p>
{evaluation_section}<table><thead><tr><th>India time</th><th>Average power</th><th>Hourly energy</th></tr></thead><tbody>{forecast_rows}</tbody></table></section>
<section><h2>Water meter signal quality</h2>{water_section}</section>
<p class="note">Generated from current SQL-backed Energy Agent results. Water record counts are not litres; no per-meter pulse conversion is claimed.</p>
</main></body></html>"""
