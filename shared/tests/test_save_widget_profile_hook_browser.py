"""shared/save-widget.js feeds shared/profile.js (TODO Z-7) and tells shared/report-problem.js the save's
schema version (Z-17), after a SUCCESSFUL save only, without ever delaying or breaking the save.

Real scripts in headless Chromium against the conftest harness: every request to the production API host
is answered by the test, so nothing reaches the network."""

import json

from conftest import page_html

SLOT_ROW = {"save_code": "ABCD-2345", "game_id": "canopy", "slot": 1, "slot_name": "Save 1", "save_data": {},
            "created_at": "2026-10-09T10:00:00+00:00", "updated_at": "2026-10-09T10:00:00+00:00"}


def page(state, extra_head=""):
    pre = f"""
window.pyodide = {{ toPy: (x) => x, globals: {{ get(name) {{
  if (name === "get_state") return () => ({{ toJs: () => ({json.dumps(state)}), destroy() {{}} }});
  return undefined; }} }} }};"""
    head = (f'<script>{pre}</script>{extra_head}'
            '<script src="/shared/report-problem.js" data-game-id="canopy"></script>'
            '<script src="/shared/profile.js" data-game-id="canopy"></script>')
    body = ('<div id="game">Game</div><script src="/shared/hub-auth.js"></script>'
            '<script src="/shared/save-widget.js" data-game-id="canopy"></script>')
    return page_html(head, body)


def open_game(harness, state, signed_in, save_status=200, extra_head=""):
    init = ["localStorage.setItem('hub_bearer_token','tok'); localStorage.setItem('hub_account_username','sam')"] if signed_in else []
    h = harness(init_scripts=init)
    h.api_responses[("GET", "/users/me/saves")] = (200, [])
    h.api_responses[("PUT", "/users/me/saves/canopy/slots/1")] = (save_status, SLOT_ROW if save_status == 200 else {"detail": "no"})
    h.api_responses[("POST", "/saves")] = (save_status, {"save_code": "WXYZ-2345", "game_id": "canopy"})
    h.api_responses[("PUT", "/users/me/profile")] = (200, {})
    h.pages["/t.html"] = page(state, extra_head)
    h.goto("/t.html")
    return h


def save(h):
    h.page.click("[data-testid=save-widget-toggle]")
    h.page.click("[data-testid=save-widget-save]")
    h.page.wait_for_function("document.querySelector('[data-testid=save-widget-save]').textContent === 'Save Progress'")


def profile_posts(h):
    # the profile helper posts from the background: give it a moment to land
    h.page.wait_for_timeout(400)
    return [json.loads(body) for method, path, body in h.api_calls if path == "/users/me/profile" and method == "PUT"]


def test_signed_in_save_posts_the_achievement_count_and_visible_seconds(harness):
    h = open_game(harness, {"v": 1, "achievements_earned": ["a", "b", "c"], "plots": [1, 2]}, signed_in=True)
    h.page.wait_for_timeout(1300)               # the page has now been open and visible for over a second
    save(h)
    posts = profile_posts(h)
    assert len(posts) == 1
    progress = posts[0]["progress"]
    assert progress["game"] == "canopy" and progress["achievements"] == 3
    assert isinstance(progress["add_seconds"], int) and 1 <= progress["add_seconds"] <= 30
    assert "plots" not in json.dumps(posts[0]) and "v" not in progress, "no save data goes to the profile"
    assert "streaks" not in progress


def test_state_without_achievements_posts_only_the_time(harness):
    h = open_game(harness, {"v": 1}, signed_in=True)
    h.page.wait_for_timeout(1300)
    save(h)
    posts = profile_posts(h)
    assert len(posts) == 1 and "achievements" not in posts[0]["progress"] and posts[0]["progress"]["add_seconds"] >= 1


def test_signed_out_save_never_touches_the_profile(harness):
    h = open_game(harness, {"v": 1, "achievements_earned": ["a"]}, signed_in=False)
    h.page.wait_for_timeout(1300)
    save(h)
    assert ("POST", "/saves") in [(m, p) for m, p, _ in h.api_calls]
    assert profile_posts(h) == []
    assert h.page.evaluate("localStorage.getItem('profile-sync:canopy')") is None


def test_a_failed_save_posts_nothing(harness):
    h = open_game(harness, {"v": 1, "achievements_earned": ["a"]}, signed_in=True, save_status=500)
    h.page.wait_for_timeout(1300)
    h.page.click("[data-testid=save-widget-toggle]")
    h.page.click("[data-testid=save-widget-save]")
    h.page.wait_for_function("document.querySelector('[data-testid=save-widget-save]').textContent === 'Save Progress'", timeout=15000)
    assert profile_posts(h) == []


def test_a_profile_helper_that_throws_never_breaks_the_save(harness):
    broken = "<script>window.NoyvjProfile = { update() { throw new Error('profile exploded'); } };</script>"
    h = open_game(harness, {"v": 1, "achievements_earned": ["a"]}, signed_in=True, extra_head=broken)
    save(h)
    assert "Saved at" in h.page.inner_text("[data-testid=save-widget-status]")
    assert ("PUT", "/users/me/saves/canopy/slots/1") in [(m, p) for m, p, _ in h.api_calls]


def test_a_game_without_the_profile_helper_still_saves(harness):
    h = harness()
    h.api_responses[("POST", "/saves")] = (200, {"save_code": "WXYZ-2345", "game_id": "canopy"})
    h.pages["/t.html"] = page_html(
        '<script>window.pyodide = { globals: { get(n) { return n === "get_state" ? () => ({ toJs: () => ({v: 1}), destroy() {} }) : undefined; } } };</script>',
        '<div id="game"></div><script src="/shared/hub-auth.js"></script><script src="/shared/save-widget.js" data-game-id="canopy"></script>')
    h.goto("/t.html")
    save(h)
    assert "Saved at" in h.page.inner_text("[data-testid=save-widget-status]")


def test_the_save_schema_version_reaches_the_report_dialog(harness):
    h = open_game(harness, {"v": 1, "schema_version": 4}, signed_in=False)
    assert h.page.evaluate("NoyvjReport.payload({note: 'x'}).schema_version") is None
    save(h)
    assert h.page.evaluate("NoyvjReport.payload({note: 'x'}).schema_version") == "4"


# ---- where the Report a problem button ends up on the real game pages (Z-17 wiring) ------------------
def test_classic_pages_mount_the_report_button_in_the_toolbar_and_desktop_pages_in_the_menu(harness):
    for slug in ("canopy", "tide", "herd"):
        h = harness()
        h.goto(f"/games/{slug}/index.html?layout=classic")
        h.page.wait_for_selector(".game-toolbar > .noyvj-report-button", state="attached")
        assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-report-button')).position") == "static"
        desktop = harness()
        desktop.goto(f"/games/{slug}/pc.html")
        desktop.page.wait_for_selector("#pc-menu-panel #noyvj-report-menu-button", state="attached")
        assert desktop.page.evaluate("document.querySelector('#noyvj-report-menu-button').closest('.pc-menu-group').querySelector('h3').textContent") == "Help"
        assert desktop.page.query_selector(".noyvj-report-button") is None, "no second, floating button on the Desktop page"
        desktop.page.evaluate("document.getElementById('noyvj-report-menu-button').click()")
        desktop.page.wait_for_selector("dialog.noyvj-report-dialog[open]")
