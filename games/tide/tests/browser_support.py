"""A tiny headless-Chromium harness for Tide's own page scripts (ui.js and the markup in index.html).

The page is served from a fake origin straight from the repository; Pyodide and every other host are
refused, so the game itself never boots and nothing reaches the network. What is under test is the
JavaScript that does not need Python: the phone view, tile taps, the dashboard layout. Skipped when
Playwright or Chromium is not installed."""

import mimetypes
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ORIGIN = "http://tide.test"


@pytest.fixture(scope="module")
def chromium():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # no browser binary
            pytest.skip(f"Chromium unavailable: {exc}")
        yield browser
        browser.close()


class TidePage:
    def __init__(self, browser, size=(360, 740), touch=True, page_name="index.html"):
        self.errors = []
        self.context = browser.new_context(
            viewport={"width": size[0], "height": size[1]}, has_touch=touch, is_mobile=touch,
        )
        self.context.route("**/*", self._serve)
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page_name = page_name

    @staticmethod
    def _serve(route, request):
        url = request.url
        if not url.startswith(ORIGIN):
            return route.abort()
        path = url[len(ORIGIN):].split("?")[0]
        file = ROOT / path.lstrip("/")
        if file.is_file():
            return route.fulfill(status=200, content_type=mimetypes.guess_type(file.name)[0] or "text/plain",
                                 body=file.read_bytes())
        return route.fulfill(status=404, body="")

    def open(self):
        self.page.goto(f"{ORIGIN}/games/tide/{self.page_name}")
        return self.page

    def close(self):
        self.context.close()


@pytest.fixture
def tide_page(chromium):
    made = []

    def make(**kwargs):
        t = TidePage(chromium, **kwargs)
        made.append(t)
        return t

    yield make
    for t in made:
        t.close()
