{#
  Model:   dim_complaint_type
  Purpose: Complaint classification (type and descriptor).
  Grain:   One row per complaint_type + descriptor.
  Depends: ref('int_service_requests_enriched')
#}

{{ config(
    tags = ["marts", "dimension", "nyc311"]
) }}

SELECT DISTINCT
    MD5(complaint_type || '|' || COALESCE(descriptor, ''))  AS complaint_type_key,
    complaint_type,
    descriptor
FROM {{ ref('int_service_requests_enriched') }}
