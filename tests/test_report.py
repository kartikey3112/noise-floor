import json
import re

from noisefloor.report import DATA_PLACEHOLDER, embed

PAGE = f'<script id="report-data" type="application/json">{DATA_PLACEHOLDER}</script>'


def test_data_is_embedded_as_json():
    html = embed(PAGE, {"overview": {"flaky_tests": 6}})
    payload = re.search(r">(.*)</script>", html).group(1)
    assert json.loads(payload) == {"overview": {"flaky_tests": 6}}


def test_a_test_name_cannot_close_the_script_tag_early():
    """A test name containing </script> must stay data, never end the tag and run as HTML."""
    html = embed(PAGE, {"name": "test_x</script><script>alert(1)</script>"})
    assert html.count("</script>") == 1  # only the real closing tag
    payload = re.search(r">(.*)</script>", html).group(1)
    assert json.loads(payload)["name"] == "test_x</script><script>alert(1)</script>"
