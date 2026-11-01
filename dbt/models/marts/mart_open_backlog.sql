{#
  Model:   mart_open_backlog
  Purpose: Q4 how many requests are still unresolved, and for how long.
  Grain:   One row per agency + complaint_type + borough (open requests only).
  Depends: ref('fct_service_requests'), ref('dim_agency'), ref('dim_complaint_type'), ref('dim_location')
#}

{{ config(
    tags = ["marts", "nyc311"]
) }}

SELECT
    a.agency,
    c.complaint_type,
    l.borough,
    COUNT(*)                                                               AS open_count,
    ROUND(AVG(EXTRACT(EPOCH FROM NOW() - f.created_at) / 86400.0), 1)      AS avg_days_open,
    MIN(f.created_at)                                                      AS oldest_open_created_at
FROM {{ ref('fct_service_requests') }} f
JOIN {{ ref('dim_agency') }} a ON a.agency_key = f.agency_key
JOIN {{ ref('dim_complaint_type') }} c ON c.complaint_type_key = f.complaint_type_key
JOIN {{ ref('dim_location') }} l ON l.location_key = f.location_key
WHERE NOT f.is_closed
GROUP BY 1, 2, 3
