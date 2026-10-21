"""Hold R and drag on the chart: the page measures distance and bearing as text and does not set the ruler point."""
import json
import re

import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

TO_PIXELS = """([f, x, y]) => {
  const m = document.getElementById('dr-chart').getScreenCTM();
  return [m.a * (f.left + f.s * x) + m.e, m.d * (f.top + f.s * (f.size - y)) + m.f];
}"""


def _ready_chart(page):
    page.wait_for_selector("#chart-holder svg", state="attached")
    page.wait_for_selector("#add-leg-button:not([disabled])")
    page.evaluate("document.getElementById('chart-holder').scrollIntoView({block: 'start'})")   # the chart starts below the fold
    view = json.loads(page.evaluate("window.pyodide.runPython('handle(json.dumps({\"action\": \"open\"}))')"))
    return view["frame"]


def test_holding_r_and_dragging_reads_out_distance_and_bearing_without_setting_the_ruler(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        frame = _ready_chart(page)
        assert page.is_visible("#measure-readout")
        start = page.evaluate(TO_PIXELS, [frame, 5, 5])
        end = page.evaluate(TO_PIXELS, [frame, 8, 9])
        page.keyboard.down("r")
        page.mouse.move(start[0], start[1])
        page.mouse.down()
        page.mouse.move(end[0], end[1], steps=6)
        page.mouse.up()
        page.keyboard.up("r")
        found = re.match(r"Measure: ([\d.]+) nm on (\d{3})", page.text_content("#measure-readout"))
        assert found is not None
        assert 4.7 <= float(found.group(1)) <= 5.3     # the drag is (3, 4) nm, so 5 nm
        assert 33 <= int(found.group(2)) <= 41         # bearing of (3 east, 4 north) is about 037
        assert page.evaluate("document.getElementById('ruler').open") is False
        assert page.page_errors == []
        browser.close()


def test_a_plain_click_on_the_chart_still_opens_the_ruler(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        frame = _ready_chart(page)
        spot = page.evaluate(TO_PIXELS, [frame, 5, 5])
        page.mouse.click(spot[0], spot[1])
        assert page.evaluate("document.getElementById('ruler').open") is True
        assert page.text_content("#measure-readout").startswith("Hold R and drag")
        assert page.page_errors == []
        browser.close()
