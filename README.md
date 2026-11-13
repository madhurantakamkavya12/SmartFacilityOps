# Agentic FacilityOps AI Platform

A prototype for facility operations analytics, based on the project brief in
`Agentic AI for Smart Facility Operations and Optimization.pdf`.

## Current implementation

The repository has an Energy Intelligence prototype:

- `src/compare_ac.py` aligns iAWE mains and air-conditioner readings into
  one-minute records for July 13 through August 4, 2013.
- `src/forecast_energy.py` evaluates an hourly same-time-of-day baseline on
  the final day, then creates a 24-hour forecast for the next day.
- `src/energy_agent.py` calculates energy, coverage, and consistency metrics,
  then produces transparent rule-based recommendations with LangGraph.
- `src/dashboard.py` presents the energy metrics, recommendations, historical
  profile, and forecast in Streamlit.

The current energy-agent run reports 360.46 kWh recorded mains energy, 121.52
kWh for both ACs, 97.9% mains-minute coverage, and 212 minutes where AC power
exceeds combined mains power. These are descriptive results from this dataset;
the recommendations are rule-based and have not been validated against labeled
anomaly data.

The iAWE files describe one New Delhi home. Treat this as a facility-operations
prototype, not evidence of performance in a commercial building.

## Run the energy prototype

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe .\src\compare_ac.py
.\.venv\Scripts\python.exe .\src\forecast_energy.py
.\.venv\Scripts\streamlit.exe run .\src\dashboard.py
```

The first command rebuilds the processed energy CSV used by the agent and
dashboard. Raw dataset files under `data\raw` should remain unchanged.

## Water data status

`water_meter.csv` is a three-field stream (`meter_id`, timestamp, state) with
some malformed rows, high-frequency state records, and one unexpected meter
ID in the full scan. The iAWE documentation
warns about false positives and repeated readings; the available files do not
establish a reliable per-meter litres-per-pulse conversion for this project.
For that reason, `src/inspect_water.py` reports data quality and state values
without converting them into water volume. Do not present state-record counts
as litres.

Use `src/inspect_water.py` for a quick 10,000-row sample or
`src/profile_water.py` for a chunked profile of the full raw file:

```powershell
.\.venv\Scripts\python.exe .\src\inspect_water.py
.\.venv\Scripts\python.exe .\src\profile_water.py
```

The full scan saves `data/processed/water_signal_profile.json`, which the
Streamlit dashboard displays under **Water Meter Signal Quality**. The profile
contains validation counts and examples of flagged rows; it does not estimate
water volume.

## Current scope: Milestone 1

| Requirement | Current status |
| --- | --- |
| Integrate utility and IoT data | Electricity data is processed; water data is profiled as a signal feed. |
| Build the Energy Agent | LangGraph metrics and rule-based recommendations are implemented. |
| Energy consumption analytics | Period totals, AC share, data coverage, anomalies, and an hourly baseline forecast are available. |
| Energy monitoring dashboard | Streamlit dashboard shows energy KPIs, recommendations, and forecast. |
| Water monitoring | Dashboard shows water meter signal quality; no litres are inferred. |
| Anomaly detection accuracy of at least 85% | Not measurable yet: there are no labeled anomaly examples. Current flags are heuristics, not validated model accuracy. |

Work on later milestones is outside the current scope. The iAWE data represents
one residence, so results should be presented as a prototype rather than
commercial facility performance.
