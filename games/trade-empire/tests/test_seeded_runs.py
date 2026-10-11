"""Z-1b -- seeded runs: hazards, guild offers and charter founding conditions come from one run seed."""

import json
import random


def test_the_same_seed_gives_the_same_hazards_and_a_different_seed_does_not(game_env):
    g = game_env.module
    g.run_seed = "TRADEEMPIRE-23456"
    first = [g.hazard_roll() for _ in range(30)]
    g.hazard_rolls = 0
    assert [g.hazard_roll() for _ in range(30)] == first
    g.hazard_rolls = 0
    g.run_seed = "TRADEEMPIRE-23457"
    assert [g.hazard_roll() for _ in range(30)] != first


def test_guild_offers_repeat_for_the_same_seed(game_env):
    g = game_env.module

    def offers(seed):
        g.run_seed, g.guild_offers = seed, 0
        out = []
        for _ in range(4):
            g._guild_clear(0)
            assert g.guild_make_offer() is True
            out.append((g.guild_contract["destination"], g.guild_contract["good"], g.guild_contract["units"]))
        return out

    assert offers("TRADEEMPIRE-BCDFG") == offers("TRADEEMPIRE-BCDFG")
    assert offers("TRADEEMPIRE-BCDFG") != offers("TRADEEMPIRE-HJKMN")


def test_a_fixed_override_still_wins_for_tests(game_env):
    g = game_env.module
    g.guild_rng = random.Random(1)
    g.hazard_rng = type("Fixed", (), {"random": staticmethod(lambda: 0.5)})()
    assert g.hazard_roll() == 0.5
    assert g.guild_make_offer() is True


def test_a_brand_new_save_has_no_seed_keys_and_old_saves_load_unchanged(game_env):
    g = game_env.module
    state = g.get_state()
    assert "run_seed" not in state and "rolls" not in state["route_hazards"] and "guild" not in state
    g.load_state(json.loads(json.dumps(state)))
    assert g.run_seed_draws() == 0 and g.run_seed_pinned is False


def test_a_typed_seed_is_saved_and_loaded(game_env):
    g = game_env.module
    ok, message = g.set_run_seed("tradeempire k7f2q")
    assert ok and g.run_seed == "TRADEEMPIRE-K7F2Q" and "set" in message
    data = json.loads(json.dumps(g.get_state()))
    assert data["run_seed"] == "TRADEEMPIRE-K7F2Q"
    g.run_seed, g.run_seed_pinned = "", False
    g.load_state(data)
    assert g.run_seed == "TRADEEMPIRE-K7F2Q" and g.run_seed_pinned is True


def test_a_bad_or_foreign_seed_is_refused_and_a_tampered_save_is_ignored(game_env):
    g = game_env.module
    for text in ("", "nonsense!", "GRID-K7F2Q"):
        ok, message = g.set_run_seed(text)
        assert not ok and message
    assert g.run_seed_pinned is False
    for bad in ("GRID-K7F2Q", 12, ["x"], "TRADEEMPIRE-0IOL1"):
        data = json.loads(json.dumps(g.get_state()))
        data["run_seed"] = bad
        g.load_state(data)
        assert g.run_seed_pinned is False and g.run_seed.startswith("TRADEEMPIRE-")  # a fresh one is made on render
        assert g.run_seed != "TRADEEMPIRE-0IOL1"


def test_the_seed_locks_once_it_has_been_used_and_the_stream_position_is_saved(game_env):
    g = game_env.module
    g.set_run_seed("TRADEEMPIRE-K7F2Q")
    g.route_hazards_enabled = True
    g.hazard_roll()
    g.hazard_roll()
    assert g.run_seed_changeable() is False
    ok, _ = g.set_run_seed("TRADEEMPIRE-23456")
    assert not ok and g.run_seed == "TRADEEMPIRE-K7F2Q"
    data = json.loads(json.dumps(g.get_state()))
    assert data["route_hazards"]["rolls"] == 2 and data["run_seed"] == "TRADEEMPIRE-K7F2Q"
    nxt = g.run_stream("hazard", 2).random()
    g.hazard_rolls = 0
    g.load_state(data)
    assert g.hazard_rolls == 2 and g.hazard_roll() == nxt


def test_a_tampered_roll_count_falls_back(game_env):
    g = game_env.module
    for bad in (-1, "x", True, 10**12):
        data = json.loads(json.dumps(g.get_state()))
        data["route_hazards"]["rolls"] = bad
        g.load_state(data)
        assert g.hazard_rolls == 0


def test_guild_offer_count_round_trips(game_env):
    g = game_env.module
    g.set_run_seed("TRADEEMPIRE-K7F2Q")
    assert g.guild_make_offer() is True
    data = json.loads(json.dumps(g.get_state()))
    assert data["guild"]["offers"] == 1
    g.guild_offers = 0
    g.load_state(data)
    assert g.guild_offers == 1
    data["guild"]["offers"] = "many"
    g.load_state(data)
    assert g.guild_offers == 0


def test_charter_founding_conditions_follow_the_seed(game_env):
    g = game_env.module

    def founding(seed, completed):
        g.run_seed, g.charters_completed = seed, completed
        g.apply_founding_conditions()
        return g.founding_seed

    assert founding("TRADEEMPIRE-BCDFG", 1) == founding("TRADEEMPIRE-BCDFG", 1)
    assert founding("TRADEEMPIRE-BCDFG", 1) != founding("TRADEEMPIRE-BCDFG", 2)
    assert founding("TRADEEMPIRE-BCDFG", 1) != founding("TRADEEMPIRE-HJKMN", 1)
    assert 1 <= g.founding_seed <= g.FOUNDING_SEED_MAX


def test_the_sandbox_gets_its_own_seed_and_the_real_one_comes_back(game_env):
    g = game_env.module
    g.set_run_seed("TRADEEMPIRE-K7F2Q")
    g.sandbox_enter()
    assert g.run_seed != "TRADEEMPIRE-K7F2Q" or g.run_seed_pinned is False
    g.sandbox_leave()
    assert g.run_seed == "TRADEEMPIRE-K7F2Q" and g.run_seed_pinned is True


def test_the_seed_panel_shows_copies_and_applies(game_env, monkeypatch):
    g = game_env.module
    el = game_env.elements
    g.render_market()
    assert el["run-seed-display"].innerText == "Run seed: TRADEEMPIRE-23456"
    copied = []
    monkeypatch.setattr(g, "_copy_text", lambda text: copied.append(text) or True)
    el["run-seed-copy-button"].dispatch("click", None)
    assert copied == ["TRADEEMPIRE-23456"] and "Copied" in el["run-seed-note"].innerText
    monkeypatch.setattr(g, "_copy_text", lambda text: False)
    el["run-seed-copy-button"].dispatch("click", None)
    assert "would not copy" in el["run-seed-note"].innerText
    el["run-seed-input"].value = "GRID-K7F2Q"
    el["run-seed-apply-button"].dispatch("click", None)
    assert "not this game" in el["run-seed-note"].innerText
    el["run-seed-input"].value = "tradeempire-k7f2q"
    el["run-seed-apply-button"].dispatch("click", None)
    assert el["run-seed-display"].innerText == "Run seed: TRADEEMPIRE-K7F2Q"
    g.route_hazards_enabled = True
    g.hazard_roll()
    g.render_market()
    assert el["run-seed-apply-button"].disabled is True and "fixed" in el["run-seed-note"].innerText


def test_a_renewal_keeps_the_seed_and_its_positions(game_env):
    g = game_env.module
    g.set_run_seed("TRADEEMPIRE-K7F2Q")
    g.hazard_roll()
    g.guild_make_offer()
    g.endgame_reached = True
    assert g.found_new_corporation() is True
    assert g.run_seed == "TRADEEMPIRE-K7F2Q" and g.hazard_rolls == 1 and g.guild_offers == 1
    assert g.founding_seed == g.run_stream("charter", 1).randint(1, g.FOUNDING_SEED_MAX)
