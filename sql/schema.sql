PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS facilities (
    facility_id   INTEGER PRIMARY KEY,
    facility_name TEXT NOT NULL,
    facility_type TEXT NOT NULL,
    location      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id    INTEGER PRIMARY KEY,
    facility_id INTEGER NOT NULL,
    asset_name  TEXT NOT NULL,
    asset_type  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (facility_id) REFERENCES facilities (facility_id),
    UNIQUE (facility_id, asset_name)
);

-- Extension to the supplied ERD: asset_id and unit preserve per-meter readings
-- and make the stored numeric value unambiguous (the electricity channels are W).
CREATE TABLE IF NOT EXISTS energy_usage (
    energy_id         INTEGER PRIMARY KEY,
    facility_id       INTEGER NOT NULL,
    asset_id          INTEGER NOT NULL,
    timestamp         TEXT NOT NULL,
    electricity_usage REAL,
    water_usage       REAL,
    unit              TEXT NOT NULL,
    source            TEXT NOT NULL,
    FOREIGN KEY (facility_id) REFERENCES facilities (facility_id),
    FOREIGN KEY (asset_id) REFERENCES assets (asset_id),
    UNIQUE (asset_id, timestamp)
);

CREATE TABLE IF NOT EXISTS occupancy_records (
    occupancy_id   INTEGER PRIMARY KEY,
    facility_id    INTEGER NOT NULL,
    zone           TEXT NOT NULL,
    occupancy_count INTEGER NOT NULL,
    timestamp      TEXT NOT NULL,
    FOREIGN KEY (facility_id) REFERENCES facilities (facility_id)
);

CREATE TABLE IF NOT EXISTS maintenance_records (
    maintenance_id   INTEGER PRIMARY KEY,
    asset_id         INTEGER NOT NULL,
    issue_type       TEXT NOT NULL,
    maintenance_date TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES assets (asset_id)
);

CREATE TABLE IF NOT EXISTS security_events (
    event_id    INTEGER PRIMARY KEY,
    facility_id INTEGER NOT NULL,
    event_type  TEXT NOT NULL,
    severity    TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    FOREIGN KEY (facility_id) REFERENCES facilities (facility_id)
);

CREATE TABLE IF NOT EXISTS cost_reports (
    report_id   INTEGER PRIMARY KEY,
    facility_id INTEGER NOT NULL,
    category    TEXT NOT NULL,
    amount      REAL NOT NULL,
    report_date TEXT NOT NULL,
    FOREIGN KEY (facility_id) REFERENCES facilities (facility_id)
);

-- Extension to the supplied ERD: details records which transparent rule fired.
CREATE TABLE IF NOT EXISTS alerts (
    alert_id    INTEGER PRIMARY KEY,
    facility_id INTEGER NOT NULL,
    alert_type  TEXT NOT NULL,
    severity    TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    details     TEXT NOT NULL,
    FOREIGN KEY (facility_id) REFERENCES facilities (facility_id),
    UNIQUE (facility_id, alert_type, created_at)
);

CREATE INDEX IF NOT EXISTS idx_energy_usage_facility_time
    ON energy_usage (facility_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_energy_usage_asset_time
    ON energy_usage (asset_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_facility_created
    ON alerts (facility_id, created_at);
CREATE INDEX IF NOT EXISTS idx_occupancy_facility_time
    ON occupancy_records (facility_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_maintenance_asset_date
    ON maintenance_records (asset_id, maintenance_date);
CREATE INDEX IF NOT EXISTS idx_security_facility_time
    ON security_events (facility_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_cost_facility_date
    ON cost_reports (facility_id, report_date);
