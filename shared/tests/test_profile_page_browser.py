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
OWNER = {**PUBLIC, "is_public": False, "favourite_game_choice": None}
EMPTY_OWNER = {"username": "newbie", "member_since": "2026-10-01", "favourite_game": None, "favourite_is_most_played": False,
               "games": [], "total_seconds": 0, "total_achievements": 0, "games_played": 0, "streaks": [], "badges": [],
               "is_public": False, "favourite_game_choice": None}


def open_profile(harness, query="?u=mara", init=(), size=(1440, 900), **kw):
    h = harness(init_scripts=list(init), size=size, **kw)
    h.goto("/profile.html" + query)
    return h


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
    h.page.wait_for_selector("#pf-owner:not([hidden])")
    assert not h.page.is_checked("#pf-public")
    assert "private" in text(h, "#pf-state").lower()
    assert h.page.is_visible("#pf-private-note") and h.page.is_hidden("#pf-share")
    assert h.page.is_visible("#pf-card") and h.page.is_visible("#pf-what-others-see")
    assert ("GET", "/profiles/mara") not in paths(h) and ("GET", "/profiles/Mara") not in paths(h)


def test_turning_it_on_shows_the_share_link_and_copies_it(harness):
    h = harness(init_scripts=[TOKEN, "window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                                     "value: {writeText: (t) => { window.__copied = t; return Promise.resolve(); }}});"])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-owner:not([hidden])")
    h.api_responses[("PUT", "/users/me/profile")] = (200, {**OWNER, "is_public": True})
    h.page.check("#pf-public")
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
    h.page.uncheck("#pf-public")
    h.page.wait_for_selector("#pf-share", state="hidden")
    assert puts(h)[-1] == {"is_public": False}


def test_a_failed_save_puts_the_switch_back_and_says_so(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-owner:not([hidden])")
    h.api_responses[("PUT", "/users/me/profile")] = (500, {"detail": "boom"})
    h.page.check("#pf-public")
    h.page.wait_for_function("document.getElementById('pf-owner-status').textContent.includes('did not save')")
    assert not h.page.is_checked("#pf-public") and h.page.is_hidden("#pf-share")


def test_favourite_game_picker_sends_the_choice_or_null_for_automatic(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-owner:not([hidden])")
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
    h.page.wait_for_selector("#pf-owner:not([hidden])")
    assert h.page.evaluate("location.search") == "?u=mara"


def test_a_brand_new_account_gets_honest_empty_states(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, EMPTY_OWNER)
    h.goto("/profile.html")
    h.page.wait_for_selector("#pf-owner:not([hidden])")
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
    h.page.wait_for_selector("#pf-owner:not([hidden])")
    h.api_responses[("PUT", "/users/me/profile")] = (200, {**OWNER, "is_public": True})
    h.page.focus("#pf-public")
    h.page.keyboard.press("Space")
    h.page.wait_for_selector("#pf-share:not([hidden])")
    assert h.page.is_checked("#pf-public")


def test_it_talks_only_to_the_profile_routes_and_sets_no_tracking(harness):
    h = harness(init_scripts=[TOKEN])
    h.api_responses[("GET", "/users/me/profile")] = (200, OWNER)
    h.goto("/profile.html?u=mara")
    h.page.wait_for_selector("#pf-owner:not([hidden])")
    h.page.wait_for_timeout(200)
    own = {p for p in paths(h) if "settings" not in p[1]}     # shared/site-settings.js syncs the theme on its own
    assert own == {("GET", "/users/me/profile")}
    assert h.page.evaluate("document.cookie") == ""
    assert h.page.evaluate("document.querySelectorAll('script[src^=\"http\"]').length") == 0


def test_phone_layout_has_no_sideways_scroll_and_big_targets(harness):
    h = harness(init_scripts=[TOKEN], size=(360, 740), touch=True)
    h.api_responses[("GET", "/users/me/profile")] = (200, {**OWNER, "is_public": True, "username": "a-rather-long-player-name-that-must-wrap-somewhere"})
    h.goto("/profile.html")
    h.page.wait_for_selector("#pf-owner:not([hidden])")
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
