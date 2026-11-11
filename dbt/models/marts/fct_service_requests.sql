{#
  Model:   fct_service_requests
  Purpose: Central fact table for 311 analytics (accumulating snapshot: created -> closed).
  Grain:   One row per service request (unique_key).
  Depends: ref('int_service_requests_enriched')
#}

{{ config(
    tags = ["marts", "fact", "nyc311"]
) }}

SELECT
    unique_key,

    -- Foreign keys
    TO_CHAR(created_at, 'YYYYMMDD')::INT                                       AS created_date_key,
    TO_CHAR(closed_at, 'YYYYMMDD')::INT                                        AS closed_date_key,
    MD5(agency)                                                                AS agency_key,
    MD5(complaint_type || '|' || COALESCE(descriptor, ''))                     AS complaint_type_key,
    MD5(COALESCE(borough, 'UNSPECIFIED') || '|' || COALESCE(incident_zip, '')) AS location_key,

    -- Degenerate attributes (few values, kept on the fact)
    status,
    channel_type,
    resolution_description,

    -- Timestamps
    created_at,
    closed_at,
    due_at,

    -- Measures and flags
    is_closed,
    resolution_time_hours,
    is_sla_breached,
    -- source data issue: closed_at earlier than created_at (resolution_time_hours is NULL for these)
    COALESCE(closed_at < created_at, FALSE)                                    AS has_invalid_close_date,
    latitude,
    longitude

FROM {{ ref('int_service_requests_enriched') }}
