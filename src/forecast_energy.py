import json
from pathlib import Path

import pandas as pd


project_folder = Path(__file__).resolve().parents[1]
data_file = (
    project_folder
    / "data"
    / "processed"
    / "energy_2013-07-13_to_2013-08-04_1min.csv"
)

timezone = "Asia/Kolkata"

# The date range used to create the processed file.
start_time = pd.Timestamp("2013-07-13 00:00:00", tz=timezone)
end_time = pd.Timestamp("2013-08-04 23:59:00", tz=timezone)

if not data_file.exists():
    raise FileNotFoundError(f"Processed data not found: {data_file}")

data = pd.read_csv(data_file)
data["timestamp"] = pd.to_datetime(
    data["timestamp"], utc=True
).dt.tz_convert(timezone)

# Rebuild the full minute timeline. Missing mains readings stay NaN;
# we do not pretend that missing measurements mean zero consumption.
data = data.sort_values("timestamp").set_index("timestamp")
full_minutes = pd.date_range(
    start=start_time,
    end=end_time,
    freq="1min",
)
data = data.reindex(full_minutes)
data.index.name = "timestamp"

# Convert one-minute readings into hourly average power and coverage.
hourly = pd.DataFrame(
    {
        "actual_W": data["total_mains_W"].resample("1h").mean(),
        "coverage": data["total_mains_W"].resample("1h").count() / 60,
    }
)

# Use only hours with at least 80% of their minute readings.
minimum_coverage = 0.80
hourly["hour_of_day"] = hourly.index.hour
last_date = hourly.index.max().date()

# Hold out the final day to check how this simple forecast performs.
training = hourly[
    (hourly.index.date < last_date)
    & (hourly["coverage"] >= minimum_coverage)
].copy()

test_day = hourly[
    (hourly.index.date == last_date)
    & (hourly["coverage"] >= minimum_coverage)
].copy()

# Baseline: predict each hour using the average for that hour
# across the earlier training days.
training_profile = training.groupby("hour_of_day")["actual_W"].mean()
test_day["predicted_W"] = test_day.index.hour.map(training_profile)
test_day = test_day.dropna(subset=["predicted_W"])

if test_day.empty:
    raise SystemExit(
        "No sufficiently complete hourly readings on the final day "
        "to evaluate the forecast."
    )

forecast_errors = test_day["actual_W"] - test_day["predicted_W"]
mae_w = forecast_errors.abs().mean()
rmse_w = (forecast_errors.pow(2).mean()) ** 0.5

print(f"Forecast check date: {last_date}")
print("Hours evaluated:", len(test_day))
print(f"Mean absolute error: {mae_w / 1000:.2f} kW")
print(f"Root mean squared error: {rmse_w / 1000:.2f} kW")

evaluation = {
    "method": "same-hour historical mean baseline",
    "holdout_date": last_date.isoformat(),
    "hours_evaluated": int(len(test_day)),
    "minimum_hour_coverage_percent": minimum_coverage * 100,
    "mae_kW": float(mae_w / 1000),
    "rmse_kW": float(rmse_w / 1000),
    "uses_future_observations": False,
}
evaluation_file = (
    project_folder
    / "data"
    / "processed"
    / "forecast_evaluation_2013-08-04.json"
)
evaluation_file.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

# After evaluating on the final day, use all valid hours to forecast
# the following day.
all_valid_hours = hourly[hourly["coverage"] >= minimum_coverage]
final_profile = all_valid_hours.groupby("hour_of_day")["actual_W"].mean()

forecast_start = (
    pd.Timestamp(last_date, tz=timezone) + pd.Timedelta(days=1)
)
forecast_times = pd.date_range(
    start=forecast_start,
    periods=24,
    freq="1h",
)

forecast = pd.DataFrame(
    {
        "timestamp": forecast_times,
        "forecast_power_W": [
            final_profile.get(hour, float("nan"))
            for hour in forecast_times.hour
        ],
    }
)

# For one-hour periods, average watts / 1,000 gives estimated kWh.
forecast["forecast_energy_kWh"] = forecast["forecast_power_W"] / 1000

output_file = (
    project_folder
    / "data"
    / "processed"
    / f"energy_forecast_{forecast_start:%Y-%m-%d}.csv"
)
forecast.to_csv(output_file, index=False)

print(f"\n24-hour baseline forecast saved to: {output_file}")
print(f"Forecast evaluation saved to: {evaluation_file}")
forecast_preview = forecast.head(6).copy()
forecast_preview["forecast_power_W"] = (
    forecast_preview["forecast_power_W"].round(2)
)
forecast_preview["forecast_energy_kWh"] = (
    forecast_preview["forecast_energy_kWh"].round(2)
)
print(forecast_preview.to_string(index=False))
