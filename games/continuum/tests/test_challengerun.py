"""K-10 daily challenge and K-11 scenario editor / mod codes."""

import json

import pytest

import challengerun as cr
import sim
import techdebt


# --- configs and codes ---------------------------------------------------------------
def test_default_config_is_the_standard_start():
    cfg = cr.default_config()
    assert (cfg["population"], cfg["food"], cfg["materials"], cfg["tools"], cfg["land"]) == (6, 20, 20, 2, 100)
    assert cfg["goal"] == 40 and cfg["modifier"] == "" and cfg["hard"] is False


def test_snap_clamps_and_rounds_onto_the_grid():
    assert cr.snap("population", 99) == 15 and cr.snap("population", -3) == 4
    assert cr.snap("land", 77) == 75 and cr.snap("goal", 43) == 45
    assert cr.snap("food", "oops") == 5 and cr.snap("food", float("nan")) == 5
    assert cr.snap("tools", None) == 0


def test_clean_config_ignores_junk():
    cfg = cr.clean_config({"population": "x", "modifier": ["a"], "hard": "yes", "goal": 1000})
    assert cfg["goal"] == 80 and cfg["modifier"] == "" and cfg["hard"] is False
    assert cr.clean_config(None) == cr.default_config()


def test_config_from_scenario_matches_the_named_scenarios():
    for scenario_id, base in sim.SCENARIOS.items():
        cfg = cr.config_from_scenario(scenario_id)
        assert cfg["population"] == min(15, max(4, base["population"]))
        assert cfg["food"] == int(base["food"]) and cfg["land"] == round(base["land_health"] * 100)


def test_every_setup_round_trips_through_its_code():
    for population in (4, 9, 15):
        for goal in (20, 55, 80):
            for modifier in cr.MODIFIER_IDS:
                for hard in (False, True):
                    cfg = cr.clean_config({"population": population, "goal": goal, "modifier": modifier,
                                           "hard": hard, "food": 37, "materials": 59, "tools": 5, "land": 65})
                    code = cr.encode(cfg)
                    assert code.startswith("CNT-") and len(code) == 14
                    back, error = cr.decode(code)
                    assert error == "" and back == cfg


def test_code_decoding_forgives_case_spacing_and_the_prefix():
    cfg = cr.default_config()
    code = cr.encode(cfg)
    assert cr.decode(code.lower())[0] == cfg
    assert cr.decode(" " + code.replace("-", " ") + " ")[0] == cfg
    assert cr.decode(code[4:])[0] == cfg


def test_bad_codes_explain_themselves():
    assert cr.decode("")[0] is None and cr.decode(None)[0] is None
    assert "not a mod code" in cr.decode("CNT-AB")[1]
    assert "not a mod code" in cr.decode("CNT-????-?????")[1]
    code = cr.encode(cr.default_config())
    body = code[4:].replace("-", "")
    bad = body[:-1] + ("A" if body[-1] != "A" else "B")
    assert "does not check out" in cr.decode(bad)[1]


def test_no_code_decodes_outside_the_ranges():
    # every 9-character body either fails or yields a config inside the ranges
    import random
    rng = random.Random(7)
    for _ in range(300):
        body = "".join(rng.choice(cr.ALPHABET) for _ in range(9))
        cfg, error = cr.decode(body)
        if cfg is not None:
            for name, (low, high, _step) in cr.RANGES.items():
                assert low <= cfg[name] <= high


def test_distinct_setups_get_distinct_codes():
    a = cr.encode(cr.clean_config({"population": 7}))
    b = cr.encode(cr.clean_config({"population": 8}))
    assert a != b


# --- the daily --------------------------------------------------------------------------
def test_the_daily_is_stable_per_date_and_valid():
    one = cr.daily("2026-10-08")
    assert one == cr.daily("2026-10-08")
    assert one["seed"] == "CONTINUUM-XTXJR"
    assert one["config"]["modifier"] in cr.MODIFIERS and one["scenario"] in cr.DAILY_BASES
    assert one["config"]["goal"] == cr.DAILY_GOAL
    assert cr.decode(cr.encode(one["config"]))[0] == one["config"]


def test_the_daily_varies_across_days():
    seen = {(d["scenario"], d["config"]["modifier"], d["config"]["hard"])
            for d in (cr.daily(f"2026-11-{n:02d}") for n in range(1, 29))}
    assert len(seen) > 8
    assert any(hard for _s, _m, hard in seen) and not all(hard for _s, _m, hard in seen)


def test_daily_with_a_bad_date_is_none():
    assert cr.daily("not a date") is None


# --- modifiers -----------------------------------------------------------------------------
def test_every_modifier_only_uses_real_effect_keys_and_is_a_trade():
    for mod_id, mod in cr.MODIFIERS.items():
        assert len(mod["effects"]) >= 2, mod_id
        for key in mod["effects"]:
            assert key in sim.NEUTRAL_EFFECTS, (mod_id, key)
        assert mod["label"] and mod["blurb"]
    assert len(cr.MODIFIER_IDS) <= 16  # four bits in the code


def test_modifier_effects_multiply_or_add_and_never_mutate():
    ui = {cr.KEY: {"kind": "custom", "config": cr.clean_config({"modifier": "bumper_harvest"})}}
    base = dict(sim.NEUTRAL_EFFECTS)
    base["food_yield_mult"] = 1.5
    out = cr.apply_effects(base, ui)
    assert out["food_yield_mult"] == pytest.approx(1.8) and out["food_storage_bonus"] == -10.0
    assert base["food_yield_mult"] == 1.5 and base["food_storage_bonus"] == 0.0
    assert cr.apply_effects(base, {}) is base
    ui2 = {cr.KEY: {"kind": "custom", "config": cr.clean_config({})}}
    assert cr.apply_effects(base, ui2) is base


# --- the record ------------------------------------------------------------------------------
def test_clean_record_survives_junk():
    assert cr.clean(None) is None and cr.clean({"kind": "weird"}) is None
    run = cr.clean({"kind": "daily", "config": "no", "seasons": -4, "score_total": float("nan"),
                    "result": {"points": "many"}, "par": True, "seed": 5})
    assert run["seasons"] == 0 and run["score_total"] == 0.0 and run["result"] is None
    assert run["par"] is None and run["seed"] == ""


def test_scoring_formula():
    assert cr.points_for(80.0, 10, 3, 1) == round(800 + 50 + 60 + 150)


def test_verdict_wording():
    assert "above par" in cr.verdict(1100, 1000) and "below par" in cr.verdict(900, 1000)
    assert "on par" in cr.verdict(1000, 1000) and cr.verdict(10, None) == ""


# --- par: the autopilot -----------------------------------------------------------------------
def test_autopilot_is_deterministic_and_sensible():
    cfg = cr.default_config()
    first = cr.autopilot(cfg)
    assert first == cr.autopilot(cfg) == cr.par_for(cfg)
    assert 600 < first < 2000


def test_par_follows_the_setup():
    plain = cr.par_for(cr.default_config())
    boon = cr.par_for(cr.clean_config({"modifier": "bumper_harvest"}))
    curse = cr.par_for(cr.clean_config({"modifier": "thin_soil"}))
    assert boon > plain > curse
    longer = cr.par_for(cr.clean_config({"goal": 80}))
    assert longer != plain


# --- ledger -------------------------------------------------------------------------------------
def test_ledger_cleans_caps_and_formats():
    raw = json.dumps([{"kind": "daily", "date": "2026-10-08", "code": "CNT-AAAA-BBBBB", "points": 900, "par": 800},
                      {"kind": "x", "points": 1}, {"kind": "custom", "points": "n"}, "junk"])
    entries = cr.clean_ledger(raw)
    assert len(entries) == 1 and "par 800" in cr.ledger_line(entries[0])
    assert cr.clean_ledger("not json") == [] and cr.clean_ledger(None) == []
    many = [{"kind": "custom", "points": n, "code": "C", "date": ""} for n in range(30)]
    assert len(cr.clean_ledger(many)) == cr.LEDGER_MAX


# --- in the game ---------------------------------------------------------------------------------
def _open_panel(game_env):
    game_env.elements["challenge-toggle-button"].dispatch("click", None)


def test_panel_toggles_and_lists_todays_challenge(game_env):
    _open_panel(game_env)
    el = game_env.elements
    assert el["challenge-panel"].hidden is False
    assert "seed CONTINUUM-" in el["challenge-daily-info"].innerText
    assert "Par " in el["challenge-daily-info"].innerText
    assert len(el["challenge-modifier-select"].children) == len(cr.MODIFIER_IDS)
    assert el["challenge-code-display"].value.startswith("CNT-")
    _open_panel(game_env)
    assert el["challenge-panel"].hidden is True


def test_starting_the_daily_applies_the_setup_and_locks_the_scenario(game_env):
    module = game_env.module
    module._challenge_utc_today_override = "2026-10-08"
    _open_panel(game_env)
    game_env.elements["challenge-daily-start-button"].dispatch("click", None)
    run = cr.get(module.campaign.ui)
    day = cr.daily("2026-10-08")
    assert run["kind"] == "daily" and run["seed"] == day["seed"] and run["date"] == "2026-10-08"
    cfg = day["config"]
    assert module.state.population == cfg["population"]
    assert module.state.resources["food"] == cfg["food"]
    assert module.state.hard_mode is cfg["hard"]
    assert module._scenario_locked() is True
    assert game_env.elements["scenario-fertile-button"].disabled is True
    assert game_env.elements["challenge-daily-start-button"].disabled is True
    assert any("Challenge run begins" in e.text for e in module.chronicle.entries)


def test_a_started_run_changes_the_effects_seen_by_the_season(game_env):
    module = game_env.module
    mod = cr.MODIFIERS["bumper_harvest"]["effects"]["food_yield_mult"]
    cfg = cr.clean_config({"modifier": "bumper_harvest"})
    _open_panel(game_env)
    game_env.elements["challenge-modifier-select"].value = "bumper_harvest"
    game_env.elements["challenge-modifier-select"].dispatch("change", None)
    game_env.elements["challenge-custom-start-button"].dispatch("click", None)
    assert module.current_effects()["food_yield_mult"] == pytest.approx(module.tree.effects()["food_yield_mult"] * mod)
    assert cr.get(module.campaign.ui)["config"]["modifier"] == cfg["modifier"]


def test_editor_dials_update_the_code_and_par(game_env):
    el = game_env.elements
    _open_panel(game_env)
    before = el["challenge-code-display"].value
    el["challenge-dial-population"].value = "11"
    el["challenge-dial-population"].dispatch("input", None)
    assert el["challenge-code-display"].value != before
    assert el["challenge-dial-population-value"].innerText == "11"
    assert "11 people" in el["challenge-preview-display"].innerText
    el["challenge-hard-checkbox"].checked = True
    el["challenge-hard-checkbox"].dispatch("change", None)
    assert "Hard Mode: on" in el["challenge-preview-display"].innerText


def test_loading_a_code_fills_the_editor_and_a_bad_code_says_why(game_env):
    el = game_env.elements
    _open_panel(game_env)
    code = cr.encode(cr.clean_config({"population": 13, "goal": 65, "modifier": "hardy_folk", "hard": True}))
    el["challenge-code-input"].value = code
    el["challenge-code-load-button"].dispatch("click", None)
    assert el["challenge-dial-population"].value == "13" and el["challenge-dial-goal"].value == "65"
    assert el["challenge-modifier-select"].value == "hardy_folk"
    assert el["challenge-code-display"].value == code
    el["challenge-code-input"].value = "CNT-ZZZZ-ZZZZZ"
    el["challenge-code-load-button"].dispatch("click", None)
    assert el["challenge-code-message"].innerText and "loaded" not in el["challenge-code-message"].innerText


def test_a_run_cannot_start_after_the_first_season_or_twice(game_env):
    el = game_env.elements
    game_env.advance_season()
    _open_panel(game_env)
    assert el["challenge-custom-start-button"].disabled is True
    el["challenge-custom-start-button"].dispatch("click", None)
    assert cr.get(game_env.module.campaign.ui) is None
    assert "fresh settlement" in el["challenge-run-status-display"].innerText


def test_hard_mode_and_consulting_are_locked_during_a_run(game_env):
    module = game_env.module
    _open_panel(game_env)
    game_env.elements["challenge-custom-start-button"].dispatch("click", None)
    before = module.state.hard_mode
    game_env.elements["hard-mode-toggle-button"].dispatch("click", None)
    assert module.state.hard_mode is before
    game_env.elements["consulting-case-smokestack-button"].dispatch("click", None)
    assert module.state.era == "tribal"


def test_a_full_run_scores_logs_and_lands_in_the_ledger(game_env):
    module = game_env.module
    _open_panel(game_env)
    game_env.elements["challenge-dial-goal"].value = "20"
    game_env.elements["challenge-dial-goal"].dispatch("input", None)
    game_env.elements["challenge-custom-start-button"].dispatch("click", None)
    game_env.advance_season(19)
    assert cr.get(module.campaign.ui)["result"] is None
    assert "Season 19 of 20" in game_env.elements["challenge-run-status-display"].innerText
    game_env.advance_season()
    run = cr.get(module.campaign.ui)
    assert run["result"]["seasons"] == 20 and run["result"]["points"] > 0
    assert run["par"] == cr.par_for(run["config"])
    assert game_env.elements["challenge-result-display"].hidden is False
    assert any("Challenge run complete" in e.text for e in module.chronicle.entries)
    fields = json.loads(module.challenge_share_result())
    assert fields["score"] == run["result"]["points"] and "par" in " ".join(map(str, fields["stats"]))
    game_env.advance_season(5)  # play on: nothing is counted twice
    assert cr.get(module.campaign.ui)["result"]["seasons"] == 20


def test_share_result_is_empty_before_a_run_finishes(game_env):
    assert json.loads(game_env.module.challenge_share_result()) == {}


def test_run_rides_the_save_and_junk_reads_as_none(game_env):
    module = game_env.module
    _open_panel(game_env)
    game_env.elements["challenge-custom-start-button"].dispatch("click", None)
    game_env.advance_season(3)
    saved = module.get_state()
    assert saved["ui"][cr.KEY]["seasons"] == 3
    saved["ui"][cr.KEY] = {"kind": "daily", "config": 5, "seasons": "many"}
    assert module.load_state(saved)
    run = cr.get(module.campaign.ui)
    assert run is not None and run["seasons"] == 0
    saved["ui"][cr.KEY] = "junk"
    assert module.load_state(saved) and cr.get(module.campaign.ui) is None


def test_stop_tracking_keeps_the_settlement(game_env):
    module = game_env.module
    _open_panel(game_env)
    game_env.elements["challenge-dial-population"].value = "12"
    game_env.elements["challenge-dial-population"].dispatch("input", None)
    game_env.elements["challenge-custom-start-button"].dispatch("click", None)
    game_env.elements["challenge-abandon-button"].dispatch("click", None)
    assert cr.get(module.campaign.ui) is None and module.state.population == 12
    assert module._scenario_locked() is False


def test_debt_and_run_modifiers_stack(game_env):
    module = game_env.module
    _open_panel(game_env)
    game_env.elements["challenge-modifier-select"].value = "busy_hands"
    game_env.elements["challenge-modifier-select"].dispatch("change", None)
    game_env.elements["challenge-custom-start-button"].dispatch("click", None)
    module.state.era = "digital"
    techdebt.put(module.campaign.ui, {"debt": 0.5})
    effects = module.current_effects()
    expected = module.tree.effects()["tool_yield_mult"] * 1.4 * techdebt.output_multiplier(techdebt.get(module.campaign.ui))
    assert effects["tool_yield_mult"] == pytest.approx(expected)


def test_finishing_the_daily_reports_it_to_the_hub_strip_and_the_ledger(game_env):
    import sys
    import types

    calls = []
    store = {}
    seed_js = types.SimpleNamespace(
        set=lambda seed: calls.append(("set", seed)),
        daily=types.SimpleNamespace(today=lambda: "2026-10-08",
                                    markCompleted=lambda game, info: calls.append(("done", game, info))),
    )
    window = types.SimpleNamespace(
        NoyvjSeed=seed_js,
        JSON=types.SimpleNamespace(parse=json.loads),
        localStorage=types.SimpleNamespace(getItem=lambda k: store.get(k), setItem=lambda k, v: store.__setitem__(k, v)),
    )
    sys.modules["js"].window = window
    try:
        module = game_env.module
        _open_panel(game_env)
        game_env.elements["challenge-daily-start-button"].dispatch("click", None)
        assert ("set", cr.daily("2026-10-08")["seed"]) in calls
        game_env.advance_season(cr.DAILY_GOAL)
        done = [c for c in calls if c[0] == "done"]
        assert len(done) == 1 and done[0][1] == "continuum"
        assert done[0][2]["score"] == cr.get(module.campaign.ui)["result"]["points"]
        ledger = cr.clean_ledger(store[cr.LEDGER_KEY])
        assert len(ledger) == 1 and ledger[0]["kind"] == "daily" and ledger[0]["date"] == "2026-10-08"
        assert "Daily 2026-10-08" in game_env.elements["challenge-ledger-list"].children[0].innerText
    finally:
        del sys.modules["js"].window


def test_a_daily_finished_on_a_later_day_does_not_count_for_that_day(game_env):
    import sys
    import types

    calls = []
    clock = {"today": "2026-10-08"}
    window = types.SimpleNamespace(
        NoyvjSeed=types.SimpleNamespace(
            set=lambda seed: None,
            daily=types.SimpleNamespace(today=lambda: clock["today"],
                                        markCompleted=lambda game, info: calls.append(info)),
        ),
        JSON=types.SimpleNamespace(parse=json.loads),
        localStorage=types.SimpleNamespace(getItem=lambda k: None, setItem=lambda k, v: None),
    )
    sys.modules["js"].window = window
    try:
        _open_panel(game_env)
        game_env.elements["challenge-daily-start-button"].dispatch("click", None)
        clock["today"] = "2026-10-09"
        game_env.advance_season(cr.DAILY_GOAL)
        assert calls == []
        assert cr.get(game_env.module.campaign.ui)["result"] is not None
    finally:
        del sys.modules["js"].window
