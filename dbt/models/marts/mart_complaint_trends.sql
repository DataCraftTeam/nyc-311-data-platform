{#
  Model:   mart_complaint_trends
  Purpose: Q1 which complaint types are most common, Q2 which are increasing over time.
  Grain:   One row per month + complaint_type.
  Depends: ref('fct_service_requests'), ref('dim_date'), ref('dim_complaint_type')
#}

{{ config(
    tags = ["marts", "nyc311"]
) }}

WITH monthly AS (

    SELECT
        d.month_start,
        c.complaint_type,
        COUNT(*) AS request_count
    FROM {{ ref('fct_service_requests') }} f
    JOIN {{ ref('dim_date') }} d ON d.date_key = f.created_date_key
    JOIN {{ ref('dim_complaint_type') }} c ON c.complaint_type_key = f.complaint_type_key
    GROUP BY 1, 2

),

with_previous AS (

    SELECT
        *,
        LAG(request_count) OVER (PARTITION BY complaint_type ORDER BY month_start) AS prev_month_count
    FROM monthly

)

SELECT
    month_start,
    complaint_type,
    request_count,
    RANK() OVER (PARTITION BY month_start ORDER BY request_count DESC)  AS rank_in_month,
    prev_month_count,
    ROUND(100.0 * (request_count - prev_month_count) / NULLIF(prev_month_count, 0), 1) AS mom_change_pct
FROM with_previous
