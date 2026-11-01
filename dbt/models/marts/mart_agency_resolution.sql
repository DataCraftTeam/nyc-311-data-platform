{#
  Model:   mart_agency_resolution
  Purpose: Q3 how long each agency takes to resolve requests.
  Grain:   One row per agency + month the request was closed.
  Depends: ref('fct_service_requests'), ref('dim_agency'), ref('dim_date')
#}

{{ config(
    tags = ["marts", "nyc311"]
) }}

SELECT
    a.agency,
    a.agency_name,
    d.month_start                                                                          AS closed_month,
    COUNT(*)                                                                               AS closed_count,
    ROUND(AVG(f.resolution_time_hours), 2)                                                 AS avg_resolution_hours,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)::NUMERIC, 2) AS median_resolution_hours,
    ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY f.resolution_time_hours)::NUMERIC, 2) AS p90_resolution_hours,
    -- share of requests with a due date that were closed late (NULL when no request had a due date)
    ROUND(100.0 * AVG(f.is_sla_breached::INT), 1)                                          AS sla_breach_pct
FROM {{ ref('fct_service_requests') }} f
JOIN {{ ref('dim_agency') }} a ON a.agency_key = f.agency_key
JOIN {{ ref('dim_date') }} d ON d.date_key = f.closed_date_key
WHERE f.resolution_time_hours IS NOT NULL
GROUP BY 1, 2, 3
