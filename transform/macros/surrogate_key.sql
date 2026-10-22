{#
  A stable key: the MD5 hash of the natural key columns joined with '|' (ADR-008).
  The same input always gives the same key, so a full rebuild never renumbers anything.
  Example: surrogate_key(['suite_name', 'class_name', 'test_name'])
#}
{% macro surrogate_key(columns) -%}
    md5(concat_ws('|', {% for column in columns -%}
        coalesce(cast({{ column }} as varchar), ''){{ ", " if not loop.last }}
    {%- endfor %}))
{%- endmacro %}
