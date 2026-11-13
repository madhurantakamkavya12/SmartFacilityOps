"""Build the local SQLite database from the processed Milestone 1 energy CSV."""

from database import DEFAULT_DB_PATH, DEFAULT_ENERGY_CSV, import_energy_csv


if __name__ == "__main__":
    if not DEFAULT_ENERGY_CSV.exists():
        raise FileNotFoundError(
            f"Processed energy CSV not found: {DEFAULT_ENERGY_CSV}. "
            "Run src/compare_ac.py first."
        )
    result = import_energy_csv()
    print(f"SQLite database: {DEFAULT_DB_PATH}")
    print(f"Energy readings imported: {result['energy_readings']:,}")
    print(f"Rule-based review alerts imported: {result['review_alerts']:,}")
