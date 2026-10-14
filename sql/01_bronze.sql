CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.nyc_311_raw (
    unique_key              TEXT PRIMARY KEY,
    created_date            TEXT,
    closed_date             TEXT,
    agency                  TEXT,
    complaint_type          TEXT,
    descriptor              TEXT,
    location_type           TEXT,
    incident_zip            TEXT,
    status                  TEXT,
    resolution_description  TEXT,
    borough                 TEXT,
    open_data_channel_type  TEXT,
    latitude                TEXT,
    longitude               TEXT,
    _ingested_at            TIMESTAMPTZ DEFAULT now(),
    _source_partition       TEXT
);