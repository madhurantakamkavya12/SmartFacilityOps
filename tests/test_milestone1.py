"""Focused integration checks for the Milestone 1 SQLite pipeline."""

import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from database import import_energy_csv, load_dashboard_data, load_energy_data
from energy_agent import energy_agent
from reporting import build_html_report


TABLES = {
    "facilities",
    "assets",
    "energy_usage",
    "occupancy_records",
    "maintenance_records",
    "security_events",
    "cost_reports",
    "alerts",
}


class Milestone1DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.database_path = self.root / "facilityops_test.db"
        self.csv_path = self.root / "energy.csv"
        self._write_fixture(self.csv_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _write_fixture(path):
        rows = [
            {
                "timestamp": "2013-07-13 00:00:00+05:30",
                "meter_1_W": 100,
                "meter_2_W": 200,
                "ac_1_W": 40,
                "ac_2_W": 10,
                "total_mains_W": 300,
                "total_ac_W": 50,
            },
            {
                "timestamp": "2013-07-13 00:01:00+05:30",
                "meter_1_W": 100,
                "meter_2_W": 200,
                "ac_1_W": 100,
                "ac_2_W": 300,
                "total_mains_W": 300,
                "total_ac_W": 400,
            },
            {
                "timestamp": "2013-07-13 00:02:00+05:30",
                "meter_1_W": None,
                "meter_2_W": 200,
                "ac_1_W": 50,
                "ac_2_W": 0,
                "total_mains_W": None,
                "total_ac_W": 50,
            },
        ]
        pd.DataFrame(rows).to_csv(path, index=False)

    def test_schema_import_integrity_and_idempotency(self):
        result = import_energy_csv(self.csv_path, self.database_path, chunksize=2)
        self.assertEqual(result, {"energy_readings": 11, "review_alerts": 1})

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            self.assertEqual(tables, TABLES)
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM energy_usage").fetchone()[0],
                11,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0], 1
            )
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO energy_usage "
                    "(facility_id, asset_id, timestamp, electricity_usage, unit, source) "
                    "VALUES (1, 999, '2013-07-13 00:00:00+05:30', 10, 'W', 'test')"
                )

        again = import_energy_csv(self.csv_path, self.database_path, chunksize=2)
        self.assertEqual(again, result)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM energy_usage").fetchone()[0],
                11,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0], 1
            )

    def test_incomplete_mains_pair_is_not_reported_as_whole_home(self):
        import_energy_csv(self.csv_path, self.database_path)
        readings, alerts = load_dashboard_data(self.database_path)
        self.assertEqual(readings.attrs["source_record_count"], 11)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(readings["total_mains_W"].iloc[0], 300)
        self.assertEqual(readings["total_ac_W"].iloc[0], 50)
        self.assertTrue(pd.isna(readings["total_mains_W"].iloc[2]))

    def test_energy_agent_uses_supplied_sql_dataframe(self):
        import_energy_csv(self.csv_path, self.database_path)
        readings = load_energy_data(self.database_path)
        result = energy_agent.invoke(
            {"data": readings, "metrics": {}, "recommendations": []}
        )
        self.assertAlmostEqual(result["metrics"]["mains_energy_kwh"], 0.01, places=8)
        self.assertEqual(result["metrics"]["anomaly_count"], 1)
        self.assertTrue(result["recommendations"])
        for recommendation in result["recommendations"]:
            self.assertEqual(
                set(recommendation), {"issue", "reason", "evidence", "action", "priority"}
            )

    def test_invalid_csv_and_missing_database_fail_clearly(self):
        invalid_csv = self.root / "bad.csv"
        pd.DataFrame([{"timestamp": "2013-07-13"}]).to_csv(invalid_csv, index=False)
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            import_energy_csv(invalid_csv, self.root / "should_not_exist.db")
        with self.assertRaises(FileNotFoundError):
            load_energy_data(self.root / "missing.db")
        with self.assertRaisesRegex(ValueError, "No energy readings"):
            energy_agent.invoke(
                {"data": pd.DataFrame(), "metrics": {}, "recommendations": []}
            )

    def test_report_generation_includes_current_sections(self):
        metrics = {
            "period": "July 13–August 4, 2013",
            "mains_energy_kwh": 1.2,
            "ac_energy_kwh": 0.3,
            "ac_share_percent": 25.0,
            "coverage_percent": 97.0,
            "peak_power_w": 300.0,
            "peak_datetime": "2013-07-13 00:00",
            "anomaly_count": 1,
            "anomaly_percent": 50.0,
        }
        recommendation = {
            "issue": "Test issue",
            "reason": "Test reason",
            "evidence": "Test evidence",
            "action": "Test action",
            "priority": "Medium",
        }
        forecast = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2013-08-05", periods=24, freq="1h", tz="Asia/Kolkata"
                ),
                "forecast_power_W": [100.0] * 24,
                "forecast_energy_kWh": [0.1] * 24,
            }
        )
        report = build_html_report(
            metrics,
            [recommendation],
            forecast,
            None,
            alerts=pd.DataFrame(
                [{"created_at": "2013-07-13", "severity": "review", "details": "test alert"}]
            ),
            forecast_evaluation={
                "holdout_date": "2013-08-04",
                "hours_evaluated": 24,
                "mae_kW": 0.1,
                "rmse_kW": 0.2,
            },
            source_record_count=11,
        )
        self.assertIn("Energy analytics report", report)
        self.assertIn("Mains energy", report)
        self.assertIn("Test issue", report)
        self.assertIn("test alert", report)
        self.assertIn("MAE 0.100 kW", report)
        self.assertIn("RMSE 0.200 kW", report)
        self.assertEqual(report.count("<tr>"), 27)  # two headers + one alert + 24 hours
        self.assertIn("Print / Save as PDF", report)


if __name__ == "__main__":
    unittest.main()
