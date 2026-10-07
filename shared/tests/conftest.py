"""Shared fixtures for the browser tests of the site-wide shared pieces (lite mode, a11y, touch
targets, error boundary, debug overlay, perf marks, info footer). Everything runs in headless
Chromium through Playwright against files read straight from the repository: requests to a fake
origin are answered from disk, and anything addressed to the live backend or any other host is
answered by the test (or refused), so no test can reach the network. Skipped when Playwright or
Chromium is not installed."""

import json
import mimetypes
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "http://harness.test"
API = "https://noyvjgames.fastapicloud.dev"


@pytest.fixture(scope="module")
def chromium():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:  # no browser binary
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


class Harness:
    """One browser context with a fake origin. Register pages with `pages["/t.html"] = html`."""

    def __init__(self, browser, size=(1440, 900), touch=False, init_scripts=(), media=None):
        self.pages = {}
        self.api_calls = []          # (method, path, body) for every request aimed at the backend
        self.api_responses = {}      # (method, path) -> (status, json-able)
        self.console = []
        self.errors = []
        self.context = browser.new_context(
            viewport={"width": size[0], "height": size[1]}, has_touch=touch, is_mobile=touch,
            **(media or {}),
        )
        for script in init_scripts:
            self.context.add_init_script(script)
        self.context.route("**/*", self._serve)
        self.page = self.context.new_page()
        self.page.on("console", lambda m: self.console.append((m.type, m.text)))
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))

    def _serve(self, route, request):
        url = request.url
        if url.startswith(API):
            path = url[len(API):]
            self.api_calls.append((request.method, path, request.post_data))
            status, body = self.api_responses.get((request.method, path.split("?")[0]), (404, {"detail": "none"}))
            return route.fulfill(status=status, content_type="application/json", body=json.dumps(body),
                                 headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*",
                                          "access-control-allow-methods": "*"})
        if not url.startswith(ORIGIN):
            return route.abort()
        path = url[len(ORIGIN):].split("?")[0]
        if path in self.pages:
            return route.fulfill(status=200, content_type="text/html", body=self.pages[path])
        file = ROOT / path.lstrip("/")
        if file.is_file():
            return route.fulfill(status=200, content_type=mimetypes.guess_type(file.name)[0] or "text/plain",
                                 body=file.read_bytes())
        return route.fulfill(status=404, body="")

    def goto(self, path="/t.html"):
        self.page.goto(ORIGIN + path)
        return self.page

    def close(self):
        self.context.close()


@pytest.fixture
def harness(chromium):
    made = []

    def make(**kwargs):
        h = Harness(chromium, **kwargs)
        made.append(h)
        return h

    yield make
    for h in made:
        h.close()


def page_html(head="", body="", extra_attrs=""):
    return (f'<!doctype html><html lang="en" {extra_attrs}><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">{head}</head><body>{body}</body></html>')
