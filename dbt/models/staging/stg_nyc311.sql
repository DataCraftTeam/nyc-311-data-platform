{#
  Model:   stg_nyc311
  Purpose: Clean, standardize, and type-cast raw NYC 311 service request records.
  Grain:   One row per service request (unique_key).
  Sources: bronze.raw_nyc_311
#}

{{ config(
    tags = ["staging", "nyc311"]
) }}

-- pull raw columns from bronze source
WITH source AS (

    SELECT
        unique_key,
        created_date,
        closed_date,
        due_date,
        agency,
        agency_name,
        complaint_type,
        descriptor,
        status,
        resolution_description,
        borough,
        incident_zip,
        latitude,
        longitude,
        open_data_channel_type
    FROM {{ source('bronze', 'raw_nyc_311') }}

),

-- clean & cast to proper data types
cleaned_and_cast AS (

    SELECT
        -- Primary key
        CAST(unique_key AS BIGINT) AS unique_key,

        -- Timestamps (convert empty text to NULL)
        CAST(NULLIF(TRIM(created_date), '') AS TIMESTAMPTZ) AS created_at,
        CAST(NULLIF(TRIM(closed_date), '') AS TIMESTAMPTZ) AS closed_at,
        CAST(NULLIF(TRIM(due_date), '') AS TIMESTAMPTZ) AS due_at,

        -- Agency & Operations
        UPPER(TRIM(agency)) AS agency,
        TRIM(agency_name) AS agency_name,
        INITCAP(TRIM(status)) AS status,
        TRIM(resolution_description) AS resolution_description,

        -- complaint classification
        TRIM(complaint_type) AS complaint_type,
        TRIM(descriptor) AS descriptor,

        -- converting empty strings or 'UNSPECIFIED' to NULL
        CASE
            WHEN UPPER(TRIM(borough)) IN ('UNSPECIFIED', '') THEN NULL
            ELSE UPPER(TRIM(borough))
        END AS borough,
        NULLIF(TRIM(incident_zip), '') AS incident_zip,
        CAST(NULLIF(TRIM(latitude), '') AS NUMERIC(10, 7)) AS latitude,
        CAST(NULLIF(TRIM(longitude), '') AS NUMERIC(10, 7)) AS longitude,

        -- missing or blank channel to 'UNKNOWN'
        COALESCE(NULLIF(TRIM(open_data_channel_type), ''), 'UNKNOWN') AS channel_type

    FROM source

)

SELECT * FROM cleaned_and_cast
