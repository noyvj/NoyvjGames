"""GG-22: a supply crate every sixth round, with a fixed, announced perk."""

import json


def _advance_to_round(game_env, target):
    while game_env.region.round_number < target:
        game_env.advance_round()


def test_none_at_the_start_and_next_round_is_named(game_env):
    m = game_env.module
    assert m.crates_ready() == 0
    assert m.next_crate_round() == 7
    text = game_env.elements["crate-display"].innerText
    assert "No supply crate waiting" in text and "round 7" in text and "a Preserve unit" in text
    assert game_env.elements["crate-open-button"].disabled is True
    assert "supply crate" not in json.dumps(m.get_state())


def test_a_crate_lands_when_round_seven_starts_and_waits(game_env):
    m = game_env.module
    _advance_to_round(game_env, 6)
    assert m.crates_ready() == 0
    game_env.advance_round()
    assert m.region.round_number == 7
    assert m.crates_ready() == 1
    assert game_env.elements["crate-open-button"].disabled is False
    assert "1 supply crate waiting" in game_env.elements["crate-display"].innerText
    assert "A supply crate arrived." in game_env.elements["sr-announcer"].innerText
    assert any("supply crate arrived" in e["text"] for e in m.science_log)
    for _ in range(3):
        game_env.advance_round()
    assert m.crates_ready() == 1  # it does not expire or stack by itself


def test_arrives_every_sixth_round(game_env):
    m = game_env.module
    _advance_to_round(game_env, 20)
    assert m.crates_delivered == 3  # rounds 7, 13, 19
    assert m.next_crate_round() == 25


def test_perks_rotate_in_a_fixed_order(game_env):
    m = game_env.module
    assert [m.crate_perk(n)[0] for n in range(1, 7)] == ["preserve", "monitor", "funds"] * 2


def test_opening_gives_the_announced_perk_to_the_least_protected_region(game_env):
    m = game_env.module
    for _ in range(2):
        game_env.invest("preserve")        # A is protected; B and C are not
    _advance_to_round(game_env, 7)
    before_b = m.region_b.capacity["preserve"]
    assert "Region B right now" in game_env.elements["crate-display"].innerText
    game_env.elements["crate-open-button"].dispatch("click", None)
    assert m.region_b.capacity["preserve"] == before_b + 1
    assert m.crates_ready() == 0 and m.crates_opened == 1
    assert game_env.elements["crate-visual"].className.count("crate-opening") == 1
    assert any("supply crate opened" in e["text"] for e in m.science_log)
    assert m.log_kind(m.science_log[-1]) == "invest"
    assert game_env.elements["crate-open-button"].disabled is True
    # the opening cue is one render only
    m.render()
    assert "crate-opening" not in game_env.elements["crate-visual"].className


def test_monitor_then_funds_crates(game_env):
    m = game_env.module
    _advance_to_round(game_env, 13)
    assert m.crates_ready() == 2
    monitors = sum(r.capacity["monitor"] for r in (m.region, m.region_b, m.region_c))
    game_env.elements["crate-open-button"].dispatch("click", None)  # preserve
    game_env.elements["crate-open-button"].dispatch("click", None)  # monitor
    assert sum(r.capacity["monitor"] for r in (m.region, m.region_b, m.region_c)) == monitors + 1
    _advance_to_round(game_env, 19)
    poorest = min((m.region, m.region_b, m.region_c), key=lambda r: r.funds)
    before = poorest.funds
    assert m.open_crate() is not None
    assert poorest.funds == before + m.CRATE_FUNDS


def test_open_with_nothing_waiting_does_nothing(game_env):
    m = game_env.module
    assert m.open_crate() is None
    game_env.elements["crate-open-button"].dispatch("click", None)
    assert m.crates_opened == 0


def test_shelf_counts_what_has_been_opened(game_env):
    m = game_env.module
    _advance_to_round(game_env, 19)
    for _ in range(3):
        m.open_crate()
    assert m.crate_shelf_counts() == {"preserve": 1, "monitor": 1, "funds": 1}
    assert "Opened so far: 3 (1 Preserve, 1 Monitor, 1 funds)" in m.crate_text()


def test_region_d_gets_nothing_from_crates(game_env):
    m = game_env.module
    _advance_to_round(game_env, 7)
    before = dict(m.region_d.capacity)
    m.open_crate()
    assert m.region_d.capacity["preserve"] == before["preserve"]
    assert m.region_d.capacity["monitor"] == before["monitor"] == 0


def test_saves_round_trip_and_old_saves_load_unchanged(game_env):
    m = game_env.module
    _advance_to_round(game_env, 13)
    m.open_crate()
    state = json.loads(json.dumps(m.get_state()))
    assert state["crates"] == {"delivered": 2, "opened": 1}
    m.crates_delivered = m.crates_opened = 0
    assert m.load_state(state)
    assert (m.crates_delivered, m.crates_opened) == (2, 1)
    state.pop("crates")
    assert m.load_state(state)
    assert (m.crates_delivered, m.crates_opened) == (0, 0)
    # an old save simply gets its next crate at the next multiple (round 13 now, so 19)
    assert m.next_crate_round() == 19


def test_bad_crate_fields_are_replaced_and_named(game_env):
    m = game_env.module
    _advance_to_round(game_env, 7)
    base = json.loads(json.dumps(m.get_state()))
    for bad in ({"delivered": 1, "opened": 2}, {"delivered": -1, "opened": 0}, {"delivered": "x", "opened": 0},
                {"delivered": True, "opened": 0}, {"delivered": 10 ** 9, "opened": 0}, {"delivered": 1}):
        state = dict(base, crates=bad)
        assert m.load_state(state)
        assert (m.crates_delivered, m.crates_opened) == (0, 0), bad
        assert "supply crates" in m.load_problems
    state = dict(base, crates="nope")
    assert m.load_state(state)
    assert "supply crates" in m.load_problems
    assert m.crates_delivered == 0


def test_rewind_takes_a_crate_back_with_the_round(game_env):
    m = game_env.module
    _advance_to_round(game_env, 6)
    game_env.advance_round()
    assert m.crates_ready() == 1
    assert m.undo_last_round() is not False
    assert m.crates_ready() == 0
