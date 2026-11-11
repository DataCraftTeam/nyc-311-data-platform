-- Initialize Bronze raw table for NYC 311 service requests
CREATE TABLE IF NOT EXISTS bronze.raw_nyc_311 (
    unique_key TEXT PRIMARY KEY,
    created_date TEXT,
    closed_date TEXT,
    due_date TEXT,
    agency TEXT,
    agency_name TEXT,
    complaint_type TEXT,
    descriptor TEXT,
    status TEXT,
    resolution_description TEXT,
    borough TEXT,
    incident_zip TEXT,
    latitude TEXT,
    longitude TEXT,
    open_data_channel_type TEXT,
    _ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    _source_batch_id UUID
);

-- Index for efficient high-watermark queries and incremental filtering
CREATE INDEX IF NOT EXISTS idx_raw_nyc_311_created_date ON bronze.raw_nyc_311 (created_date);
