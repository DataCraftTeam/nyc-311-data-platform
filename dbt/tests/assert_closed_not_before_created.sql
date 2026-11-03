{#
  Test:    assert_closed_not_before_created
  Purpose: Surface requests whose closed_at is earlier than created_at.
           This is a source data issue, so it warns instead of failing the build.
#}

{{ config(
    severity = "warn"
) }}

SELECT
    unique_key,
    created_at,
    closed_at,
    created_at - closed_at AS closed_before_created_by
FROM {{ ref('fct_service_requests') }}
WHERE has_invalid_close_date
