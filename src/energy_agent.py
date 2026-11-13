from pathlib import Path
from typing import TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph


project_folder = Path(__file__).resolve().parents[1]
data_file = (
    project_folder
    / "data"
    / "processed"
    / "energy_2013-07-13_to_2013-08-04_1min.csv"
)

timezone = "Asia/Kolkata"
start_date = pd.Timestamp("2013-07-13")
end_date = pd.Timestamp("2013-08-04")
expected_minutes = ((end_date - start_date).days + 1) * 24 * 60


class EnergyAgentState(TypedDict):
    data_path: str
    data: pd.DataFrame | None
    metrics: dict[str, float | int | str]
    recommendations: list[str]


def analyze_energy(state: EnergyAgentState) -> dict:
    """Calculate energy and data-quality metrics for the full period."""
    data = state.get("data")
    if data is None:
        csv_path = Path(state["data_path"])
        if not csv_path.exists():
            raise FileNotFoundError(f"Data file not found: {csv_path}")
        data = pd.read_csv(csv_path)
    else:
        data = data.copy()

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
        raise ValueError(f"CSV is missing columns: {missing_columns}")

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
    """Create transparent recommendations from the calculated metrics."""
    metrics = state["metrics"]
    recommendations = []

    # This is a starter threshold for this prototype, not a universal rule.
    if metrics["ac_share_percent"] >= 30:
        recommendations.append(
            f"ACs account for {metrics['ac_share_percent']}% of "
            "recorded energy. Compare AC run times with occupancy and "
            "room temperatures before changing schedules or setpoints."
        )

    if metrics["coverage_percent"] < 95:
        recommendations.append(
            f"{metrics['missing_minutes']} minutes have no readings "
            "from both mains meters. Check sensor and data collection "
            "availability before treating the period total as complete."
        )

    if metrics["anomaly_count"] > 0:
        recommendations.append(
            f"{metrics['anomaly_count']} minutes "
            f"({metrics['anomaly_percent']}%) have AC power above "
            "combined mains power. Review those readings before using "
            "them for automated decisions."
        )

    if metrics["peak_power_w"] > 2 * metrics["median_power_w"]:
        recommendations.append(
            f"Mains power peaked at {metrics['peak_power_w']} W on "
            f"{metrics['peak_datetime']}. Review which loads were "
            "running then; a peak alone does not prove energy was wasted."
        )

    if not recommendations:
        recommendations.append(
            "No rule-based recommendations were triggered for this period."
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
    result = energy_agent.invoke(
        {
            "data_path": str(data_file),
            "data": None,
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
