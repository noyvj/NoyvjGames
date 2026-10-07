"""J-14 -- the charter crest beside the title (a shape plus a word) and the
career log of completed charters in the Charter panel."""

import pytest


def _renew(module, times=1):
    for _ in range(times):
        module.endgame_reached = True
        assert module.found_new_corporation() is True


def _trip(game_env):
    game_env.load()
    game_env.depart("ferrum")
    game_env.tick(game_env.module.TRAVEL_TICKS)


@pytest.mark.parametrize("done,label,glyph", [
    (0, "Founder", "●"), (1, "Renewed", "▲"), (2, "Renewed", "▲"), (3, "Veteran", "■"),
    (4, "Veteran", "■"), (5, "Master", "◆"), (9, "Master", "◆"), (10, "Sovereign", "★"),
    (500, "Sovereign", "★"),
])
def test_crest_tiers_pair_a_word_with_a_distinct_shape(game_env, done, label, glyph):
    assert game_env.module.crest_for(done) == (label, glyph)


def test_every_tier_has_its_own_shape_and_word(game_env):
    tiers = game_env.module.CREST_TIERS
    assert len({t[1] for t in tiers}) == len(tiers) == len({t[2] for t in tiers})


def test_the_title_crest_updates_with_renewals_and_names_the_charter_kind(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["charter-crest"].innerText == "● Founder"
    _renew(m)
    assert game_env.elements["charter-crest"].innerText == "▲ Renewed"
    assert "Charters completed: 1" in game_env.elements["charter-crest"].title
    m.hard_charter_active = True
    m.render()
    assert game_env.elements["charter-crest"].innerText.endswith("(harder)")


def test_the_career_log_starts_empty_with_an_explanation(game_env):
    game_env.toggle_charter()
    items = game_env.elements["charter-career-list"].children
    assert len(items) == 1 and "No completed charters logged yet" in items[0].innerText
    assert "Active crest: ● Founder" in game_env.elements["charter-crest-display"].innerText


def test_a_renewal_logs_the_charter_it_just_finished(game_env):
    m = game_env.module
    _trip(game_env)
    units = m.ledger_charter_units
    peak = m.max_profit_ever
    assert units > 0
    _renew(m)
    assert m.charter_career == [{"n": 1, "hard": False, "units": units, "routes": 1, "peak": int(peak), "perks": 0}]
    assert m.ledger_charter_units == 0  # the new charter starts counting from zero
    assert m.ledger_units_moved >= units  # the lifetime ledger keeps it


def test_the_log_grows_with_each_renewal_and_lists_newest_first(game_env):
    m = game_env.module
    _renew(m)
    _trip(game_env)
    _renew(m)
    assert [e["n"] for e in m.charter_career] == [1, 2]
    game_env.toggle_charter()
    texts = [c.innerText for c in game_env.elements["charter-career-list"].children]
    assert texts[0].startswith("▲ Charter 2 (Renewed crest)") and "Charter 1" in texts[1]
    assert "units moved" in texts[0] and "peak profit" in texts[0] and "perk(s) owned" in texts[0]


def test_a_harder_charter_is_flagged_in_the_log(game_env):
    m = game_env.module
    _renew(m)
    m.hard_charter_next = True
    _renew(m)  # begins a harder charter
    assert m.hard_charter_active is True
    _renew(m)  # finishes it
    assert m.charter_career[-1]["hard"] is True and m.charter_career[0]["hard"] is False
    game_env.toggle_charter()
    assert game_env.elements["charter-career-list"].children[0].innerText.split(" ")[1:3] == ["Harder", "charter"]


def test_the_log_is_capped(game_env):
    m = game_env.module
    m.charter_career = [{"n": i, "hard": False, "units": 1, "routes": 1, "peak": 1, "perks": 0} for i in range(1, m.CAREER_MAX_ENTRIES + 1)]
    m.charters_completed = m.CAREER_MAX_ENTRIES
    _renew(m)
    assert len(m.charter_career) == m.CAREER_MAX_ENTRIES and m.charter_career[-1]["n"] == m.CAREER_MAX_ENTRIES + 1


def test_the_career_round_trips_through_a_save(game_env):
    m = game_env.module
    _trip(game_env)
    _renew(m)
    _trip(game_env)
    saved = m.get_state()
    assert len(saved["charter"]["career"]) == 1 and saved["ledger"]["charter_units"] == m.ledger_charter_units
    entry = dict(m.charter_career[0])
    units = m.ledger_charter_units
    m.charter_career = []
    m.ledger_charter_units = 0
    m.load_state(saved)
    assert m.charter_career == [entry] and m.ledger_charter_units == units


def test_a_fresh_game_writes_no_career_data(game_env):
    saved = game_env.module.get_state()
    assert "charter" not in saved and "ledger" not in saved


@pytest.mark.parametrize("bad_entry", [
    "x", 5, None, {}, {"n": 0, "hard": False, "units": 1, "routes": 1, "peak": 1, "perks": 0},
    {"n": 1, "hard": "yes", "units": 1, "routes": 1, "peak": 1, "perks": 0},
    {"n": 1, "hard": False, "units": -1, "routes": 1, "peak": 1, "perks": 0},
    {"n": 1, "hard": False, "units": True, "routes": 1, "peak": 1, "perks": 0},
    {"n": 1, "hard": False, "units": 1, "routes": 10**9, "peak": 1, "perks": 0},
    {"n": 1, "hard": False, "units": 1, "routes": 1, "peak": 1, "perks": 99},
    {"n": 1, "hard": False, "units": 1, "routes": 1.5, "peak": 1, "perks": 0},
])
def test_tampered_entries_are_dropped(game_env, bad_entry):
    m = game_env.module
    _renew(m)
    saved = m.get_state()
    saved["charter"]["career"] = [bad_entry]
    m.load_state(saved)
    assert m.charter_career == []


@pytest.mark.parametrize("bad", [None, "x", 5, {"a": 1}, True])
def test_a_tampered_career_value_falls_back_to_empty(game_env, bad):
    m = game_env.module
    _renew(m)
    saved = m.get_state()
    saved["charter"]["career"] = bad
    m.load_state(saved)
    assert m.charter_career == []


def test_the_log_never_holds_more_than_the_completed_charters(game_env):
    m = game_env.module
    _renew(m)
    saved = m.get_state()
    row = {"n": 1, "hard": False, "units": 1, "routes": 1, "peak": 1, "perks": 0}
    saved["charter"]["career"] = [dict(row, n=n) for n in (1, 2, 3, 4)]
    m.load_state(saved)
    assert len(m.charter_career) == 1


def test_saves_from_before_the_log_load_with_an_empty_one(game_env):
    m = game_env.module
    _renew(m, 2)
    saved = m.get_state()
    saved["charter"].pop("career")
    saved.get("ledger", {}).pop("charter_units", None)
    m.load_state(saved)
    assert m.charter_career == [] and m.ledger_charter_units == 0 and m.charters_completed == 2
    game_env.toggle_charter()
    assert "No completed charters" in game_env.elements["charter-career-list"].children[0].innerText


def test_charter_units_cannot_exceed_the_lifetime_ledger(game_env):
    m = game_env.module
    _trip(game_env)
    saved = m.get_state()
    saved["ledger"]["charter_units"] = saved["ledger"]["units"] + 500
    m.load_state(saved)
    assert m.ledger_charter_units == m.ledger_units_moved
