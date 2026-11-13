from pathlib import Path

import pandas as pd


project_folder = Path(__file__).resolve().parents[1]
data_file = project_folder / "data" / "raw" / "iawe" / "water_meter.csv"
sample_rows = 10_000

# The source SQL schema names these fields meter_id, timestamp, and state.
# Keep the source row order and strings until each field has been checked.
raw = pd.read_csv(
    data_file,
    header=None,
    names=["meter_id", "timestamp_raw", "state_raw"],
    nrows=sample_rows,
    dtype=str,
)

timestamps = pd.to_numeric(raw["timestamp_raw"], errors="coerce")
states = pd.to_numeric(raw["state_raw"], errors="coerce")

# The published data is from 2013. Unix timestamps should therefore be in
# a plausible epoch range; this also catches the differently shaped leading
# records seen in the raw file without reinterpreting their fields.
valid_timestamp = timestamps.between(1_350_000_000, 1_400_000_000)
valid_state = states.isin([0, 1])
valid_meter = raw["meter_id"].isin(["1", "2"])
valid_format = valid_timestamp & valid_state & valid_meter
valid_rows = raw.loc[valid_format].copy()
valid_rows["timestamp_seconds"] = timestamps.loc[valid_rows.index]
valid_rows["state"] = states.loc[valid_rows.index].astype("int8")
valid_rows["timestamp"] = pd.to_datetime(
    valid_rows["timestamp_seconds"], unit="s", utc=True
).dt.tz_convert("Asia/Kolkata")

# Repeated state=1 records may reflect repeated polling of the same unresolved
# meter interval. They cannot safely be counted as separate volume pulses.
ordered = valid_rows.sort_values(["meter_id", "timestamp_seconds"]).copy()
state_change = ordered.groupby("meter_id")["state"].diff().fillna(0).ne(0)

print("Rows sampled:", len(raw))
print("Rows with a plausible Unix timestamp and state 0/1:", len(valid_rows))
print("Rows needing format review:", int((~valid_format).sum()))
print("Meter IDs in valid rows:")
print(valid_rows["meter_id"].value_counts().sort_index().to_string())

print("\nState counts in valid rows (not pulse or volume counts):")
print(valid_rows["state"].value_counts().sort_index().to_string())
print("State transitions in sample:", int(state_change.sum()))

if not valid_rows.empty:
    print("\nTimestamp range:")
    print(valid_rows["timestamp"].min(), "to", valid_rows["timestamp"].max())

if (~valid_format).any():
    print("\nFirst rows needing format review:")
    print(
        raw.loc[~valid_format]
        .head(10)
        .to_string(index=False)
    )

print("\nInterpretation: this report does not estimate litres or water volume.")
