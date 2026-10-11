"""The Daily Job in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable). The clock is fixed
by the browser, so the view passes a known date to the engine. Never touches the live backend."""

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
    yield "http://localhost:%d/games/heist-committee/" % port
    server.shutdown()


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900), ("pc.html", 360, 740)])
def test_play_an_archive_day_from_the_calendar(base, page_name, width, height):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.clock.set_fixed_time("2026-10-20T09:00:00Z")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + page_name + "#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function("window.HC && window.HC.view", timeout=90000)
        assert "Day 20" in page.inner_text("#daily-today")
        page.click("[data-testid=heist-daily-archive]")
        assert page.locator("[data-testid=heist-daily-day]:not([disabled])").count() == 20
        page.click("[data-date='2026-10-05']")
        assert page.evaluate("HC.view.phase") == "scout" and page.evaluate("HC.view.daily.number") == 5
        page.click("[data-testid=heist-to-recruit]")
        assert page.locator("[data-testid^=heist-check-]").count() == 0          # every quirk is already on the file
        for cid in page.evaluate("HC.view.offer.map(c => c.id)")[:5]:
            page.click("[data-testid=heist-hire-%s]" % cid)
        page.click("[data-testid=heist-confirm-crew]")
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        page.evaluate("HC.send({action: 'start_heist'})")
        page.evaluate("HC.send({action: 'skip'})")
        page.evaluate("HC.send({action: 'finish'})")
        assert "Daily Job 5" in page.inner_text("[data-testid=heist-daily-result]")
        page.click("[data-testid=heist-back-to-board]")
        assert "Played 1 of 20" in page.inner_text("[data-testid=heist-daily-tally]")
        assert page.evaluate("HC.view.cash") == 300 and page.evaluate("HC.view.reputation") == 0
        page.reload()
        page.wait_for_function("window.HC && window.HC.view", timeout=90000)
        assert "Played 1 of 20" in page.inner_text("[data-testid=heist-daily-tally]")
        browser.close()
    assert errors == []


def _play_daily_to_payout(page, date):
    page.evaluate("HC.send({action: 'daily_open', date: '%s'})" % date)
    page.click("[data-testid=heist-to-recruit]")
    for cid in page.evaluate("HC.view.offer.map(c => c.id)")[:5]:
        page.click("[data-testid=heist-hire-%s]" % cid)
    page.click("[data-testid=heist-confirm-crew]")
    page.evaluate("HC.send({action: 'start_heist'})")
    page.evaluate("HC.send({action: 'skip'})")
    page.evaluate("HC.send({action: 'finish'})")
    assert page.evaluate("HC.view.phase") == "payout"


@pytest.mark.parametrize("width,height", [(1440, 900), (360, 740)])
def test_todays_job_is_told_to_the_shared_daily_record_and_an_archive_job_is_not(base, width, height):
    """Z-5b: finishing TODAY's Daily Job writes noyvj-daily-v1 once; an older job from the calendar never does."""
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.clock.set_fixed_time("2026-10-20T09:00:00Z")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "index.html#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function("window.HC && window.HC.view", timeout=90000)
        _play_daily_to_payout(page, "2026-10-05")
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None
        page.click("[data-testid=heist-back-to-board]")
        _play_daily_to_payout(page, "2026-10-20")
        record = page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1'))")
        assert record["date"] == "2026-10-20" and list(record["runs"]) == ["heist-committee"]
        assert "best payout" in record["runs"]["heist-committee"]["text"]
        assert record["streaks"]["heist-committee"]["count"] == 1
        browser.close()
    assert errors == []


@pytest.mark.parametrize("width,height", [(1440, 900), (360, 740)])
def test_the_career_seed_is_given_shown_copied_and_can_be_started_from(base, width, height):
    """Z-1c: a fresh career gets a shareable seed, a typed seed gives the same board every time, and it survives a reload."""
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "index.html#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function("window.HC && window.HC.view && window.HC.view.career_seed_text", timeout=90000)
        first = page.evaluate("HC.view.career_seed_text")
        assert first.startswith("HEISTCOMMITT-") and page.evaluate("NoyvjSeed.current()") == first
        assert first in page.inner_text("[data-testid=heist-career-seed]")
        page.click("[data-testid=heist-career-seed] .noyvj-seed-copy button")
        assert page.evaluate("navigator.clipboard.readText()") == first

        def board_for(text):
            page.fill("[data-testid=heist-career-seed] input", text)
            page.click("[data-testid=heist-career-seed] button[type=submit]")
            confirm = page.locator("button:has-text('Start over')")
            if confirm.count():
                confirm.first.click()
            full = text.upper() if "-" in text else "HEISTCOMMITT-" + text.upper()
            page.wait_for_function("HC.view.career_seed_text === %s" % repr(full), timeout=10000)
            return page.evaluate("HC.view.board.map(t => t.id)")

        a = board_for("k7f2q")
        assert page.evaluate("HC.view.career_seed_text") == "HEISTCOMMITT-K7F2Q"
        b = board_for("HEISTCOMMITT-K7F2Q")
        assert a == b
        page.fill("[data-testid=heist-career-seed] input", "TIDE-K7F2Q")
        page.click("[data-testid=heist-career-seed] button[type=submit]")
        assert "for TIDE" in page.inner_text("[data-testid=heist-career-seed] .noyvj-seed-error")
        page.reload()
        page.wait_for_function("window.HC && window.HC.view", timeout=90000)
        assert page.evaluate("HC.view.career_seed_text") == "HEISTCOMMITT-K7F2Q"
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        browser.close()
    assert errors == []
