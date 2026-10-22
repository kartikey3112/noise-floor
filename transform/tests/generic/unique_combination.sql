{#
  Fails when any combination of the given columns appears more than once, i.e. the model's
  grain isn't what it claims. Usage in a .yml file:
    data_tests:
      - unique_combination:
          arguments: {columns: [test_key, commit_key]}
#}
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as copies
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
