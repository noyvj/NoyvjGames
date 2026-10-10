"""Browser tests for the hub lobby rework (GN-11 to GN-16): the nav dropdowns, the feedback panel in the nav,
the side-by-side quick strips with the "More for you" fold, picture-only collapsed cards with the rating badge,
and one scrolling row of games per theme.

Same harness as the other hub browser tests: the real pages in headless Chromium, the live backend answered by
the test, every other host refused. Nothing here reaches the network.
"""

import json

from hub_browser_fixtures import chromium, harness  # noqa: F401  (pytest fixtures)

SEEN = "localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"
SIGNED_IN = "localStorage.setItem('hub_bearer_token','t');localStorage.setItem('hub_account_username','u');"
FIRST_SLUGS = ("sol", "canopy", "grid", "tide", "aftermath", "herd", "thaw", "loop", "drift", "champ-de-mots",
               "continuum", "signal", "lexis", "heist-committee", "lighthouse", "pocket-bazaar", "dead-reckoning",
               "logic-gates", "robot-script", "hull-repair", "station-medic", "stranded", "evidence-hunt", "trade-empire")


def hub(harness, *scripts, **kwargs):
    h = harness(init_scripts=[SEEN, *scripts], **kwargs)
    h.api_responses[("GET", "/ratings-summary")] = (200, {"games": {
        "sol": {"average": 4.5, "count": 2, "distribution": {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1}}}})
    page = h.goto("/index.html")
    page.wait_for_selector(".game-row")
    return h, page


# ---------------------------------------------------------------- GN-14: nav dropdowns

def test_nav_is_four_dropdowns_plus_theme_and_lite(harness):
    h, page = hub(harness)
    names = page.evaluate("[...document.querySelectorAll('.hub-nav-menu > summary')].map(s => s.firstChild.textContent)")
    assert names == ["Me", "Updates", "Feedback", "Help"]
    # nothing was lost: every link the old bar had is still in a menu, and the quick toggles stay on the bar
    hrefs = page.evaluate("[...document.querySelectorAll('.hub-nav-menu a')].map(a => a.getAttribute('href'))")
    for href in ("achievements.html", "map.html", "my-stats.html", "whats-new.html", "roadmap.html", "events.html",
                 "sources.html", "help.html", "settings.html"):
        assert href in hrefs, href
    assert page.locator(".hub-nav > .theme-toggle").count() == 1 and page.locator(".hub-nav > #lite-toggle").count() == 1
    assert page.evaluate("document.querySelectorAll('.hub-nav-menu[open]').length") == 0
    assert page.evaluate("!!document.getElementById('tutorial-restart-button') && !!document.querySelector('#nav-help #tutorial-restart-button')")
    assert h.errors == []


def test_menus_open_one_at_a_time_and_escape_returns_focus(harness):
    h, page = hub(harness)
    page.focus("#nav-me > summary")
    page.keyboard.press("Enter")
    assert page.evaluate("document.getElementById('nav-me').open") is True
    assert page.is_visible("#nav-me a[href='map.html']")
    page.focus("#nav-updates > summary")
    page.keyboard.press("Enter")
    page.wait_for_function("document.getElementById('nav-updates').open && !document.getElementById('nav-me').open")
    page.keyboard.press("Escape")
    assert page.evaluate("document.getElementById('nav-updates').open") is False
    assert page.evaluate("document.activeElement === document.querySelector('#nav-updates > summary')")
    # an outside click closes it too
    page.click("#nav-help > summary")
    assert page.evaluate("document.getElementById('nav-help').open") is True
    page.mouse.click(8, 600)
    assert page.evaluate("document.getElementById('nav-help').open") is False
    # choosing an item closes the menu (the tour button starts the tour)
    page.click("#nav-help > summary")
    page.click("#tutorial-restart-button")
    assert page.evaluate("document.getElementById('nav-help').open") is False
    page.wait_for_selector("#tutorial-card")


def test_nav_targets_are_at_least_44px_and_nothing_scrolls_sideways(harness):
    for size in ((1440, 900), (360, 740)):
        h, page = hub(harness, size=size)
        for sel in (".hub-nav-menu > summary", ".hub-nav .theme-toggle", "#lite-toggle"):
            box = page.locator(sel).first.bounding_box()
            assert box["height"] >= 43.5, (sel, size, box)
        page.click("#nav-feedback > summary")
        for sel in ("#nav-feedback #site-feedback-submit", "#nav-feedback .noyvj-report-button", "#nav-feedback .star"):
            box = page.locator(sel).first.bounding_box()
            assert box["height"] >= 43.5, (sel, size, box)
        panel = page.locator("#nav-feedback-panel").bounding_box()
        assert panel["x"] >= -0.5 and panel["x"] + panel["width"] <= size[0] + 0.5, (size, panel)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_updates_badge_mirrors_the_whats_new_count(harness):
    log = "### 2026-10-09 a\ntext\n### 2026-10-10 b\ntext\n"
    h = harness(init_scripts=[SEEN, "localStorage.setItem('hub_whats_new_seen','2026-10-08');"])
    h.pages["/BCM114-DEV-LOG.md"] = log
    h.pages["/BCM206-DEV-LOG.md"] = ""
    page = h.goto("/index.html")
    page.wait_for_function("!document.getElementById('updates-nav-badge').hidden", timeout=8000)
    assert page.evaluate("document.getElementById('updates-nav-badge').textContent") == page.evaluate("document.getElementById('whats-new-badge').textContent")


# ---------------------------------------------------------------- GN-16: feedback in the nav

def test_site_feedback_form_lives_in_the_feedback_menu_and_still_posts(harness):
    h, page = hub(harness)
    assert page.evaluate("!!document.querySelector('#nav-feedback #site-feedback-section')")
    assert page.evaluate("document.querySelectorAll('#site-feedback-section').length") == 1
    assert page.evaluate("document.querySelector('.hub-footer #site-feedback-section') === null")
    h.api_responses[("GET", "/feedback")] = (200, [{"rating": 4, "comment": "fine"}])
    h.api_responses[("POST", "/feedback")] = (200, {"ok": True})
    page.click("#nav-feedback > summary")
    page.click("#site-feedback-stars .star[data-value='4']")
    page.fill("#site-feedback-comment", "nice hub")
    page.click("#site-feedback-submit")
    page.wait_for_function("document.getElementById('site-feedback-status').textContent.includes('Thanks')")
    posts = [c for c in h.api_calls if c[0] == "POST" and c[1] == "/feedback"]
    assert len(posts) == 1 and json.loads(posts[0][2]) == {"rating": 4, "comment": "nice hub"}


def test_report_a_problem_is_mounted_for_the_hub_and_sends_nothing_until_asked(harness):
    h, page = hub(harness)
    page.click("#nav-feedback > summary")
    button = page.locator("#nav-report-slot .noyvj-report-button")
    assert button.count() == 1 and button.inner_text() == "Report a problem"
    assert page.locator(".noyvj-report-floating").count() == 0, "no second, floating button"
    button.click()
    page.wait_for_selector("dialog.noyvj-report-dialog[open]")
    assert page.evaluate("document.getElementById('nav-feedback').open") is False
    assert "hub" in page.inner_text("dialog.noyvj-report-dialog")
    assert [c for c in h.api_calls if c[0] == "POST"] == []
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('dialog.noyvj-report-dialog[open]')")
    page.wait_for_function("document.activeElement === document.querySelector('#nav-feedback > summary')")


def test_footer_feedback_link_opens_the_feedback_menu(harness):
    h, page = hub(harness)
    page.click(".hub-footer a[data-open-feedback]")
    page.wait_for_function("document.getElementById('nav-feedback').open")
    assert page.evaluate("document.activeElement.id") == "site-feedback-comment"
    page.wait_for_function("window.scrollY < 50")


def test_links_from_other_pages_to_the_feedback_anchor_open_the_menu(harness):
    h = harness(init_scripts=[SEEN])
    page = h.goto("/index.html#site-feedback-section")
    page.wait_for_function("document.getElementById('nav-feedback').open")
    assert page.is_visible("#site-feedback-comment")


# ---------------------------------------------------------------- GN-12: strips

def test_pickup_and_recently_added_sit_side_by_side_and_more_for_you_is_folded(harness):
    h, page = hub(harness, "localStorage.setItem('last-played:canopy', String(Date.now() - 3600000));")
    page.wait_for_function("!document.getElementById('recently-added-section').hidden && !document.getElementById('pickup-section').hidden")
    a = page.locator("#pickup-section").bounding_box()
    b = page.locator("#recently-added-section").bounding_box()
    assert abs(a["y"] - b["y"]) < 2 and b["x"] > a["x"] + a["width"] - 1, "same row, side by side"
    # the lower-value strips are inside one closed details
    for sel in ("#for-you-section", "#community-highlights-section", "#rarest-section"):
        assert page.evaluate(f"!!document.querySelector('#more-for-you {sel}')"), sel
    assert page.evaluate("document.getElementById('more-for-you').open") is False
    assert page.is_hidden("#community-highlights-section")
    page.click("#more-for-you > summary")
    assert page.is_visible("#community-highlights-section")
    # the games come before nothing but the strips: far fewer screens of scrolling than before
    assert page.evaluate("document.getElementById('game-filter-bar').getBoundingClientRect().top + scrollY") < 1700
    assert page.evaluate("document.getElementById('continue-playing-section').closest('#pickup-section') !== null")


def test_account_saves_join_the_pickup_strip_without_repeating_local_games(harness):
    saves = [{"game_id": g, "save_code": "AAAA-BBBB", "updated_at": f"2026-10-0{i + 1}T00:00:00Z", "save_data": {}}
             for i, g in enumerate(("canopy", "grid", "tide", "herd", "thaw", "loop"))]
    h = harness(init_scripts=[SEEN, SIGNED_IN, "localStorage.setItem('last-played:canopy', String(Date.now() - 3600000));"])
    h.api_responses[("GET", "/users/me/saves")] = (200, saves)
    page = h.goto("/index.html")
    page.wait_for_function("!document.getElementById('continue-playing-section').hidden")
    local = page.evaluate("[...document.querySelectorAll('#pickup-list a')].map(a => a.getAttribute('href'))")
    account = page.evaluate("[...document.querySelectorAll('#continue-playing-list a.continue-playing-item')].map(a => a.getAttribute('href'))")
    assert local == ["games/canopy/index.html"]
    assert "games/canopy/index.html" not in account and len(account) == 4, "capped, and canopy is already listed above"
    assert account[0] == "games/loop/index.html", "newest save first"
    assert "more saved games" in page.inner_text("#continue-playing-list")
    # signing out (no saves, nothing local) hides the whole strip again
    page.evaluate("document.getElementById('account-signout-button').click()")
    page.wait_for_function("document.getElementById('continue-playing-section').hidden")


def test_pickup_strip_shows_for_account_saves_alone(harness):
    h = harness(init_scripts=[SEEN, SIGNED_IN])
    h.api_responses[("GET", "/users/me/saves")] = (200, [{"game_id": "sol", "save_code": "AAAA-BBBB", "updated_at": "2026-10-01T00:00:00Z", "save_data": {}}])
    page = h.goto("/index.html")
    page.wait_for_function("!document.getElementById('pickup-section').hidden")
    assert page.evaluate("document.getElementById('pickup-list').children.length") == 0
    assert "Continue SOL" in page.inner_text("#pickup-section")


# ---------------------------------------------------------------- GN-13: collapsed cards

def test_collapsed_card_is_picture_name_show_more_and_a_rating_badge(harness):
    h, page = hub(harness)
    page.wait_for_function("document.querySelector('.title-card .title-card-rating-badge')")
    card = page.locator(".title-card:has(.review-widget[data-game-slug='sol'])")
    assert card.locator(".title-card-rating-badge").inner_text() == "4.5 stars (2)"
    assert card.locator(".title-card-expand").inner_text() == "Show more"
    for sel in (".title-card-thumb", ".title-card-name", ".title-card-expand", ".title-card-rating-badge"):
        assert card.locator(sel).is_visible(), sel
    for sel in (".title-card-blurb", ".title-card-tags", ".review-widget", ".star-rating", ".comment-box", ".title-card-share"):
        assert not card.locator(sel).first.is_visible(), sel
    # the badge is on the picture
    thumb, badge = card.locator(".title-card-thumb").bounding_box(), card.locator(".title-card-rating-badge").bounding_box()
    assert thumb["x"] <= badge["x"] and badge["x"] + badge["width"] <= thumb["x"] + thumb["width"] + 1
    assert thumb["y"] <= badge["y"] and badge["y"] + badge["height"] <= thumb["y"] + thumb["height"] + 1
    # a game nobody has rated says so
    assert page.locator(".title-card:has(.review-widget[data-game-slug='grid']) .title-card-rating-badge").inner_text() == "No ratings yet"
    card.locator(".title-card-expand").click()
    assert card.locator(".title-card-expand").inner_text() == "Show less"
    assert card.locator(".title-card-blurb").is_visible() and card.locator(".star-rating").is_visible()
    assert page.evaluate("document.body.innerText.includes('Show details')") is False


def test_the_rating_badge_is_not_searchable(harness):
    h, page = hub(harness)
    page.wait_for_function("document.querySelector('.title-card .title-card-rating-badge')")
    page.fill("#game-search-input", "4.5 stars")
    page.wait_for_timeout(300)
    assert page.evaluate("[...document.querySelectorAll('.title-card')].filter(c => !c.hidden).length") == 0
    page.fill("#game-search-input", "no ratings yet")
    page.wait_for_timeout(300)
    assert page.evaluate("[...document.querySelectorAll('.title-card')].filter(c => !c.hidden).length") == 0


# ---------------------------------------------------------------- GN-11: carousels

def rows(page):
    return page.evaluate("[...document.querySelectorAll('.game-row')].map(r => [r.dataset.row, [...r.querySelectorAll('.title-card .review-widget')].map(w => w.dataset.gameSlug)])")


def test_one_row_per_first_subject_tag_with_real_cards_inside_the_grid(harness):
    h, page = hub(harness)
    got = dict(rows(page))
    assert list(got) == ["climate", "space", "economy", "civilization", "language-learning", "quick", "deep-systems"]
    assert got["climate"] == ["canopy", "grid", "tide", "aftermath", "herd", "thaw", "loop", "drift"]
    assert set(got["space"]) == {"sol", "lexis", "stranded"}   # Lexis has space first, then language learning
    assert got["economy"] == ["trade-empire"] and got["civilization"] == ["continuum"] and got["language-learning"] == ["champ-de-mots"]
    assert sum(len(v) for v in got.values()) == 24
    assert page.evaluate("document.querySelectorAll('#game-grid .title-card').length") == 24
    assert page.evaluate("[...document.querySelectorAll('.game-row-title')].map(h => h.tagName).every(t => t === 'H2')")
    assert page.evaluate("[...document.querySelectorAll('.title-card-name')].every(h => h.tagName === 'H3')")
    assert page.inner_text(".game-row[data-row='climate'] .game-row-count") == "8 games"


def test_rows_are_keyboard_reachable_with_labelled_scroll_buttons(harness):
    h, page = hub(harness, size=(900, 800))
    row = page.locator(".game-row[data-row='climate']")
    labels = row.locator(".game-row-controls button").evaluate_all("bs => bs.map(b => b.getAttribute('aria-label'))")
    assert labels == ["Scroll the Climate row left", "Scroll the Climate row right"]
    track = row.locator(".game-row-track")
    assert track.get_attribute("tabindex") == "0" and track.get_attribute("role") == "region"
    assert page.evaluate("document.getElementById(document.querySelector('.game-row-track').getAttribute('aria-labelledby')).textContent") == "Climate"
    controls = row.locator(".game-row-controls button")
    assert controls.first.is_disabled() and not controls.last.is_disabled()
    controls.last.focus()
    page.keyboard.press("Enter")
    page.wait_for_function("document.querySelector('.game-row-track').scrollLeft > 100")
    assert not controls.first.is_disabled()
    # a one-card row has nothing to scroll, so its buttons are not offered
    assert not page.locator(".game-row[data-row='economy'] .game-row-controls").is_visible()
    # Tab is never trapped: from the row's last control the next stop is outside the row
    page.focus(".game-row[data-row='climate'] .game-row-track")
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("!document.querySelector('.game-row[data-row=climate] .game-row-track').contains(document.activeElement)")


def test_scroll_buttons_do_not_animate_under_reduced_motion(harness):
    h, page = hub(harness, size=(900, 800), media={"reduced_motion": "reduce"})
    page.evaluate("""window.__scrolls = []; const t = document.querySelector('.game-row-track');
        const orig = t.scrollBy.bind(t); t.scrollBy = (o) => { window.__scrolls.push(o.behavior); return orig(o); }; null;""")
    page.locator(".game-row[data-row='climate'] .game-row-controls button").last.click()
    assert page.evaluate("window.__scrolls") == ["auto"]
    assert page.evaluate("getComputedStyle(document.querySelector('.game-row-track')).scrollBehavior") == "auto"


def test_filters_hide_rows_with_no_visible_card_and_the_empty_message_still_works(harness):
    h, page = hub(harness)
    visible = "[...document.querySelectorAll('.game-row')].filter(r => !r.hidden).map(r => r.dataset.row)"
    page.select_option("#game-tag-filter", "space")
    page.wait_for_function("document.querySelectorAll('.game-row:not([hidden])').length === 1")
    assert page.evaluate(visible) == ["space"] and page.inner_text(".game-row[data-row='space'] .game-row-count") == "3 games"
    page.select_option("#game-tag-filter", "")
    page.wait_for_function("document.querySelectorAll('.game-row:not([hidden])').length === 7")
    page.fill("#game-search-input", "zzzzqq")
    page.wait_for_function("document.querySelectorAll('.game-row:not([hidden])').length === 0")
    assert page.is_visible("#game-filter-empty")
    page.fill("#game-search-input", "")
    page.wait_for_function("document.querySelectorAll('.game-row:not([hidden])').length === 7")
    assert page.is_hidden("#game-filter-empty")


def test_sorting_orders_each_row_and_keeps_the_rows(harness):
    h, page = hub(harness)
    page.wait_for_function("document.querySelector('.title-card[data-review-count=\"2\"]')")
    page.select_option("#game-sort", "rating")
    page.wait_for_function("document.querySelector('.game-row[data-row=space] .title-card .review-widget').dataset.gameSlug === 'sol'")
    assert [r[0] for r in rows(page)] == ["climate", "space", "economy", "civilization", "language-learning", "quick", "deep-systems"]
    page.select_option("#game-sort", "default")
    page.wait_for_function("document.querySelector('.game-row[data-row=space] .title-card .review-widget').dataset.gameSlug === 'sol'")
    assert dict(rows(page))["climate"][0] == "canopy"


def test_calm_filter_hides_rows_it_empties(harness):
    h, page = hub(harness, "localStorage.setItem('noyvj-calm', 'on');")
    page.wait_for_function("document.documentElement.getAttribute('data-calm') === 'true'")
    page.wait_for_timeout(300)
    shown_cards = page.evaluate("[...document.querySelectorAll('.title-card')].filter(c => !c.hidden).length")
    shown_rows = page.evaluate("[...document.querySelectorAll('.game-row')].filter(r => !r.hidden).length")
    assert 0 < shown_cards < 24
    assert shown_rows == page.evaluate("new Set([...document.querySelectorAll('.title-card')].filter(c => !c.hidden).map(c => c.closest('.game-row').dataset.row)).size")


def test_layout_has_no_sideways_scroll_on_a_phone(harness):
    h, page = hub(harness, size=(360, 740), touch=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    track = page.locator(".game-row[data-row='climate'] .game-row-track").bounding_box()
    assert track["x"] >= -8 and track["x"] + track["width"] <= 368
