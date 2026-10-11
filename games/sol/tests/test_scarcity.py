"""A-11 (Scarcity Run), A-12 (the seed words) and the pure helpers in challenges.py."""

import json
import re
import types
from pathlib import Path

import challenges

GAME_DIR = Path(__file__).resolve().parent.parent
TODAY = "2026-10-11"


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _panel_text(env, panel="scarcity-panel"):
    return "\n".join(t for t in _texts(env.elements[panel]) if t)


def _buttons(element, found=None):
    found = [] if found is None else found
    if getattr(element, "tagName", "").lower() == "button" or element.getAttribute("data-action"):
        found.append(element)
    for child in element.children:
        _buttons(child, found)
    return found


def _today(env, date=TODAY):
    env.module.TODAY_OVERRIDE = date


def _rich_game(env):
    """A mid-campaign game with a lot of optional state set, so a leak anywhere shows up in get_state()."""
    m = env.module
    env.unlock_tier(2)
    env.earth.update({"resource_count": 4200.0, "generator_count": 14, "recycler_count": 6})
    env.mars.update({"resource_count": 900.0, "generator_count": 4, "recycler_count": 2, "ecology_health": 71.0,
                     "terraform_progress": 33.0})
    env.earth["trade_routes"] = {"Mars": 2}
    m.prestige_level = 2
    m.prestige_points_earned = 2
    m.prestige_nodes.add("head_start")
    m.total_ticks = 54321
    m.run_start_tick = 1000
    m.best_run_ticks = 40000
    m.best_click_streak = 17
    m.chain_counts["spin_up"] = 2
    m.run_splits.update({"Moon": 900, "Mars": 950})
    m.pb_splits.update({"Moon": 800})
    m.mission_stamps[:] = ["earth_crew"]
    m.mission_slots[:] = []
    m._refill_mission_slots()
    m.survey_data = 3
    m.chart_revealed = 2
    m.stress_best_margin = 4.5
    m.build_plan[:] = [{"text": "Recyclers first", "done": True}]
    m.mutators_next[:] = ["thin_atmosphere"]
    m.doctrine_rules[:] = [{"planet": "Mars", "cond": "ecology_below", "level": 30, "action": "recycler"}]
    m.visited_bodies.update({"Earth", "Mars", "Moon"})
    m.story_log[:] = ["arrive:Earth"]
    m._full_render()


def _play_a_bit(env, ticks=40):
    m = env.module
    for _ in range(ticks):
        env.click("Earth")
        m.tick()


# --- pure helpers (challenges.py) -------------------------------------------------------------------------


def test_seed_words_are_pronounceable_triples_from_the_word_lists():
    for date in ("2026-10-01", "2026-10-11", "2027-03-31"):
        words = challenges.seed_words(date)
        assert re.fullmatch(r"[a-z]+-[a-z]+-[2-9]", words)
        assert challenges.is_seed_words(words)
    assert challenges.seed_words("2026-10-11") == challenges.seed_words("2026-10-11")
    assert not challenges.is_seed_words("amber-orbit-1") and not challenges.is_seed_words("nope")


def test_word_lists_are_clean_data():
    for words in (challenges.ADJECTIVES, challenges.NOUNS):
        assert len(words) == len(set(words)) == 40
        assert all(re.fullmatch(r"[a-z]{3,9}", w) for w in words)
    assert not set(challenges.ADJECTIVES) & set(challenges.NOUNS)
    assert challenges.SEED_SPACE == 12800


def test_seed_words_never_collide_over_three_hundred_consecutive_dates():
    seen = {}
    for i in range(300):
        date = challenges.add_days("2026-10-01", i)
        words = challenges.seed_words(date)
        assert words not in seen, (date, seen.get(words))
        seen[words] = date


def test_seed_words_never_collide_for_the_whole_cycle():
    words = {challenges.seed_words(challenges.add_days("2026-10-01", i)) for i in range(challenges.SEED_SPACE)}
    assert len(words) == challenges.SEED_SPACE


def test_neighbouring_days_do_not_look_alike():
    a, b, c = (challenges.seed_words(challenges.add_days("2026-10-01", i)) for i in range(3))
    assert len({a.split("-")[0], b.split("-")[0], c.split("-")[0]}) > 1


def test_dates_are_strict_and_the_epoch_is_day_one():
    assert challenges.valid_date("2026-10-01") and not challenges.valid_date("2026-13-01")
    assert not challenges.valid_date("2026-1-1") and not challenges.valid_date(20261001) and not challenges.valid_date("")
    assert challenges.day_number("2026-10-01") == 1 and challenges.day_number("2026-10-11") == 11
    assert challenges.playable("2026-10-01", "2026-10-11") and challenges.playable("2026-10-11", "2026-10-11")
    assert not challenges.playable("2026-09-30", "2026-10-11") and not challenges.playable("2026-10-12", "2026-10-11")
    assert not challenges.playable("junk", "2026-10-11") and not challenges.playable("2026-10-05", None)


def test_the_daily_is_a_pure_function_of_the_date():
    a = challenges.make_spec("2026-10-11")
    assert a == challenges.make_spec("2026-10-11")
    assert a["words"] == challenges.seed_words("2026-10-11") and a["date"] == "2026-10-11"
    assert challenges.make_spec("2026-10-11", 1) != a
    assert challenges.make_spec("2026-10-12") != a


def test_every_daily_stays_inside_the_published_ranges():
    for i in range(120):
        spec = challenges.make_spec(challenges.add_days("2026-10-01", i))
        assert spec["target_pct"] in challenges.TARGET_CHOICES and spec["decay"] in challenges.DECAY_CHOICES
        assert spec["cost"] in challenges.COST_CHOICES and len(spec["targets"]) in (2, 3)
        assert set(spec["targets"]) <= set(challenges.WORLDS)
        assert min(spec["yields"].values()) < 1 <= max(spec["yields"].values())  # a thin pile and a rich one every day
        for world, load in spec["loadout"].items():
            assert load["generators"] + load["recyclers"] >= 1  # every world starts with a way to earn
            assert load["ecology"] in challenges.ECOLOGY_CHOICES and load["stock"] in challenges.STOCK_CHOICES


def test_goal_text_reads_naturally():
    spec = {"targets": ["Moon", "Mars"], "target_pct": 40}
    assert challenges.goal_text(spec) == "Terraform the Moon and Mars to 40%."
    assert challenges.goal_text({"targets": ["Earth", "Moon", "Mars"], "target_pct": 30}) == \
        "Terraform Earth, the Moon and Mars to 30%."


def test_month_grid_starts_on_monday_and_pads_with_none():
    weeks = challenges.month_weeks(2026, 10)
    assert all(len(w) == 7 for w in weeks)
    assert weeks[0][:3] == [None, None, None] and weeks[0][3] == "2026-10-01"  # 1 Oct 2026 is a Thursday
    flat = [d for w in weeks for d in w if d]
    assert flat[0] == "2026-10-01" and flat[-1] == "2026-10-31" and len(flat) == 31
    assert challenges.shift_month(2026, 12, 1) == (2027, 1) and challenges.shift_month(2026, 1, -1) == (2025, 12)


def test_records_are_validated_entry_by_entry():
    good = {"ticks": 1500, "tries": 2, "under_par": True}
    raw = {
        "2026-10-05": good,
        "2026-10-06": {"ticks": 900, "tries": 1},
        "2026-09-30": {"ticks": 900, "tries": 1},          # before the epoch
        "2026-13-01": {"ticks": 900, "tries": 1},          # not a date
        "2026-10-07": {"ticks": 0, "tries": 1},            # nothing finishes in zero ticks
        "2026-10-08": {"ticks": True, "tries": 1},         # a bool is not a tick count
        "2026-10-09": {"ticks": "1200", "tries": 1},
        "2026-10-10": "junk",
        5: {"ticks": 900, "tries": 1},
    }
    clean = challenges.clean_days(raw)
    assert set(clean) == {"2026-10-05", "2026-10-06"}
    assert clean["2026-10-05"] == good and "under_par" not in clean["2026-10-06"]
    assert challenges.clean_days("nope") == {} and challenges.clean_days(None) == {}


def test_merge_record_keeps_the_best_time_and_counts_tries():
    first = challenges.merge_record(None, 2000, 1800)
    assert first == {"ticks": 2000, "tries": 1}
    second = challenges.merge_record(first, 1700, 1800)
    assert second == {"ticks": 1700, "tries": 2, "under_par": True}
    third = challenges.merge_record(second, 2500, 1800)
    assert third == {"ticks": 1700, "tries": 3, "under_par": True}


def test_tally_has_no_streak_and_counts_only_open_days():
    days = {"2026-10-02": {"ticks": 900, "tries": 1}, "2026-10-04": {"ticks": 800, "tries": 1, "under_par": True},
            "2026-11-01": {"ticks": 800, "tries": 1}}  # a "future" day in the save is not counted
    tally = challenges.tally(days, "2026-10-11")
    assert tally == {"open": 11, "played": 2, "under_par": 1}
    assert "streak" not in json.dumps(tally)
    assert challenges.tally({}, "2026-09-01")["open"] == 0


def test_leaderboard_hook_is_named_and_pure():
    entry = challenges.leaderboard_entry("2026-10-05", {"ticks": 1234, "tries": 1})
    assert entry == {"board": "sol-scarcity-daily", "date": "2026-10-05", "words": challenges.seed_words("2026-10-05"),
                     "score": 1234, "unit": "ticks"}


def test_challenges_module_never_reads_the_clock():
    source = (GAME_DIR / "challenges.py").read_text()
    for forbidden in ("time.time", "datetime.now", "date.today", "import time", "import random", "utcnow"):
        assert forbidden not in source


# --- the fairness proof ---------------------------------------------------------------------------------


def test_every_date_over_300_consecutive_days_is_completable_by_the_reference_plan(game_env):
    m = game_env.module
    for i in range(300):
        date = challenges.add_days("2026-10-01", i)
        spec = m.scarcity_spec(date)
        assert spec["par"] <= m.SCARCITY_BOUND_TICKS and spec["par"] >= m.SCARCITY_MIN_TICKS, date
        assert spec["attempt"] < 4, date  # the first candidate is almost always the day
        assert spec["par_recording"]["pct"][-1] >= spec["target_pct"] * 10 - 10
    assert len(m._scarcity_specs) <= 61  # memoised, and bounded


def test_the_reference_plan_is_deterministic(game_env):
    m = game_env.module
    spec = challenges.make_spec("2026-10-11")
    first = m._scarcity_headless(spec)
    second = m._scarcity_headless(spec)
    assert first == second and first[0] is not None


def test_a_headless_proof_leaves_the_real_game_untouched(game_env):
    m = game_env.module
    _rich_game(game_env)
    before = json.dumps(m.get_state(), sort_keys=True)
    m.scarcity_spec("2026-10-03")
    assert json.dumps(m.get_state(), sort_keys=True) == before
    assert m._scarcity is None and m._dry_run is False


def test_a_bad_date_has_no_run(game_env):
    m = game_env.module
    _today(game_env)
    for bad in ("2026-09-30", "2026-10-12", "nope"):
        assert m.start_scarcity_run(bad) is False and m._scarcity is None


# --- playing a day on a copy ----------------------------------------------------------------------------


def test_starting_a_day_swaps_in_the_day_and_leaving_restores_the_campaign_byte_for_byte(game_env):
    m = game_env.module
    _today(game_env)
    _rich_game(game_env)
    before = json.dumps(m.get_state(), sort_keys=True)
    assert m.start_scarcity_run(TODAY) is True
    spec = m._scarcity["spec"]
    assert m.total_ticks < 100 and m.prestige_level == 0 and m.current_planet == "Earth"
    assert env_planet_matches_loadout(m, spec)
    assert m.unlocked_bodies == {"Moon", "Mars"} and m.mutators_run == [] and m.doctrine_rules == []
    # the widget would be handed the real campaign while the run is on
    assert json.dumps(m.get_state(), sort_keys=True) == before
    _play_a_bit(game_env)
    env_buy_things(game_env)
    assert json.dumps(m.get_state(), sort_keys=True) == before
    assert m.leave_scarcity_run() is True and m._scarcity is None
    assert json.dumps(m.get_state(), sort_keys=True) == before
    assert m.prestige_level == 2 and m.total_ticks == 54321 and game_env.earth["generator_count"] == 14
    assert not m.leave_scarcity_run()


def env_planet_matches_loadout(m, spec):
    for world, load in spec["loadout"].items():
        state = m.planet_state[world]
        if (state["generator_count"], state["recycler_count"]) != (load["generators"], load["recyclers"]):
            return False
        if state["resource_count"] != load["stock"] or state["ecology_health"] != load["ecology"]:
            return False
    return True


def env_buy_things(env):
    env.earth["resource_count"] += 500
    env.buy_generator("Earth")
    env.buy_recycler("Earth")


def test_finishing_a_day_writes_only_the_run_record_to_the_save(game_env):
    m = game_env.module
    _today(game_env)
    _rich_game(game_env)
    before = m.get_state()
    m.start_scarcity_run(TODAY)
    for world in m._scarcity["spec"]["targets"]:
        m.planet_state[world]["terraform_progress"] = float(m._scarcity["spec"]["target_pct"])
    m.tick()
    assert m._scarcity["done"] is not None
    record = m.scarcity_days[TODAY]
    assert record["ticks"] == m._scarcity["done"] and record["tries"] == 1
    saved = m.get_state()
    assert saved.pop("scarcity_days") == {TODAY: record}
    assert json.dumps(saved, sort_keys=True) == json.dumps(before, sort_keys=True)
    m.leave_scarcity_run()
    assert m.get_state()["scarcity_days"] == {TODAY: record}
    assert "scarcity_days" not in before


def test_time_is_counted_in_game_ticks_not_wall_clock(game_env):
    m = game_env.module
    _today(game_env)
    m.start_scarcity_run(TODAY)
    for _ in range(37):
        m.tick()
    assert m.total_ticks == 37
    for world in m._scarcity["spec"]["targets"]:
        m.planet_state[world]["terraform_progress"] = 100.0
    m.tick()
    assert m.scarcity_days[TODAY]["ticks"] == 38


def test_a_second_finish_keeps_the_best_time_and_counts_the_try(game_env):
    m = game_env.module
    _today(game_env)
    m.scarcity_days[TODAY] = {"ticks": 3, "tries": 1}
    m.start_scarcity_run(TODAY)
    for _ in range(6):
        m.tick()
    for world in m._scarcity["spec"]["targets"]:
        m.planet_state[world]["terraform_progress"] = 100.0
    m.tick()
    assert m._scarcity["done"] == 7
    assert m.scarcity_days[TODAY]["ticks"] == 3 and m.scarcity_days[TODAY]["tries"] == 2


def test_under_par_is_recorded_when_you_beat_the_reference_plan(game_env):
    m = game_env.module
    _today(game_env)
    m.start_scarcity_run(TODAY)
    for world in m._scarcity["spec"]["targets"]:
        m.planet_state[world]["terraform_progress"] = 100.0
    m.tick()
    assert m.scarcity_days[TODAY].get("under_par") is True  # one tick is certainly under par
    assert {"scarcity_survivor", "outplayed_governor"} <= set(m.achievement_ids_earned())


def test_the_rules_of_the_day_change_the_numbers(game_env):
    m = game_env.module
    _today(game_env)
    m.start_scarcity_run(TODAY)
    spec = m._scarcity["spec"]
    world = "Earth"
    cfg = m.PLANETS[world]
    base = cfg["generator_base_cost"] * (1.0 - m.research_effect("machinery_discount"))
    assert m.generator_cost(world) == __import__("math").ceil(
        base * spec["cost"] * m._cost_growth(cfg, "generator_cost_growth") ** m.planet_state[world]["generator_count"])
    assert m.scarcity_decay() == spec["decay"] and m.scarcity_terraform() == challenges.TERRAFORM_SPEED
    state = m.planet_state[world]
    state.update({"generator_count": 2, "recycler_count": 0, "ecology_health": 100.0, "resource_count": 0.0})
    m._simulate_planet(world, 0.0)
    expected_decay = 2 * cfg["ecology_decay_per_generator_per_sec"] * 0.1 * spec["decay"]
    assert abs((100.0 - state["ecology_health"]) - expected_decay) < 1e-9
    # the world's yield factor scales hand mining too
    state["resource_count"] = 0.0
    game_env.click(world)
    assert abs(state["resource_count"] - m._yield_multiplier() * spec["yields"][world]) < 1e-9
    m.leave_scarcity_run()
    assert m.scarcity_decay() == 1.0 and m.scarcity_cost() == 1.0 and m.scarcity_terraform() == 1.0 and m.scarcity_yield("Earth") == 1.0


def test_gameplay_extras_are_off_inside_a_run_and_back_after(game_env):
    m = game_env.module
    _today(game_env)
    game_env.local_storage.setItem("sol-anomalies", "on")
    game_env.local_storage.setItem("sol-click-streak", "on")
    game_env.local_storage.setItem("sol-chain-bonus", "on")
    assert m._anomalies_enabled() and m._setting_on("sol-click-streak")
    m.start_scarcity_run(TODAY)
    assert not m._anomalies_enabled() and not m._setting_on("sol-click-streak") and not m._setting_on("sol-chain-bonus")
    assert not m._setting_on("sol-rivals")
    m.leave_scarcity_run()
    assert m._anomalies_enabled() and m._setting_on("sol-click-streak")


def test_a_run_never_counts_for_achievements_the_board_or_prestige(game_env):
    m = game_env.module
    _today(game_env)
    reported = []
    window = types.SimpleNamespace(NoyvjLeaderboard=types.SimpleNamespace(report=lambda *a: reported.append(a)))
    import js
    js.window = window
    m.start_scarcity_run(TODAY)
    for planet in m.PLANETS:
        m.planet_state[planet]["terraform_progress"] = 100.0
    m.tick()
    m.tick()
    assert reported == [] and m.full_system_completed_tick is None and m.best_run_ticks is None
    assert m._prestige_available() is False
    assert game_env.elements["win-banner"].hidden is True
    m.leave_scarcity_run()
    assert m.full_system_completed_tick is None and m.run_completed is False
    del js.window


def test_capsules_belong_to_the_campaign(game_env):
    m = game_env.module
    _today(game_env)
    capsule = m.freeze_capsule("before")
    m.start_scarcity_run(TODAY)
    assert m.freeze_capsule("inside") is None
    assert "Leave it first" in m.capsule_replay(capsule["id"]) and "Leave it first" in m.capsule_diff(capsule["id"])
    assert len(m.capsules) == 1
    m.leave_scarcity_run()
    assert m.capsule_replay(capsule["id"]).startswith("Replay")


def test_stats_codes_and_comparison_wait_for_the_campaign(game_env):
    m = game_env.module
    _today(game_env)
    m.start_scarcity_run(TODAY)
    assert m.export_stats_code() == ""
    ok, message = m.import_stats_code("SOLSTATS1:abc")
    assert ok is False and "Leave it first" in message
    game_env.elements["stats-export-button"].dispatch("click", None)
    assert "Leave it first" in game_env.elements["stats-code-status"].innerText
    m.leave_scarcity_run()
    assert m.export_stats_code().startswith("SOLSTATS1:")


def test_loading_a_save_ends_a_run_and_takes_the_saves_record(game_env):
    m = game_env.module
    _today(game_env)
    m.start_scarcity_run(TODAY)
    data = {"planet_state": {"Earth": {"resource_count": 77.0}}, "scarcity_days": {"2026-10-03": {"ticks": 900, "tries": 1}}}
    assert m.load_state(data) is True
    assert m._scarcity is None and m.planet_state["Earth"]["resource_count"] == 77.0
    assert m.scarcity_days == {"2026-10-03": {"ticks": 900, "tries": 1}}
    assert m.generator_cost("Earth") == m.PLANETS["Earth"]["generator_base_cost"]  # no leftover day rules


def test_an_old_save_loads_unchanged_and_new_keys_are_written_only_when_set(game_env):
    m = game_env.module
    assert "scarcity_days" not in m.get_state()
    old = m.get_state()
    m.load_state(json.loads(json.dumps(old)))
    assert m.scarcity_days == {} and "scarcity_days" not in m.get_state()
    m.scarcity_days["2026-10-04"] = {"ticks": 1000, "tries": 1}
    assert m.get_state()["scarcity_days"] == {"2026-10-04": {"ticks": 1000, "tries": 1}}


def test_a_hand_edited_record_map_is_cleaned_entry_by_entry_on_load(game_env):
    m = game_env.module
    data = m.get_state()
    data["scarcity_days"] = {"2026-10-04": {"ticks": 1000, "tries": 1}, "junk": {"ticks": 5, "tries": 1},
                             "2026-10-05": {"ticks": -4, "tries": 1}, "2026-10-06": 12}
    m.load_state(data)
    assert m.scarcity_days == {"2026-10-04": {"ticks": 1000, "tries": 1}}
    data["scarcity_days"] = "garbage"
    m.load_state(data)
    assert m.scarcity_days == {}


def test_restarting_a_day_goes_back_to_the_loadout_and_still_leaves_the_campaign_alone(game_env):
    m = game_env.module
    _today(game_env)
    _rich_game(game_env)
    before = json.dumps(m.get_state(), sort_keys=True)
    m.start_scarcity_run(TODAY)
    _play_a_bit(game_env, 20)
    assert m.start_scarcity_run(TODAY) is True
    assert m.total_ticks == 0 and env_planet_matches_loadout(m, m._scarcity["spec"])
    m.start_scarcity_run("2026-10-03")  # a different day while one is on
    assert m._scarcity["spec"]["date"] == "2026-10-03"
    m.leave_scarcity_run()
    assert json.dumps(m.get_state(), sort_keys=True) == before


# --- A-12: the seed words on the Stats & Share card and in the panel ---------------------------------------


def test_the_stats_card_shows_todays_seed_words(game_env):
    m = game_env.module
    _today(game_env)
    card = m.build_share_card_text()
    assert f"Today's seed: {challenges.seed_words(TODAY)}" in card
    m.scarcity_days[TODAY] = {"ticks": 1234, "tries": 1}
    assert "Scarcity Run today: 2m 3s" in m.build_share_card_text()
    m.TODAY_OVERRIDE = None
    assert "Today's seed" not in m.build_share_card_text()  # no clock, no line


def test_the_stats_card_describes_the_run_while_one_is_on(game_env):
    m = game_env.module
    _today(game_env)
    m.start_scarcity_run(TODAY)
    card = m.build_share_card_text()
    assert "SOL Scarcity Run" in card and challenges.seed_words(TODAY) in card and "Goal: Terraform" in card
    assert "My Solar System" not in card
    fields = m.copy_result_fields()
    assert fields["unit"].startswith("Scarcity Run ") and fields["game"] == "SOL"


def test_the_panel_shows_the_seed_goal_rules_and_par(game_env):
    m = game_env.module
    _today(game_env)
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    text = _panel_text(game_env)
    spec = m.scarcity_spec(TODAY)
    assert challenges.seed_words(TODAY) in text and challenges.goal_text(spec) in text
    assert "(par)" in text and "Today's Scarcity Run" in text and "no streaks" in text
    assert "ecology decays" in text.lower() and "Start on Earth" in text


def test_the_calendar_offers_every_open_day_and_nothing_else(game_env):
    _today(game_env)
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    days = [b for b in _buttons(game_env.elements["scarcity-panel"]) if b.getAttribute("data-action") == "pick"]
    open_days = [b.getAttribute("data-date") for b in days if not b.disabled]
    assert open_days == [challenges.add_days("2026-10-01", i) for i in range(11)]
    assert all(b.disabled for b in days if b.getAttribute("data-date") > TODAY)
    # nothing earlier than October exists to page back to, and nothing later than this month to page forward to
    nav = {b.getAttribute("data-value"): b for b in _buttons(game_env.elements["scarcity-panel"]) if b.getAttribute("data-action") == "month"}
    assert nav["-1"].disabled and nav["1"].disabled


def test_picking_a_past_day_shows_its_card_and_playing_it_starts_the_run(game_env):
    m = game_env.module
    _today(game_env)
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    game_env.panel_click("scarcity-panel", action="pick", date="2026-10-03")
    text = _panel_text(game_env)
    assert challenges.seed_words("2026-10-03") in text and "Past day" in text and "Play 3 October 2026" in text
    game_env.panel_click("scarcity-panel", action="play", date="2026-10-03")
    assert m._scarcity["spec"]["date"] == "2026-10-03"
    assert game_env.elements["scarcity-strip"].hidden is False
    assert challenges.seed_words("2026-10-03") in game_env.elements["scarcity-strip-text"].innerText
    assert "Leave the run" in _panel_text(game_env)
    game_env.elements["scarcity-leave-button"].dispatch("click", None)
    assert m._scarcity is None and game_env.elements["scarcity-strip"].hidden is True


def test_a_future_day_cannot_be_picked_or_played(game_env):
    m = game_env.module
    _today(game_env)
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    game_env.panel_click("scarcity-panel", action="pick", date="2026-10-20")
    game_env.panel_click("scarcity-panel", action="play", date="2026-10-20")
    assert m._scarcity is None and "That day is not open yet" in _panel_text(game_env)


def test_the_tally_and_grid_have_no_streak_and_use_symbols_with_a_legend(game_env):
    m = game_env.module
    _today(game_env)
    m.scarcity_days.update({"2026-10-02": {"ticks": 900, "tries": 1}, "2026-10-04": {"ticks": 800, "tries": 1, "under_par": True}})
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    text = _panel_text(game_env)
    assert "Days played: 2 of the 11 open so far" in text and "streak" not in text.replace("no streaks", "")
    assert "■" in text and "★" in text and "□" in text and "not played" in text
    picks = {b.getAttribute("data-date"): b for b in _buttons(game_env.elements["scarcity-panel"]) if b.getAttribute("data-action") == "pick"}
    assert "done in" in picks["2026-10-02"].getAttribute("aria-label")
    assert "faster than the Governor alone" in picks["2026-10-04"].getAttribute("aria-label")


def test_the_panel_names_the_leaderboard_hook_and_sends_nothing(game_env):
    m = game_env.module
    _today(game_env)
    m.scarcity_days["2026-10-02"] = {"ticks": 900, "tries": 1}
    assert m.scarcity_leaderboard_entry("2026-10-02")["board"] == "sol-scarcity-daily"
    assert m.scarcity_leaderboard_entry("2026-10-03") is None
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    assert "sol-scarcity-daily" in _panel_text(game_env) and "nothing is sent anywhere" in _panel_text(game_env)


def test_without_a_clock_the_panel_says_so_instead_of_guessing(game_env):
    game_env.module.TODAY_OVERRIDE = None
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    assert "date is not available" in _panel_text(game_env)


# --- achievements -------------------------------------------------------------------------------------


def test_the_three_scarcity_achievements_and_the_catalogue_size(game_env):
    m = game_env.module
    ids = {entry["id"] for entry in m.ACHIEVEMENTS}
    assert {"scarcity_survivor", "outplayed_governor", "seven_scarce_days"} <= ids
    assert len(m.ACHIEVEMENTS) == 36
    assert not {"scarcity_survivor", "outplayed_governor", "seven_scarce_days"} & set(m.achievement_ids_earned())
    for i in range(6):
        m.scarcity_days[challenges.add_days("2026-10-01", i)] = {"ticks": 900, "tries": 1}
    assert m.ACHIEVEMENT_PROGRESS["seven_scarce_days"]() == (6, 7)
    assert "seven_scarce_days" not in m.achievement_ids_earned() and "scarcity_survivor" in m.achievement_ids_earned()
    m.scarcity_days["2026-10-07"] = {"ticks": 900, "tries": 1, "under_par": True}
    assert {"seven_scarce_days", "outplayed_governor"} <= set(m.achievement_ids_earned())


# --- the pages ------------------------------------------------------------------------------------------------


def test_every_new_element_exists_on_both_pages_and_the_new_files_are_fetched():
    ids = ["scarcity-toggle-button", "scarcity-panel", "scarcity-strip", "scarcity-strip-text", "scarcity-leave-button", "ghost-strip"]
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text()
        for element_id in ids:
            assert f'id="{element_id}"' in html, (page, element_id)
        assert 'fetch("challenges.py")' in html and 'fetch("../../shared/seed.py")' in html
    config = json.loads((GAME_DIR / "pc-config.json").read_text())
    assert ["scarcity-panel", "scarcity-toggle-button", "Scarcity Run"] in config["windows"]
    assert any("scarcity-toggle-button" in group["ids"] for group in config["toolbar"]["menu"])
    assert "#scarcity-strip" in config["zones"]["stagebar"] and "#ghost-strip" in config["zones"]["stagebar"]


def test_the_stats_card_and_game_have_no_real_world_tie_in():
    source = (GAME_DIR / "challenges.py").read_text().lower()
    assert "http" not in source and "fetch" not in source


# --- Z-5b: finishing TODAY's run is told to the shared daily record the hub's Today strip reads -------------------
def _fake_shared_daily(game_env):
    import sys
    calls = []

    class Obj:
        @classmethod
        def new(cls):
            return types.SimpleNamespace()

    js = sys.modules["js"]
    js.Object = Obj
    js.window = types.SimpleNamespace(NoyvjSeed=types.SimpleNamespace(
        daily=types.SimpleNamespace(markCompleted=lambda game, info: calls.append((game, info.text)))))
    return calls


def _finish_run(m, date):
    m.start_scarcity_run(date)
    for world in m._scarcity["spec"]["targets"]:
        m.planet_state[world]["terraform_progress"] = float(m._scarcity["spec"]["target_pct"]) + 5
    m.tick()
    assert m._scarcity["done"] is not None


def test_finishing_todays_run_marks_the_shared_daily_once(game_env):
    m = game_env.module
    _today(game_env)
    calls = _fake_shared_daily(game_env)
    _finish_run(m, TODAY)
    assert len(calls) == 1 and calls[0][0] == "sol"
    assert calls[0][1].startswith("Scarcity Run " + challenges.seed_words(TODAY) + " in ")
    assert len(calls[0][1]) <= 120


def test_an_older_day_from_the_calendar_never_marks_the_shared_daily(game_env):
    m = game_env.module
    _today(game_env)
    calls = _fake_shared_daily(game_env)
    _finish_run(m, "2026-10-03")
    assert calls == []


def test_a_page_without_the_shared_script_still_finishes_the_run(game_env):
    m = game_env.module
    _today(game_env)
    _finish_run(m, TODAY)
    assert TODAY in m.scarcity_days


def test_a_failing_shared_record_never_breaks_the_result(game_env):
    import sys
    m = game_env.module
    _today(game_env)
    calls = _fake_shared_daily(game_env)

    def boom(game, info):
        raise RuntimeError("storage is full")

    sys.modules["js"].window.NoyvjSeed.daily.markCompleted = boom
    _finish_run(m, TODAY)
    assert TODAY in m.scarcity_days and calls == []
