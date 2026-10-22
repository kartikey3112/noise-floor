{#
  Referential integrity on a composite key: every row's (col1, col2, ...) must exist in `to`.
  dbt's built-in relationships test only handles a single column.
  Example: every test case must belong to a build that exists.
#}
{% test relationships_on_two_columns(model, to, columns) %}
select {{ columns | join(', ') }}
from {{ model }} as child
where not exists (
    select 1
    from {{ to }} as parent
    where {% for column in columns -%}
        parent.{{ column }} = child.{{ column }}{{ " and " if not loop.last }}
    {%- endfor %}
)
{% endtest %}
