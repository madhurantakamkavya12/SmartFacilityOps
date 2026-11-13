# Agentic FacilityOps AI Platform

A prototype for facility operations analytics, based on the project brief in
`Agentic AI for Smart Facility Operations and Optimization.pdf`.

## Current implementation

The repository has an Energy Intelligence prototype backed by a local SQL database:

- `src/compare_ac.py` aligns iAWE mains and air-conditioner readings into
  one-minute records for July 13 through August 4, 2013.
- `src/forecast_energy.py` evaluates an hourly same-time-of-day baseline on
  the final day, then creates a 24-hour forecast for the next day.
- `src/energy_agent.py` calculates energy, coverage, and consistency metrics,
  then produces structured, evidence-backed rule-based recommendations with
  LangGraph. It accepts the DataFrame supplied by the SQL layer and contains no
  CSV loading fallback.
- `sql/schema.sql` defines the eight relational entities in the supplied ERD.
- `src/setup_database.py` creates a local SQLite database and imports the
  processed electricity channels and rule-based review alerts.
- `src/database.py` is the SQL data-access layer. It loads the channel totals and
  stored alerts in one connection and supplies the readings to both dashboard
  views and the Energy Agent.
- `src/dashboard.py` presents the SQL-backed metrics, alert records,
  recommendations, historical profile, and forecast in Streamlit.
- `src/reporting.py` builds the downloadable HTML report from current metrics,
  alerts, recommendations, forecast, and water quality profile.

SQLite is used for this local prototype because it is a relational SQL database
and needs no separate server. The supplied ERD is the model: Milestone 1 loads
`facilities`, `assets`, `energy_usage`, and `alerts`. Occupancy, maintenance,
security, and cost tables are created but remain empty until corresponding
observations are available. `energy_usage` adds an asset reference and a unit
field so each meter channel and its watt reading can be identified. The database
file is generated locally and excluded from Git; the schema and loader are
committed instead.

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
.\.venv\Scripts\python.exe .\src\setup_database.py
.\.venv\Scripts\streamlit.exe run .\src\dashboard.py
```

The first command rebuilds the processed energy CSV. The database setup command
imports its four electricity channels into `data\processed\facilityops.db`;
the dashboard and Energy Agent receive their energy readings from this SQL
database. The 24-hour forecast remains a processed CSV output, with the
chronological holdout evaluation stored as JSON. Raw dataset files under
`data\raw` should remain unchanged.

Run the automated Milestone 1 checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

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
Streamlit dashboard displays under **Water quality**. The profile contains
validation counts and examples of flagged rows; it does not estimate water
volume. Water-meter assets are registered in SQL, but no litres are inserted
into `water_usage` without a validated calibration.

## Current scope: Milestone 1

| Requirement | Current status |
| --- | --- |
| Integrate utility and IoT data | Electricity channels and rule-review alerts are stored in SQLite; water is profiled as a signal feed. |
| Build the Energy Agent | LangGraph calculates metrics from the SQL data-access DataFrame and returns structured, rule-based recommendations. |
| Energy consumption analytics | Period totals, AC share, data coverage, anomalies, and an hourly baseline forecast are available. |
| Energy monitoring dashboard | Streamlit dashboard shows energy KPIs, recommendations, and forecast. |
| Water monitoring | Dashboard shows water meter signal quality; no litres are inferred. |
| Anomaly detection accuracy of at least 85% | Not measurable yet: there are no labeled anomaly examples. Current flags are heuristics, not validated model accuracy. |

The implemented alert is a consistency heuristic: combined AC-submeter power
exceeds combined mains power in a one-minute interval. Synthetic tests check
that the rule and alert storage behave as expected; those tests are not an
estimate of real-world anomaly accuracy. The forecast evaluation uses a
chronological final-day holdout and reports MAE and RMSE separately.

Work on later milestones is outside the current scope. The iAWE data represents
one residence, so results should be presented as a prototype rather than
commercial facility performance. Do not populate the other ERD areas with
invented occupancy, maintenance, security, or cost records.
