"""The hub's "Rarest things you own" strip (planning/TODO.md QI-45) in headless Chromium with the backend
mocked: it lists the five rarest earned achievements by the public earned_pct numbers, never ranks an
achievement whose percentage is withheld, hides when signed out or with nothing rankable, and writes server
text as plain text."""

SIGNED_IN = ("localStorage.setItem('hub_bearer_token','tok'); localStorage.setItem('hub_account_username','mara');"
             "localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1')")
SIGNED_OUT = "localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1')"


def save(game, earned):
    return {"game_id": game, "updated_at": "2026-10-09T10:00:00", "created_at": "2026-10-01T10:00:00",
            "save_code": "X-" + game, "save_data": {"achievements_earned": earned}}


def stats(**games):
    return {"min_bucket": 5, "games": games}


def open_hub(harness, init, saves, stat_body):
    h = harness(init_scripts=[init])
    h.api_responses[("GET", "/users/me/saves")] = (200, saves)
    h.api_responses[("GET", "/stats/achievements")] = (200, stat_body)
    h.goto("/index.html")
    return h


def rows(h):
    h.page.wait_for_timeout(1200)
    return h.page.evaluate("[...document.querySelectorAll('#rarest-list a')].map(a => a.textContent)")


def catalog_ids(game, n):
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parents[2] / "games" / game / "achievements.json").read_text())
    return [a["id"] for a in data["achievements"]][:n], {a["id"]: a["label"] for a in data["achievements"]}


def test_lists_the_rarest_earned_first_and_caps_at_five(harness):
    ids, labels = catalog_ids("canopy", 7)
    pcts = [50.0, 3.2, 12.0, 80.0, 7.5, 20.0, 1.1]
    s = stats(canopy={"suppressed": False, "save_count": 40, "achievements": {i: {"earned_pct": p} for i, p in zip(ids, pcts)}})
    h = open_hub(harness, SIGNED_IN, [save("canopy", ids)], s)
    out = rows(h)
    assert len(out) == 5
    assert out[0].startswith(labels[ids[6]]) and "1.1%" in out[0] and "Gold" in out[0]
    assert "Bronze" not in " ".join(out[:3])
    assert h.page.is_visible("#rarest-section")


def test_withheld_percentages_are_never_ranked(harness):
    ids, labels = catalog_ids("canopy", 3)
    s = stats(canopy={"suppressed": False, "save_count": 40, "achievements": {ids[0]: {"earned_pct": 9.0}}})
    h = open_hub(harness, SIGNED_IN, [save("canopy", ids)], s)
    out = rows(h)
    assert len(out) == 1 and labels[ids[0]] in out[0]


def test_suppressed_game_and_unearned_ones_are_skipped_and_section_hides(harness):
    ids, _ = catalog_ids("canopy", 2)
    s = stats(canopy={"suppressed": True, "save_count": 1, "achievements": {ids[0]: {"earned_pct": 1.0}}})
    h = open_hub(harness, SIGNED_IN, [save("canopy", ids)], s)
    assert rows(h) == []
    assert h.page.is_hidden("#rarest-section")


def test_signed_out_visitors_never_see_it(harness):
    ids, _ = catalog_ids("canopy", 2)
    s = stats(canopy={"suppressed": False, "save_count": 40, "achievements": {ids[0]: {"earned_pct": 1.0}}})
    h = open_hub(harness, SIGNED_OUT, [], s)
    assert h.page.is_hidden("#rarest-section")


def test_server_text_stays_text(harness):
    ids, _ = catalog_ids("canopy", 1)
    s = stats(canopy={"suppressed": False, "save_count": 40, "achievements": {ids[0]: {"earned_pct": 2}}})
    h = open_hub(harness, SIGNED_IN, [save("canopy", ids)], s)
    rows(h)
    assert h.page.evaluate("document.querySelectorAll('#rarest-list *:not(li):not(a)').length") == 0
