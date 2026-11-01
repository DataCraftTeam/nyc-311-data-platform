{#
  Model:   int_service_requests_enriched
  Purpose: Enrich standardized NYC 311 service request records with operational and SLA metrics.
  Grain:   One row per service request (unique_key).
  Depends: ref('stg_nyc311')
#}

{{ config(
    tags = ["intermediate", "nyc311"]
) }}

WITH staging AS (

    SELECT * FROM {{ ref('stg_nyc311') }}

),

enriched AS (

    SELECT
        *,

        -- Close status flag
        closed_at IS NOT NULL AS is_closed,

        -- Resolution time in hours (only applicable to closed requests; guards against negative duration)
        CASE
            WHEN closed_at IS NOT NULL AND created_at IS NOT NULL AND closed_at >= created_at
                THEN ROUND(CAST(EXTRACT(EPOCH FROM (closed_at - created_at)) / 3600.0 AS NUMERIC), 2)
            ELSE NULL
        END AS resolution_time_hours,

        -- SLA Breach flag:
        -- NULL when no due date was assigned
        -- TRUE if closed after due date or currently open past due date
        -- FALSE if closed on/before due date or open within due date
        CASE
            WHEN due_at IS NULL THEN NULL
            WHEN closed_at IS NOT NULL THEN closed_at > due_at
            WHEN closed_at IS NULL THEN CURRENT_TIMESTAMP > due_at
            ELSE FALSE
        END AS is_sla_breached

    FROM staging

)

SELECT * FROM enriched

