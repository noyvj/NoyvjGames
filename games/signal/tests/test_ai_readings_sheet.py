"""R4-SIPC-3 (Desktop): the readings sheet beside the board. It is a hidden section in index.html that the Desktop shell
moves into the side column and pc.js fills from the page's own #waterfall. The first version polled localStorage for
fields the view does not have (`value`), never re-sorted and styled a class the board cell does not match."""

import contextlib
import functools
import http.server
import json
import socket
import threading
from pathlib import Path

import pytest
from .pagefiles import app_text

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
PC_HTML = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
CONFIG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
APP = app_text()


def test_the_section_exists_hidden_in_both_pages_and_is_registered_in_the_side_zone():
    assert '<section id="readings-sheet"' in HTML and 'aria-label="Readings sheet" hidden>' in HTML
    assert 'id="readings-sheet"' in PC_HTML
    assert "#readings-sheet" in CONFIG["zones"]["side"]


def test_it_reads_what_app_js_really_draws():
    block = PC_JS[PC_JS.index("// R4-SIPC-3"):]
    assert "localStorage" not in block and "signal:lastview" not in block
    assert '"#waterfall .wf-item"' in block
    # the waterfall item is glyph, value, label in that order (renderWaterfall)
    render = APP[APP.index("function renderWaterfall"):APP.index("function countdownText")]
    assert render.index("p.glyph") < render.index("String(p.v)") < render.index("p.label")
    assert "MutationObserver" in block and "data-sort" in block and "aria-sort" in block


def test_every_class_pc_js_adds_is_styled_and_the_sheet_is_not_a_classic_stray():
    for cls in ("sheet-tile", "sheet-highlight", "sheet-empty"):
        assert cls in PC_JS and cls in PC_CSS
    assert "#readings-sheet[hidden] { display: none; }" in PC_CSS
    assert "readings-sheet" not in (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert "transition" not in PC_CSS[PC_CSS.index("R4-SIPC-3"):]       # nothing animates, so nothing to switch off


pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = GAME_DIR.parents[1]


@pytest.fixture(scope="module")
def base():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://localhost:%d/games/signal/" % port
    server.shutdown()


# a waterfall as app.js draws it, fed straight into the page so the test needs no engine
FEED = """() => {
  const box = document.getElementById("waterfall");
  box.innerHTML = "";
  [["C3", 2, "·"], ["A1", 7, "#"], ["B2", 4, "+"]].forEach(([label, v, g]) => {
    const item = document.createElement("div"); item.className = "wf-item";
    [g, String(v), label].forEach(t => { const s = document.createElement("span"); s.textContent = t; item.appendChild(s); });
    box.appendChild(item);
  });
}"""


def test_rows_sort_and_a_click_highlights_the_tile(base):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + "pc.html#play")
        page.wait_for_selector("#readings-sheet:not([hidden])")
        page.wait_for_selector("#board .cell")
        assert page.eval_on_selector("#readings-sheet", "e => e.parentElement.id") == "pc-side"
        page.evaluate(FEED)
        page.wait_for_function("document.querySelectorAll('#readings-sheet tbody tr').length === 3")
        tiles = lambda: page.eval_on_selector_all("#readings-sheet .sheet-tile", "els => els.map(e => e.textContent)")  # noqa: E731
        assert tiles() == ["C3", "A1", "B2"]                       # ping order
        page.click("#readings-sheet [data-sort=tile]")
        assert tiles() == ["A1", "B2", "C3"]
        page.click("#readings-sheet [data-sort=value]")
        assert tiles() == ["A1", "B2", "C3"]                       # strongest reading first: 7, 4, 2
        page.click("#readings-sheet [data-sort=value]")
        assert tiles() == ["C3", "B2", "A1"]
        assert page.get_attribute("#readings-sheet th:nth-child(3)", "aria-sort") == "ascending"
        page.click("#readings-sheet .sheet-tile >> text=B2")
        assert page.eval_on_selector("#board .cell[data-r='1'][data-c='1']", "e => e.classList.contains('sheet-highlight')")
        browser.close()


def test_classic_page_never_shows_it(base):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + "index.html#play")
        page.wait_for_selector("#board .cell")
        assert not page.is_visible("#readings-sheet")
        browser.close()
