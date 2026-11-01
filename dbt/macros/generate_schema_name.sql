{#
  Override dbt's default schema naming behavior.
  
  By default, dbt concatenates the target schema and custom schema (e.g., 'silver_staging' or 'silver_gold').
  This macro ensures:
  - If a custom schema is specified (e.g. 'gold'), dbt writes directly to 'gold'.
  - If no custom schema is specified, dbt writes to the target schema ('silver').
#}

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}

