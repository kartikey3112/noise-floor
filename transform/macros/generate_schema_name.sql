{#
  Use each folder's schema name as it is (staging, intermediate, marts, seeds), instead of
  dbt's default of prefixing it with the target schema (main_staging, ...).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name is not none else target.schema }}
{%- endmacro %}
