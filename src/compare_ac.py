from pathlib import Path

import pandas as pd


project_folder = Path(__file__).resolve().parents[1]
electricity_folder = (
    project_folder / "data" / "raw" / "iawe" / "electricity"
)

# Use the dataset creator's recommended period, in India time.
start_time = pd.Timestamp("2013-07-13 00:00:00", tz="Asia/Kolkata")
end_time = pd.Timestamp("2013-08-04 23:59:59", tz="Asia/Kolkata")

start_timestamp = int(start_time.timestamp())
end_timestamp = int(end_time.timestamp())


def read_window(file_name):
    """Read timestamp and power values in the selected date range."""
    matching_parts = []
    file_path = electricity_folder / file_name

    # Read each large CSV in chunks to limit memory use.
    for chunk in pd.read_csv(
        file_path,
        usecols=["timestamp", "W"],
        chunksize=200_000,
    ):
        in_window = chunk["timestamp"].between(
            start_timestamp, end_timestamp
        )

        if in_window.any():
            part = chunk.loc[in_window].copy()

            # Convert text-like numbers to numeric values.
            part["W"] = pd.to_numeric(part["W"], errors="coerce")
            part = part.dropna(subset=["W"])
            matching_parts.append(part)

    if not matching_parts:
        return pd.DataFrame(columns=["timestamp", "W"])

    return pd.concat(matching_parts, ignore_index=True)


def minute_average(frame, power_column, output_name):
    """Average a channel's power readings for each minute."""
    minute_index = pd.to_datetime(
        frame["timestamp"], unit="s", utc=True
    ).dt.floor("min")

    readings = pd.Series(
        frame[power_column].to_numpy(),
        index=minute_index,
        name=output_name,
    )

    return readings.groupby(level=0).mean()


# Channels 1 and 2 are the two mains meters.
meter_1 = read_window("1.csv").rename(
    columns={"W": "meter_1_W"}
)
meter_2 = read_window("2.csv").rename(
    columns={"W": "meter_2_W"}
)

# Channels 4 and 5 are the two air conditioners.
air_conditioner_1 = read_window("4.csv").rename(
    columns={"W": "ac_1_W"}
)
air_conditioner_2 = read_window("5.csv").rename(
    columns={"W": "ac_2_W"}
)

print("Rows in the selected date range:")
print("Meter 1:", len(meter_1))
print("Meter 2:", len(meter_2))
print("Air conditioner 1:", len(air_conditioner_1))
print("Air conditioner 2:", len(air_conditioner_2))

if meter_1.empty or meter_2.empty:
    raise SystemExit("One or both mains channels have no readings.")

# Average each channel by minute, then align channels by minute.
meter_1_minutes = minute_average(meter_1, "meter_1_W", "meter_1_W")
meter_2_minutes = minute_average(meter_2, "meter_2_W", "meter_2_W")
ac_1_minutes = minute_average(
    air_conditioner_1, "ac_1_W", "ac_1_W"
)
ac_2_minutes = minute_average(
    air_conditioner_2, "ac_2_W", "ac_2_W"
)

minute_data = pd.concat(
    [
        meter_1_minutes,
        meter_2_minutes,
        ac_1_minutes,
        ac_2_minutes,
    ],
    axis=1,
).sort_index()

# The AC plug records readings while its appliance is on.
# Here, a missing AC reading is treated as that unit being off.
minute_data[["ac_1_W", "ac_2_W"]] = minute_data[
    ["ac_1_W", "ac_2_W"]
].fillna(0)

# Keep only minutes when both mains meters have readings.
minute_data = minute_data.dropna(
    subset=["meter_1_W", "meter_2_W"]
).copy()

# Combine the two mains meters and the two AC units.
minute_data["total_mains_W"] = (
    minute_data["meter_1_W"] + minute_data["meter_2_W"]
)
minute_data["total_ac_W"] = (
    minute_data["ac_1_W"] + minute_data["ac_2_W"]
)

# Display timestamps in India time.
minute_data.index = minute_data.index.tz_convert("Asia/Kolkata")

# Count every minute in the selected, inclusive date range.
expected_minutes = int(
    (
        end_time.floor("min") - start_time.floor("min")
    ).total_seconds()
    / 60
) + 1

coverage_percent = len(minute_data) / expected_minutes * 100

# Each row is average power for one minute; W / 60,000 gives kWh.
mains_energy_kwh = minute_data["total_mains_W"].sum() / 60_000
ac_energy_kwh = minute_data["total_ac_W"].sum() / 60_000

if mains_energy_kwh > 0:
    ac_share_percent = ac_energy_kwh / mains_energy_kwh * 100
else:
    ac_share_percent = 0.0

anomaly_count = int(
    (minute_data["total_ac_W"] > minute_data["total_mains_W"]).sum()
)
anomalies = minute_data.loc[
    minute_data["total_ac_W"] > minute_data["total_mains_W"],
    ["total_mains_W", "total_ac_W"],
].copy()

anomalies["excess_W"] = (
    anomalies["total_ac_W"] - anomalies["total_mains_W"]
)

print("\nFirst 10 minutes where AC exceeds mains:")
print(anomalies.head(10).round(1).to_string())

print("\nOne-minute analysis:")
print("Minutes with both mains readings:", len(minute_data))
print("Expected minutes:", expected_minutes)
print(f"Mains data coverage: {coverage_percent:.1f}%")
print(
    "Minutes where both ACs exceed combined mains:",
    anomaly_count,
)

print("\nFirst five minute readings:")
print(
    minute_data[
        [
            "meter_1_W",
            "meter_2_W",
            "total_mains_W",
            "ac_1_W",
            "ac_2_W",
            "total_ac_W",
        ]
    ].head(5).round(2).to_string()
)

print("\nEnergy estimates for recorded minutes:")
print(f"Mains energy: {mains_energy_kwh:.2f} kWh")
print(f"Both ACs' energy: {ac_energy_kwh:.2f} kWh")
print(f"AC share of recorded mains energy: {ac_share_percent:.1f}%")

# Save a separate multi-day file for forecasting.
processed_file = (
    project_folder
    / "data"
    / "processed"
    / "energy_2013-07-13_to_2013-08-04_1min.csv"
)
processed_file.parent.mkdir(parents=True, exist_ok=True)
minute_data.to_csv(processed_file, index_label="timestamp")

print(f"\nProcessed data saved to: {processed_file}")