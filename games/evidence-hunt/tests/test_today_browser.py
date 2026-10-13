"""Z-5c in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable): Today's run opens the practice house the UTC
date's seed makes, and solving a house from today's seed (never an older day's) counts once in the shared record the hub reads. The browser clock is fixed. Requests to the live backend are blocked: nothing is ever sent there."""

import contextlib
import functools
import http.server
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


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
    yield "http://localhost:%d/games/evidence-hunt/" % port
    server.shutdown()


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === '' && !!window.evidenceHuntStartPractice"

SOLVE = """() => {
    for (let i = 0; i < 150; i++) {
        let r = null;
        for (let k = 0; k < 3; k++) window.evidenceHuntStartPractice({action: 'hint'});
        r = window.evidenceHuntStartPractice({action: 'hint_do'});
        if (r && r.result) return r.case.code;
    }
    return null;
}"""


def open_practice(page, page_name):
    """The Practice panel: a toolbar button in Classic, an icon (the toolbar button is in the Menu) on the Desktop page."""
    if page_name == "pc.html":
        page.click("button.pc-icon-button[title*='Practice'], button.pc-icon-button[aria-label*='Practice']")
    else:
        page.click("#practice-toggle-button")


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_todays_run_opens_the_dated_house_and_solving_it_counts_once(base, page_name, width, height):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.clock.set_fixed_time("2026-10-20T09:00:00Z")
        ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + page_name + "#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        today = page.evaluate("NoyvjSeed.daily.seed('evidence-hunt', '2026-10-20')")
        old = page.evaluate("NoyvjSeed.daily.seed('evidence-hunt', '2026-10-19')")
        open_practice(page, page_name)
        assert "Play today's run" in page.inner_text("#practice-today") and today in page.inner_text("#practice-today")

        # a house from an older day's seed, and an ordinary practice house, never count
        page.evaluate("(t) => window.evidenceHuntStartPractice({action: 'practice', today: t})", old)
        assert page.evaluate(SOLVE)
        page.evaluate("window.evidenceHuntStartPractice({action: 'practice', difficulty: 2})")
        assert page.evaluate(SOLVE)
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None

        # the button opens today's house; opening is not finishing
        open_practice(page, page_name)
        page.click("#practice-today button")
        code = page.inner_text("#case-code-text")
        assert code.startswith("EH") and page.is_visible("#case-code")
        assert page.evaluate("NoyvjSeed.current()") == today
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None
        assert page.evaluate(SOLVE) == code
        record = page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1'))")
        assert record["date"] == "2026-10-20" and list(record["runs"]) == ["evidence-hunt"]
        assert record["runs"]["evidence-hunt"]["seed"] == today and code in record["runs"]["evidence-hunt"]["text"]
        assert record["streaks"]["evidence-hunt"]["count"] == 1

        # the same house again counts nothing more, and the button now says it is done
        open_practice(page, page_name)
        page.click("#practice-today button")
        assert page.evaluate(SOLVE) == code
        assert page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1')).streaks['evidence-hunt'].count") == 1
        open_practice(page, page_name)
        assert "Today's run done" in page.inner_text("#practice-today")
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        browser.close()
    assert errors == []


def test_fy60_the_todays_run_button_never_prints_a_streak():
    """FY-60: the pledge bans streaks, so the game asks the shared button to leave its streak line out."""
    today = (ROOT / "games" / "evidence-hunt" / "today.js").read_text(encoding="utf-8")
    seed = (ROOT / "shared" / "seed.js").read_text(encoding="utf-8")
    assert "hideStreak: true" in today
    assert "opts.hideStreak" in seed
