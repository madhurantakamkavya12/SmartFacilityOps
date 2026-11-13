"""SQLite persistence for the Milestone 1 FacilityOps prototype."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "facilityops.db"
DEFAULT_ENERGY_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "energy_2013-07-13_to_2013-08-04_1min.csv"
)
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

FACILITY_ID = 1
ASSET_IDS = {
    "meter_1_W": 1,
    "meter_2_W": 2,
    "ac_1_W": 3,
    "ac_2_W": 4,
}
ASSET_ROWS = [
    (1, FACILITY_ID, "Mains meter 1", "mains_electricity", "active"),
    (2, FACILITY_ID, "Mains meter 2", "mains_electricity", "active"),
    (3, FACILITY_ID, "Air conditioner 1", "ac_submeter", "active"),
    (4, FACILITY_ID, "Air conditioner 2", "ac_submeter", "active"),
    (5, FACILITY_ID, "Water meter 1", "water_meter", "active"),
    (6, FACILITY_ID, "Water meter 2", "water_meter", "active"),
]


@contextmanager
def connect(db_path: Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, enable foreign keys, and always close it."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Create the supplied relational entities and seed this sample facility."""
    with connect(db_path) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.execute(
            """
            INSERT INTO facilities (facility_id, facility_name, facility_type, location)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(facility_id) DO UPDATE SET
                facility_name = excluded.facility_name,
                facility_type = excluded.facility_type,
                location = excluded.location
            """,
            (FACILITY_ID, "iAWE sample residence", "residential", "New Delhi, India"),
        )
        connection.executemany(
            """
            INSERT INTO assets (asset_id, facility_id, asset_name, asset_type, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                facility_id = excluded.facility_id,
                asset_name = excluded.asset_name,
                asset_type = excluded.asset_type,
                status = excluded.status
            """,
            ASSET_ROWS,
        )


def import_energy_csv(
    csv_path: Path = DEFAULT_ENERGY_CSV,
    db_path: Path = DEFAULT_DB_PATH,
    chunksize: int = 10_000,
) -> dict[str, int]:
    """Load per-meter one-minute electricity readings and rule-review alerts."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Processed energy CSV not found: {csv_path}")
    required_columns = {
        "timestamp",
        "meter_1_W",
        "meter_2_W",
        "ac_1_W",
        "ac_2_W",
        "total_mains_W",
        "total_ac_W",
    }
    actual_columns = set(pd.read_csv(csv_path, nrows=0).columns)
    missing_columns = required_columns - actual_columns
    if missing_columns:
        raise ValueError(
            "Processed energy CSV is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    initialize_database(db_path)
    reading_count = 0
    alert_count = 0

    with connect(db_path) as connection:
        connection.execute(
            "DELETE FROM energy_usage WHERE facility_id = ?", (FACILITY_ID,)
        )
        connection.execute(
            "DELETE FROM alerts WHERE facility_id = ? AND alert_type = ?",
            (FACILITY_ID, "ac_power_above_mains"),
        )

        for chunk in pd.read_csv(csv_path, chunksize=chunksize):
            reading_rows = []
            for row in chunk.itertuples(index=False):
                if pd.isna(row.timestamp):
                    raise ValueError("Processed energy CSV contains a missing timestamp.")
                timestamp = str(row.timestamp)
                for column, asset_id in ASSET_IDS.items():
                    value = getattr(row, column)
                    if pd.isna(value):
                        continue
                    if value < 0:
                        raise ValueError(
                            f"Negative power reading in {column} at {timestamp}."
                        )
                    reading_rows.append(
                        (
                            FACILITY_ID,
                            asset_id,
                            timestamp,
                            float(value),
                            None,
                            "W",
                            "iAWE one-minute average power",
                        )
                    )

            connection.executemany(
                """
                INSERT INTO energy_usage
                    (facility_id, asset_id, timestamp, electricity_usage,
                     water_usage, unit, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                reading_rows,
            )
            reading_count += len(reading_rows)

            alert_rows = []
            for row in chunk.itertuples(index=False):
                if (
                    pd.notna(row.total_ac_W)
                    and pd.notna(row.total_mains_W)
                    and row.total_ac_W > row.total_mains_W
                ):
                    alert_rows.append(
                        (
                            FACILITY_ID,
                            "ac_power_above_mains",
                            "review",
                            str(row.timestamp),
                            (
                                "iAWE one-minute averages: combined AC power "
                                f"{row.total_ac_W:.2f} W exceeds combined mains "
                                f"power {row.total_mains_W:.2f} W. Rule-based review flag; "
                                "not a confirmed equipment fault."
                            ),
                        )
                    )
            connection.executemany(
                """
                INSERT INTO alerts
                    (facility_id, alert_type, severity, created_at, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                alert_rows,
            )
            alert_count += len(alert_rows)

    return {"energy_readings": reading_count, "review_alerts": alert_count}


def load_dashboard_data(
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load dashboard readings, alerts, and source count with one connection."""
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")
    query = """
        SELECT
            usage.timestamp AS timestamp,
            CASE
                WHEN COUNT(DISTINCT CASE
                    WHEN asset.asset_type = 'mains_electricity'
                         AND usage.electricity_usage IS NOT NULL
                    THEN asset.asset_id END)
                    = (SELECT COUNT(*) FROM assets AS expected
                       WHERE expected.facility_id = usage.facility_id
                         AND expected.asset_type = 'mains_electricity'
                         AND expected.status = 'active')
                THEN SUM(CASE WHEN asset.asset_type = 'mains_electricity'
                              THEN usage.electricity_usage END)
                ELSE NULL
            END AS total_mains_W,
            SUM(CASE WHEN asset.asset_type = 'ac_submeter'
                     THEN usage.electricity_usage END) AS total_ac_W
        FROM energy_usage AS usage
        JOIN assets AS asset ON asset.asset_id = usage.asset_id
        WHERE usage.facility_id = ?
        GROUP BY usage.timestamp
        ORDER BY usage.timestamp
    """
    with connect(db_path) as connection:
        frame = pd.read_sql_query(query, connection, params=(FACILITY_ID,))
        alerts = pd.read_sql_query(
            """
            SELECT alert_id, alert_type, severity, created_at, details
            FROM alerts
            WHERE facility_id = ?
            ORDER BY created_at DESC, alert_id DESC
            """,
            connection,
            params=(FACILITY_ID,),
        )
        record_count = connection.execute(
            "SELECT COUNT(*) FROM energy_usage WHERE facility_id = ?",
            (FACILITY_ID,),
        ).fetchone()[0]
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True).dt.tz_convert(
            "Asia/Kolkata"
        )
    frame.attrs["source_record_count"] = int(record_count)
    return frame, alerts


def load_energy_data(db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return minute-level mains and AC totals aggregated from SQLite."""
    frame, _ = load_dashboard_data(db_path)
    return frame
