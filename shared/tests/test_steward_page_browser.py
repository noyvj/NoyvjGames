"""The hub's Climate Steward page (planning/TODO.md B-23) in headless Chromium with the backend mocked: one portrait of
the eight climate worlds read from the signed-in account's most recent save of each game. A game's optional `summary`
list is validated (bad items dropped), Canopy is read from fields it already saves, the newest save wins, signed-out
visitors and games without a save get an honest empty state, and nothing is ever sent except the one GET."""

QUIET = "localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1')"
SIGNED_IN = QUIET + ";localStorage.setItem('hub_bearer_token','tok')"
SLUGS = ["canopy", "grid", "tide", "aftermath", "herd", "thaw", "loop", "drift"]


def save(game, when, data):
    return {"game_id": game, "updated_at": when, "save_data": data}


def open_page(harness, init=SIGNED_IN, saves=None, size=(1440, 900), status=200):
    h = harness(init_scripts=[init], size=size)
    if saves is not None:
        h.api_responses[("GET", "/users/me/saves")] = (status, saves)
    h.goto("/steward.html")
    h.page.wait_for_selector("#steward-grid li")
    return h


def card_text(h, slug):
    return h.page.inner_text("#" + slug)


def test_signed_out_shows_an_honest_empty_state(harness):
    h = open_page(harness, QUIET)
    assert "Sign in" in h.page.inner_text("#steward-summary")
    assert h.page.locator("#steward-grid > li").count() == 8
    assert "Not read yet" in card_text(h, "tide")
    assert [c for c in h.api_calls if c[1] == "/users/me/saves"] == []
    assert "tending" not in h.page.inner_text("main")
    assert h.errors == []


def test_signed_in_with_a_mix_of_games(harness):
    saves = [
        save("canopy", "2026-10-09T12:00:00", {
            "standing_value": 1234.5, "community_relations": 62, "total_replants": 7, "total_recoveries": 2}),
        save("tide", "2026-10-09T12:00:00", {"summary": [
            {"label": "Coastline rows still dry", "value": 5, "unit": "of 6"},
            {"label": "Settlers housed", "value": 120, "unit": ""},
            {"label": "Seawall tier", "value": 2, "unit": "of 4", "note": "Seawalls"}]}),
        save("thaw", "2026-10-09T12:00:00", {"summary": [{"label": "Warming held back", "value": 1.25, "unit": "°C"}]}),
    ]
    h = open_page(harness, saves=saves)
    assert h.page.inner_text("#steward-summary") == "You are tending 3 of 8 climate worlds."
    portrait = h.page.inner_text("#steward-portrait")
    assert "Canopy, Tide and Thaw" in portrait and "Still waiting for you" in portrait and "Grid" in portrait
    canopy = card_text(h, "canopy")
    assert "Standing forest value" in canopy and "1,234.5" in canopy and "62 of 100" in canopy and "Plots replanted" in canopy
    assert "Plots recovered" not in canopy  # at most three numbers per card
    tide = card_text(h, "tide")
    assert "5 of 6" in tide and "Seawalls" in tide and "2 of 4" in tide
    assert "1.3°C" in card_text(h, "thaw") or "1.2°C" in card_text(h, "thaw")
    assert "No save yet" in card_text(h, "grid")
    assert h.page.get_attribute("#tide a.steward-card-link", "href").endswith("games/tide/index.html")
    assert "read from your saves only" in h.page.inner_text("#steward-note")
    assert h.errors == []


def test_every_number_with_a_bar_has_its_number_beside_it(harness):
    saves = [save("tide", "2026-10-09T12:00:00", {"summary": [{"label": "Rows", "value": 3, "unit": "of 6"}]})]
    h = open_page(harness, saves=saves)
    row = h.page.evaluate("""() => { const dd = document.querySelector('#tide .steward-stat-value');
      return { number: dd.querySelector('.steward-stat-number').textContent, bar: !!dd.querySelector('.steward-bar'),
               hidden: dd.querySelector('.steward-bar').getAttribute('aria-hidden') }; }""")
    assert row == {"number": "3 of 6", "bar": True, "hidden": "true"}


def test_malformed_summaries_are_ignored(harness):
    good = {"label": "Rows", "value": 3, "unit": "of 6"}
    saves = [
        save("tide", "2026-10-09T12:00:00", {"summary": [
            good,
            {"label": "", "value": 1, "unit": ""},
            {"label": "x" * 41, "value": 1, "unit": ""},
            {"label": "Not a number", "value": "9", "unit": ""},
            {"label": "Long unit", "value": 1, "unit": "u" * 13},
            "nonsense", None, 5,
        ]}),
        save("grid", "2026-10-09T12:00:00", {"summary": "not a list"}),
        save("herd", "2026-10-09T12:00:00", {"summary": [{"label": "A", "value": 1, "unit": ""}] * 9 + [{"label": "Late", "value": 2}]}),
        save("loop", "2026-10-09T12:00:00", "not an object"),
        save("canopy", "2026-10-09T12:00:00", {"standing_value": "lots", "community_relations": 900}),
    ]
    h = open_page(harness, saves=saves)
    tide = card_text(h, "tide")
    assert "Rows" in tide and "Not a number" not in tide and "Long unit" not in tide
    assert h.page.locator("#tide .steward-stat").count() == 1
    assert "does not carry summary numbers" in card_text(h, "grid")
    assert "Late" not in card_text(h, "herd")
    assert "does not carry summary numbers" in card_text(h, "loop")
    assert "does not carry summary numbers" in card_text(h, "canopy")
    assert h.page.inner_text("#steward-summary") == "You are tending 5 of 8 climate worlds."
    assert h.errors == []


def test_text_is_never_interpreted_as_html(harness):
    saves = [save("tide", "2026-10-09T12:00:00", {"summary": [
        {"label": "<img src=x onerror=alert(1)>", "value": 1, "unit": "", "note": "<b>bold</b>"}]})]
    h = open_page(harness, saves=saves)
    assert h.page.locator("#tide img, #tide b").count() == 0
    assert "<img" in card_text(h, "tide") and "<b>bold</b>" in card_text(h, "tide")


def test_most_recent_save_wins(harness):
    old = {"summary": [{"label": "Rows", "value": 1, "unit": "of 6"}]}
    new = {"summary": [{"label": "Rows", "value": 4, "unit": "of 6"}]}
    saves = [save("tide", "2026-10-09T12:00:00", new), save("tide", "2026-10-01T12:00:00", old),
             save("tide", "2026-10-05T12:00:00", old)]
    h = open_page(harness, saves=saves)
    assert "4 of 6" in card_text(h, "tide") and "1 of 6" not in card_text(h, "tide")
    assert "2026-10-09" in card_text(h, "tide")


def test_unreadable_saves_do_not_break_the_page(harness):
    h = open_page(harness, saves={"detail": "x"}, status=500)
    assert "could not be read" in h.page.inner_text("#steward-summary")
    assert h.page.locator("#steward-grid > li").count() == 8
    assert h.errors == []


def test_nothing_is_sent_except_the_one_get(harness):
    h = open_page(harness, saves=[save("canopy", "2026-10-09T12:00:00", {"standing_value": 5})])
    gets = [c for c in h.api_calls if c[1] == "/users/me/saves"]
    assert gets and all(c[0] == "GET" for c in gets)
    # (the shared theme sync may PUT /users/me/settings; that is site-wide infrastructure, not this page)
    assert [c for c in h.api_calls if c[0] != "GET" and c[1] != "/users/me/settings"] == []


def test_no_account_with_zero_saves_says_so(harness):
    h = open_page(harness, saves=[])
    assert h.page.inner_text("#steward-summary") == "You are tending 0 of 8 climate worlds."
    assert "None of the climate worlds has a save yet" in h.page.inner_text("#steward-portrait")


def test_fits_a_phone_and_light_theme(harness):
    saves = [save(s, "2026-10-09T12:00:00", {"summary": [
        {"label": "Warming pulled back by restoration", "value": 1234567.8, "unit": "of 9999999"},
        {"label": "A", "value": 1, "unit": "%"}]}) for s in SLUGS]
    h = open_page(harness, SIGNED_IN, saves, size=(360, 740))
    assert h.page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert h.page.evaluate("[...document.querySelectorAll('.steward-card-link')].every(a => a.getBoundingClientRect().height >= 44)")
    h.page.evaluate("document.documentElement.setAttribute('data-theme','light')")
    bg = h.page.evaluate("getComputedStyle(document.querySelector('.steward-card')).backgroundColor")
    assert bg.startswith("rgba(255, 255, 255") or bg.startswith("rgb(255, 255, 255")
    assert h.errors == []
