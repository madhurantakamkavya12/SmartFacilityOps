from typing import TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from database import DEFAULT_DB_PATH, load_energy_data

timezone = "Asia/Kolkata"
start_date = pd.Timestamp("2013-07-13")
end_date = pd.Timestamp("2013-08-04")
expected_minutes = ((end_date - start_date).days + 1) * 24 * 60


class EnergyAgentState(TypedDict):
    data: pd.DataFrame
    metrics: dict[str, float | int | str]
    recommendations: list[dict[str, str]]


def analyze_energy(state: EnergyAgentState) -> dict:
    """Calculate metrics from readings provided by the SQL data-access layer."""
    data = state["data"].copy()
    if data.empty:
        raise ValueError("No energy readings were supplied to the Energy Agent.")

    required_columns = [
        "timestamp",
        "total_mains_W",
        "total_ac_W",
    ]
    missing_columns = [
        column for column in required_columns
        if column not in data.columns
    ]
    if missing_columns:
        raise ValueError(f"SQL readings are missing required columns: {missing_columns}")

    data["timestamp"] = pd.to_datetime(
        data["timestamp"], utc=True
    ).dt.tz_convert(timezone)

    recorded_mains = data.dropna(subset=["total_mains_W"])

    # Each row is one minute. Divide watt-minutes by 60,000 for kWh.
    mains_energy_kwh = recorded_mains["total_mains_W"].sum() / 60_000
    ac_energy_kwh = recorded_mains["total_ac_W"].sum() / 60_000

    if mains_energy_kwh > 0:
        ac_share_percent = ac_energy_kwh / mains_energy_kwh * 100
    else:
        ac_share_percent = 0.0

    coverage_percent = len(recorded_mains) / expected_minutes * 100
    missing_minutes = max(0, expected_minutes - len(recorded_mains))

    anomaly_count = int(
        (
            recorded_mains["total_ac_W"]
            > recorded_mains["total_mains_W"]
        ).sum()
    )
    anomaly_percent = (
        anomaly_count / len(recorded_mains) * 100
        if len(recorded_mains) > 0
        else 0.0
    )

    peak_index = recorded_mains["total_mains_W"].idxmax()
    peak_row = recorded_mains.loc[peak_index]

    metrics = {
        "period": "July 13–August 4, 2013",
        "mains_energy_kwh": round(float(mains_energy_kwh), 2),
        "ac_energy_kwh": round(float(ac_energy_kwh), 2),
        "ac_share_percent": round(float(ac_share_percent), 1),
        "coverage_percent": round(float(coverage_percent), 1),
        "missing_minutes": int(missing_minutes),
        "anomaly_count": anomaly_count,
        "anomaly_percent": round(float(anomaly_percent), 2),
        "peak_power_w": round(float(peak_row["total_mains_W"]), 1),
        "peak_datetime": peak_row["timestamp"].strftime(
            "%Y-%m-%d %H:%M"
        ),
        "median_power_w": round(
            float(recorded_mains["total_mains_W"].median()), 1
        ),
    }

    return {"metrics": metrics}


def recommend_actions(state: EnergyAgentState) -> dict:
    """Create structured, evidence-based recommendations from calculated metrics."""
    metrics = state["metrics"]
    recommendations = []

    # This is a starter threshold for this prototype, not a universal rule.
    if metrics["ac_share_percent"] >= 30:
        recommendations.append(
            {
                "issue": "High AC share of recorded electricity",
                "reason": "The two AC submeters account for a large share of measured mains energy.",
                "evidence": f"{metrics['ac_energy_kwh']:.2f} kWh · {metrics['ac_share_percent']:.1f}% of recorded mains energy",
                "action": "Compare AC run times with occupancy and room temperatures before changing schedules or setpoints.",
                "priority": "Medium",
            }
        )

    if metrics["coverage_percent"] < 95:
        recommendations.append(
            {
                "issue": "Incomplete mains-meter coverage",
                "reason": "Some expected one-minute slots lack readings from both mains meters.",
                "evidence": f"{metrics['missing_minutes']:,} missing minutes · {metrics['coverage_percent']:.1f}% coverage",
                "action": "Check meter connectivity and collection gaps before relying on the period total.",
                "priority": "High",
            }
        )

    if metrics["anomaly_count"] > 0:
        recommendations.append(
            {
                "issue": "AC reading exceeds combined mains",
                "reason": "The AC submeters report more power than the two mains meters for these minutes.",
                "evidence": f"{metrics['anomaly_count']:,} minutes · {metrics['anomaly_percent']:.2f}% of recorded mains minutes",
                "action": "Review timestamp alignment, meter mapping, and submeter readings before using these records for decisions.",
                "priority": "Review",
            }
        )

    if metrics["peak_power_w"] > 2 * metrics["median_power_w"]:
        recommendations.append(
            {
                "issue": "High observed mains peak",
                "reason": "The peak is more than twice the period median; a peak alone does not prove waste.",
                "evidence": f"{metrics['peak_power_w']:,.1f} W at {metrics['peak_datetime']} · median {metrics['median_power_w']:,.1f} W",
                "action": "Inspect the operating schedule and loads around the peak before considering changes.",
                "priority": "Medium",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "issue": "No review rules were triggered",
                "reason": "The measured metrics did not cross the current starter thresholds.",
                "evidence": f"{metrics['coverage_percent']:.1f}% mains coverage; {metrics['anomaly_count']} consistency flags",
                "action": "Continue monitoring and validate thresholds against labeled facility data.",
                "priority": "Info",
            }
        )

    return {"recommendations": recommendations}


# LangGraph runs analysis first, then produces recommendations.
builder = StateGraph(EnergyAgentState)
builder.add_node("analyze_energy", analyze_energy)
builder.add_node("recommend_actions", recommend_actions)

builder.add_edge(START, "analyze_energy")
builder.add_edge("analyze_energy", "recommend_actions")
builder.add_edge("recommend_actions", END)

energy_agent = builder.compile()


if __name__ == "__main__":
    if not DEFAULT_DB_PATH.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {DEFAULT_DB_PATH}. Run src/setup_database.py first."
        )
    sql_readings = load_energy_data(DEFAULT_DB_PATH)
    result = energy_agent.invoke(
        {
            "data": sql_readings,
            "metrics": {},
            "recommendations": [],
        }
    )

    metrics = result["metrics"]

    print(f"\nEnergy Agent Report — {metrics['period']}")
    print(f"Mains energy: {metrics['mains_energy_kwh']} kWh")
    print(f"Both ACs: {metrics['ac_energy_kwh']} kWh")
    print(f"AC share: {metrics['ac_share_percent']}%")
    print(f"Mains data coverage: {metrics['coverage_percent']}%")
    print(
        f"Peak mains power: {metrics['peak_power_w']} W "
        f"at {metrics['peak_datetime']}"
    )

    print("\nRecommendations:")
    for number, recommendation in enumerate(
        result["recommendations"], start=1
    ):
        print(f"{number}. {recommendation}")
