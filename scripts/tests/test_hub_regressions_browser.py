"""Regression tests for bugs found by the hub QA pass (QA-1/QA-2, 2026-10-08). Each one drives the
real page in headless Chromium with the backend answered by the test."""

from hub_browser_fixtures import chromium, harness  # noqa: F401  (pytest fixtures)

STORAGE_BLOCKED = "Object.defineProperty(window,'localStorage',{get(){throw new DOMException('denied','SecurityError')}});"
SIGNED_IN = "localStorage.setItem('hub_bearer_token','tok');localStorage.setItem('hub_account_username','tester');"


def test_admin_page_escapes_quotes_in_usernames(harness):
    """A username is free text and is also placed inside quoted attributes (aria-label, data-id):
    a quote in it used to break out of the attribute and run script on the owner's admin page."""
    evil = 'x" autofocus onfocus="window.__pwned=1" data-x="'
    h = harness(init_scripts=[SIGNED_IN])
    h.api_responses[("GET", "/users/me")] = (200, {"username": "noyvj"})
    h.api_responses[("GET", "/admin/users")] = (200, [{
        "id": evil, "username": evil, "email": evil, "save_count": 1,
        "created_at": "2026-10-01T00:00:00Z", "is_test": False}])
    page = h.goto("/admin.html")
    page.wait_for_selector(".test-flag", state="attached")
    assert page.evaluate("window.__pwned || 0") == 0
    assert page.evaluate("document.querySelector('.test-flag').hasAttribute('onfocus')") is False
    assert evil in page.evaluate("document.querySelector('.test-flag').getAttribute('aria-label')")
    assert page.evaluate("escapeHtml(\"a'b\\\"c<d>&\")") == "a&#39;b&quot;c&lt;d&gt;&amp;"


def test_hub_script_survives_blocked_storage(harness):
    """With site storage blocked (some privacy modes) the hub script used to throw at the sign-in
    check and never reach the feedback list, install banner or visit counter."""
    h = harness(init_scripts=[STORAGE_BLOCKED])
    h.api_responses[("GET", "/feedback")] = (200, [{"rating": 5, "comment": "fine"}])
    page = h.goto("/index.html")
    page.wait_for_function("document.getElementById('site-feedback-list').textContent.includes('fine')")
    assert h.errors == []
    assert page.evaluate("document.getElementById('pageview-count').textContent") != ""
    assert page.evaluate("document.getElementById('account-signed-out').hidden") is False


def test_achievements_page_survives_blocked_storage(harness):
    h = harness(init_scripts=[STORAGE_BLOCKED])
    page = h.goto("/achievements.html")
    page.wait_for_selector(".ach-game", state="attached")
    assert h.errors == []


def test_signing_in_asks_for_the_saves_list_once(harness):
    """The saves list, Continue Playing and the achievements dashboard all need GET /users/me/saves;
    they share one request now instead of sending three."""
    h = harness(init_scripts=[SIGNED_IN, "localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"])
    h.api_responses[("GET", "/users/me/saves")] = (200, [{
        "game_id": "canopy", "save_code": "ABC", "updated_at": "2026-10-01T00:00:00Z",
        "save_data": {"achievements_earned": ["a"]}}])
    page = h.goto("/index.html")
    page.wait_for_function("document.getElementById('continue-playing-list').textContent.includes('Canopy')")
    page.wait_for_function("document.getElementById('account-achievements-dashboard').textContent.includes('All games')")
    assert page.evaluate("document.getElementById('account-my-saves').textContent").startswith("canopy: ABC")
    assert [c for c in h.api_calls if c[0] == "GET" and c[1] == "/users/me/saves"].__len__() == 1


def test_community_highlight_wording_does_not_say_only(harness):
    """'Only 90% of players' read wrongly for common achievements; the sentence is neutral now."""
    h = harness(init_scripts=["localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"])
    h.api_responses[("GET", "/stats/achievements")] = (200, {"games": {"canopy": {"save_count": 5, "achievements": {"first_harvest": {"earned_pct": 90}}}}})
    h.api_responses[("GET", "/stats/games")] = (200, {"games": {}})
    page = h.goto("/index.html")
    page.wait_for_function("document.getElementById('community-highlights-text').textContent.includes('earned')")
    text = page.evaluate("document.getElementById('community-highlights-text').textContent")
    assert text == '90% of Canopy players have earned "first harvest" so far.'


def test_rating_responses_resort_the_grid_once(harness):
    """Each card loads its own ratings; the grid is re-sorted once for the burst, not once per card."""
    h = harness(init_scripts=["localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"])
    for slug in ("sol", "canopy", "grid", "tide", "aftermath", "herd", "thaw", "loop", "drift",
                 "champ-de-mots", "continuum", "signal", "lexis", "trade-empire"):
        h.api_responses[("GET", f"/ratings/{slug}")] = (200, [{"stars": 4, "comment": None}])
    h.page.add_init_script("window.__sorts = 0; document.addEventListener('DOMContentLoaded', () => {"
                           "const g = document.getElementById('game-grid'); const a = g.append.bind(g);"
                           "g.append = (...n) => { window.__sorts += 1; return a(...n); }; });")
    page = h.goto("/index.html")
    page.wait_for_function("document.querySelectorAll('.title-card[data-review-count=\"1\"]').length === 14")
    page.wait_for_timeout(300)
    # one initial sort plus one for the burst of ratings; never one per card
    assert page.evaluate("window.__sorts") <= 3


def _log_tail_route(page, entries_by_log):
    """Answer the dev-log requests like a server that honours Range: 206 with a short tail."""
    seen_ranges = []

    def serve(route, request):
        name = request.url.rsplit("/", 1)[-1]
        seen_ranges.append((name, request.headers.get("range")))
        body = "...cut mid-sentence of an older entry\n" + "".join(
            f"### {date}\n**Did:** something\n\n" for date in entries_by_log[name])
        route.fulfill(status=206, content_type="text/markdown", body=body,
                      headers={"content-range": "bytes 0-99/500000"})

    page.route("**/BCM114-DEV-LOG.md", serve)
    page.route("**/BCM206-DEV-LOG.md", serve)
    return seen_ranges


def test_whats_new_badge_asks_for_the_log_tails_only(harness):
    """The nav badge needs only the newest headings, not the half megabyte of both dev logs."""
    h = harness(init_scripts=["localStorage.setItem('hub_whats_new_seen','2026-10-05');"
                              "localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"])
    ranges = _log_tail_route(h.page, {
        "BCM114-DEV-LOG.md": ["2026-10-04", "2026-10-06", "2026-10-07"],
        "BCM206-DEV-LOG.md": ["2026-10-01", "2026-10-08"]})
    page = h.goto("/index.html")
    page.wait_for_function("!document.getElementById('whats-new-badge').hidden", timeout=8000)
    assert page.evaluate("document.getElementById('whats-new-badge').textContent") == "3"
    assert sorted(ranges) == [("BCM114-DEV-LOG.md", "bytes=-24576"), ("BCM206-DEV-LOG.md", "bytes=-24576")]


def test_whats_new_badge_says_plus_when_the_tail_may_hide_more(harness):
    h = harness(init_scripts=["localStorage.setItem('hub_whats_new_seen','2026-10-05');"
                              "localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"])
    _log_tail_route(h.page, {"BCM114-DEV-LOG.md": ["2026-10-06", "2026-10-07"], "BCM206-DEV-LOG.md": ["2026-10-04"]})
    page = h.goto("/index.html")
    page.wait_for_function("!document.getElementById('whats-new-badge').hidden", timeout=8000)
    assert page.evaluate("document.getElementById('whats-new-badge').textContent") == "2+"
