"""profile.html / profile.js (planning/TODO.md Y-1) in headless Chromium: the public view, the honest
not-public and empty states, the owner's switch (off by default), share link, favourite picker,
keyboard use, phone width and the themes. The backend is answered by the test."""

import json

from conftest import page_html  # noqa: F401  (keeps the shared fixtures importable the same way)

TOKEN = "localStorage.setItem('hub_bearer_token','tok-abc');"

PUBLIC = {
    "username": "mara", "member_since": "2026-03-14", "favourite_game": "canopy", "favourite_is_most_played": False,
    "games": [{"game": "canopy", "seconds": 7200, "achievements": 9}, {"game": "signal", "seconds": 1800, "achievements": 2}],
    "total_seconds": 9000, "total_achievements": 11, "games_played": 2,
    "streaks": [{"game": "signal", "label": "daily", "value": 12}, {"game": "canopy", "label": "perfect_run", "value": 3}],
    "badges": [
        {"id": "first-steps", "label": "First steps", "detail": "Earned a first achievement.", "kind": "milestone"},
        {"id": "achiever-10", "label": "Ten achievements", "detail": "Earned 10 achievements across the site.", "kind": "milestone"},
        {"id": "halloween-2026", "label": "Halloween 2026", "detail": "A seasonal event badge.", "kind": "event"},
    ],
}
LADDER = [  # AN-16: the same shape the backend sends (app/profiles.py TITLES)
    ("newcomer", "Newcomer", "Everyone starts here."),
    ("tinkerer", "Tinkerer", "Earn 1 achievement across all games, or try 2 games and play for an hour in total."),
    ("regular", "Regular", "Earn 10 achievements across all games, or try 3 games and play for 3 hours in total."),
    ("collector", "Collector", "Earn 25 achievements across all games, or try 6 games and play for 10 hours in total."),
    ("keeper", "Keeper of the Hub", "Earn 200 achievements across all games."),
]


def with_titles(data, earned_count):
    """`data` plus a titles shelf where the first `earned_count` titles are earned."""
    shelf = [{"id": i, "label": l, "detail": d, "earned": n < earned_count} for n, (i, l, d) in enumerate(LADDER)]
    top = shelf[earned_count - 1]
    return {**data, "titles": shelf, "title": {k: top[k] for k in ("id", "label", "detail")}}


PUBLIC = with_titles(PUBLIC, 3)
OWNER = {**PUBLIC, "is_public": False, "favourite_game_choice": None}
EMPTY_OWNER = with_titles({"username": "newbie", "member_since": "2026-10-01", "favourite_game": None, "favourite_is_most_played": False,
               "games": [], "total_seconds": 0, "total_achievements": 0, "games_played": 0, "streaks": [], "badges": [],
               "is_public": False, "favourite_game_choice": None}, 1)


def open_profile(harness, query="?u=mara", init=(), size=(1440, 900), **kw):
    h = harness(init_scripts=list(init), size=size, **kw)
    h.goto("/profile.html" + query)
    return h


def open_owner(h):
    """GN-10: the owner's page shows like anyone's; the controls open from the Profile settings button."""
    h.page.wait_for_selector("#pf-ownerbar:not([hidden])")
    if h.page.get_attribute("#pf-settings-toggle", "aria-expanded") != "true":
        h.page.click("#pf-settings-toggle")
    h.page.wait_for_selector("#pf-owner:not([hidden])")


def paths(h):
    return [(c[0], c[1]) for c in h.api_calls]


def puts(h):
    """The profile PUTs only (shared/site-settings.js also syncs the theme for a signed-in player)."""
    return [json.loads(c[2]) for c in h.api_calls if c[0] == "PUT" and c[1] == "/users/me/profile"]


def text(h, selector):
    return h.page.inner_text(selector)


def test_public_profile_shows_only_the_public_data(harness):
    h = harness()
    h.api_responses[("GET", "/profiles/mara")] = (200, PUBLIC)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert text(h, "#pf-name") == "mara"
    assert "March 2026" in text(h, "#pf-since")
    assert text(h, "#pf-fav") == "Canopy"
    assert h.page.get_attribute("#pf-fav a", "href").endswith("games/canopy/index.html")
    assert "about 3 hours across 2 games" in text(h, "#pf-time") or "about 2 hours across 2 games" in text(h, "#pf-time")
    badges = h.page.eval_on_selector_all("#pf-badges li", "els => els.map(e => e.textContent)")
    assert len(badges) == 3 and any("First steps" in b for b in badges) and any("Halloween 2026" in b and "Seasonal" in b for b in badges)
    rows = h.page.eval_on_selector_all("#pf-games li", "els => els.map(e => e.textContent)")
    assert "Canopy" in rows[0] and "9 achievements" in rows[0] and "Signal" in rows[1] and "2 achievements" in rows[1]
    assert "12" in text(h, "#pf-streaks") and "daily" in text(h, "#pf-streaks") and "perfect run" in text(h, "#pf-streaks")
    assert h.page.is_hidden("#pf-owner") and h.page.is_hidden("#pf-message") and h.page.is_hidden("#pf-what-others-see")
    assert ("GET", "/profiles/mara") in paths(h)
    assert not any(p.startswith("/users/me") for _, p in paths(h))      # signed out: no account call at all
    assert h.errors == []


def test_not_public_and_unknown_look_exactly_the_same(harness):
    seen = []
    for name in ("private-one", "never-existed"):
        h = harness()
        h.api_responses[("GET", f"/profiles/{name}")] = (404, {"detail": "There is no public profile with that name."})
        h.goto(f"/profile.html?u={name}")
        h.page.wait_for_selector("#pf-message:not([hidden])")
        seen.append((text(h, "#pf-message-h"), text(h, "#pf-message-text")))
        assert h.page.is_hidden("#pf-card") and h.page.is_hidden("#pf-owner")
    assert seen[0] == seen[1]
    assert "private by default" in seen[0][1]


def test_server_trouble_is_not_reported_as_a_missing_profile(harness):
    h = harness()
    h.api_responses[("GET", "/profiles/mara")] = (500, {"detail": "boom"})
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-message:not([hidden])")
    assert "could not be loaded" in text(h, "#pf-message-h") and "No public profile" not in text(h, "#pf-message-h")


def test_no_name_and_signed_out_explains_how_to_get_one(harness):
    h = harness()
    h.goto("/profile.html")
    h.page.wait_for_selector("#pf-message:not([hidden])")
    assert "profile.html?u=name" in text(h, "#pf-message-text")
    assert h.api_calls == []


def test_owner_sees_a_private_profile_with_the_switch_off(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=Mara")                                # any capitalisation of your own name
    open_owner(h)
    assert not h.page.is_checked("#pf-vis-public") and h.page.is_checked("#pf-vis-private")
    assert "private" in text(h, "#pf-state").lower()
    assert h.page.is_visible("#pf-private-note") and h.page.is_hidden("#pf-share")
    assert h.page.is_visible("#pf-card") and h.page.is_visible("#pf-what-others-see")
    assert ("GET", "/profiles/mara") not in paths(h) and ("GET", "/profiles/Mara") not in paths(h)


def test_turning_it_on_shows_the_share_link_and_copies_it(harness):
    h = harness(init_scripts=[TOKEN, "window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                                     "value: {writeText: (t) => { window.__copied = t; return Promise.resolve(); }}});"])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    open_owner(h)
    h.api_responses[("PUT", "/users/me/profile")] = (200, {**OWNER, "is_public": True})
    h.page.check("#pf-vis-public")
    h.page.wait_for_selector("#pf-share:not([hidden])")
    assert puts(h) == [{"is_public": True}]
    link = h.page.input_value("#pf-link")
    assert link.endswith("/profile.html?u=mara")
    assert "public" in text(h, "#pf-state").lower() and h.page.is_hidden("#pf-private-note")
    h.page.click("#pf-copy")
    h.page.wait_for_function("window.__copied !== null")
    assert h.page.evaluate("window.__copied") == link
    assert "copied" in text(h, "#pf-owner-status").lower()
    # and off again
    h.api_responses[("PUT", "/users/me/profile")] = (200, {**OWNER, "is_public": False})
    h.page.check("#pf-vis-private")
    h.page.wait_for_selector("#pf-share", state="hidden")
    assert puts(h)[-1] == {"is_public": False}


def test_a_failed_save_puts_the_switch_back_and_says_so(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    open_owner(h)
    h.api_responses[("PUT", "/users/me/profile")] = (500, {"detail": "boom"})
    h.page.check("#pf-vis-public")
    h.page.wait_for_function("document.getElementById('pf-owner-status').textContent.includes('did not save')")
    assert not h.page.is_checked("#pf-vis-public") and h.page.is_checked("#pf-vis-private") and h.page.is_hidden("#pf-share")


def test_favourite_game_picker_sends_the_choice_or_null_for_automatic(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    open_owner(h)
    assert h.page.eval_on_selector("#pf-favourite", "s => s.options[0].textContent").startswith("The one I play most")
    assert h.page.eval_on_selector("#pf-favourite", "s => s.options.length") >= 14
    h.api_responses[("PUT", "/users/me/profile")] = (200, {**OWNER, "favourite_game": "tide", "favourite_game_choice": "tide"})
    h.page.select_option("#pf-favourite", "tide")
    h.page.wait_for_function("document.getElementById('pf-fav').textContent.includes('Tide')")
    h.api_responses[("PUT", "/users/me/profile")] = (200, OWNER)
    h.page.select_option("#pf-favourite", "")
    h.page.wait_for_function("document.getElementById('pf-fav').textContent.includes('Canopy')")
    assert puts(h) == [{"favourite_game": "tide"}, {"favourite_game": None}]


def test_viewing_someone_elses_page_while_signed_in_is_the_public_view(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.api_responses[("GET", "/profiles/other")] = (200, {**PUBLIC, "username": "other"})
    h.goto("/profile.html?u=other")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert text(h, "#pf-name") == "other" and h.page.is_hidden("#pf-owner")


def test_no_name_when_signed_in_opens_your_own_page_and_fixes_the_address(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html")
    open_owner(h)
    assert h.page.evaluate("location.search") == "?u=mara"


def test_a_brand_new_account_gets_honest_empty_states(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, EMPTY_OWNER)
    h.goto("/profile.html")
    open_owner(h)
    assert "No badges yet" in text(h, "#pf-badges")
    assert "Nothing recorded yet" in text(h, "#pf-games") and "signed in" in text(h, "#pf-games")
    assert text(h, "#pf-time") == "none recorded yet" and text(h, "#pf-fav") == "not chosen yet"
    assert h.page.is_hidden("#pf-streaks-wrap")


def test_a_public_page_with_nothing_yet_does_not_promise_anything(harness):
    h = harness()
    h.api_responses[("GET", "/profiles/newbie")] = (200, {k: v for k, v in EMPTY_OWNER.items() if k not in ("is_public", "favourite_game_choice")})
    h.goto("/profile.html?u=newbie")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert text(h, "#pf-badges").strip() == "No badges yet."
    assert text(h, "#pf-games").strip() == "No achievements recorded yet."


def test_names_are_text_not_markup(harness):
    h = harness()
    h.api_responses[("GET", "/profiles/x")] = (200, {**PUBLIC, "username": "<img src=x onerror=window.__pwned=1>",
                                                        "badges": [{"id": "b", "label": "<b>bold</b>", "detail": "<i>x</i>", "kind": "milestone"}]})
    h.goto("/profile.html?u=x")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert h.page.evaluate("window.__pwned") is None
    assert h.page.query_selector("#pf-card img, #pf-badges b, #pf-badges i") is None
    assert "<img" in text(h, "#pf-name")


def test_keyboard_alone_can_flip_the_switch(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    open_owner(h)
    h.api_responses[("PUT", "/users/me/profile")] = (200, {**OWNER, "is_public": True})
    h.page.focus("#pf-vis-public")
    h.page.keyboard.press("Space")
    h.page.wait_for_selector("#pf-share:not([hidden])")
    assert h.page.is_checked("#pf-vis-public")


def test_it_talks_only_to_the_profile_routes_and_sets_no_tracking(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    open_owner(h)
    h.page.wait_for_timeout(200)
    own = {p for p in paths(h) if "settings" not in p[1]}     # shared/site-settings.js syncs the theme on its own
    assert own == {("GET", "/users/me/profile"), ("POST", "/users/me/profile/backfill")}
    assert h.page.evaluate("document.cookie") == ""
    assert h.page.evaluate("document.querySelectorAll('script[src^=\"http\"]').length") == 0


def test_phone_layout_has_no_sideways_scroll_and_big_targets(harness):
    h = harness(init_scripts=[TOKEN], size=(360, 740), touch=True)
    h.api_responses[("GET", "/users/me/profile")] = (200, {**OWNER, "is_public": True, "username": "a-rather-long-player-name-that-must-wrap-somewhere"})
    h.goto("/profile.html")
    open_owner(h)
    assert h.page.evaluate("document.documentElement.scrollWidth <= 360")
    small = h.page.evaluate("""[...document.querySelectorAll('#pf-owner button, #pf-owner select, #pf-owner input[type=text], label.pf-switch')]
        .filter(e => e.offsetParent !== null && e.getBoundingClientRect().height < 44).map(e => e.id || e.className)""")
    assert small == []


def test_the_page_follows_the_site_theme(harness):
    """Colours come from the hub's own theme rules; the contrast itself was checked by eye in both themes."""
    seen = {}
    for theme in ("dark", "light"):
        h = harness(init_scripts=[f"localStorage.setItem('theme','{theme}')"])
        h.api_responses[("GET", "/profiles/mara")] = (200, PUBLIC)
        h.goto("/profile.html?u=mara")
        h.page.wait_for_selector("#pf-card:not([hidden])")
        assert h.page.get_attribute("html", "data-theme") == theme
        seen[theme] = h.page.evaluate("getComputedStyle(document.querySelector('#pf-badges li')).color")
    assert seen["dark"] != seen["light"]


# ---- GN-10: the owner's page is a normal profile plus a settings button ----

def test_owner_sees_the_card_first_and_the_controls_only_after_pressing_profile_settings(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-ownerbar:not([hidden])")
    assert h.page.is_visible("#pf-card") and h.page.is_hidden("#pf-owner")
    assert h.page.get_attribute("#pf-settings-toggle", "aria-expanded") == "false"
    assert "Private" in text(h, "#pf-vis-badge")
    h.page.click("#pf-settings-toggle")
    assert h.page.is_visible("#pf-owner") and h.page.get_attribute("#pf-settings-toggle", "aria-expanded") == "true"
    h.page.click("#pf-settings-toggle")
    assert h.page.is_hidden("#pf-owner")


def test_visitors_never_get_the_settings_button(harness):
    h = harness()
    h.api_responses[("GET", "/profiles/mara")] = (200, PUBLIC)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert h.page.is_hidden("#pf-ownerbar") and h.page.is_hidden("#pf-settings-toggle")


def test_visibility_has_private_public_and_a_friends_option_that_says_it_is_not_there_yet(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    open_owner(h)
    assert h.page.is_disabled("#pf-vis-friends")
    assert "no friends list" in text(h, "#pf-vis-friends-note").lower()
    h.api_responses[("PUT", "/users/me/profile")] = (200, {**OWNER, "is_public": True})
    h.page.check("#pf-vis-public")
    h.page.wait_for_selector("#pf-share:not([hidden])")
    assert puts(h) == [{"is_public": True}]
    assert "anyone with your link" in text(h, "#pf-vis-badge").lower()


# ---- GN-7: fill the profile in from existing saves ----

def test_signed_in_owner_is_backfilled_once_per_device_and_the_card_updates(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, EMPTY_OWNER)
    filled = {**EMPTY_OWNER, "games": [{"game": "canopy", "seconds": 0, "achievements": 29}], "games_played": 1,
              "total_achievements": 29}
    h.api_responses[("POST", "/users/me/profile/backfill")] = (200, {"updated": [{"game": "canopy", "achievements": 29}], "profile": filled})
    h.goto("/profile.html")
    open_owner(h)
    h.page.wait_for_function("document.getElementById('pf-games').textContent.includes('29 achievements')")
    assert "Updated 1 game" in text(h, "#pf-owner-status")
    posts = [c for c in h.api_calls if c[0] == "POST" and c[1] == "/users/me/profile/backfill"]
    assert len(posts) == 1
    h.page.reload()
    h.page.wait_for_selector("#pf-ownerbar:not([hidden])")
    h.page.wait_for_timeout(300)
    assert len([c for c in h.api_calls if c[0] == "POST" and c[1] == "/users/me/profile/backfill"]) == 1   # not repeated


def test_the_backfill_button_works_again_by_hand_and_says_when_nothing_changed(harness):
    h = harness(init_scripts=[TOKEN, "localStorage.setItem('pf-backfilled:newbie','1')"])
    h.api_responses[("GET", "/users/me/profile")] = (200, EMPTY_OWNER)
    h.api_responses[("POST", "/users/me/profile/backfill")] = (200, {"updated": [], "profile": EMPTY_OWNER})
    h.goto("/profile.html")
    open_owner(h)
    assert not [c for c in h.api_calls if c[1] == "/users/me/profile/backfill"]
    h.page.click("#pf-backfill")
    h.page.wait_for_function("document.getElementById('pf-owner-status').textContent.includes('already matches')")


def test_a_failed_backfill_says_so_and_changes_nothing(harness):
    h = harness(init_scripts=[TOKEN, "localStorage.setItem('pf-backfilled:newbie','1')"])
    h.api_responses[("GET", "/users/me/profile")] = (200, EMPTY_OWNER)
    h.api_responses[("POST", "/users/me/profile/backfill")] = (500, {"detail": "boom"})
    h.goto("/profile.html")
    open_owner(h)
    h.page.click("#pf-backfill")
    h.page.wait_for_function("document.getElementById('pf-owner-status').textContent.includes('Nothing changed')")


# ---- AN-16: account-wide titles ----

def titles_rows(h):
    return h.page.eval_on_selector_all("#pf-titles li", "els => els.map(e => e.textContent.replace(/\\s+/g, ' ').trim())")


def test_the_current_title_sits_under_the_name_and_the_shelf_lists_every_title(harness):
    h = harness()
    h.api_responses[("GET", "/profiles/mara")] = (200, PUBLIC)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert text(h, "#pf-title") == "Title: Regular"
    below = h.page.evaluate("""document.getElementById('pf-name').nextElementSibling.id""")
    assert below == "pf-title"
    rows = titles_rows(h)
    assert len(rows) == 5 and h.page.is_visible("#pf-titles-wrap")
    for row, (_i, label, _d) in zip(rows, LADDER):
        assert label in row


def test_earned_titles_are_marked_in_text_and_a_glyph_and_the_rest_say_what_earns_them(harness):
    h = harness()
    h.api_responses[("GET", "/profiles/mara")] = (200, PUBLIC)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    rows = titles_rows(h)
    for row in rows[:3]:
        assert row.startswith("✓") and row.endswith("Earned")
    assert "Current title." in rows[2] and "Current title." not in rows[1]
    for row, (_i, label, detail) in zip(rows[3:], LADDER[3:]):
        assert row.startswith("○") and row.endswith("Not yet") and label in row
        assert "How to earn it: " + detail in row
    assert "Earn 25 achievements across all games" in rows[3]
    # the glyphs are decoration; the words carry the meaning for a screen reader
    assert h.page.eval_on_selector_all("#pf-titles .pf-glyph", "els => els.every(e => e.getAttribute('aria-hidden') === 'true')")


def test_the_owner_sees_the_same_shelf_and_a_brand_new_account_starts_as_newcomer(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, EMPTY_OWNER)
    h.goto("/profile.html")
    open_owner(h)
    assert text(h, "#pf-title") == "Title: Newcomer"
    rows = titles_rows(h)
    assert rows[0].startswith("✓") and all(r.startswith("○") for r in rows[1:])


def test_a_response_with_no_titles_still_renders_without_a_title_or_shelf(harness):
    older = {k: v for k, v in PUBLIC.items() if k not in ("titles", "title")}
    h = harness()
    h.api_responses[("GET", "/profiles/mara")] = (200, older)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert h.page.is_hidden("#pf-title") and h.page.is_hidden("#pf-titles-wrap")
    assert text(h, "#pf-name") == "mara" and len(h.page.query_selector_all("#pf-badges li")) == 3
    assert h.errors == []


def test_title_names_are_text_not_markup(harness):
    h = harness()
    data = with_titles(PUBLIC, 2)
    data["titles"][1]["label"] = "<img src=x onerror=window.__pwned=1>"
    data["title"]["label"] = "<b>bold</b>"
    h.api_responses[("GET", "/profiles/x")] = (200, data)
    h.goto("/profile.html?u=x")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert h.page.evaluate("window.__pwned") is None
    assert h.page.query_selector("#pf-title b, #pf-titles img") is None
    assert text(h, "#pf-title") == "Title: <b>bold</b>"


def test_the_titles_shelf_fits_a_phone(harness):
    h = harness(size=(360, 740), touch=True)
    h.api_responses[("GET", "/profiles/mara")] = (200, with_titles(PUBLIC, 4))
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-card:not([hidden])")
    assert h.page.evaluate("document.documentElement.scrollWidth <= 360")
    assert len(titles_rows(h)) == 5
