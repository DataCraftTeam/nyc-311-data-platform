{#
  Model:   dim_agency
  Purpose: City agencies that respond to 311 requests.
  Grain:   One row per agency acronym.
  Depends: ref('int_service_requests_enriched')
#}

{{ config(
    tags = ["marts", "dimension", "nyc311"]
) }}

SELECT
    MD5(agency)          AS agency_key,
    agency,
    MAX(agency_name)     AS agency_name
FROM {{ ref('int_service_requests_enriched') }}
GROUP BY agency
