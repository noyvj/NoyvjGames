"""Warm night colours and half-asleep mode on the hub (planning/TODO.md QI-52, QI-51): the hub and the
settings page load the shared files, the settings page mounts both controls, and the hub grid shows only
calm games while calm is on without fighting the search filter."""

QUIET = "localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1')"


def open_hub(harness, init=(), path="/index.html"):
    h = harness(init_scripts=[QUIET] + list(init))
    h.goto(path)
    h.page.wait_for_function("document.querySelectorAll('.title-card-session').length > 0" if path == "/index.html" else "true")
    return h


def visible_slugs(h):
    return h.page.evaluate("""[...document.querySelectorAll('.title-card')].filter(c => !c.hidden)
      .map(c => c.querySelector('.review-widget').dataset.gameSlug)""")


def test_hub_loads_both_shared_files_and_night_is_off_by_default(harness):
    h = open_hub(harness)
    assert h.page.evaluate("typeof NoyvjNight === 'object' && typeof NoyvjCalm === 'object'")
    assert h.page.get_attribute("html", "data-night") == "off"
    assert h.page.get_attribute("html", "data-calm") in (None, "false")
    assert len(visible_slugs(h)) >= 20


def test_night_mode_on_tints_the_hub(harness):
    h = open_hub(harness, init=["localStorage.setItem('noyvj-night:mode','on')"])
    assert h.page.get_attribute("html", "data-night") == "on"
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-night-overlay')).opacity") != "0"


def test_calm_mode_shows_only_calm_games_and_restores(harness):
    h = open_hub(harness)
    everything = visible_slugs(h)
    h.page.evaluate("NoyvjCalm.setOn(true)")
    calm = visible_slugs(h)
    assert 0 < len(calm) < len(everything)
    assert all(s in h.page.evaluate("NoyvjCalm.CALM_GAMES") for s in calm)
    h.page.evaluate("NoyvjCalm.setOn(false)")
    assert visible_slugs(h) == everything


def test_calm_off_does_not_unhide_cards_the_search_hid(harness):
    h = open_hub(harness)
    h.page.fill("#game-search-input", "canopy")
    h.page.wait_for_load_state("networkidle")      # the extended search index widens the match once it loads
    h.page.fill("#game-search-input", "canopy ")
    h.page.fill("#game-search-input", "canopy")
    searched = visible_slugs(h)
    assert "canopy" in searched and 0 < len(searched) < 20
    h.page.evaluate("NoyvjCalm.setOn(true)")
    assert set(visible_slugs(h)) == set(searched) & set(h.page.evaluate("NoyvjCalm.CALM_GAMES"))
    h.page.evaluate("NoyvjCalm.setOn(false)")
    assert visible_slugs(h) == searched


def test_search_changes_while_calm_is_on_stay_calm_only(harness):
    h = open_hub(harness)
    h.page.evaluate("NoyvjCalm.setOn(true)")
    h.page.fill("#game-search-input", "sol")
    assert all(s in h.page.evaluate("NoyvjCalm.CALM_GAMES") for s in visible_slugs(h))
    h.page.fill("#game-search-input", "")
    assert len(visible_slugs(h)) > 0


def test_settings_page_mounts_both_controls(harness):
    h = open_hub(harness, path="/settings.html")
    assert h.page.locator("#settings-night-slot .noyvj-night-control").count() == 1
    assert h.page.locator("#settings-calm-slot .noyvj-calm-control").count() == 1
    h.page.select_option("#settings-night-slot select >> nth=0", "on")
    assert h.page.evaluate("localStorage.getItem('noyvj-night:mode')") == "on"
    assert h.errors == []
