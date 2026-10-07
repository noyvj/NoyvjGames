"""Round-3 batch: PC-17 (research buttons follow the Iron count), A-22 (Governor
mood), A-24 (build plan as spreadsheet text), A-25 (chain reactions), A-26
(rhythm streak), A-30 (speedrun splits), A-31 (trophy shelf).

The shared fixture switches the rhythm bonus and the chain-reaction gifts OFF so
every older test keeps its exact numbers; the helpers below switch them on."""

import json
import re
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent


def _m(game_env):
    return game_env.module


def _streak_on(game_env):
    game_env.local_storage.setItem("sol-click-streak", "on")


def _chains_on(game_env):
    game_env.local_storage.setItem("sol-chain-bonus", "on")


def _texts(element):
    return [getattr(child, "innerText", "") for child in element.descendants()]


# --- PC-17 ---------------------------------------------------------------------


def _node_buttons(game_env):
    return [e for e in game_env.elements["research-node-list"].descendants() if getattr(e, "tagName", "") == "BUTTON"]


def test_research_buttons_follow_the_iron_count_without_a_rebuild(game_env):
    m = _m(game_env)
    rows_before = list(game_env.elements["research-node-list"].children)
    buttons = _node_buttons(game_env)
    available = [b for b in buttons if not b.disabled or True]
    assert buttons, "the fresh game lists research nodes"
    root = next(b for b in buttons if m.research_node_status(m.RESEARCH_NODE_BY_ID[b.getAttribute("data-node")]) == "available")
    assert root.disabled is True  # no Iron yet
    game_env.earth["resource_count"] = 10_000
    m.tick()
    assert root.disabled is False
    game_env.earth["resource_count"] = 0
    m.tick()
    assert root.disabled is True
    # The list itself was never rebuilt: same row objects, same button objects.
    assert list(game_env.elements["research-node-list"].children) == rows_before
    assert root in _node_buttons(game_env)
    assert available


def test_locked_node_buttons_stay_disabled_whatever_the_iron(game_env):
    m = _m(game_env)
    game_env.earth["resource_count"] = 10_000
    m.tick()
    for button in _node_buttons(game_env):
        node = m.RESEARCH_NODE_BY_ID[button.getAttribute("data-node")]
        if m.research_node_status(node) == "locked":
            assert button.disabled is True


def test_buying_a_node_still_rebuilds_the_list_and_refreshes_the_flags(game_env):
    m = _m(game_env)
    game_env.earth["resource_count"] = 10_000
    root_id = next(n["id"] for n in m.RESEARCH_NODES if not n["requires"] and n["tier"] == 0)
    game_env.research_node(root_id)
    assert root_id in m.researched_nodes
    child_buttons = [b for b in _node_buttons(game_env) if not b.disabled]
    assert child_buttons  # the root's children are now buyable with the Iron left


def test_pc_js_no_longer_patches_the_research_buttons():
    js = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
    assert "keepResearchFresh" not in js
    assert "research-node--available" not in js


# --- A-26: rhythm streak -------------------------------------------------------------


def test_streak_is_off_in_the_fixture_so_old_numbers_hold(game_env):
    for _ in range(30):
        game_env.click()
    assert game_env.earth["resource_count"] == pytest.approx(30.0)


def test_streak_adds_one_percent_per_ten_clicks_and_caps_at_five(game_env):
    _streak_on(game_env)
    m = _m(game_env)
    for _ in range(9):
        game_env.click()
    assert m.streak_bonus_pct() == 0
    assert game_env.earth["resource_count"] == pytest.approx(9.0)
    game_env.click()  # the 10th click
    assert m.streak_bonus_pct() == 1
    assert game_env.earth["resource_count"] == pytest.approx(9.0 + 1.01)
    for _ in range(90):
        game_env.click()
    assert m.click_streak == 100
    assert m.streak_bonus_pct() == m.STREAK_MAX_BONUS_PCT == 5


def test_streak_ends_when_clicks_stop_and_only_the_best_is_kept(game_env):
    _streak_on(game_env)
    m = _m(game_env)
    for _ in range(12):
        game_env.click()
    m.tick()
    assert m.click_streak == 12
    for _ in range(m.STREAK_WINDOW_TICKS + 1):
        m.tick()
    assert m.click_streak == 0
    assert m.best_click_streak == 12
    assert m.serialize_state()["best_click_streak"] == 12
    game_env.click()
    assert m.click_streak == 1  # starts over, best stays
    assert m.best_click_streak == 12


def test_streak_readout_is_plain_text_and_hidden_when_idle(game_env):
    _streak_on(game_env)
    m = _m(game_env)
    el = game_env.elements["click-streak"]
    assert el.hidden is True
    for _ in range(4):
        game_env.click()
    assert el.hidden is False
    assert "Rhythm streak: 4" in el.innerText
    assert "bonus starts at 10" in el.innerText
    for _ in range(8):
        game_env.click()
    assert "+1% mining yield" in el.innerText
    for _ in range(m.STREAK_WINDOW_TICKS + 1):
        m.tick()
    assert el.hidden is True


def test_streak_never_touches_automation(game_env):
    _streak_on(game_env)
    m = _m(game_env)
    game_env.earth["generator_count"] = 5
    for _ in range(50):
        game_env.click()
    before = game_env.earth["resource_count"]
    m.tick()
    # one tick of five Auto-Miners at 1/s: exactly the base production, no rhythm bonus in it
    assert game_env.earth["resource_count"] - before == pytest.approx(5 * 0.1)


def test_turning_the_setting_off_clears_the_streak(game_env):
    _streak_on(game_env)
    m = _m(game_env)
    for _ in range(5):
        game_env.click()
    game_env.local_storage.setItem("sol-click-streak", "off")
    game_env.click()
    assert m.click_streak == 0
    assert game_env.elements["click-streak"].hidden is True


def test_in_rhythm_achievement_needs_forty_in_a_row(game_env):
    _streak_on(game_env)
    m = _m(game_env)
    for _ in range(39):
        game_env.click()
    assert "in_rhythm" not in m.achievement_ids_earned()
    game_env.click()
    assert "in_rhythm" in m.achievement_ids_earned()
    progress = {e["id"]: e["progress"] for e in m.achievements_summary()}
    assert progress["in_rhythm"] == (40, 40)


def test_best_streak_survives_a_save_round_trip_and_bad_values_are_ignored(game_env):
    m = _m(game_env)
    m.best_click_streak = 33
    data = m.serialize_state()
    m.best_click_streak = 0
    m.deserialize_state(data)
    assert m.best_click_streak == 33
    for bad in (-4, "x", 1.5, True, None):
        data["best_click_streak"] = bad
        m.deserialize_state(data)
        assert m.best_click_streak == 0


# --- A-30: splits ------------------------------------------------------------------------


def _research_final_of_level_one(game_env):
    m = _m(game_env)
    final = m.RESEARCH_TIERS[0]["final"]
    for node in m.RESEARCH_NODES:
        if node["tier"] == 0 and node["id"] != final:
            m.researched_nodes.add(node["id"])
    game_env.earth["resource_count"] = 100_000
    game_env.research_node(final)
    return final


def test_unlocking_a_level_records_a_split_for_each_world(game_env):
    m = _m(game_env)
    m.total_ticks = 1234
    _research_final_of_level_one(game_env)
    assert m.run_splits == {"Moon": 1234, "Mars": 1234}


def test_splits_are_measured_from_the_start_of_the_run(game_env):
    m = _m(game_env)
    m.run_start_tick = 1000
    m.total_ticks = 1500
    _research_final_of_level_one(game_env)
    assert m.run_splits["Moon"] == 500


def test_a_completed_run_becomes_the_personal_best_only_if_faster(game_env):
    m = _m(game_env)
    for planet in m.PLANETS:
        game_env.state(planet)["terraform_progress"] = m.TERRAFORM_MAX
    m.run_splits.update({"Moon": 100, "Mars": 100})
    m.total_ticks = 900
    m._note_full_completion()
    assert m.best_run_ticks == 900
    assert m.pb_splits == {"Moon": 100, "Mars": 100, "full": 900}
    # a slower second run does not replace it
    m.run_completed = False
    m.run_start_tick = 900
    m.run_splits.clear()
    m.run_splits.update({"Moon": 500})
    m.total_ticks = 900 + 2000
    m._note_full_completion()
    assert m.best_run_ticks == 900
    assert m.pb_splits["full"] == 900
    # a faster one does
    m.run_completed = False
    m.run_start_tick = 2900
    m.run_splits.clear()
    m.run_splits.update({"Moon": 50})
    m.total_ticks = 2900 + 400
    m._note_full_completion()
    assert m.best_run_ticks == 400
    assert m.pb_splits == {"Moon": 50, "full": 400}


def test_prestige_starts_new_splits_but_keeps_the_personal_best(game_env):
    m = _m(game_env)
    for planet in m.PLANETS:
        game_env.state(planet)["terraform_progress"] = m.TERRAFORM_MAX
    m.run_splits.update({"Moon": 10})
    m.pb_splits.update({"Moon": 10, "full": 100})
    game_env.prestige()
    assert m.run_splits == {}
    assert m.pb_splits == {"Moon": 10, "full": 100}


def test_split_panel_text_has_signed_deltas(game_env):
    m = _m(game_env)
    m.run_splits.update({"Moon": 900})
    m.pb_splits.update({"Moon": 600, "Mars": 700, "full": 9000})
    game_env.elements["splits-toggle-button"].dispatch("click", None)
    panel = game_env.elements["splits-panel"]
    assert panel.hidden is False
    text = "\n".join(_texts(panel))
    assert "Moon: 15m 0s" not in text  # ticks are tenths of a second, not seconds
    assert "Moon: 1m 30s (best 1m 0s, +30s)" in text
    assert "Mars: not yet (best 1m 10s)" in text
    assert "Venus: not yet" in text
    m.run_splits["Moon"] = 400
    m.update_splits_display()
    assert "-20s" in "\n".join(_texts(panel))
    m.run_splits["Moon"] = 600
    m.update_splits_display()
    assert "same as best" in "\n".join(_texts(panel))


def test_split_panel_says_when_there_is_no_best_yet(game_env):
    m = _m(game_env)
    m.run_splits.update({"Moon": 100})
    game_env.elements["splits-toggle-button"].dispatch("click", None)
    assert "no personal best yet" in "\n".join(_texts(game_env.elements["splits-panel"]))


def test_splits_round_trip_and_are_sanitised(game_env):
    m = _m(game_env)
    m.run_splits.update({"Moon": 5, "Mars": 6})
    m.pb_splits.update({"Moon": 4, "full": 99})
    data = m.serialize_state()
    m.run_splits.clear()
    m.pb_splits.clear()
    m.deserialize_state(data)
    assert m.run_splits == {"Moon": 5, "Mars": 6}
    assert m.pb_splits == {"Moon": 4, "full": 99}
    data["run_splits"] = {"Moon": -1, "Mars": "x", "Nowhere": 3, "Venus": True, "Pluto": 7}
    data["pb_splits"] = "garbage"
    m.deserialize_state(data)
    assert m.run_splits == {"Pluto": 7}
    assert m.pb_splits == {}


def test_empty_splits_are_not_written_to_the_save(game_env):
    data = _m(game_env).serialize_state()
    assert "run_splits" not in data and "pb_splits" not in data


# --- A-31: trophy shelf -----------------------------------------------------------------------


def test_shelf_is_hidden_until_something_is_earned_then_shows_it(game_env):
    m = _m(game_env)
    shelf = game_env.elements["trophy-shelf"]
    assert shelf.hidden is True
    game_env.earth["resource_count"] = 5
    m.tick()
    assert shelf.hidden is False
    labels = [c.innerText for c in shelf.descendants() if c.className == "trophy-label"]
    assert labels == ["First Ore"]
    badge = shelf.children[0]
    assert badge.getAttribute("role") == "listitem"
    assert "trophy-badge--new" in badge.className  # earned this session: it glows


def test_shelf_shows_only_the_five_most_recent_newest_first(game_env):
    m = _m(game_env)
    for key in m.ACHIEVEMENT_CHECKS:
        m.ACHIEVEMENT_CHECKS[key] = lambda: True
    ids = [e["id"] for e in m.ACHIEVEMENTS][:8]
    m.recent_trophies[:] = ids
    m.render_trophy_shelf()
    labels = [c.innerText for c in game_env.elements["trophy-shelf"].descendants() if c.className == "trophy-label"]
    by_id = {e["id"]: e["label"] for e in m.ACHIEVEMENTS}
    assert labels == [by_id[i] for i in reversed(ids[-5:])]
    assert all("trophy-badge--new" not in c.className for c in game_env.elements["trophy-shelf"].children)


def test_shelf_skips_achievements_no_longer_earned(game_env):
    m = _m(game_env)
    m.recent_trophies[:] = ["first_ore", "automated"]
    game_env.earth["resource_count"] = 5
    m.render_trophy_shelf()
    labels = [c.innerText for c in game_env.elements["trophy-shelf"].descendants() if c.className == "trophy-label"]
    assert labels == ["First Ore"]


def test_trophies_round_trip_drop_junk_and_seed_old_saves(game_env):
    m = _m(game_env)
    game_env.earth["resource_count"] = 5
    game_env.earth["generator_count"] = 1
    m.tick()
    data = m.serialize_state()
    assert data["recent_trophies"]
    m.recent_trophies.clear()
    m.deserialize_state(data)
    assert m.recent_trophies == data["recent_trophies"]
    data["recent_trophies"] = ["first_ore", "first_ore", 7, "nope", "automated"]
    m.deserialize_state(data)
    assert m.recent_trophies == ["first_ore", "automated"]
    del data["recent_trophies"]  # a save from before the shelf existed
    m.deserialize_state(data)
    assert m.recent_trophies == m.achievement_ids_earned()[-m.TROPHY_HISTORY_MAX:]
    assert m.recent_trophies


def test_loading_a_save_never_makes_the_shelf_glow(game_env):
    m = _m(game_env)
    game_env.earth["resource_count"] = 5
    m.tick()
    data = m.serialize_state()
    m.deserialize_state(data)
    m.render_trophy_shelf()
    assert all("trophy-badge--new" not in c.className for c in game_env.elements["trophy-shelf"].children)


def test_flourish_is_pure_css_and_switchable():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert 'html[data-trophy-flourish="off"] .trophy-badge--new' in css
    assert 'html[data-reduced-motion="true"] .trophy-badge--new' in css
    assert "prefers-reduced-motion: reduce" in css[css.index(".trophy-badge--new"):]


# --- A-25: chain reactions ----------------------------------------------------------------------


def _rich(game_env):
    for planet in _m(game_env).PLANETS:
        game_env.state(planet)["resource_count"] = 100_000


def _fired(game_env, chain_id):
    return _m(game_env).chain_counts.get(chain_id, 0)


def test_chains_do_nothing_when_the_setting_is_off(game_env):
    _rich(game_env)
    game_env.click()
    game_env.buy_generator()
    game_env.click()
    assert _m(game_env).chain_counts == {}


def test_spin_up(game_env):
    _chains_on(game_env)
    _rich(game_env)
    game_env.click()
    game_env.buy_generator()
    before = game_env.earth["resource_count"]
    game_env.click()
    assert _fired(game_env, "spin_up") == 1
    # +1 for the click, plus a bonus of (40 + 4 per Auto-Miner) at the 1.0 yield multiplier
    assert game_env.earth["resource_count"] - before == pytest.approx(1 + 40 + 4 * 1)


def test_the_bonus_scales_with_the_yield_multiplier(game_env):
    _chains_on(game_env)
    m = _m(game_env)
    m.prestige_level = 2
    assert m._chain_reward("Earth") == pytest.approx(40 * m._yield_multiplier())


def test_whistle_stop(game_env):
    _chains_on(game_env)
    game_env.unlock_tier(1)
    game_env.travel_to_moon()
    game_env.return_to_earth()
    assert _fired(game_env, "whistle_stop") == 0
    game_env.travel_to_mars()
    assert _fired(game_env, "whistle_stop") == 1


def test_mars_landing_needs_the_right_world(game_env):
    _chains_on(game_env)
    _rich(game_env)
    game_env.unlock_tier(1)
    game_env.travel_to_moon()
    game_env.click("Moon")
    game_env.buy_generator("Moon")
    assert _fired(game_env, "mars_landing") == 0
    game_env.return_to_earth()
    game_env.travel_to_mars()
    game_env.click("Mars")
    game_env.buy_generator("Mars")
    assert _fired(game_env, "mars_landing") == 1


def test_spread_thin_needs_three_different_worlds(game_env):
    _chains_on(game_env)
    _rich(game_env)
    game_env.unlock_tier(1)
    game_env.buy_generator("Earth")
    game_env.buy_generator("Earth")
    game_env.buy_generator("Earth")
    assert _fired(game_env, "spread_thin") == 0
    game_env.travel_to_moon()
    game_env.buy_generator("Moon")
    game_env.return_to_earth()
    game_env.travel_to_mars()
    game_env.buy_generator("Mars")
    assert _fired(game_env, "spread_thin") == 1


def test_closed_loop(game_env):
    _chains_on(game_env)
    _rich(game_env)
    m = _m(game_env)
    m.unlocked_bodies.add("Mars")
    game_env.buy_trade_route("Earth")
    game_env.buy_recycler("Mars")
    root = next(n["id"] for n in m.RESEARCH_NODES if not n["requires"] and n["tier"] == 0)
    game_env.research_node(root)
    assert _fired(game_env, "closed_loop") == 1


def test_scholars_dash(game_env):
    _chains_on(game_env)
    _rich(game_env)
    for _ in range(3):
        game_env.fund_research()
    assert _fired(game_env, "scholars_dash") == 1


def test_skyward(game_env):
    _chains_on(game_env)
    _rich(game_env)
    m = _m(game_env)
    game_env.unlock_tier(2)
    game_env.buy_sky_city("JupiterMoons")
    assert m.chain_counts.get("skyward", 0) == 0
    game_env.buy_trade_route("JupiterMoons")
    assert m.chain_counts.get("skyward", 0) == 1


def test_a_chain_has_to_finish_inside_its_window(game_env):
    _chains_on(game_env)
    _rich(game_env)
    m = _m(game_env)
    game_env.click()
    game_env.buy_generator()
    for _ in range(m.CHAIN_WINDOW_TICKS + 5):
        m.tick()
    game_env.click()
    assert _fired(game_env, "spin_up") == 0


def test_a_chain_cannot_refire_inside_its_cooldown_but_can_after(game_env):
    _chains_on(game_env)
    _rich(game_env)
    m = _m(game_env)

    def run():
        game_env.click()
        game_env.buy_generator()
        game_env.click()

    run()
    assert _fired(game_env, "spin_up") == 1
    m.total_ticks += m.CHAIN_WINDOW_TICKS + 10  # window passed, cooldown not yet
    run()
    assert _fired(game_env, "spin_up") == 1
    m.total_ticks += m.CHAIN_COOLDOWN_TICKS
    run()
    assert _fired(game_env, "spin_up") == 2


def test_governor_purchases_do_not_count(game_env):
    _chains_on(game_env)
    m = _m(game_env)
    game_env.unlock_tier(1)
    game_env.mars["resource_count"] = 10_000
    game_env.travel_to_moon()  # Mars is now governed and buys by itself
    before = len(m._action_log)
    for _ in range(40):
        m.tick()
    assert game_env.mars["generator_count"] + game_env.mars["recycler_count"] > 0
    assert len(m._action_log) == before


def test_repeated_mining_is_one_log_entry(game_env):
    m = _m(game_env)
    for _ in range(30):
        game_env.click()
    assert len(m._action_log) == 1


def test_panel_shows_hints_until_found_then_the_recipe(game_env):
    _chains_on(game_env)
    _rich(game_env)
    m = _m(game_env)
    game_env.elements["chains-toggle-button"].dispatch("click", None)
    text = "\n".join(_texts(game_env.elements["chains-panel"]))
    assert "0 of 7 found" in text
    assert text.count("Not found yet") == 7
    assert text.count("Hint:") == 7
    assert "buy an Auto-Miner" not in text
    game_env.click()
    game_env.buy_generator()
    game_env.click()
    text = "\n".join(_texts(game_env.elements["chains-panel"]))
    assert "1 of 7 found" in text and "Spin-Up" in text
    assert "On Earth: mine, buy an Auto-Miner, then mine again." in text
    assert text.count("Hint:") == 6
    assert "(1/7)" in game_env.elements["chains-toggle-button"].innerText
    assert m.chains_found() == 1


def test_chain_data_is_well_formed(game_env):
    m = _m(game_env)
    assert len({c["id"] for c in m.CHAINS}) == len(m.CHAINS) == 7
    for chain in m.CHAINS:
        assert chain["hint"] and chain["recipe"] and chain["name"]
        for kind, planet in chain["steps"]:
            assert kind in {"mine", "gen", "rec", "route", "sky", "travel", "research"}
            assert planet in (None, "*") or planet in m.PLANETS


def test_chain_counts_round_trip_and_junk_is_dropped(game_env):
    m = _m(game_env)
    m.chain_counts.update({"spin_up": 3, "skyward": 1})
    data = m.serialize_state()
    m.chain_counts.clear()
    m.deserialize_state(data)
    assert m.chain_counts == {"spin_up": 3, "skyward": 1}
    data["chain_counts"] = {"spin_up": 0, "skyward": -2, "ghost": 4, "whistle_stop": True, "scholars_dash": 2}
    m.deserialize_state(data)
    assert m.chain_counts == {"scholars_dash": 2}
    data["chain_counts"] = ["nope"]
    m.deserialize_state(data)
    assert m.chain_counts == {}


def test_finding_every_chain_earns_chain_reactor(game_env):
    m = _m(game_env)
    assert "chain_reactor" not in m.achievement_ids_earned()
    for chain in m.CHAINS:
        m.chain_counts[chain["id"]] = 1
    assert "chain_reactor" in m.achievement_ids_earned()


def test_prestige_keeps_the_collection_but_clears_the_live_log(game_env):
    m = _m(game_env)
    for planet in m.PLANETS:
        game_env.state(planet)["terraform_progress"] = m.TERRAFORM_MAX
    m.chain_counts["spin_up"] = 2
    game_env.click()
    game_env.prestige()
    assert m.chain_counts == {"spin_up": 2}
    assert m._action_log == []


def test_a_chain_toast_names_the_chain_and_the_gift(game_env):
    _chains_on(game_env)
    _rich(game_env)
    game_env.click()
    game_env.buy_generator()
    game_env.click()
    toast = game_env.elements["achievement-toast-text"].innerText
    assert "New chain reaction: Spin-Up" in toast and "Iron" in toast


# --- A-22: Governor mood -----------------------------------------------------------------------------


def test_player_actions_count_manual_work_only(game_env):
    _rich(game_env)
    game_env.unlock_tier(1)
    m = _m(game_env)
    for _ in range(3):
        game_env.click()
    game_env.buy_generator()
    game_env.buy_recycler()
    assert game_env.earth["player_actions"] == 5
    game_env.travel_to_moon()  # travelling is not work on a world
    assert game_env.earth["player_actions"] == 5
    assert game_env.moon["player_actions"] == 0
    game_env.reset_world("Earth")
    assert game_env.earth["player_actions"] == 0
    assert m.planet_state["Earth"]["player_actions"] == 0


def test_every_personality_has_three_distinct_moods(game_env):
    m = _m(game_env)
    seen = set()
    for lines in m.GOVERNOR_MOODS.values():
        assert len(lines) == 3 and all(lines)
        seen.update(lines)
    assert len(seen) == 9


@pytest.mark.parametrize("actions,level", [(0, 0), (9, 0), (10, 1), (99, 1), (100, 2), (5000, 2)])
def test_mood_level_follows_how_much_the_player_handled_the_world(game_env, actions, level):
    m = _m(game_env)
    game_env.mars["governor_personality"] = "balanced"
    game_env.mars["player_actions"] = actions
    assert m.governor_mood("Mars") == m.GOVERNOR_MOODS["balanced"][level]


def test_global_personality_uses_the_global_priority(game_env):
    m = _m(game_env)
    for priority, personality in (("growth", "aggressive"), ("balance", "balanced"), ("ecology", "conservative")):
        m.governor_priority = priority
        assert m.governor_mood("Mars") == m.GOVERNOR_MOODS[personality][0]


def test_the_mood_shows_on_each_card_of_the_governor_report(game_env):
    game_env.unlock_tier(1)
    game_env.toggle_governor_report()
    panel = game_env.elements["governor-report-panel"]
    moods = [c.innerText for c in panel.descendants() if c.className == "governor-report-card-mood"]
    assert len(moods) == len(_m(game_env).PLANETS) - 1
    assert all(text.startswith("Mood: ") for text in moods)


def test_bad_player_action_counts_are_repaired_on_load(game_env):
    m = _m(game_env)
    data = m.serialize_state()
    for bad in (-3, "x", 2.5, True, None):
        data["planet_state"]["Mars"]["player_actions"] = bad
        m.deserialize_state(data)
        assert m.planet_state["Mars"]["player_actions"] == 0
    del data["planet_state"]["Mars"]["player_actions"]
    m.deserialize_state(data)
    assert m.planet_state["Mars"]["player_actions"] == 0


# --- A-24: build plan as spreadsheet text ----------------------------------------------------------------


def test_build_plan_tsv_is_one_row_per_step_with_flat_text(game_env):
    m = _m(game_env)
    m.build_plan[:] = [
        {"text": "Mine 10 Iron", "done": True},
        {"text": "tab\there and\nnewline", "done": False},
    ]
    rows = m.build_plan_tsv().split("\n")
    assert rows[0] == "Step\tWhat\tDone"
    assert rows[1] == "1\tMine 10 Iron\tyes"
    assert rows[2] == "2\ttab here and newline\tno"
    assert len(rows) == 3
    assert all(row.count("\t") == 2 for row in rows)


def test_copy_button_falls_back_to_a_text_box_without_a_clipboard(game_env):
    m = _m(game_env)
    m.build_plan[:] = [{"text": "Build a Recycler", "done": False}]
    game_env.elements["build-plan-copy-button"].dispatch("click", None)
    output = game_env.elements["build-plan-copy-output"]
    assert output.value == m.build_plan_tsv()
    assert output.hidden is False
    assert "copy it yourself" in game_env.elements["build-plan-copy-status"].innerText


def test_copy_button_with_an_empty_plan_says_so(game_env):
    game_env.elements["build-plan-copy-button"].dispatch("click", None)
    assert "Nothing to copy" in game_env.elements["build-plan-copy-status"].innerText
    assert game_env.elements["build-plan-copy-output"].hidden is True


def test_copy_button_uses_the_clipboard_when_there_is_one(game_env):
    import sys
    import types

    m = _m(game_env)
    m.build_plan[:] = [{"text": "Step", "done": False}]
    written = []
    clip = types.SimpleNamespace(writeText=lambda text: written.append(text))
    sys.modules["js"].navigator = types.SimpleNamespace(clipboard=clip)
    try:
        game_env.elements["build-plan-copy-button"].dispatch("click", None)
    finally:
        del sys.modules["js"].navigator
    assert written == [m.build_plan_tsv()]
    assert game_env.elements["build-plan-copy-output"].hidden is True
    assert "Copied" in game_env.elements["build-plan-copy-status"].innerText


# --- structure: both layouts, settings, accessibility -------------------------------------------------------


NEW_IDS = [
    "trophy-shelf", "click-streak", "chains-toggle-button", "chains-panel", "splits-toggle-button",
    "splits-panel", "build-plan-copy-button", "build-plan-copy-status", "build-plan-copy-output",
    "click-streak-checkbox", "chain-bonus-checkbox", "trophy-flourish-checkbox", "show-timing-checkbox",
]


@pytest.mark.parametrize("page", ["index.html", "pc.html"])
def test_new_elements_exist_in_both_pages(page):
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    for element_id in NEW_IDS:
        assert f'id="{element_id}"' in html, (page, element_id)


def test_new_panels_are_reachable_from_the_desktop_menu():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    windows = {w[0]: w[1] for w in cfg["windows"]}
    assert windows["chains-panel"] == "chains-toggle-button"
    assert windows["splits-panel"] == "splits-toggle-button"
    menu_ids = [i for group in cfg["toolbar"]["menu"] for i in group["ids"]]
    assert "chains-toggle-button" in menu_ids and "splits-toggle-button" in menu_ids
    stage = cfg["zones"]["stagebar"]
    assert "#trophy-shelf" in stage and "#click-streak" in stage


def test_new_panels_close_with_escape():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert '{ toggle: "chains-toggle-button", panel: "chains-panel" }' in html
    assert '{ toggle: "splits-toggle-button", panel: "splits-panel" }' in html


def test_settings_js_manages_the_four_new_switches():
    js = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    for key in ("sol-click-streak", "sol-chain-bonus", "sol-trophy-flourish", "sol-show-timing"):
        assert key in js
    assert 'data-show-timing' in js and 'data-trophy-flourish' in js
    assert "TOGGLES.forEach" in js[js.index("settings-reset-button"):]  # Reset to Default covers them


def test_splits_page_is_hidden_unless_show_timing_is_on():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert 'html:not([data-show-timing="on"]) #splits-toggle-button' in css
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<input type="checkbox" id="show-timing-checkbox">', html)  # off by default


def test_trophy_shelf_and_copy_box_are_labelled_for_screen_readers():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert 'id="trophy-shelf" class="trophy-shelf" role="list" aria-label=' in html
    assert 'id="build-plan-copy-output"' in html and 'aria-label="Build plan as tab-separated text"' in html
    assert 'id="build-plan-copy-status" class="copy-share-card-status" role="status"' in html


def test_new_achievements_are_in_the_catalog():
    ids = [a["id"] for a in json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]]
    assert "in_rhythm" in ids and "chain_reactor" in ids and len(ids) == 26
