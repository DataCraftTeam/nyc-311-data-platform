{#
  Model:   dim_location
  Purpose: Where the request happened (borough and ZIP code).
  Grain:   One row per borough + incident_zip.
  Depends: ref('int_service_requests_enriched')
#}

{{ config(
    tags = ["marts", "dimension", "nyc311"]
) }}

SELECT DISTINCT
    MD5(COALESCE(borough, 'UNSPECIFIED') || '|' || COALESCE(incident_zip, ''))  AS location_key,
    COALESCE(borough, 'UNSPECIFIED')                                           AS borough,
    incident_zip
FROM {{ ref('int_service_requests_enriched') }}
