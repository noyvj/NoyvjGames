"""O-5..O-8: founding a new settlement, the archive jumping-off buttons, the
founder's legacy and the Refuge Start scenario."""

import json
import sys
import types

import pytest

import archive
import consulting
import founding
import research
import save
import sim

GOOD_THUMB = archive.THUMB_PREFIX + "QUJD"


class FakeStorage:
    def __init__(self):
        self.data = {}
        self.fail = False

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        if self.fail:
            raise RuntimeError("quota")
        self.data[key] = value


class FakeConfirm:
    def __init__(self):
        self.asked = []

    def ask(self, **kwargs):
        self.asked.append(kwargs)


def _window(confirm=None):
    storage = FakeStorage()
    win = types.SimpleNamespace(localStorage=storage)
    if confirm is not None:
        win.ConfirmDialog = confirm
    sys.modules["js"].window = win
    return storage


def _stored(storage):
    return json.loads(storage.data.get(archive.STORAGE_KEY, "[]"))


def _play(env, seasons=3):
    env.advance_season(seasons)


def _click(env, element_id):
    env.elements[element_id].dispatch("click", None)


def _reach(env, era):
    env.state.era = era
    env.module.campaign.furthest_era = era
    env.module.tree.current_era = era


def _tree_vars(tree):
    return {"researched": list(tree.researched), "era": tree.current_era}


# --- engine: the legacy table -------------------------------------------


def test_every_era_maps_to_exactly_one_legacy():
    for era in sim.ERA_ORDER:
        owners = [lid for lid, legacy in founding.LEGACIES.items() if era in legacy["eras"]]
        assert len(owners) == 1, era
    assert founding.legacy_id_for_era("mars") is None


def test_legacy_bonuses_are_small_single_resource_gifts():
    caps = {"food": 8.0, "materials": 12.0, "knowledge": 4.0, "tools": 1.0}
    for legacy in founding.LEGACIES.values():
        assert legacy["resource"] in caps
        assert 0 < legacy["amount"] <= caps[legacy["resource"]]
        assert legacy["label"] and legacy["blurb"]


def test_make_legacy_uses_the_record_era_and_rejects_junk():
    assert founding.make_legacy({"era": "medieval"}) == {"id": "builders_plans", "from_era": "medieval", "applied": False}
    assert founding.make_legacy({"era": "relay"})["id"] == "salvage_kit"
    for bad in (None, 5, "x", {}, {"era": "mars"}, {"era": ["tribal"]}):
        assert founding.make_legacy(bad) is None


def test_clean_legacy_is_adversarially_safe():
    good = {"id": "seed_stock", "from_era": "tribal", "applied": True}
    assert founding.clean_legacy(good) == good
    assert founding.clean_legacy({"id": "seed_stock", "from_era": "tribal", "applied": 1})["applied"] is False
    for bad in (None, [], "seed_stock", {"id": ["x"], "from_era": "tribal"}, {"id": "nope", "from_era": "tribal"},
                {"id": "seed_stock", "from_era": "space"}, {"id": "seed_stock", "from_era": {"a": 1}}, {"id": True}):
        assert founding.clean_legacy(bad) is None
    assert founding.get_legacy({"legacy": 7}) is None
    assert founding.get_legacy(None) is None


def test_clean_earned_filters_and_caps():
    valid = ["a", "b"]
    assert founding.clean_earned(["a", "a", "b", "zzz", 3, ["a"], {"x": 1}, None], valid) == ["a", "b"]
    assert founding.clean_earned("a", valid) == []
    assert founding.clean_earned(None, valid) == []
    assert len(founding.clean_earned([str(i) for i in range(1000)], [str(i) for i in range(1000)])) == founding.EARNED_MAX


def test_status_text_states():
    entry = {"id": "seed_stock", "from_era": "tribal", "applied": False}
    assert founding.status_text(None) == ""
    assert "+6 food" in founding.status_text(entry)
    assert "Arrives with your first season" in founding.status_text(entry)
    assert "Not used" in founding.status_text(entry, consulting_active=True)
    assert "Delivered" in founding.status_text(dict(entry, applied=True))


def test_apply_legacy_delivers_once_and_only_in_season_one():
    c = save.Campaign()
    c.ui["legacy"] = {"id": "seed_stock", "from_era": "tribal", "applied": False}
    food = c.state.resources["food"]
    assert founding.apply_legacy(c) is not None
    assert c.state.resources["food"] == food + 6.0
    assert founding.apply_legacy(c) is None  # never twice
    assert c.state.resources["food"] == food + 6.0
    late = save.Campaign()
    late.state.season = 5
    late.ui["legacy"] = {"id": "seed_stock", "from_era": "tribal", "applied": False}
    food = late.state.resources["food"]
    assert founding.apply_legacy(late) is None
    assert late.state.resources["food"] == food
    assert founding.get_legacy(late.ui)["applied"] is True  # consumed, not kept for later


def test_apply_legacy_is_skipped_for_a_consulting_case():
    c = save.Campaign()
    c.ui["legacy"] = {"id": "recorded_lessons", "from_era": "digital", "applied": False}
    before = dict(c.state.resources)
    assert founding.apply_legacy(c, consulting_active=True) is None
    assert c.state.resources == before


def test_legacy_never_breaks_the_opening_balance():
    """A legacy is at most one season's small gift: with it, the standard
    opening still scores the same band and survives the same ten idle seasons."""
    import sustainability

    for legacy_id, legacy in founding.LEGACIES.items():
        base = save.Campaign()
        gifted = save.Campaign()
        gifted.ui["legacy"] = {"id": legacy_id, "from_era": legacy["eras"][0], "applied": False}
        founding.apply_legacy(gifted)
        for _ in range(10):
            base.state.advance_season(base.tree.effects())
            gifted.state.advance_season(gifted.tree.effects())
        b = sustainability.score(base.state, base.tree.effects())
        g = sustainability.score(gifted.state, gifted.tree.effects())
        assert sustainability.score_label(g) == sustainability.score_label(b)
        assert gifted.state.population >= base.state.population - 0
        assert abs(gifted.state.population - base.state.population) <= 2


# --- engine: reset -------------------------------------------------------


def test_found_new_resets_everything_a_fresh_campaign_has():
    c = save.Campaign()
    for _ in range(12):
        c.state.advance_season(c.tree.effects())
        c.state.record_score(80.0)
    c.state.hard_mode = True
    c.state.scenario = "frontier"
    c.state.era = "digital"
    c.furthest_era = "digital"
    c.state.pollution = 0.5
    c.state.calm_streak = 9
    c.state.trajectory = [[1, 1, 1, 1]]
    c.state.resources["knowledge"] = 500.0
    c.tree.restore(["fire_keeping", "foraging_lore"])
    c.era_snapshots = {"tribal": {"x": 1}}
    c.has_revisited = True
    c.ui = {"founders_log": [{"note": "hi"}], "play_seconds": 99, "consulting": {"case": "sprawl"}}
    c.log.check_population(c.state)
    assert founding.found_new(c, c.log)
    fresh = save.Campaign()
    assert vars(c.state) == vars(fresh.state)
    assert c.tree.researched == [] and c.tree.current_era == sim.FIRST_ERA
    assert c.furthest_era == sim.FIRST_ERA and c.revisiting is None and c.parked_state is None
    assert c.era_snapshots == {} and c.has_revisited is False
    assert c.ui == {}  # nothing non-default is written
    assert c.to_dict()["ui"] == {}
    assert c.log.entries == fresh.log.entries


def test_found_new_keeps_the_same_objects_so_aliases_stay_valid():
    c = save.Campaign()
    state, tree, log = c.state, c.tree, c.log
    founding.found_new(c, c.log)
    assert c.state is state and c.tree is tree and c.log is log


def test_found_new_refuses_during_a_look_back():
    c = save.Campaign()
    c.state.era = "agrarian"
    c.record_era_snapshot("tribal")
    c.furthest_era = "agrarian"
    assert c.enter_revisit("tribal")
    assert founding.found_new(c, c.log) is False
    assert c.revisiting == "tribal"


def test_found_new_stores_only_validated_ui_keys():
    c = save.Campaign()
    founding.found_new(c, c.log, {"id": "bogus"}, ["a", "b"])
    assert "legacy" not in c.ui
    assert c.ui["earned_before"] == ["a", "b"]
    founding.found_new(c, c.log, {"id": "seed_stock", "from_era": "tribal", "applied": False}, [])
    assert c.ui == {"legacy": {"id": "seed_stock", "from_era": "tribal", "applied": False}}


def test_is_pristine():
    c = save.Campaign()
    assert founding.is_pristine(c)
    c.state.season = 2
    assert not founding.is_pristine(c)
    c = save.Campaign()
    c.tree.restore(["fire_keeping"])
    assert not founding.is_pristine(c)
    c = save.Campaign()
    consulting.apply(c, "smokestack")  # inherited research is not the player's
    assert founding.is_pristine(c)


def test_consulting_abandon_keeps_legacy_and_earned_before():
    c = save.Campaign()
    c.ui["legacy"] = {"id": "seed_stock", "from_era": "tribal", "applied": False}
    c.ui["earned_before"] = ["reached_space"]
    assert consulting.apply(c, "smokestack")
    assert consulting.abandon(c)
    assert c.ui["legacy"]["id"] == "seed_stock" and c.ui["earned_before"] == ["reached_space"]
    assert "consulting" not in c.ui


# --- Refuge scenario (O-8) ------------------------------------------------


def test_refuge_is_a_distinct_shape_not_a_dial():
    standard = sim.CityState(scenario="standard")
    refuge = sim.CityState(scenario="refuge")
    assert refuge.scenario == "refuge"
    assert refuge.population > standard.population * 1.5  # a larger group
    assert refuge.land_health < 0.75  # depleted land
    assert refuge.resources["knowledge"] > standard.resources["knowledge"]  # the elders' memory
    assert refuge.population > refuge.housing_capacity()  # too few roofs
    assert refuge.population >= refuge.assigned_workers()
    assert sim.CityState(scenario="standard").resources["knowledge"] == sim.START_KNOWLEDGE


def _food_first(state, tree):
    while state.idle_workers() > 0:
        need = state.population * 2 / (3 * state.land_health)
        if state.allocation["foragers"] < need and state.allocation["foragers"] < state.population - 2:
            state.allocation["foragers"] += 1
        else:
            state.allocation["keepers"] += 1
    for node_id, node in sorted(tree.nodes.items(), key=lambda kv: kv[1].cost):
        if node_id not in tree.researched and tree.research(node_id, state.resources):
            break
    if state.population > state.housing_capacity(tree.effects()) and state.resources["materials"] >= 12:
        state.buildings["shelter"] += 1
        state.resources["materials"] -= 12


def test_refuge_is_fair_a_sensible_plan_keeps_everyone_fed_and_heals_the_land():
    state = sim.CityState(scenario="refuge")
    tree = research.build_tree()
    for _ in range(30):
        _food_first(state, tree)
        state.advance_season(tree.effects())
    assert state.population >= 12  # nobody was lost
    assert state.land_health > 0.6  # the ground recovered


def test_refuge_punishes_leaving_the_crowd_idle():
    state = sim.CityState(scenario="refuge")
    tree = research.build_tree()
    for _ in range(10):
        state.advance_season(tree.effects())
    assert state.population < 8


def test_refuge_unlock_rule():
    assert founding.refuge_unlocked([], []) is False
    assert founding.refuge_unlocked(["reached_agrarian"], [{"era": "medieval"}]) is False
    assert founding.refuge_unlocked(["reached_space"], []) is True
    assert founding.refuge_unlocked(["reached_relay"], []) is True
    assert founding.refuge_unlocked([], [{"era": "space"}]) is True
    assert founding.refuge_unlocked([], ["junk", None, {"era": ["space"]}, {"era": "mars"}]) is False


# --- game.py flow ---------------------------------------------------------


def test_refuge_button_is_locked_until_space_age_reached(game_env):
    e = game_env
    _window()
    e.module.render()
    button = e.elements["scenario-refuge-button"]
    assert button.disabled is True and "🔒" in button.innerText
    _click(e, "scenario-refuge-button")
    assert e.state.scenario == "standard"  # refused even if clicked
    _reach(e, "space")
    e.module.render()
    assert button.disabled is False and "🔒" not in button.innerText


def test_refuge_unlocked_by_an_archived_space_settlement_and_applies(game_env):
    e = game_env
    storage = _window()
    storage.data[archive.STORAGE_KEY] = json.dumps(
        [{"saved_on": "2026-09-01", "era": "relay", "seasons": 90, "peak_population": 300, "peak_score": 80,
          "rank": "Gold", "scenario": "standard", "hard_mode": False, "achievements": 5, "thumb": ""}]
    )
    e.module.render()
    _click(e, "scenario-refuge-button")
    assert e.state.scenario == "refuge"
    assert e.state.population == 12 and e.state.resources["knowledge"] == 6.0
    _click(e, "scenario-standard-button")
    assert e.state.resources["knowledge"] == sim.START_KNOWLEDGE  # switching back restores the opening
    assert e.state.population == sim.START_POPULATION


def test_found_new_flow_archives_first_then_resets(game_env):
    e = game_env
    storage = _window()
    _play(e, 4)
    e.state.hard_mode = True
    seasons_before = e.state.season
    _click(e, "found-settlement-button")
    stored = _stored(storage)
    assert len(stored) == 1 and stored[0]["seasons"] == seasons_before and stored[0]["hard_mode"] is True
    assert e.state.season == 1 and e.state.hard_mode is False
    assert e.state.era == sim.FIRST_ERA
    assert "filed in the archive" in e.elements["found-settlement-status"].innerText
    # the scenario picker, hard mode and consulting are open again
    assert e.elements["scenario-standard-button"].disabled is False
    assert e.elements["consulting-case-smokestack-button"].disabled is False
    assert e.module.sim_speed == 0  # every new settlement starts paused


def test_no_archive_means_no_reset_never_lose_an_unarchived_settlement(game_env):
    e = game_env
    _play(e, 4)  # no window at all: nowhere to archive
    _click(e, "found-settlement-button")
    assert e.state.season == 5
    assert "nothing was changed" in e.elements["found-settlement-status"].innerText
    storage = _window()
    storage.fail = True  # a full or blocked store
    _click(e, "found-settlement-button")
    assert e.state.season == 5 and storage.data == {}


def test_an_empty_settlement_needs_no_archive(game_env):
    e = game_env
    storage = _window()
    _click(e, "found-settlement-button")
    assert _stored(storage) == []
    assert e.state.season == 1


def test_already_archived_settlement_is_not_filed_twice(game_env):
    e = game_env
    storage = _window()
    _play(e, 3)
    e.module.on_archive_current()
    assert len(_stored(storage)) == 1
    _click(e, "found-settlement-button")
    assert len(_stored(storage)) == 1  # identical: not duplicated
    _play(e, 2)
    _click(e, "found-settlement-button")
    assert len(_stored(storage)) == 2  # it moved on, so the new state is filed


def test_confirm_dialog_gates_the_action(game_env):
    e = game_env
    confirm = FakeConfirm()
    storage = _window(confirm)
    _play(e, 3)
    _click(e, "found-settlement-button")
    assert len(confirm.asked) == 1
    ask = confirm.asked[0]
    assert ask["allowSkip"] is False and ask["id"] == "continuum-found-settlement"
    assert "archive" in ask["message"]
    assert e.state.season == 4 and _stored(storage) == []  # nothing happens until confirmed
    ask["onConfirm"]()
    assert e.state.season == 1 and len(_stored(storage)) == 1


def test_found_new_is_refused_during_a_look_back(game_env):
    e = game_env
    storage = _window()
    e.state.era = "agrarian"
    e.module.campaign.record_era_snapshot("tribal")
    e.module.campaign.furthest_era = "agrarian"
    assert e.module.campaign.enter_revisit("tribal")
    e.module.render()
    assert e.elements["found-settlement-button"].disabled is True
    e.module.on_found_new_settlement()
    assert "Return to the present" in e.elements["found-settlement-status"].innerText
    e.module.found_new_settlement()
    assert e.module.campaign.revisiting == "tribal" and _stored(storage) == []


def test_legacy_flows_from_the_archived_settlement_and_arrives_with_season_one(game_env):
    e = game_env
    storage = _window()
    _play(e, 3)
    _reach(e, "medieval")
    _click(e, "found-settlement-button")
    assert _stored(storage)[-1]["era"] == "medieval"
    entry = founding.get_legacy(e.module.campaign.ui)
    assert entry == {"id": "builders_plans", "from_era": "medieval", "applied": False}
    line = e.elements["legacy-display"]
    assert line.hidden is False and "Master Builders' Plans" in line.innerText and "+8 materials" in line.innerText
    materials = e.state.resources["materials"]
    assert materials == sim.START_MATERIALS  # not delivered yet
    e.advance_season()
    assert founding.get_legacy(e.module.campaign.ui)["applied"] is True
    assert "Delivered" in e.elements["legacy-display"].innerText
    assert any("Founder's legacy arrives" in en.text for en in e.module.chronicle.entries)
    e.advance_season(3)
    # exactly one delivery: the stock is nowhere near legacy-inflated (no stacking)
    assert founding.get_legacy(e.module.campaign.ui)["applied"] is True


def test_legacy_is_not_lost_by_picking_a_scenario_and_does_not_stack(game_env):
    e = game_env
    storage = _window()
    _play(e, 2)
    _click(e, "found-settlement-button")  # a tribal settlement: Seed Stock
    _click(e, "scenario-fertile-button")
    assert founding.get_legacy(e.module.campaign.ui)["id"] == "seed_stock"
    e.advance_season()  # delivered on top of the scenario's own opening
    _reach(e, "digital")
    _play(e, 2)
    _click(e, "found-settlement-button")
    # only the most recent archived settlement counts: Recorded Lessons, not both
    entry = founding.get_legacy(e.module.campaign.ui)
    assert entry["id"] == "recorded_lessons" and len(_stored(storage)) == 2
    assert set(e.module.campaign.ui) <= {"legacy", "earned_before"}


def test_a_consulting_case_does_not_receive_the_legacy(game_env):
    e = game_env
    _window()
    _play(e, 2)
    _reach(e, "space")
    _click(e, "found-settlement-button")
    _click(e, "consulting-case-smokestack-button")
    assert "Not used" in e.elements["legacy-display"].innerText
    e.advance_season()
    assert founding.get_legacy(e.module.campaign.ui)["applied"] is True  # consumed
    assert not any("Founder's legacy arrives" in en.text for en in e.module.chronicle.entries)


def test_an_unplayed_consulting_case_earns_no_legacy_for_its_inherited_era(game_env):
    e = game_env
    storage = _window()
    _click(e, "consulting-case-smokestack-button")
    _play(e, 2)
    _click(e, "found-settlement-button")
    assert founding.get_legacy(e.module.campaign.ui) is None  # inherited Industrial is not "reached"
    assert len(_stored(storage)) == 1


def test_achievements_earned_survive_founding_a_new_settlement(game_env):
    e = game_env
    _window()
    _play(e, 2)
    _reach(e, "space")
    before = e.module.achievement_ids_earned()
    assert "reached_space" in before
    _click(e, "found-settlement-button")
    after = e.module.achievement_ids_earned()
    assert set(before) <= set(after)
    assert e.module.get_state()["achievements_earned"] == after
    assert e.module.refuge_unlocked() is True


def test_hidden_state_keys_appear_only_when_non_default(game_env):
    e = game_env
    _window()
    ui = e.module.get_state()["ui"]
    assert "legacy" not in ui and "earned_before" not in ui
    _play(e, 2)
    _click(e, "found-settlement-button")
    ui = e.module.get_state()["ui"]
    assert "legacy" in ui and ui["earned_before"] == ["thriving_once"]  # only what was actually earned


def test_load_state_validates_the_new_ui_keys(game_env):
    e = game_env
    data = e.module.get_state()
    for bad in ({"id": "seed_stock", "from_era": "tribal", "applied": "yes"}, {"id": ["x"]}, "junk", 12, [1], {"id": True}):
        data["ui"]["legacy"] = bad
        data["ui"]["earned_before"] = bad
        assert e.module.load_state(json.loads(json.dumps(data)))
        assert founding.get_legacy(e.module.campaign.ui) in (None, {"id": "seed_stock", "from_era": "tribal", "applied": False})
        assert isinstance(e.module.achievement_ids_earned(), list)
    data["ui"]["earned_before"] = ["reached_space", "not_real", 5]
    e.module.load_state(json.loads(json.dumps(data)))
    ids = e.module.achievement_ids_earned()
    assert "reached_space" in ids and "not_real" not in ids
    e.module.render()  # nothing crashes with the garbage loaded


def test_a_saved_pending_legacy_survives_a_save_round_trip(game_env):
    e = game_env
    _window()
    _play(e, 2)
    _click(e, "found-settlement-button")
    data = json.loads(json.dumps(e.module.get_state()))
    e.module.campaign.ui.clear()
    assert founding.get_legacy(e.module.campaign.ui) is None
    assert e.module.load_state(data)
    assert founding.get_legacy(e.module.campaign.ui)["applied"] is False


def test_archive_entries_have_found_buttons(game_env):
    e = game_env
    storage = _window()
    _play(e, 3)
    e.module.on_archive_current()
    e.elements["summary-toggle-button"].dispatch("click", None)

    def find(wanted):
        def walk(el):
            for ch in el.children:
                if getattr(ch, "id", None) == wanted:
                    return ch
                got = walk(ch)
                if got:
                    return got
        return walk(e.elements["summary-panel"])

    assert find("archive-found-button") is not None
    entry_button = find("archive-found-0-button")
    assert entry_button is not None
    assert "Found a new settlement" in entry_button.innerText
    entry_button.dispatch("click", None)
    assert e.state.season == 1
    assert len(_stored(storage)) == 1  # the entry was already the current settlement: not duplicated


def test_the_scene_state_rebuilds_for_the_reset_settlement(game_env):
    e = game_env
    _window()
    _play(e, 2)
    _reach(e, "digital")
    _click(e, "found-settlement-button")
    visual = e.module.get_visual_state()
    assert visual["era"] == "tribal" and visual["season"] == 1
    assert e.module.hamlet_on in (True, False)  # the Hamlet view renders without error on the reset state
    e.module.render()


def test_the_paused_clock_does_not_carry_progress_into_the_new_settlement(game_env):
    e = game_env
    _window()
    e.module.set_speed(4)
    e.module.tick_clock(0.9)
    _play(e, 1)
    _click(e, "found-settlement-button")
    assert e.module.sim_speed == 0 and e.module.season_progress == 0.0


@pytest.mark.parametrize("scenario", list(sim.SCENARIOS))
def test_every_scenario_round_trips_through_save_and_archive(scenario):
    state = sim.CityState(scenario=scenario)
    fresh = sim.CityState()
    save.restore_city(fresh, save.city_snapshot(state))
    assert fresh.scenario == scenario
    c = save.Campaign(state)
    assert archive.make_record(c, 0, "2026-09-27")["scenario"] == scenario
