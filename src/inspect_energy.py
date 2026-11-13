from pathlib import Path

import pandas as pd
import plotly.express as px

# Find the project folder, then build the path to the electricity CSV.
project_folder = Path(__file__).resolve().parents[1]
data_file = (
    project_folder
    / "data"
    / "raw"
    / "iawe"
    / "electricity"
    / "1.csv"
)

# Read only 10,000 rows for this first exploration.
data = pd.read_csv(data_file, nrows=10_000)

# Convert Unix seconds to readable India time.
data["datetime"] = pd.to_datetime(
    data["timestamp"], unit="s", utc=True
).dt.tz_convert("Asia/Kolkata")

intervals = data["timestamp"].diff().dropna()

print("\nTime-gap check:")
print("Most common interval (seconds):", intervals.mode().iloc[0])
print("Largest interval (seconds):", intervals.max())
print("Intervals longer than 1 second:", (intervals > 1).sum())

gap_seconds = data["timestamp"].diff()
gap_mask = gap_seconds > 1

gap_report = data.loc[gap_mask, ["datetime"]].copy()
gap_report["previous_datetime"] = data["datetime"].shift(1)[gap_mask]
gap_report["gap_seconds"] = gap_seconds[gap_mask]

print("\nFive largest data gaps:")
print(
    gap_report.nlargest(5, "gap_seconds")[
        ["previous_datetime", "datetime", "gap_seconds"]
    ].to_string(index=False)
)

print("Rows read:", len(data))
print("Time range:", data["datetime"].min(), "to", data["datetime"].max())
print("\nPower, frequency, and voltage summary:")
print(data[["W", "f", "VLN"]].describe().round(2))

# Estimate energy over intervals no longer than 60 seconds.
gaps = data["timestamp"].diff()
valid_intervals = gaps.gt(0) & gaps.le(60)

average_power_w = (data["W"] + data["W"].shift(1)) / 2
energy_kwh = (
    average_power_w[valid_intervals] * gaps[valid_intervals]
).sum() / 3_600_000

total_seconds = gaps.iloc[1:].sum()
covered_seconds = gaps[valid_intervals].sum()
coverage_percent = covered_seconds / total_seconds * 100

print("\nEnergy estimate for these 10,000 rows:")
print(f"Estimated energy: {energy_kwh:.6f} kWh")
print(f"Time coverage: {coverage_percent:.1f}%")

channel_2_file = data_file.with_name("2.csv")
channel_2 = pd.read_csv(channel_2_file, nrows=10_000)

print("\nChannel 2 power summary:")
print(channel_2["W"].describe().round(2))

mains_1 = data[["timestamp", "W"]].rename(columns={"W": "meter_1_W"})
mains_2 = channel_2[["timestamp", "W"]].rename(columns={"W": "meter_2_W"})

# Keep only timestamps where both meters recorded a reading.
combined_mains = mains_1.merge(mains_2, on="timestamp", how="inner")
combined_mains["total_W"] = (
    combined_mains["meter_1_W"] + combined_mains["meter_2_W"]
)

print("\nCombined mains at matching timestamps:")
print("Matching readings:", len(combined_mains))
print(combined_mains["total_W"].describe().round(2))

# Sort by time before calculating intervals.
combined_mains = combined_mains.sort_values("timestamp").reset_index(drop=True)

# Find the seconds between combined readings.
total_gaps = combined_mains["timestamp"].diff()
valid_total_intervals = total_gaps.gt(0) & total_gaps.le(60)

# Estimate energy using the average power at each interval's endpoints.
average_total_power_w = (
    combined_mains["total_W"] + combined_mains["total_W"].shift(1)
) / 2

total_energy_kwh = (
    average_total_power_w[valid_total_intervals]
    * total_gaps[valid_total_intervals]
).sum() / 3_600_000

total_elapsed_seconds = total_gaps.iloc[1:].sum()
total_covered_seconds = total_gaps[valid_total_intervals].sum()
total_coverage = total_covered_seconds / total_elapsed_seconds * 100

print("\nCombined mains energy estimate:")
print(f"Estimated energy: {total_energy_kwh:.4f} kWh")
print(f"Time coverage: {total_coverage:.1f}%")

# Convert timestamps for the chart.
plot_data = combined_mains.copy()
plot_data["datetime"] = pd.to_datetime(
    plot_data["timestamp"], unit="s", utc=True
).dt.tz_convert("Asia/Kolkata")

# Break the line after gaps longer than 60 seconds.
long_gaps = plot_data["timestamp"].diff() > 60
plot_data.loc[long_gaps, "total_W"] = float("nan")

fig = px.line(
    plot_data,
    x="datetime",
    y="total_W",
    title="Combined Mains Power — Sample",
    labels={"datetime": "Time (India)", "total_W": "Power (W)"},
)
fig.update_traces(connectgaps=False)

# Save the interactive chart in the processed-data folder.
chart_file = project_folder / "data" / "processed" / "energy_sample.html"
chart_file.parent.mkdir(parents=True, exist_ok=True)
fig.write_html(str(chart_file))

print(f"\nInteractive chart saved to: {chart_file}")