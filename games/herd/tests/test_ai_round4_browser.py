"""Live pass over the Round 4 Herd view ideas: one Pyodide boot per page (phone Classic, wide Classic,
Desktop) and real clicks. The wiring is pinned without a browser in test_ai_round4_audit.py."""

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
READY = ("(() => { const s = document.querySelector('#engine-status');"
         " if (s) return s.textContent === '' || s.hidden;"
         " return !!window.pyodide && !!window.pyodide.globals.get('get_state'); })()")


@pytest.fixture(scope="module")
def base():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://localhost:%d/games/herd/" % port
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _open(browser, base, page_name, width, height):
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + page_name + "#play")
    page.wait_for_function(READY, timeout=90000)
    page.wait_for_timeout(1000)
    return ctx, page, errors


@pytest.fixture(scope="module")
def phone(browser, base):
    ctx, page, errors = _open(browser, base, "index.html", 360, 740)
    yield page, errors
    ctx.close()


@pytest.fixture(scope="module")
def wide_classic(browser, base):
    ctx, page, errors = _open(browser, base, "index.html", 1440, 900)
    yield page
    ctx.close()


@pytest.fixture(scope="module")
def desktop(browser, base):
    ctx, page, errors = _open(browser, base, "pc.html", 1440, 900)
    yield page, errors
    ctx.close()


def test_phone_has_no_horizontal_overflow_and_no_script_errors(phone):
    page, errors = phone
    assert page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0
    assert errors == []


def test_wide_classic_page_still_shows_the_levers_and_none_of_the_phone_pieces(wide_classic):
    page = wide_classic
    assert page.is_visible("#grow-herd-button") and page.is_visible("#feed-invest-button")
    for hidden in ("#mobile-top-strip", "#herd-slider-container", "#calm-barn-toggle"):
        assert not page.is_visible(hidden), hidden


def test_phone_top_strip_is_fixed_and_follows_the_round(phone):
    page, _errors = phone
    box = page.locator("#mobile-top-strip").bounding_box()
    assert box["y"] == 0 and box["height"] >= 40
    page.click("#grow-herd-button")
    page.click("#advance-round-button")
    page.wait_for_timeout(500)
    page.evaluate("window.scrollTo(0, 0)")
    text = page.inner_text("#mobile-top-strip")
    assert "Round 2" in text and "Funds: " in text and "Methane: 1" in text
    assert page.inner_text("#mobile-strip-label") == "Stable"


def test_phone_herd_slider_plans_then_buys_the_real_units(phone):
    page, _errors = phone
    herd_now = int(page.inner_text("#herd-display").split(":")[1])
    page.fill("#herd-size-slider", str(herd_now + 2))
    page.wait_for_timeout(300)
    assert page.inner_text("#herd-slider-value") == str(herd_now + 2)
    assert "→" in page.inner_text("#herd-slider-methane")
    assert page.inner_text("#herd-slider-buy-button").startswith("Grow to %d" % (herd_now + 2))
    page.click("#herd-slider-buy-button")
    page.wait_for_timeout(400)
    assert page.inner_text("#herd-display") == "Herd size: %d" % (herd_now + 2)


def test_phone_thermometer_opens_the_methane_breakdown(phone):
    page, _errors = phone
    page.evaluate("window.scrollTo(0, 0)")
    assert page.is_visible("#methane-thermometer")
    assert "Methane" in page.get_attribute("#methane-thermometer", "aria-label")
    page.click("#methane-thermometer")
    page.wait_for_timeout(600)
    assert page.evaluate("document.getElementById('explain-panel').open") is True
    assert page.inner_text("#explain-output").startswith("Methane this round")


def test_phone_lever_shelf_scrolls_sideways_and_keeps_the_levers_reachable(phone):
    page, _errors = phone
    shelf = page.evaluate("(() => { const s = document.getElementById('mobile-lever-shelf');"
                          " return [s.scrollWidth, s.clientWidth, getComputedStyle(s).overflowX]; })()")
    assert shelf[0] > shelf[1] and shelf[2] == "auto"
    for lever in ("#grow-herd-button", "#feed-invest-button", "#caps-invest-button", "#capture-invest-button",
                  "#plant-pivot-invest-button"):
        assert page.locator(lever).count() == 1
    # Advance Round sits right after the shelf
    assert page.evaluate("document.getElementById('mobile-lever-shelf').nextElementSibling.id") == "round-announcer"


def test_phone_calm_barn_leaves_one_word_the_pasture_and_advance_then_exits(phone):
    page, _errors = phone
    page.evaluate("window.scrollTo(0, 0)")
    page.click("#calm-barn-toggle")
    page.wait_for_timeout(300)
    assert page.get_attribute("#calm-barn-toggle", "aria-pressed") == "true"
    assert page.inner_text("#calm-barn-word") == "Healthy farm"
    for shown in ("#calm-barn-word", "#calm-barn-exit", "#advance-round-button", "#pasture-visual"):
        assert page.is_visible(shown), shown
    for gone in ("#grow-herd-button", "#mobile-top-strip", "#methane-thermometer", "#settings-toggle-button"):
        assert not page.is_visible(gone), gone
    assert page.evaluate("localStorage.getItem('herd-calm-barn')") == "true"
    round_before = page.inner_text("#round-display")
    page.click("#advance-round-button")
    page.wait_for_timeout(400)
    assert page.inner_text("#round-display") != round_before  # the round still advances from the calm barn
    page.click("#calm-barn-exit")
    page.wait_for_timeout(300)
    assert page.is_visible("#grow-herd-button")
    assert page.evaluate("localStorage.getItem('herd-calm-barn')") is None


def test_desktop_hold_i_labels_the_pasture_and_clears_on_release(desktop):
    page, errors = desktop
    for _ in range(3):
        page.click("#grow-herd-button")
    page.keyboard.down("i")
    page.wait_for_timeout(200)
    names = page.evaluate("[...document.querySelectorAll('.pasture-label strong')].map(e => e.textContent)")
    assert {"Sky and weather", "Barn", "Fence", "Cows"} <= set(names)
    inside = page.evaluate("""(() => { const box = document.getElementById('pasture-visual').getBoundingClientRect();
        return [...document.querySelectorAll('.pasture-label')].every(l => { const r = l.getBoundingClientRect();
        return r.left >= box.left - 1 && r.right <= box.right + 1 && r.top >= box.top - 1 && r.bottom <= box.bottom + 1; }); })()""")
    assert inside is True
    page.keyboard.up("i")
    page.wait_for_timeout(100)
    assert page.locator(".pasture-label").count() == 0
    assert errors == []


def test_desktop_right_click_menu_buys_pins_and_opens_the_real_windows(desktop):
    page, _errors = desktop
    page.click("#grow-herd-button", button="right")
    assert page.is_visible("#lever-context-menu")
    items = page.evaluate("[...document.querySelectorAll('#lever-context-menu button')].map(b => b.textContent)")
    assert items == ["Buy", "Pin as a goal", "Show cost over time", "Compare with baseline farm"]
    herd = int(page.inner_text("#herd-display").split(":")[1])
    page.click("#lever-context-menu [data-action=buy]")
    page.wait_for_timeout(400)
    assert page.inner_text("#herd-display") == "Herd size: %d" % (herd + 1)  # the Grow Herd button, not the x1 stepper
    assert not page.is_visible("#lever-context-menu")
    # Pin: a visible Goal badge that survives in localStorage
    page.click("#caps-invest-button", button="right")
    page.click("#lever-context-menu [data-action=pin]")
    assert page.inner_text("[data-measure=caps] .goal-pinned-badge") == "Goal"
    assert page.evaluate("localStorage.getItem('herd-pinned-goals')") == '["caps"]'
    page.click("#caps-invest-button", button="right")
    assert page.inner_text("#lever-context-menu [data-action=pin]") == "Unpin goal"
    page.keyboard.press("Escape")
    assert not page.is_visible("#lever-context-menu")
    # the menu keeps working after an outside click closed it once
    page.click("#caps-invest-button", button="right")
    page.mouse.click(5, 500)
    assert not page.is_visible("#lever-context-menu")
    page.click("#feed-invest-button", button="right")
    assert page.is_visible("#lever-context-menu")
    # cost over time: the real lever history window, filtered to this lever
    page.click("#lever-context-menu [data-action=history]")
    page.wait_for_timeout(400)
    assert page.is_visible("#pc-collection-panel")
    assert page.evaluate("document.getElementById('lever-history-filter').value") == "feed"
