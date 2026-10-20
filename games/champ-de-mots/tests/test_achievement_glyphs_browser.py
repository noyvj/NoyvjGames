import contextlib
import functools
import http.server
import socket
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
GAME = "champ-de-mots"


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
    yield "http://localhost:%d/games/%s/" % (port, GAME)
    server.shutdown()


READY = ("(() => { const s = document.querySelector('#engine-status');"
         " if (s) return s.textContent === '' || s.hidden;"
         " return !!window.pyodide && !!window.pyodide.globals.get('get_state'); })()")


def open_game(p, base, width=1280, height=800):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def test_achievement_glyphs_four_styles(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)

        # Inject the achievement element to test styles in isolation.
        page.evaluate("""() => {
            const p = document.createElement('p');
            p.className = 'achievement-earned';
            p.innerHTML = '<span class="achievement-glyph" data-glyph-word="sprout">🌱</span>';
            document.body.appendChild(p);
        }""")

        # High-def (default)
        clip_path = page.evaluate("() => getComputedStyle(document.querySelector('.achievement-glyph')).getPropertyValue('clip-path')")
        assert clip_path == "none"

        # Low-poly
        page.evaluate("document.documentElement.setAttribute('data-visual-style', 'lowpoly')")
        clip_path = page.evaluate("() => getComputedStyle(document.querySelector('.achievement-glyph')).getPropertyValue('clip-path')")
        assert clip_path.startswith("polygon(")

        # Cartoon
        page.evaluate("document.documentElement.setAttribute('data-visual-style', 'cartoon')")
        border_top_width = page.evaluate("() => getComputedStyle(document.querySelector('.achievement-glyph')).getPropertyValue('border-top-width')")
        assert border_top_width == "2px"

        # Text-based
        page.evaluate("document.documentElement.setAttribute('data-visual-style', 'textbased')")
        font_size = page.evaluate("() => getComputedStyle(document.querySelector('.achievement-glyph')).getPropertyValue('font-size')")
        assert font_size == "0px"

        pseudo_content = page.evaluate("() => getComputedStyle(document.querySelector('.achievement-glyph'), '::after').getPropertyValue('content')")
        assert pseudo_content == '"[sprout] "'

        assert True
        browser.close()
