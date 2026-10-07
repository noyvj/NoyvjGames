"""The hub's leaderboards.html (planning/TODO.md Y-3, without the friends tab) in
headless Chromium, with the whole backend mocked: nothing reaches the live API.
Skipped when Playwright or Chromium is not installed."""

import json
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "http://harness.test"
API = "https://noyvjgames.fastapicloud.dev"

REGISTRY = {"min_visible": 3, "top_n": 10, "boards": [
    {"game_id": "canopy", "board": "community_investment", "label": "Daily community investment", "order": "desc",
     "windows": ["daily", "weekly", "alltime"], "integer": False, "unit": "growth", "default_window": "alltime"},
    {"game_id": "last-line", "board": "endless_best_wave", "label": "Endless: best wave", "order": "desc",
     "windows": ["weekly", "alltime"], "integer": True, "unit": "waves", "default_window": "alltime"},
]}


def board(window, entries, suppressed=False, mine=None, period="all"):
    return {"window": window, "period": period, "suppressed": suppressed, "min_visible": 3, "entries": entries,
            "mine": mine, "shows_username": False}


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


def open_page(browser, signed_in=False, registry=REGISTRY, board_status=200):
    calls = []

    def api(route, request):
        url = urlparse(request.url)
        body = request.post_data_json if request.post_data else None
        calls.append((request.method, url.path, parse_qs(url.query), body))
        cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}
        if request.method == "OPTIONS":
            return route.fulfill(status=204, headers=cors)
        if url.path == "/leaderboard":
            return route.fulfill(status=200 if registry else 500, headers=cors, content_type="application/json", body=json.dumps(registry or {}))
        if url.path.startswith("/leaderboard/"):
            window = parse_qs(url.query).get("window", ["alltime"])[0]
            if board_status != 200:
                return route.fulfill(status=board_status, headers=cors, content_type="application/json", body="{}")
            if url.path.endswith("/endless_best_wave"):
                data = board(window, [{"rank": 1, "name": "Player 7F2Q", "score": 12, "detail": "seed 1", "you": False}] * 3)
            elif window == "daily":
                data = board("daily", [], suppressed=True, period="2026-10-08",
                             mine={"score": 4.5, "detail": "", "rank": 1, "name": "Player 9ABC"})
            else:
                data = board(window, [{"rank": 1, "name": "<b>bold</b>", "score": 150.4, "detail": "", "you": True}] * 3)
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps(data))
        if url.path == "/users/me/scores":
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps({
                "show_username": True,
                "scores": [{"game_id": "canopy", "board": "community_investment", "label": "Daily community investment", "unit": "growth",
                            "window": "alltime", "period": "all", "score": 150.4, "detail": "", "rank": 2}]}))
        return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps({"show_username": False}))

    context = browser.new_context(viewport={"width": 1000, "height": 900})
    page = context.new_page()

    def serve(route, request):
        file = ROOT / (request.url[len(ORIGIN):].split("?")[0].lstrip("/") or "index.html")
        if file.is_file():
            return route.fulfill(status=200, content_type=mimetypes.guess_type(file.name)[0] or "text/plain", body=file.read_bytes())
        return route.fulfill(status=404, body="")

    page.route("**/*", lambda route, request: route.abort())
    page.route(f"{ORIGIN}/**", serve)
    page.route(f"{API}/**", api)
    page.add_init_script(
        "localStorage.clear();" + ("localStorage.setItem('hub_bearer_token', 'test-token');" if signed_in else "")
    )
    page.goto(f"{ORIGIN}/leaderboards.html")
    page.wait_for_timeout(500)
    return context, page, calls


def test_lists_the_registered_games_and_shows_the_default_board(browser):
    context, page, calls = open_page(browser)
    assert page.locator("#lb-game option").all_inner_texts() == ["Canopy", "Last Line"]
    assert page.locator("#lb-board option").all_inner_texts() == ["Daily community investment"]
    assert page.locator("#lb-title").inner_text() == "Canopy: Daily community investment"
    assert [b.inner_text() for b in page.locator("#lb-windows button").all()] == ["Today", "This week", "✓ All time"]
    assert "Sign in on the hub" in page.locator("#lb-status").inner_text()
    assert page.locator("#lb-account").is_hidden()
    assert page.locator("#lb-play").get_attribute("href") == "games/canopy/index.html"
    context.close()


def test_switching_windows_and_games_requests_the_right_board(browser):
    context, page, calls = open_page(browser)
    page.locator("#lb-windows button").nth(0).click()
    page.wait_for_timeout(250)
    assert "at least 3 players" in page.locator("#lb-message").inner_text()
    assert page.locator("#lb-rows li").count() == 0
    assert "Period 2026-10-08 (UTC)" in page.locator("#lb-period").inner_text()
    assert "Your entry: 4.5 growth, rank 1, shown as Player 9ABC." in page.locator("#lb-mine").inner_text()
    page.select_option("#lb-game", "last-line")
    page.wait_for_timeout(250)
    assert [b.inner_text() for b in page.locator("#lb-windows button").all()] == ["This week", "✓ All time"]
    assert page.locator("#lb-rows li").all_inner_texts() == ["Player 7F2Q: 12 waves (seed 1)"] * 3
    assert any(c[1] == "/leaderboard/last-line/endless_best_wave" and c[2]["window"] == ["alltime"] for c in calls)
    context.close()


def test_server_text_is_shown_as_text_and_your_row_is_marked(browser):
    context, page, calls = open_page(browser, signed_in=True)
    assert page.locator("#lb-rows li").first.inner_text() == "<b>bold</b> (you): 150 growth"
    assert page.locator("#lb-rows b").count() == 0
    context.close()


def test_a_signed_in_player_sees_their_scores_and_the_one_privacy_switch(browser):
    context, page, calls = open_page(browser, signed_in=True)
    assert page.locator("#lb-account").is_visible()
    assert page.locator("#lb-show-username").is_checked()
    assert page.locator("#lb-my-scores li").all_inner_texts() == [
        "Canopy, Daily community investment, All time: 150 growth, rank 2"]
    page.locator("#lb-show-username").uncheck()
    page.wait_for_timeout(300)
    puts = [c for c in calls if c[0] == "PUT" and c[1] == "/users/me/leaderboard-privacy"]
    assert puts and puts[0][1] == "/users/me/leaderboard-privacy" and puts[0][3] == {"show_username": False}
    context.close()


def test_an_unreachable_backend_says_so(browser):
    context, page, _ = open_page(browser, registry=None)
    assert "Couldn't load the boards" in page.locator("#lb-status").inner_text()
    context.close()
    context, page, _ = open_page(browser, board_status=500)
    assert "unavailable" in page.locator("#lb-message").inner_text()
    context.close()


def test_the_page_is_usable_at_phone_width(browser):
    context, page, _ = open_page(browser)
    page.set_viewport_size({"width": 360, "height": 740})
    page.wait_for_timeout(150)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    heights = page.evaluate("[...document.querySelectorAll('#lb-windows button, #lb-controls select')].map((e) => e.getBoundingClientRect().height)")
    assert heights and min(heights) >= 44
    context.close()
