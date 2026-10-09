"""GB-3: the Expedition. A separate 12-season mode on a seeded map with upgrades chosen from the shared skill tree.
Fixed upgrades, no random boons, no permadeath; the seed only decides the map; leaving returns to normal play."""

import json
import pathlib
import sys
import types

import seed as seed_lib
import skill_tree

from .gb_helpers import advance_to, make_mature, tile, tile_marks

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEED = "CANOPY-K7F2Q"
OTHER = "CANOPY-9XM4D"


def _start(env, seed=SEED):
    assert env.module.start_expedition(seed) == seed
    return env.module


def _open_panel(env):
    env.elements["expedition-toggle-button"].dispatch("click", None)


def _click(env, element_id):
    env.elements[element_id].dispatch("click", None)


def _buy(m, *node_ids):
    for node_id in node_ids:
        assert m.buy_expedition_node(node_id)["ok"], node_id


# --- the map ---------------------------------------------------------------------------------

def test_the_map_is_a_pure_function_of_the_seed(game_env):
    m = game_env.module
    assert m.expedition_map(SEED) == m.expedition_map(SEED)
    assert m.expedition_map(SEED) != m.expedition_map(OTHER)


def test_the_map_has_six_rich_six_thin_and_four_bare_distinct_plots(game_env):
    m = game_env.module
    for seed in (SEED, OTHER, "CANOPY-ZZZZZ", "CANOPY-22222"):
        rich, thin, bare = m.expedition_map(seed)
        assert (len(rich), len(thin), len(bare)) == (6, 6, 4)
        assert len(set(rich) | set(thin) | set(bare)) == 16
        assert all(0 <= i < 36 for i in rich + thin + bare)


def test_the_map_comes_from_the_shared_seed_stream(game_env):
    m = game_env.module
    picks = seed_lib.Rng(SEED).fork("map").sample(range(36), 16)
    rich, thin, bare = m.expedition_map(SEED)
    assert rich == sorted(picks[:6]) and thin == sorted(picks[6:12]) and bare == sorted(picks[12:])


def test_starting_applies_the_map_and_leaves_the_rest_alone(game_env):
    m = _start(game_env)
    rich, thin, bare = m.expedition_map(SEED)
    assert [i for i, k in sorted(m.expedition_terrain.items()) if k == "rich"] == rich
    assert [i for i, k in sorted(m.expedition_terrain.items()) if k == "thin"] == thin
    assert [p.index for p in m.plots if p.state == m.BARE] == bare
    assert all(p.clear_count == 0 for p in m.plots)  # a bare start is not a clear
    assert all(p.productivity_multiplier() == 1.0 for p in m.plots)


def test_terrain_changes_growth_only_on_the_main_forest(game_env):
    m = _start(game_env)
    rich, thin, _bare = m.expedition_map(SEED)
    normal = next(i for i in range(36) if i not in m.expedition_terrain)
    assert m.expedition_growth_multiplier(m.plots[rich[0]]) == m.EXPEDITION_RICH_GROWTH
    assert m.expedition_growth_multiplier(m.plots[thin[0]]) == m.EXPEDITION_THIN_GROWTH
    assert m.expedition_growth_multiplier(m.plots[normal]) == 1.0
    assert m.expedition_growth_multiplier(m.highland_plots[rich[0] % 12]) == 1.0


def test_a_rich_plot_out_grows_a_thin_one(game_env):
    m = _start(game_env)
    rich, thin, bare = m.expedition_map(SEED)
    for index in (rich[0], thin[0]):
        plot = m.plots[index]
        plot.state = m.PRESERVED
        plot.ticks_intact = 5
    assert m.plots[rich[0]].accrue_tick() > m.plots[thin[0]].accrue_tick()


# --- the seed ----------------------------------------------------------------------------------

def test_a_fresh_seed_is_a_valid_canopy_seed(game_env):
    m = game_env.module
    for _ in range(5):
        assert seed_lib.is_valid(m.new_expedition_seed(), "canopy")


def test_a_bad_seed_is_refused_with_a_reason_and_nothing_changes(game_env):
    m = game_env.module
    assert m.start_expedition("hello") is None
    assert m.current_expedition is None
    assert "not a seed" in m._expedition_message.lower()
    assert m.start_expedition("GRID-K7F2Q") is None
    assert "GRID" in m._expedition_message


def test_a_typed_seed_is_cleaned_up(game_env):
    m = game_env.module
    assert m.start_expedition("  canopy k7f2q ") == SEED
    assert m.current_expedition["seed"] == SEED


def test_an_empty_seed_starts_a_fresh_one(game_env):
    m = game_env.module
    seed = m.start_expedition("")
    assert seed_lib.is_valid(seed, "canopy") and m.current_expedition["seed"] == seed


# --- starting, settings, resetting --------------------------------------------------------------

def test_starting_is_a_fresh_normal_forest_with_no_other_mode(game_env):
    m = game_env.module
    game_env.change_difficulty(m.DIFFICULTY_RANGER)
    game_env.change_pace(m.PACE_FREQUENT)
    _start(game_env)
    assert (m.current_grid_size, m.current_difficulty, m.current_pace) == ("normal", m.DIFFICULTY_NORMAL, m.PACE_NORMAL)
    assert m.current_challenge == m.CHALLENGE_NONE and m.current_level is None and m.current_scenario == m.SCENARIO_NONE
    assert m.forest_tick == 0 and m.total_income == 0.0
    assert m.current_expedition == {"seed": SEED, "owned": [], "done_tick": None, "score": None}


def test_starting_asks_first_when_a_forest_would_be_given_up(game_env, fake_confirm_dialog):
    m = game_env.module
    m.total_income = 25.0
    game_env.elements["expedition-seed-input"].value = SEED
    _click(game_env, "expedition-start-button")
    assert m.current_expedition is None
    assert "25.0 income" in fake_confirm_dialog.asks[-1]["message"] and SEED in fake_confirm_dialog.asks[-1]["message"]
    fake_confirm_dialog.cancel()
    assert m.current_expedition is None and m.total_income == 25.0
    _click(game_env, "expedition-start-button")
    fake_confirm_dialog.confirm()
    assert m.current_expedition["seed"] == SEED and m.total_income == 0.0


def test_starting_an_untouched_forest_needs_no_question(game_env, fake_confirm_dialog):
    m = game_env.module
    game_env.elements["expedition-seed-input"].value = SEED
    m.total_income = 0.0
    for plot in m.plots:
        plot.value = 0.0
    _click(game_env, "expedition-start-button")
    assert fake_confirm_dialog.asks == [] and m.current_expedition["seed"] == SEED


def test_reset_session_retries_the_same_seed_with_no_upgrades(game_env):
    m = _start(game_env)
    game_env.tick(45)
    _buy(m, "sun_terraces")
    game_env.reset_session()
    assert m.current_expedition == {"seed": SEED, "owned": [], "done_tick": None, "score": None}
    assert m.forest_tick == 0
    rich, thin, bare = m.expedition_map(SEED)
    assert [p.index for p in m.plots if p.state == m.BARE] == bare


def test_changing_any_setting_or_starting_a_level_leaves_the_expedition(game_env):
    m = game_env.module
    for change in (
        lambda: game_env.change_difficulty(m.DIFFICULTY_RANGER),
        lambda: game_env.change_grid_size("small"),
        lambda: game_env.change_pace(m.PACE_RELAXED),
        lambda: game_env.change_challenge(m.CHALLENGE_SPRINT),
        lambda: m.start_level("wren_hollow"),
    ):
        _start(game_env)
        assert m.current_expedition is not None
        change()
        assert m.current_expedition is None and m.expedition_terrain == {}
        m.reset_session(grid_size="normal", difficulty=m.DIFFICULTY_NORMAL, challenge=m.CHALLENGE_NONE, pace=m.PACE_NORMAL, level=None)


def test_starting_an_expedition_ends_a_level(game_env):
    m = game_env.module
    m.start_level("wren_hollow")
    assert m.current_level == "wren_hollow"
    _start(game_env)
    assert m.current_level is None and m.current_expedition is not None


# --- the skill tree ---------------------------------------------------------------------------------

def test_the_tree_is_valid_and_costs_more_than_you_can_earn(game_env):
    m = game_env.module
    assert skill_tree.validate(m.EXPEDITION_TREE) == []
    assert skill_tree.totals(m.EXPEDITION_TREE, [])["total_cost"] > m.EXPEDITION_MAX_POINTS
    assert m.EXPEDITION_MAX_POINTS == 14


def test_three_points_at_the_start_and_one_more_each_season_capped(game_env):
    m = _start(game_env)
    assert m.expedition_points_earned() == 3 and m.expedition_points_free() == 3
    advance_to(game_env, 39)
    assert m.expedition_points_earned() == 3
    advance_to(game_env, 40)
    assert m.expedition_points_earned() == 4
    advance_to(game_env, 440)
    assert m.expedition_points_earned() == 14
    advance_to(game_env, 520)
    assert m.expedition_points_earned() == 14


def test_a_season_boundary_toasts_the_new_point(game_env):
    _start(game_env)
    advance_to(game_env, 40)
    assert "season 2 of 12" in game_env.elements["achievement-toast"].innerText
    assert "+1 upgrade point" in game_env.elements["achievement-toast"].innerText


def test_buying_needs_points_and_prerequisites(game_env):
    m = _start(game_env)
    assert m.buy_expedition_node("mycelium_net")["reason"] == "locked"
    _buy(m, "sun_terraces", "mycelium_net")
    assert m.expedition_points_free() == 0
    assert m.buy_expedition_node("old_roots")["reason"] == "points"
    assert m.buy_expedition_node("sun_terraces")["reason"] == "owned"
    assert m.buy_expedition_node("nope")["reason"] == "unknown"


def test_refunding_is_free_and_unlimited_but_not_from_under_a_dependent(game_env):
    m = _start(game_env)
    _buy(m, "sun_terraces", "mycelium_net")
    assert m.refund_expedition_node("sun_terraces")["reason"] == "needed"
    assert m.refund_expedition_node("mycelium_net")["ok"]
    assert m.expedition_points_free() == 2
    _buy(m, "mycelium_net")
    assert m.refund_all_expedition()["ok"] and m.expedition_points_free() == 3
    assert m.current_expedition["owned"] == []


def test_upgrades_do_nothing_outside_an_expedition(game_env):
    m = game_env.module
    assert m.buy_expedition_node("sun_terraces")["ok"] is False
    assert m.expedition_growth_multiplier(m.plots[0]) == 1.0
    assert m.expedition_soil_factor() == 1.0 and m.expedition_payout_multiplier() == 1.0
    assert m.expedition_tend_cooldown() == m.TEND_COOLDOWN_TICKS and m.expedition_extra_heal() == 0


# --- what each upgrade does -------------------------------------------------------------------------

def test_growth_upgrades_stack_to_24_percent(game_env):
    m = _start(game_env)
    normal = next(i for i in range(36) if i not in m.expedition_terrain)
    plot = m.plots[normal]
    assert m.expedition_growth_multiplier(plot) == 1.0
    advance_to(game_env, 120)
    _buy(m, "sun_terraces", "mycelium_net", "old_roots")
    assert abs(m.expedition_growth_multiplier(plot) - 1.24) < 1e-9


def test_a_growth_upgrade_really_raises_a_plots_income(game_env):
    m = _start(game_env)
    normal = next(i for i in range(36) if i not in m.expedition_terrain and m.plots[i].state != m.BARE)
    plot = m.plots[normal]
    plot.ticks_intact = 5
    before = plot.accrue_tick()
    plot.ticks_intact = 5
    _buy(m, "sun_terraces")
    after = plot.accrue_tick()
    assert abs(after / before - 1.06) < 1e-9


def test_terraced_soil_cuts_the_soil_lost_per_clear(game_env):
    m = _start(game_env)
    assert abs(m.current_degrade_per_clear() - m.DEGRADE_PER_CLEAR) < 1e-9
    _buy(m, "terraced_soil")
    assert abs(m.current_degrade_per_clear() - m.DEGRADE_PER_CLEAR * 0.75) < 1e-9


def test_quick_nursery_shortens_replanting(game_env):
    m = _start(game_env)
    bare = m.plots[m.expedition_map(SEED)[2][0]]
    bare.replant()
    base = bare.replant_ticks_remaining
    bare.state = m.BARE
    _buy(m, "terraced_soil", "quick_nursery")
    bare.replant()
    assert bare.replant_ticks_remaining == base - 3


def test_soil_salve_heals_a_clear_cut_twice_as_fast(game_env):
    m = _start(game_env)
    plot = make_mature(m, 3)
    game_env.select(3)
    m.on_clear_cut()
    advance_to(game_env, 10)
    assert plot.soil_dip_ticks == m.CLEAR_CUT_HEAL_TICKS - 10
    _buy(m, "terraced_soil", "soil_salve")
    game_env.tick(10)
    assert plot.soil_dip_ticks == m.CLEAR_CUT_HEAL_TICKS - 10 - 20


def test_trade_route_pays_more_for_clears_and_clear_cuts(game_env):
    m = _start(game_env)
    advance_to(game_env, 5)
    _buy(m, "trade_route")
    make_mature(m, 3)
    game_env.select(3)
    m.on_clear()
    assert abs(m.total_income - 100.0 * 1.15) < 1e-9
    make_mature(m, 4)
    game_env.select(4)
    before = m.total_income
    m.on_clear_cut()
    assert abs((m.total_income - before) - 100.0 * 1.2 * 1.15) < 1e-9


def test_trade_route_is_taken_back_by_undo(game_env):
    m = _start(game_env)
    _buy(m, "trade_route")
    make_mature(m, 3)
    game_env.select(3)
    m.on_clear()
    assert m.undo_last_clear() is True
    assert m.total_income == 0.0


def test_tend_rhythm_halves_the_cooldown(game_env):
    m = _start(game_env)
    _buy(m, "tend_rhythm")
    plot = m.plots[3]
    plot.state, plot.ticks_intact = m.PRESERVED, 3
    m.tend_plot(3)
    game_env.tick(m.TEND_DURATION_TICKS)
    assert m.tend_cooldown_ticks == m.EXPEDITION_TEND_COOLDOWN


def test_the_seed_vault_rests_during_an_expedition(game_env):
    m = game_env.module
    m.vault_owned[:] = ["deep_roots"]
    assert m.vault_growth_multiplier() > 1.0
    _start(game_env)
    assert m.vault_effects() == frozenset() and m.vault_growth_multiplier() == 1.0
    m.on_leave_expedition()
    assert m.vault_growth_multiplier() > 1.0


# --- no randomness --------------------------------------------------------------------------------------

def _scripted_run(env, seed):
    m = env.module
    m.start_expedition(seed)
    _buy(m, "sun_terraces", "terraced_soil")
    for tick in range(1, 140):
        env.tick()
        if tick == 50:
            _buy(m, "mycelium_net")
        if tick == 60:
            for i in range(36):
                if m.plots[i].state in m.ACCRUING_STATES and i not in (0, 1):
                    env.select(i)
                    m.on_clear()
                    break
        if tick == 70:
            for i in range(36):
                if m.plots[i].state == m.BARE:
                    env.select(i)
                    m.on_replant()
                    break
    return round(m.total_income, 6), round(m.standing_forest_value(), 6), [p.state for p in m.plots]


def test_the_same_seed_and_the_same_choices_give_the_same_run_every_time(game_env):
    first = _scripted_run(game_env, SEED)
    game_env.module.reset_session()
    second_env_result = _scripted_run(game_env, SEED)
    assert first == second_env_result


def test_no_upgrade_text_or_code_path_mentions_chance(game_env):
    m = game_env.module
    for node in m.EXPEDITION_TREE["nodes"]:
        text = (node["label"] + node["description"]).lower()
        assert not any(word in text for word in ("random", "chance", "luck", "roll", "gamble"))


# --- finishing --------------------------------------------------------------------------------------------

def test_twelve_seasons_complete_the_run_with_a_score(game_env):
    m = _start(game_env)
    advance_to(game_env, m.EXPEDITION_TICKS - 1)
    assert not m.expedition_finished()
    game_env.tick()
    assert m.expedition_finished()
    assert m.current_expedition["done_tick"] == m.EXPEDITION_TICKS
    assert m.current_expedition["score"] == m.expedition_score() > 0
    assert m.expedition_meta["finished"] == 1 and m.expedition_best_for(SEED) == m.current_expedition["score"]
    assert "Expedition complete" in game_env.elements["achievement-toast"].innerText


def test_the_run_finishes_once_and_play_can_go_on(game_env):
    m = _start(game_env)
    advance_to(game_env, m.EXPEDITION_TICKS + 30)
    assert m.expedition_meta["finished"] == 1
    assert m.current_expedition["done_tick"] == m.EXPEDITION_TICKS
    assert sum(1 for e in m.forest_log if "complete" in e["text"] and e["kind"] == "expedition") == 1


def test_the_best_score_per_seed_only_goes_up(game_env):
    m = _start(game_env)
    m.expedition_meta["best"][SEED] = 10 ** 6
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert m.expedition_best_for(SEED) == 10 ** 6
    assert m.expedition_meta["finished"] == 1


def test_no_fail_state_an_untouched_forest_still_finishes(game_env):
    m = _start(game_env)
    m.community_relations = 0
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert m.expedition_finished()


def test_finishing_earns_the_achievements_and_two_maps_needs_two_seeds(game_env):
    m = _start(game_env)
    advance_to(game_env, m.EXPEDITION_TICKS)
    earned = m.achievement_ids_earned()
    assert "expedition_complete" in earned and "two_maps" not in earned
    _start(game_env, OTHER)
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert "two_maps" in m.achievement_ids_earned()


def test_the_same_seed_twice_is_still_one_map(game_env):
    m = _start(game_env)
    advance_to(game_env, m.EXPEDITION_TICKS)
    _start(game_env)
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert m.expedition_meta["finished"] == 2 and len(m.expedition_meta["best"]) == 1
    assert "two_maps" not in m.achievement_ids_earned()


def test_records_are_kept_per_browser_and_reloaded(game_env):
    m = _start(game_env)
    advance_to(game_env, m.EXPEDITION_TICKS)
    blob = json.loads(game_env.local_storage.getItem(m.EXPEDITION_STORAGE_KEY))
    assert blob["finished"] == 1 and blob["best"][SEED] == m.current_expedition["score"] and blob["last_seed"] == SEED
    m.expedition_meta.update(best={}, finished=0, last_seed="")
    m._load_expedition_meta()
    assert m.expedition_meta["finished"] == 1 and SEED in m.expedition_meta["best"]


def test_bad_stored_records_fall_back(game_env):
    m = game_env.module
    game_env.local_storage.setItem(m.EXPEDITION_STORAGE_KEY, json.dumps({"best": {"junk": 5, SEED: True, OTHER: 7, "CANOPY-ABCDE": "x"}, "finished": -3, "last_seed": 5}))
    m._load_expedition_meta()
    assert m.expedition_meta == {"best": {OTHER: 7}, "finished": 0, "last_seed": ""}
    game_env.local_storage.setItem(m.EXPEDITION_STORAGE_KEY, "{not json")
    m._load_expedition_meta()
    assert m.expedition_meta == {"best": {}, "finished": 0, "last_seed": ""}


# --- leaving ------------------------------------------------------------------------------------------------

def test_leaving_goes_back_to_normal_play_on_the_same_forest(game_env):
    m = _start(game_env)
    advance_to(game_env, 30)
    _buy(m, "sun_terraces")
    states = [(p.state, p.value, p.ticks_intact) for p in m.plots]
    income = m.total_income
    assert m.on_leave_expedition() is True
    assert m.current_expedition is None and m.expedition_terrain == {}
    assert [(p.state, p.value, p.ticks_intact) for p in m.plots] == states and m.total_income == income
    assert m.expedition_growth_multiplier(m.plots[0]) == 1.0
    assert "expedition" not in m.get_state()
    assert m.on_leave_expedition() is False


def test_the_forest_keeps_playing_after_leaving(game_env):
    m = _start(game_env)
    m.on_leave_expedition()
    game_env.tick(5)
    assert m.forest_tick == 5 and not any(k.startswith("plot-terrain") for k in [tile(game_env, 0).className])


# --- saving ----------------------------------------------------------------------------------------------------

def test_a_normal_game_writes_no_expedition_key(game_env):
    assert "expedition" not in game_env.module.get_state()


def test_an_expedition_round_trips_through_a_save(game_env):
    m = _start(game_env)
    advance_to(game_env, 45)
    _buy(m, "sun_terraces", "terraced_soil")
    state = json.loads(json.dumps(m.get_state()))
    assert state["expedition"] == {"seed": SEED, "owned": ["sun_terraces", "terraced_soil"], "done_tick": None, "score": None}
    m.on_leave_expedition()
    m.load_state(state)
    assert m.current_expedition["seed"] == SEED and m.current_expedition["owned"] == ["sun_terraces", "terraced_soil"]
    assert m.expedition_terrain == {**{i: "rich" for i in m.expedition_map(SEED)[0]}, **{i: "thin" for i in m.expedition_map(SEED)[1]}}
    assert m.forest_tick == 45


def test_a_finished_expedition_round_trips(game_env):
    m = _start(game_env)
    advance_to(game_env, m.EXPEDITION_TICKS + 3)
    score = m.current_expedition["score"]
    state = json.loads(json.dumps(m.get_state()))
    m.on_leave_expedition()
    m.load_state(state)
    assert m.current_expedition["done_tick"] == m.EXPEDITION_TICKS and m.current_expedition["score"] == score


def test_an_old_save_loads_unchanged_and_ends_a_live_expedition(game_env):
    m = _start(game_env)
    old = json.loads(json.dumps(m.get_state()))
    del old["expedition"]
    m.load_state(old)
    assert m.current_expedition is None and m.expedition_terrain == {}


def test_a_save_made_in_normal_play_loaded_into_an_expedition_ends_it(game_env):
    m = game_env.module
    normal = json.loads(json.dumps(m.get_state()))
    _start(game_env)
    m.load_state(normal)
    assert m.current_expedition is None


def test_bad_expedition_keys_fall_back_to_normal_play(game_env):
    m = _start(game_env)
    good = json.loads(json.dumps(m.get_state()))
    for bad in (
        None, "x", 5, [], {}, {"seed": 5}, {"seed": "nope"}, {"seed": "GRID-K7F2Q"}, {"seed": True},
        {"seed": SEED, "owned": "all"},
    ):
        data = dict(good)
        data["expedition"] = bad
        m.load_state(data)
        if isinstance(bad, dict) and bad.get("seed") == SEED:
            assert m.current_expedition["seed"] == SEED and m.current_expedition["owned"] == []
        else:
            assert m.current_expedition is None, bad
        m.start_expedition(SEED)


def test_owned_upgrades_are_cleaned_and_trimmed_to_the_points_earned(game_env):
    m = _start(game_env)
    data = json.loads(json.dumps(m.get_state()))
    data["expedition"]["owned"] = ["old_roots", "mycelium_net", "sun_terraces", "sun_terraces", 5, None, "ghost", "trade_route", "tend_rhythm"]
    m.load_state(data)
    owned = m.current_expedition["owned"]
    assert owned[:3] == ["old_roots", "mycelium_net", "sun_terraces"] or skill_tree.spent(m.EXPEDITION_TREE, owned) <= 3
    assert skill_tree.spent(m.EXPEDITION_TREE, owned) <= m.expedition_points_earned()
    assert len(owned) == len(set(owned)) and all(isinstance(i, str) for i in owned)


def test_a_bad_done_tick_or_score_is_ignored(game_env):
    m = _start(game_env)
    base = json.loads(json.dumps(m.get_state()))
    for done, score in ((True, 5), ("x", 5), (-4, 5), (10, 5), (float("nan"), 5), (m.EXPEDITION_TICKS, "x"), (m.EXPEDITION_TICKS, -1)):
        data = json.loads(json.dumps(base))
        data["expedition"]["done_tick"] = done
        data["expedition"]["score"] = score
        m.load_state(data)
        assert m.current_expedition is not None
        assert m.current_expedition["done_tick"] is None  # the forest has not reached season 12
    advance_to(game_env, m.EXPEDITION_TICKS)
    data = json.loads(json.dumps(m.get_state()))
    data["expedition"]["score"] = "x"
    m.load_state(data)
    assert isinstance(m.current_expedition["score"], int) and m.current_expedition["score"] >= 0


def test_an_expedition_in_a_save_with_other_settings_is_dropped(game_env):
    m = _start(game_env)
    data = json.loads(json.dumps(m.get_state()))
    data["current_difficulty"] = m.DIFFICULTY_RANGER
    m.load_state(data)
    assert m.current_expedition is None
    m.start_expedition(SEED)
    data = json.loads(json.dumps(m.get_state()))
    data["current_grid_size"] = "small"
    data["plots"] = data["plots"][:16]
    m.load_state(data)
    assert m.current_expedition is None


# --- the panel ---------------------------------------------------------------------------------------------------

def test_the_panel_opens_and_closes(game_env):
    panel = game_env.elements["expedition-panel"]
    assert panel.hidden is True
    _open_panel(game_env)
    assert panel.hidden is False and game_env.elements["expedition-toggle-button"].innerText == "Hide Expedition"
    _open_panel(game_env)
    assert panel.hidden is True


def test_status_and_toggle_label_follow_the_run(game_env):
    m = game_env.module
    assert game_env.elements["expedition-status"].hidden is True
    _start(game_env)
    status = game_env.elements["expedition-status"]
    assert status.hidden is False and SEED in status.innerText and "season 1 of 12" in status.innerText and "3 upgrade points" in status.innerText
    assert "1/12" in game_env.elements["expedition-toggle-button"].innerText
    advance_to(game_env, 80)
    assert "season 3 of 12" in status.innerText and "5 upgrade points" in status.innerText
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert "complete" in status.innerText and str(m.current_expedition["score"]) in status.innerText
    m.on_leave_expedition()
    assert status.hidden is True


def test_the_panel_shows_the_map_summary_and_records(game_env):
    m = _start(game_env)
    _open_panel(game_env)
    assert "6 rich-soil plots" in game_env.elements["expedition-map-note"].innerText
    assert "4 plots start bare" in game_env.elements["expedition-map-note"].innerText
    assert "Season 1 of 12" in game_env.elements["expedition-summary"].innerText
    assert game_env.elements["expedition-seed-input"].value == SEED
    assert game_env.elements["expedition-leave-button"].disabled is False
    assert game_env.elements["expedition-start-button"].innerText == "Retry this seed"
    assert game_env.elements["expedition-tree"].hidden is False
    m.on_leave_expedition()
    assert game_env.elements["expedition-leave-button"].disabled is True
    assert game_env.elements["expedition-tree"].hidden is True
    assert "No Expedition running" in game_env.elements["expedition-summary"].innerText


def test_new_seed_fills_the_box_and_start_uses_it(game_env):
    m = game_env.module
    m.new_expedition_seed = lambda: OTHER
    _open_panel(game_env)
    _click(game_env, "expedition-new-seed-button")
    assert game_env.elements["expedition-seed-input"].value == OTHER
    assert OTHER in game_env.elements["expedition-seed-message"].innerText
    _click(game_env, "expedition-start-button")
    assert m.current_expedition["seed"] == OTHER


def test_a_bad_typed_seed_shows_the_reason_and_starts_nothing(game_env):
    m = game_env.module
    _open_panel(game_env)
    game_env.elements["expedition-seed-input"].value = "hello"
    _click(game_env, "expedition-start-button")
    assert m.current_expedition is None
    assert "not a seed" in game_env.elements["expedition-seed-message"].innerText.lower()


def test_typing_in_the_box_is_not_overwritten_by_a_tick(game_env):
    _start(game_env)
    _open_panel(game_env)
    game_env.elements["expedition-seed-input"].value = "CANOPY-ABC"
    game_env.tick(3)
    assert game_env.elements["expedition-seed-input"].value == "CANOPY-ABC"


def test_copy_seed_uses_the_clipboard_when_there_is_one(game_env):
    copied = []
    clipboard = types.SimpleNamespace(writeText=lambda text: copied.append(text))
    sys.modules["js"].window = types.SimpleNamespace(navigator=types.SimpleNamespace(clipboard=clipboard))
    _start(game_env)
    _open_panel(game_env)
    _click(game_env, "expedition-copy-button")
    assert copied == [SEED] and "Copied" in game_env.elements["expedition-seed-message"].innerText


def test_copy_seed_without_a_clipboard_still_shows_the_seed(game_env):
    _start(game_env)
    _open_panel(game_env)
    _click(game_env, "expedition-copy-button")
    assert SEED in game_env.elements["expedition-seed-message"].innerText


def test_terrain_is_marked_on_the_tiles_by_shape_and_words(game_env):
    m = _start(game_env)
    rich, thin, bare = m.expedition_map(SEED)
    assert "terrain-mark" in tile_marks(game_env, rich[0]) and "terrain-mark" in tile_marks(game_env, thin[0])
    assert "plot-terrain--rich" in tile(game_env, rich[0]).className and "plot-terrain--thin" in tile(game_env, thin[0]).className
    assert "rich soil" in tile(game_env, rich[0]).getAttribute("aria-label")
    assert "thin soil" in tile(game_env, thin[0]).getAttribute("aria-label")
    plain = next(i for i in range(36) if i not in m.expedition_terrain)
    assert "terrain-mark" not in tile_marks(game_env, plain)
    marks = {c.innerText for i in (rich[0], thin[0]) for c in tile(game_env, i).children if c.className == "terrain-mark"}
    assert marks == {"▲", "▽"}


# --- markup, wiring and the shared files ----------------------------------------------------------------------------

IDS = [
    "expedition-toggle-button", "expedition-panel", "expedition-status", "expedition-seed-input", "expedition-new-seed-button",
    "expedition-copy-button", "expedition-seed-message", "expedition-start-button", "expedition-leave-button",
    "expedition-summary", "expedition-map-note", "expedition-tree", "expedition-result", "expedition-bests",
]


def test_every_expedition_id_exists_once_on_each_page():
    for page in ("index.html", "pc.html"):
        html = (ROOT / page).read_text()
        for element_id in IDS:
            assert html.count(f'id="{element_id}"') == 1, (page, element_id)


def test_the_desktop_boot_reaches_the_expedition_from_the_menu_and_a_window():
    config = json.loads((ROOT / "pc-config.json").read_text())
    assert ["expedition-panel", "expedition-toggle-button", "Expedition"] in config["windows"]
    assert ["expedition-toggle-button", "\U0001F9ED"] in config["toolbar"]["icons"]
    assert "#expedition-status" in config["zones"]["stagebar"]
    pc = (ROOT / "pc.html").read_text()
    assert "expedition-panel" in pc and "NOYVJ_PC_TOOLBAR" in pc and "expedition-toggle-button" in pc


def test_the_boot_script_writes_seed_py_into_pyodide_and_lists_the_panel_for_the_shortcuts():
    for page in ("index.html", "pc.html"):
        html = (ROOT / page).read_text()
        assert 'fetch("../../shared/seed.py")' in html and 'writeFile("seed.py"' in html
        assert 'toggle: "expedition-toggle-button", panel: "expedition-panel"' in html


def test_the_game_does_not_import_the_random_module_or_use_a_clock_for_the_map():
    game = (ROOT / "game.py").read_text()
    assert "import random" not in game
    section = game[game.index("# GB-3 (2026-10-10): the Expedition"):game.index("# --- per-tick hook and state ---")]
    assert "time.time" not in section and "Date" not in section
