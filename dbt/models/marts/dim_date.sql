{#
  Model:   dim_date
  Purpose: Calendar dimension covering every created/closed date in the data.
  Grain:   One row per calendar day.
  Depends: ref('int_service_requests_enriched')
#}

{{ config(
    tags = ["marts", "dimension", "nyc311"]
) }}

WITH bounds AS (

    SELECT
        MIN(created_at)::DATE                                AS start_date,
        GREATEST(MAX(created_at), MAX(closed_at))::DATE      AS end_date
    FROM {{ ref('int_service_requests_enriched') }}

)

SELECT
    TO_CHAR(d, 'YYYYMMDD')::INT          AS date_key,
    d::DATE                              AS full_date,
    EXTRACT(YEAR FROM d)::INT            AS year,
    EXTRACT(QUARTER FROM d)::INT         AS quarter,
    EXTRACT(MONTH FROM d)::INT           AS month,
    TO_CHAR(d, 'Mon')                    AS month_name,
    DATE_TRUNC('month', d)::DATE         AS month_start,
    EXTRACT(ISODOW FROM d)::INT          AS day_of_week,
    TO_CHAR(d, 'Dy')                     AS day_name,
    EXTRACT(ISODOW FROM d) IN (6, 7)     AS is_weekend
FROM bounds,
     GENERATE_SERIES(start_date, end_date, INTERVAL '1 day') AS d
