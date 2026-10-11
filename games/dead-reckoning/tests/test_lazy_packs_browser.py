"""The lazy packs in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable): the first screen does not fetch the
deferred files, opening a chapter or the practice generator fetches its pack once, a save made after using a pack restores in a fresh
page where the pack is not loaded yet, and a pack that cannot load never breaks or alters the save. Requests to the live backend are
blocked and nothing is saved anywhere but this test's own browser context."""

import contextlib
import functools
import http.server
import json
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

DEFERRED = ["charts_wind.py", "charts_fixes.py", "charts_fog.py", "charts_tides.py", "charts_compass.py", "charts_two.py", "genmake.py", "gentwo.py"]
READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === '' && document.querySelector('#chart-holder svg')"
UNLOCK = ("window.pyodide.runPython(\"import state\\nfor cid in ('open-01','open-02','open-03','open-04'):\\n"
          "    meta['charts'][cid] = dict(state.new_record(), stars=1)\\n\"); window.deadReckoningRefresh();")


def _online():
    try:
        urllib.request.urlopen("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js", timeout=5).close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def base():
    if not _online():
        pytest.skip("Pyodide's CDN is not reachable")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://localhost:%d/games/dead-reckoning/" % port
    server.shutdown()


class Session:
    def __init__(self, p, base, page_name="index.html", width=1440, height=900, block=()):
        self.browser = p.chromium.launch()
        self.ctx = self.browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        self.ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
        for name in block:
            self.ctx.route("**/" + name, lambda route: route.abort())
        self.page = self.ctx.new_page()
        self.errors = []
        self.requests = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.on("request", lambda r: self.requests.append(r.url.rsplit("/", 1)[-1].split("?")[0]))
        self.base, self.page_name = base, page_name

    def start(self, clear=True):
        self.page.goto(self.base + self.page_name + "#play")
        if clear:
            self.page.evaluate("localStorage.clear()")
            self.page.reload()
        self.page.wait_for_function(READY, timeout=90000)
        return self

    def count(self, name):
        return self.requests.count(name)

    def close(self):
        self.browser.close()


def _open_chart(page, name):
    page.click("#picker-toggle-button")
    page.click("#picker-body button:has-text('%s')" % name)
    page.wait_for_function("document.querySelector('#chart-title').textContent === %s" % json.dumps(name), timeout=30000)


def test_the_first_screen_fetches_no_deferred_file_and_a_chapter_loads_once_when_opened(base):
    with sync_playwright() as p:
        s = Session(p, base).start()
        page = s.page
        assert "modules.json" in s.requests and "lazy_packs.py" in s.requests and "charts_index.py" in s.requests
        for name in DEFERRED:
            assert s.count(name) == 0, name + " must not load with the first screen"
        assert page.evaluate("window.NoyvjPacks.used()") == []
        page.evaluate("() => { " + UNLOCK + " }")
        page.click("#picker-toggle-button")
        notes = page.locator(".pack-note")
        before = notes.count()
        assert before >= 1 and "Loads when opened" in notes.first.inner_text()
        assert "KB" in notes.first.inner_text()
        # the first open fetches the pack once, with the loading card shown while it is on its way
        page.click("#picker-body button:has-text('Fresh Breeze')")
        page.wait_for_function("document.querySelector('#chart-title').textContent === 'Fresh Breeze'", timeout=30000)
        assert s.count("charts_wind.py") == 1
        assert page.evaluate("window.NoyvjPacks.used()") == ["chapter-wind"]
        # a second open (another chart, then back) is instant: no new request
        _open_chart(page, "First Light")
        _open_chart(page, "Fresh Breeze")
        assert s.count("charts_wind.py") == 1
        page.click("#picker-toggle-button")
        assert page.locator(".pack-note").filter(has_text="Loads when opened").count() == before - 1, "the loaded chapter loses its note"
        assert not s.errors, s.errors
        s.close()


def test_the_practice_generator_and_two_ships_are_fetched_on_first_use_only(base):
    with sync_playwright() as p:
        s = Session(p, base).start()
        page = s.page
        page.click("#picker-toggle-button")
        assert s.count("genmake.py") == 0
        page.click("#practice-levels button >> nth=0")
        page.wait_for_function("document.querySelector('#practice-line') && !document.querySelector('#practice-line').hidden", timeout=60000)
        assert s.count("genmake.py") == 1 and s.count("gentwo.py") == 0
        page.click("#picker-toggle-button")
        page.check("#practice-two-checkbox")
        page.click("#practice-levels button >> nth=0")
        page.wait_for_function("document.querySelector('#practice-line').textContent.indexOf('two ships') >= 0", timeout=90000)
        assert s.count("gentwo.py") == 1 and s.count("genmake.py") == 1
        assert page.evaluate("window.NoyvjPacks.used()") == ["practice", "two-ships"]
        assert not s.errors, s.errors
        s.close()


def _play_wind_chart(page):
    page.evaluate("() => { " + UNLOCK + " }")
    _open_chart(page, "Fresh Breeze")
    page.click("#add-leg-button")
    page.wait_for_function("document.querySelectorAll('#legs-list li.leg').length === 1")


def test_a_save_made_after_using_a_pack_restores_in_a_fresh_page_where_the_pack_is_not_loaded(base):
    with sync_playwright() as p:
        s = Session(p, base).start()
        page = s.page
        _play_wind_chart(page)
        state = page.evaluate("window.pyodide.globals.get('get_state')().toJs({dict_converter: Object.fromEntries})")
        assert state["packs_used"] == ["chapter-wind"] and state["run"]["chart_id"] == "wind-01" and len(state["run"]["legs"]) == 1
        saved = page.evaluate("localStorage.getItem('dead-reckoning:state')")
        s.close()

        t = Session(p, base)
        t.page.goto(base + "index.html#play")
        t.page.evaluate("s => localStorage.setItem('dead-reckoning:state', s)", saved)
        t.page.reload()
        t.page.wait_for_function(READY, timeout=90000)
        t.page.wait_for_function("document.querySelector('#chart-title').textContent === 'Fresh Breeze'", timeout=30000)
        assert t.count("charts_wind.py") == 1, "the pack is fetched first, through requires, because the save names it"
        assert t.page.evaluate("document.querySelectorAll('#legs-list li.leg').length") == 1
        assert not t.errors, t.errors
        t.close()


def test_a_pack_that_cannot_load_never_breaks_or_alters_the_save(base):
    with sync_playwright() as p:
        s = Session(p, base).start()
        _play_wind_chart(s.page)
        saved = s.page.evaluate("localStorage.getItem('dead-reckoning:state')")
        s.close()

        t = Session(p, base, block=["charts_wind.py"])
        t.page.goto(base + "index.html#play")
        t.page.evaluate("s => localStorage.setItem('dead-reckoning:state', s)", saved)
        t.page.reload()
        # the loader's card offers "Not now"; the game goes on from a core chart
        t.page.wait_for_selector("text=Not now", timeout=60000)
        t.page.click("text=Not now")
        t.page.wait_for_function(READY, timeout=90000)
        assert t.page.evaluate("document.querySelector('#chart-title').textContent") != "Fresh Breeze"
        state = t.page.evaluate("window.pyodide.globals.get('get_state')().toJs({dict_converter: Object.fromEntries})")
        assert state["run"]["chart_id"] == "wind-01" and len(state["run"]["legs"]) == 1, "the saved plan is written back unchanged"
        assert state["packs_used"] == ["chapter-wind"]
        assert not t.errors, t.errors
        t.close()


@pytest.mark.parametrize("width,height", [(360, 740)])
def test_the_loading_state_fits_a_phone(base, width, height):
    with sync_playwright() as p:
        s = Session(p, base, width=width, height=height).start()
        s.page.evaluate("() => { " + UNLOCK + " }")
        s.page.click("#picker-toggle-button")
        assert s.page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        s.close()


def test_the_desktop_page_opens_a_lazy_chapter_too(base):
    with sync_playwright() as p:
        s = Session(p, base, page_name="pc.html").start()
        s.page.evaluate("() => { " + UNLOCK + " }")
        s.page.click("button.pc-icon-button[title*='Chart'], button.pc-icon-button[aria-label*='Chart']")
        s.page.click("#picker-body button:has-text('Fresh Breeze')")
        s.page.wait_for_function("document.querySelector('#chart-title').textContent === 'Fresh Breeze'", timeout=30000)
        assert s.count("charts_wind.py") == 1 and not s.errors, s.errors
        s.close()
