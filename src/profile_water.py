from collections import Counter
import json
from pathlib import Path

import pandas as pd


project_folder = Path(__file__).resolve().parents[1]
data_file = project_folder / "data" / "raw" / "iawe" / "water_meter.csv"
chunk_size = 250_000
minimum_timestamp = 1_350_000_000
maximum_timestamp = 1_400_000_000
known_meter_ids = {"1", "2"}

row_count = 0
valid_count = 0
invalid_count = 0
meter_counts = Counter()
state_counts = Counter()
invalid_examples = []
minimum_seen = None
maximum_seen = None

for chunk in pd.read_csv(
    data_file,
    header=None,
    names=["meter_id", "timestamp_raw", "state_raw"],
    dtype=str,
    chunksize=chunk_size,
):
    row_count += len(chunk)
    timestamps = pd.to_numeric(chunk["timestamp_raw"], errors="coerce")
    states = pd.to_numeric(chunk["state_raw"], errors="coerce")
    plausible_timestamp = timestamps.between(
        minimum_timestamp, maximum_timestamp
    )
    binary_state = states.isin([0, 1])
    known_meter = chunk["meter_id"].isin(known_meter_ids)
    valid = plausible_timestamp & binary_state & known_meter

    valid_count += int(valid.sum())
    invalid_count += int((~valid).sum())
    meter_counts.update(chunk.loc[valid, "meter_id"].value_counts().to_dict())
    state_counts.update(states.loc[valid].value_counts().to_dict())

    if valid.any():
        chunk_min = float(timestamps.loc[valid].min())
        chunk_max = float(timestamps.loc[valid].max())
        minimum_seen = (
            chunk_min if minimum_seen is None else min(minimum_seen, chunk_min)
        )
        maximum_seen = (
            chunk_max if maximum_seen is None else max(maximum_seen, chunk_max)
        )

    if len(invalid_examples) < 10:
        invalid_examples.extend(
            chunk.loc[~valid].head(10 - len(invalid_examples)).to_dict("records")
        )

    if row_count % 5_000_000 < len(chunk):
        print(f"Scanned {row_count:,} rows", flush=True)

start = None
end = None
if minimum_seen is not None:
    start = pd.to_datetime(minimum_seen, unit="s", utc=True).tz_convert("Asia/Kolkata")
    end = pd.to_datetime(maximum_seen, unit="s", utc=True).tz_convert("Asia/Kolkata")

profile = {
    "source_file": "data/raw/iawe/water_meter.csv",
    "row_count": row_count,
    "valid_row_count": valid_count,
    "invalid_row_count": invalid_count,
    "timestamp_filter_seconds": {
        "minimum": minimum_timestamp,
        "maximum": maximum_timestamp,
    },
    "timestamp_start_india": start.isoformat() if start is not None else None,
    "timestamp_end_india": end.isoformat() if end is not None else None,
    "meter_record_counts": {
        str(key): int(value) for key, value in sorted(meter_counts.items())
    },
    "state_record_counts": {
        str(int(key)): int(value) for key, value in sorted(state_counts.items())
    },
    "known_meter_ids": sorted(known_meter_ids),
    "invalid_examples": invalid_examples,
    "volume_estimate_available": False,
}

processed_folder = project_folder / "data" / "processed"
processed_folder.mkdir(parents=True, exist_ok=True)
profile_file = processed_folder / "water_signal_profile.json"
profile_file.write_text(json.dumps(profile, indent=2), encoding="utf-8")

print("\nWater-meter data profile")
print("Rows:", f"{row_count:,}")
print("Rows passing timestamp, state, and meter-ID checks:", f"{valid_count:,}")
print("Rows needing review:", f"{invalid_count:,}")
print("Rows by meter ID:", dict(sorted(meter_counts.items())))
print(
    "State values (record counts, not water volume):",
    {int(key): value for key, value in sorted(state_counts.items())},
)
if start is not None and end is not None:
    print("Timestamp range:", start, "to", end)

if invalid_examples:
    print("\nFirst rows needing review:")
    print(pd.DataFrame(invalid_examples).to_string(index=False))

print("\nThese checks do not estimate litres or water volume.")
print("Profile saved to:", profile_file)
