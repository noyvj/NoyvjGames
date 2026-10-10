"""The hub's 100% map page (planning/TODO.md QI-44) in headless Chromium with the backend mocked: one ring per
game from game-manifest.json, rings fill from the signed-in account's most recent saves, the list of what is
left is plain text, signed-out visitors see empty rings and a sign-in hint, and the order can be switched."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "game-manifest.json").read_text())["achievements"]
QUIET = "localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1')"
SIGNED_IN = QUIET + ";localStorage.setItem('hub_bearer_token','tok')"


def catalog(game):
    return json.loads((ROOT / "games" / game / "achievements.json").read_text())["achievements"]


def open_map(harness, init, saves=None, size=(1440, 900)):
    h = harness(init_scripts=[init], size=size)
    if saves is not None:
        h.api_responses[("GET", "/users/me/saves")] = (200, saves)
    h.goto("/map.html")
    h.page.wait_for_selector("#map-grid li")
    return h


def node(h, slug):
    return h.page.evaluate("""(slug) => { const d = document.getElementById(slug); return d && {
      complete: d.dataset.complete, count: d.querySelector('.map-node-count').textContent,
      ring: d.querySelector('.map-ring').getAttribute('aria-label'), left: d.querySelectorAll('.map-left li').length }; }""", slug)


def test_one_node_per_game_with_achievements_and_signed_out_rings_are_empty(harness):
    h = open_map(harness, QUIET)
    n = h.page.locator("#map-grid > li").count()
    assert n >= len(MANIFEST) - 2 and n > 20
    assert "not signed in" in h.page.inner_text("#map-summary")
    assert "Sign in" in h.page.inner_text("#map-note")
    c = node(h, "canopy")
    assert c["complete"] == "false" and c["left"] == len(catalog("canopy"))
    assert h.errors == []


def test_rings_fill_from_the_most_recent_save(harness):
    ids = [a["id"] for a in catalog("canopy")]
    saves = [
        {"game_id": "canopy", "updated_at": "2026-10-01T10:00:00", "save_data": {"achievements_earned": ids[:1]}},
        {"game_id": "canopy", "updated_at": "2026-10-09T10:00:00", "save_data": {"achievements_earned": ids[:3]}},
    ]
    h = open_map(harness, SIGNED_IN, saves)
    c = node(h, "canopy")
    assert c["count"].startswith("3 of %d earned" % len(ids))
    assert c["left"] == len(ids) - 3
    assert f"3 of {len(ids)} achievements" in c["ring"]
    assert "Closest to finished: Canopy" in h.page.inner_text("#map-next")


def test_a_finished_game_is_marked_complete_in_words(harness):
    ids = [a["id"] for a in catalog("canopy")]
    saves = [{"game_id": "canopy", "updated_at": "2026-10-09T10:00:00", "save_data": {"achievements_earned": ids}}]
    h = open_map(harness, SIGNED_IN, saves)
    c = node(h, "canopy")
    assert c["complete"] == "true" and c["count"].startswith("Complete")
    assert h.page.locator("#canopy .map-left").count() == 0
    assert "Everything in this game is earned" in h.page.text_content("#canopy")


def test_order_switch_puts_the_closest_game_first(harness):
    ids = [a["id"] for a in catalog("tide")]
    saves = [{"game_id": "tide", "updated_at": "2026-10-09T10:00:00", "save_data": {"achievements_earned": ids[:-1]}}]
    h = open_map(harness, SIGNED_IN, saves)
    h.page.click('#map-controls button[data-order="close"]')
    first = h.page.evaluate("document.querySelector('#map-grid details').id")
    assert first == "tide"
    assert h.page.get_attribute('#map-controls button[data-order="close"]', "aria-pressed") == "true"


def test_unreadable_saves_fall_back_to_the_signed_out_view(harness):
    h = harness(init_scripts=[SIGNED_IN])
    h.api_responses[("GET", "/users/me/saves")] = (500, {"detail": "x"})
    h.goto("/map.html")
    h.page.wait_for_selector("#map-grid li")
    assert "not signed in" in h.page.inner_text("#map-summary") or "empty" in h.page.inner_text("#map-summary")


def test_fits_a_phone(harness):
    h = open_map(harness, QUIET, size=(360, 740))
    assert h.page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert h.page.evaluate("[...document.querySelectorAll('.map-node summary')].every(s => s.getBoundingClientRect().height >= 44)")


def test_hash_opens_that_game(harness):
    h = harness(init_scripts=[QUIET])
    h.goto("/map.html#tide")
    h.page.wait_for_selector("#map-grid li")
    assert h.page.evaluate("document.getElementById('tide').open") is True
