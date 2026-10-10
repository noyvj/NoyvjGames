"""shared/leaderboard.js in headless Chromium (Playwright), planning/TODO.md W-5.

Covers the new general boards (NoyvjLeaderboard.addBoard / data-api="scores"):
window tabs, anonymous names and the suppression note, the opt-in and username
switches, what report() sends and when, period keys that agree with the backend's
(app/boards.py), and that server text is never written as markup. Also pins the
original one-script-per-board form (SOL, Signal, Aftermath, Herd) as unchanged.

Every API call is answered by a mock inside the page's network layer: nothing
here can reach the live backend (an abort-all route is registered first).
Skipped when Playwright or Chromium is not installed."""

import json
import mimetypes
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
import boards  # noqa: E402  (pure module: no database needed)

ORIGIN = "http://harness.test"
API = "https://noyvjgames.fastapicloud.dev"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body><div id="leaderboard-mount"></div>
<script src="/shared/hub-auth.js"></script>
<script src="/shared/leaderboard.js"></script></body></html>"""


class Api:
    """A stateful stand-in for the backend: records every call, answers from `responses`."""

    def __init__(self):
        self.calls = []
        self.board = {}      # (window) -> response body for GET /leaderboard/...
        self.legacy = {"entries": [], "mine": None}
        self.board_status = 200

    def handle(self, route, request):
        url = urlparse(request.url)
        body = request.post_data_json if request.post_data else None
        self.calls.append({"method": request.method, "path": url.path, "query": parse_qs(url.query), "body": body,
                           "auth": request.headers.get("authorization")})
        cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}
        if request.method == "OPTIONS":
            return route.fulfill(status=204, headers=cors)
        path = url.path
        if request.method == "GET" and path.startswith("/leaderboard/"):
            window = parse_qs(url.query).get("window", ["alltime"])[0]
            if self.board_status != 200:
                return route.fulfill(status=self.board_status, headers=cors, content_type="application/json", body="{}")
            data = self.board.get(window, self.board.get("default", {}))
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps(data))
        if request.method == "GET" and path.startswith("/leaderboards/"):
            return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps(self.legacy))
        return route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps({"accepted": True, "removed": 1}))

    def to(self, method, path_prefix):
        return [c for c in self.calls if c["method"] == method and c["path"].startswith(path_prefix)]


def board_body(entries=(), suppressed=False, mine=None, shows_username=False, window="alltime", min_visible=3):
    return {
        "game_id": "g", "board": "b", "window": window, "suppressed": suppressed, "min_visible": min_visible,
        "entries": list(entries), "mine": mine, "shows_username": shows_username, "total": None if suppressed else len(entries),
    }


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


def open_page(browser, api, signed_in=True, store=None, html=PAGE):
    context = browser.new_context(viewport={"width": 1000, "height": 800})
    page = context.new_page()

    def serve(route, request):
        url = request.url[len(ORIGIN):].split("?")[0]
        if url == "/t.html":
            return route.fulfill(status=200, content_type="text/html", body=html)
        file = ROOT / url.lstrip("/")
        if file.is_file():
            return route.fulfill(status=200, content_type=mimetypes.guess_type(file.name)[0] or "text/plain", body=file.read_bytes())
        return route.fulfill(status=404, body="")

    page.route("**/*", lambda route, request: route.abort())   # nothing leaves the harness unless matched below
    page.route(f"{ORIGIN}/**", serve)
    page.route(f"{API}/**", api.handle)
    page.goto(f"{ORIGIN}/t.html")
    seed = dict(store or {})
    if signed_in:
        seed["hub_bearer_token"] = "test-token"
    page.evaluate("(s) => { localStorage.clear(); for (const k in s) localStorage.setItem(k, s[k]); }", seed)
    return context, page


def add_board(page, **overrides):
    config = {"game": "g", "board": "b", "title": "Test board", "unit": "pts", "order": "desc",
              "windows": ["daily", "weekly", "alltime"], "mount": "#leaderboard-mount"}
    config.update(overrides)
    page.evaluate("(c) => NoyvjLeaderboard.addBoard(c)", config)


def open_panel(page):
    page.locator(".noyvj-leaderboard summary").click()
    page.wait_for_timeout(150)


# ---- period keys agree with the backend -----------------------------------------------

def test_period_keys_match_the_backend_on_a_sweep_of_moments(browser):
    context, page = open_page(browser, Api())
    start = datetime(2024, 12, 20, tzinfo=timezone.utc)
    stamps = []
    moment = start
    while moment < datetime(2030, 2, 1, tzinfo=timezone.utc):
        stamps.append(int(moment.timestamp() * 1000))
        moment += timedelta(hours=53)   # drifts through every hour of the day and every weekday
    for edge in ("2026-12-31T23:59:59", "2027-01-01T00:00:00", "2027-01-03T23:59:59", "2027-01-04T00:00:00",
                 "2026-10-11T23:59:59", "2026-10-12T00:00:00", "2020-12-31T12:00:00", "2021-01-03T12:00:00"):
        stamps.append(int(datetime.fromisoformat(edge).replace(tzinfo=timezone.utc).timestamp() * 1000))
    js = page.evaluate(
        "(stamps) => stamps.map((ms) => ['daily', 'weekly', 'alltime'].map((w) => NoyvjLeaderboard.periodKey(w, ms)))", stamps
    )
    expected = [[boards.window_period(w, ms / 1000) for w in ("daily", "weekly", "alltime")] for ms in stamps]
    assert js == expected
    assert len(stamps) > 800
    context.close()


# ---- the panel -----------------------------------------------------------------------------

def test_the_panel_has_a_tab_per_declared_window_and_loads_the_default(browser):
    api = Api()
    api.board["default"] = board_body([{"rank": 1, "name": "Player 7F2Q", "score": 42, "detail": "", "you": False}] * 3)
    context, page = open_page(browser, api)
    add_board(page, windows=["weekly", "alltime"])
    open_panel(page)
    buttons = page.locator(".noyvj-lb-windows button")
    assert [b.inner_text() for b in buttons.all()] == ["This week", "✓ All time"]
    assert buttons.nth(1).get_attribute("aria-pressed") == "true" and buttons.nth(0).get_attribute("aria-pressed") == "false"
    assert api.to("GET", "/leaderboard/g/b")[0]["query"]["window"] == ["alltime"]
    rows = page.locator(".noyvj-leaderboard-list li").all_inner_texts()
    assert rows == ["Player 7F2Q: 42 pts"] * 3
    buttons.nth(0).click()
    page.wait_for_timeout(150)
    assert api.to("GET", "/leaderboard/g/b")[-1]["query"]["window"] == ["weekly"]
    assert page.locator(".noyvj-lb-windows button").nth(0).inner_text() == "✓ This week"
    context.close()


def test_a_board_below_the_minimum_says_so_and_still_shows_your_own_entry(browser):
    api = Api()
    api.board["default"] = board_body([], suppressed=True, mine={"score": 9, "detail": "", "rank": 2, "name": "Player 4K8M"})
    context, page = open_page(browser, api)
    add_board(page)
    open_panel(page)
    status = page.locator(".noyvj-leaderboard .comparison-message").first.inner_text()
    assert "at least 3 players" in status
    assert page.locator(".noyvj-leaderboard-list li").count() == 0
    assert "Your entry: 9 pts, rank 2, shown as Player 4K8M." in page.locator(".noyvj-leaderboard").inner_text()
    context.close()


def test_you_versus_everyone_sentence_uses_rank_and_total_and_stays_quiet_without_them(browser):
    """K-10: 'ahead of about N% of the other players' only when the server reports a total of at least two."""
    cases = [
        (4, 5, "You are ahead of about 25% of the other 4 players on this board."),
        (1, 11, "You are ahead of about 100% of the other 10 players on this board."),
        (3, 3, "You are ahead of about 0% of the other 2 players on this board."),
        (1, 2, "You are ahead of about 100% of the other 1 player on this board."),
        (1, 1, None),
        (9, 4, None),
        (2, None, None),
    ]
    for rank, total, expected in cases:
        api = Api()
        body = board_body([], mine={"score": 9, "detail": "", "rank": rank, "name": "Player 4K8M"})
        body["suppressed"] = total is None
        body["total"] = total
        api.board["default"] = body
        context, page = open_page(browser, api)
        add_board(page)
        open_panel(page)
        text = page.locator(".noyvj-leaderboard").inner_text()
        assert "Your entry: 9 pts, rank %d, shown as Player 4K8M." % rank in text
        assert ("ahead of about" in text) == (expected is not None)
        if expected:
            assert expected in text
        context.close()


def test_your_own_row_is_marked_in_words_not_only_style(browser):
    api = Api()
    api.board["default"] = board_body([
        {"rank": 1, "name": "Player AAAA", "score": 5, "detail": "", "you": False},
        {"rank": 2, "name": "Player BBBB", "score": 4, "detail": "seed 7", "you": True},
        {"rank": 3, "name": "Player CCCC", "score": 3, "detail": "", "you": False},
    ])
    context, page = open_page(browser, api)
    add_board(page)
    open_panel(page)
    assert page.locator(".noyvj-leaderboard-list li").all_inner_texts() == [
        "Player AAAA: 5 pts", "Player BBBB (you): 4 pts (seed 7)", "Player CCCC: 3 pts"]
    context.close()


def test_server_text_is_never_written_as_markup(browser):
    api = Api()
    evil = '<img src=x onerror="window.pwned=1">'
    api.board["default"] = board_body([{"rank": 1, "name": evil, "score": 1, "detail": evil, "you": False}] * 3)
    context, page = open_page(browser, api)
    add_board(page, title=evil)
    open_panel(page)
    assert page.locator(".noyvj-leaderboard img").count() == 0
    assert page.evaluate("window.pwned") is None
    assert evil in page.locator(".noyvj-leaderboard-list li").first.inner_text()
    assert evil in page.locator(".noyvj-leaderboard summary").inner_text()
    context.close()


def test_signed_out_players_see_the_board_but_not_the_switches(browser):
    api = Api()
    api.board["default"] = board_body([{"rank": 1, "name": "Player AAAA", "score": 5, "detail": "", "you": False}] * 3)
    context, page = open_page(browser, api, signed_in=False)
    add_board(page)
    open_panel(page)
    assert page.locator(".noyvj-leaderboard-optin").first.is_hidden()
    assert page.locator(".noyvj-leaderboard-optin").nth(1).is_hidden()
    assert "Sign in on the hub" in page.locator(".noyvj-leaderboard").inner_text()
    assert api.calls and all(c["auth"] is None for c in api.calls)
    context.close()


def test_an_unreachable_backend_shows_a_short_unavailable_line(browser):
    api = Api()
    api.board_status = 500
    context, page = open_page(browser, api)
    add_board(page)
    open_panel(page)
    assert "unavailable" in page.locator(".noyvj-leaderboard .comparison-message").first.inner_text()
    context.close()


def test_declarative_script_tag_mounts_a_general_board(browser):
    api = Api()
    api.board["default"] = board_body([{"rank": 1, "name": "Player AAAA", "score": 5, "detail": "", "you": False}] * 3)
    html = PAGE.replace(
        '<script src="/shared/leaderboard.js"></script>',
        '<script src="/shared/leaderboard.js" data-api="scores" data-game-id="g" data-board="b" data-order="asc" '
        'data-title="Fastest" data-unit="s" data-windows="weekly, alltime" data-mount="#leaderboard-mount"></script>',
    )
    context, page = open_page(browser, api, html=html)
    open_panel(page)
    assert [b.inner_text() for b in page.locator(".noyvj-lb-windows button").all()] == ["This week", "✓ All time"]
    assert "Community leaderboard: Fastest" in page.locator("summary").inner_text()
    assert page.evaluate("NoyvjLeaderboard._boards['g/b'].order") == "asc"
    context.close()


def test_buttons_are_big_enough_to_tap(browser):
    api = Api()
    api.board["default"] = board_body([])
    context, page = open_page(browser, api)
    add_board(page)
    open_panel(page)
    heights = page.evaluate("[...document.querySelectorAll('.noyvj-lb-windows button')].map((b) => b.getBoundingClientRect().height)")
    assert len(heights) == 3 and min(heights) >= 44
    context.close()


# ---- opt-in and the username switch ------------------------------------------------------

def test_nothing_is_sent_until_the_player_opts_in_and_the_best_is_remembered(browser):
    api = Api()
    api.board["default"] = board_body([])
    context, page = open_page(browser, api)
    add_board(page)
    sent = page.evaluate("NoyvjLeaderboard.report('g', 'b', 50, 'run 1')")
    assert sent is False
    assert api.to("POST", "/scores") == []
    assert page.evaluate("NoyvjLeaderboard.isOptedIn('g', 'b')") is False
    context.close()


def test_ticking_opt_in_sends_what_the_player_already_earned_one_window_at_a_time(browser):
    api = Api()
    api.board["default"] = board_body([])
    context, page = open_page(browser, api)
    add_board(page)
    page.evaluate("NoyvjLeaderboard._setNow(() => Date.UTC(2026, 9, 8, 12))")
    page.evaluate("NoyvjLeaderboard.report('g', 'b', 50, 'run 1')")
    open_panel(page)
    page.locator(".noyvj-leaderboard-optin input").first.check()
    page.wait_for_timeout(300)
    posts = api.to("POST", "/scores")
    assert [p["body"]["windows"] for p in posts] == [["daily"], ["weekly"], ["alltime"]]
    for p in posts:
        assert p["body"] == {"game": "g", "board": "b", "score": 50, "detail": "run 1", "opt_in": True, "windows": p["body"]["windows"]}
        assert p["auth"] == "Bearer test-token"
    assert page.evaluate("NoyvjLeaderboard.isOptedIn('g', 'b')") is True
    context.close()


def test_a_stale_daily_best_is_not_resent_as_todays_when_opting_in_later(browser):
    api = Api()
    api.board["default"] = board_body([])
    context, page = open_page(browser, api)
    add_board(page)
    page.evaluate("NoyvjLeaderboard._setNow(() => Date.UTC(2026, 9, 1, 12))")
    page.evaluate("NoyvjLeaderboard.report('g', 'b', 50, 'old')")
    page.evaluate("NoyvjLeaderboard._setNow(() => Date.UTC(2026, 9, 20, 12))")   # weeks later
    open_panel(page)
    page.locator(".noyvj-leaderboard-optin input").first.check()
    page.wait_for_timeout(300)
    assert [p["body"]["windows"] for p in api.to("POST", "/scores")] == [["alltime"]]
    context.close()


def test_unticking_opt_in_deletes_the_players_rows(browser):
    api = Api()
    api.board["default"] = board_body([])
    context, page = open_page(browser, api, store={"lb-optin:g:b": "true"})
    add_board(page)
    open_panel(page)
    box = page.locator(".noyvj-leaderboard-optin input").first
    assert box.is_checked()
    box.uncheck()
    page.wait_for_timeout(300)
    deletes = api.to("DELETE", "/scores/g/b")
    assert len(deletes) == 1 and deletes[0]["auth"] == "Bearer test-token"
    assert page.evaluate("NoyvjLeaderboard.isOptedIn('g', 'b')") is False
    context.close()


def test_report_posts_only_the_windows_that_improved(browser):
    api = Api()
    api.board["default"] = board_body([])
    context, page = open_page(browser, api, store={"lb-optin:g:b": "true"})
    add_board(page)
    page.evaluate("NoyvjLeaderboard._setNow(() => Date.UTC(2026, 9, 8, 12))")   # Thursday
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 100, 'first')") is True
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 60, 'worse')") is False   # beats nothing: no request
    page.evaluate("NoyvjLeaderboard._setNow(() => Date.UTC(2026, 9, 9, 12))")   # Friday, same week
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 60, 'new day')") is True
    page.evaluate("NoyvjLeaderboard._setNow(() => Date.UTC(2026, 9, 12, 12))")   # next Monday: a new week and day
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 30, 'new week')") is True
    page.evaluate("NoyvjLeaderboard._setNow(() => Date.UTC(2026, 9, 12, 13))")
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 150, 'record')") is True
    posts = api.to("POST", "/scores")
    assert [(p["body"]["score"], p["body"]["windows"]) for p in posts] == [
        (100, ["daily", "weekly", "alltime"]),
        (60, ["daily"]),
        (30, ["daily", "weekly"]),
        (150, ["daily", "weekly", "alltime"]),
    ]
    context.close()


def test_an_ascending_board_improves_downwards(browser):
    api = Api()
    context, page = open_page(browser, api, store={"lb-optin:g:b": "true"})
    add_board(page, order="asc", windows=["alltime"])
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 300)") is True
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 400)") is False
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 250)") is True
    assert [p["body"]["score"] for p in api.to("POST", "/scores")] == [300, 250]
    context.close()


def test_a_signed_out_player_who_opted_in_earlier_sends_nothing(browser):
    api = Api()
    context, page = open_page(browser, api, signed_in=False, store={"lb-optin:g:b": "true"})
    add_board(page)
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 10)") is False
    assert api.to("POST", "/scores") == []
    context.close()


def test_a_board_added_without_a_mount_still_reports(browser):
    api = Api()
    context, page = open_page(browser, api, store={"lb-optin:g:b": "true"})
    add_board(page, mount=None, windows=["alltime"])
    assert page.locator(".noyvj-leaderboard").count() == 0
    assert page.evaluate("NoyvjLeaderboard.report('g', 'b', 10, 'x')") is True
    assert api.to("POST", "/scores")[0]["body"]["windows"] == ["alltime"]
    context.close()


def test_non_numbers_are_ignored(browser):
    api = Api()
    context, page = open_page(browser, api, store={"lb-optin:g:b": "true"})
    add_board(page)
    for bad in ("'12'", "NaN", "Infinity", "null", "undefined"):
        assert page.evaluate(f"NoyvjLeaderboard.report('g', 'b', {bad})") is False
    assert api.to("POST", "/scores") == []
    context.close()


def test_the_username_switch_calls_the_one_account_setting(browser):
    api = Api()
    api.board["default"] = board_body([], shows_username=True)
    context, page = open_page(browser, api)
    add_board(page)
    open_panel(page)
    box = page.locator(".noyvj-leaderboard-optin input").nth(1)
    assert box.is_checked()   # reflects the account's saved choice
    box.uncheck()
    page.wait_for_timeout(300)
    puts = api.to("PUT", "/users/me/leaderboard-privacy")
    assert len(puts) == 1 and puts[0]["body"] == {"show_username": False} and puts[0]["auth"] == "Bearer test-token"
    context.close()


def test_add_board_ignores_junk_config(browser):
    context, page = open_page(browser, Api())
    assert page.evaluate("NoyvjLeaderboard.addBoard(null)") is None
    assert page.evaluate("NoyvjLeaderboard.addBoard({ game: 'g' })") is None
    context.close()


# ---- the original form is unchanged -----------------------------------------------------------

LEGACY_TAG = ('<script src="/shared/leaderboard.js" data-game-id="sol" data-board="fastest_completion" data-order="asc" '
              'data-title="fastest full completion" data-unit="s" data-mount="#leaderboard-mount"></script>')


def test_the_original_script_tag_form_still_works_exactly_as_before(browser):
    api = Api()
    api.legacy = {"entries": [{"rank": 1, "username": "alice", "score": 120.5, "detail": "run"},
                              {"rank": 2, "username": "bob", "score": 300, "detail": ""}],
                  "mine": {"score": 300, "detail": "", "rank": 2}}
    html = PAGE.replace('<script src="/shared/leaderboard.js"></script>', LEGACY_TAG)
    context, page = open_page(browser, api, html=html)
    open_panel(page)
    assert api.to("GET", "/leaderboards/sol/fastest_completion")
    assert page.locator(".noyvj-leaderboard-list li").all_inner_texts() == ["alice: 121 s (run)", "bob: 300 s"]   # the original rounding rule
    assert "Your entry: 300 s, rank 2." in page.locator(".noyvj-leaderboard").inner_text()
    assert page.locator(".noyvj-lb-windows").count() == 0   # no window tabs on a legacy board
    assert page.locator(".noyvj-leaderboard-optin").count() == 1
    context.close()


def test_the_original_report_still_uses_put_and_the_legacy_route(browser):
    api = Api()
    html = PAGE.replace('<script src="/shared/leaderboard.js"></script>', LEGACY_TAG)
    context, page = open_page(browser, api, html=html, store={"lb-optin:sol:fastest_completion": "true"})
    assert page.evaluate("NoyvjLeaderboard.report('sol', 'fastest_completion', 500, 'a')") is True
    assert page.evaluate("NoyvjLeaderboard.report('sol', 'fastest_completion', 600, 'slower')") is False   # asc: worse
    assert page.evaluate("NoyvjLeaderboard.report('sol', 'fastest_completion', 400, 'b')") is True
    puts = api.to("PUT", "/leaderboards/sol/fastest_completion")
    assert [p["body"] for p in puts] == [{"score": 500, "detail": "a"}, {"score": 400, "detail": "b"}]
    assert api.to("POST", "/scores") == []
    context.close()


def test_the_original_form_is_not_opted_in_without_the_checkbox(browser):
    api = Api()
    html = PAGE.replace('<script src="/shared/leaderboard.js"></script>', LEGACY_TAG)
    context, page = open_page(browser, api, html=html)
    assert page.evaluate("NoyvjLeaderboard.report('sol', 'fastest_completion', 500)") is False
    assert api.to("PUT", "/leaderboards/") == []
    context.close()


def test_a_legacy_and_a_general_board_can_share_one_page(browser):
    api = Api()
    api.board["default"] = board_body([])
    html = PAGE.replace('<script src="/shared/leaderboard.js"></script>', LEGACY_TAG)
    context, page = open_page(browser, api, html=html, store={"lb-optin:g:b": "true", "lb-optin:sol:fastest_completion": "true"})
    add_board(page, windows=["alltime"])
    page.evaluate("NoyvjLeaderboard.report('sol', 'fastest_completion', 9)")
    page.evaluate("NoyvjLeaderboard.report('g', 'b', 9)")
    assert len(api.to("PUT", "/leaderboards/sol/fastest_completion")) == 1
    assert len(api.to("POST", "/scores")) == 1
    context.close()


def test_the_four_wired_games_still_use_the_original_form():
    for slug, board in (("sol", "fastest_completion"), ("signal", "best_streak"), ("aftermath", "hardest_schedule"), ("herd", "decoupling_gap")):
        html = (ROOT / "games" / slug / "index.html").read_text()
        tag = re.search(r'<script src="\.\./\.\./shared/leaderboard\.js"[^>]*>', html).group(0)
        assert f'data-board="{board}"' in tag and "data-api" not in tag, slug
