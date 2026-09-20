"""K22 -- consulting mode (consulting.py + game.py wiring)."""

import copy

import consulting
import save
import sim
import sustainability


def _fresh(case="smokestack"):
    c = save.Campaign()
    assert consulting.apply(c, case)
    return c


def test_every_case_is_a_valid_struggling_city():
    for case_id, case in consulting.CASES.items():
        c = _fresh(case_id)
        s = c.state
        ef = c.tree.effects()
        assert s.era == case["era"] and c.furthest_era == case["era"]
        assert s.assigned_workers() <= s.population
        assert set(case["buildings"]) <= set(sim.BUILDINGS)
        assert set(case["allocation"]) <= set(sim.ROLES)
        label = sustainability.score_label(sustainability.score(s, ef))
        assert label not in consulting.GOOD_LABELS
        assert 0.0 <= s.pollution <= 1.0 and 0.0 <= s.sprawl <= 1.0


def test_inherited_research_unlocks_every_tier_up_to_the_era_but_not_beyond():
    import research
    for case_id, case in consulting.CASES.items():
        c = _fresh(case_id)
        first = research.era_tiers(case["era"])[0]
        assert all(c.tree.tier_unlocked(t) for t in range(1, first + 1))
        assert not c.tree.tier_unlocked(research.era_tiers("space")[-1])
        assert all(n in c.tree.nodes for n in c.tree.researched)


def test_inherited_research_does_not_count_towards_tradition_achievements(game_env):
    e = game_env
    e.elements["consulting-case-sprawl-button"].dispatch("click", None)
    assert e.module.tree.affinity("provision") >= 8  # inherited...
    assert e.module._earned_affinity("provision") == 0  # ...but not earned
    earned = e.module.achievement_ids_earned()
    assert "provision_specialist" not in earned and "craft_specialist" not in earned


def test_the_sprawl_case_is_winnable_with_planners_and_transit():
    c = _fresh("sprawl")
    s = c.state
    a = s.allocation
    a["factory_workers"] = 9
    a["planners"] = 8
    a["gatherers"] += 3
    a["keepers"] += 5
    entry = None
    for _ in range(consulting.SEASON_LIMIT):
        ef = c.tree.effects()
        for b, cap in (("sanitation_works", 4), ("transit_hubs", 4), ("public_works", 5), ("shelter", 99), ("hearth", 99)):
            while s.can_build(b) and s.buildings[b] < cap:
                if b == "hearth" and s.culture_capacity(ef) >= s.population:
                    break
                if b == "shelter" and s.housing_capacity(ef) >= s.population + 3:
                    break
                s.build(b)
        s.clamp_allocation()
        s.advance_season(ef)
        entry = consulting.step(c, ef)
        if entry["result"]:
            break
    assert entry["result"] == "turned_around"


def test_only_a_pristine_start_can_take_a_case():
    c = save.Campaign()
    c.state.advance_season(c.tree.effects())
    assert not consulting.apply(c, "smokestack")
    c = _fresh()
    assert not consulting.apply(c, "sprawl")  # already consulting
    assert not consulting.apply(save.Campaign(), "no-such-case")


def test_idle_play_misses_and_a_sensible_plan_turns_it_around():
    idle = _fresh()
    for _ in range(consulting.SEASON_LIMIT):
        ef = idle.tree.effects()
        idle.state.advance_season(ef)
        entry = consulting.step(idle, ef)
    assert entry["result"] == "missed"

    plan = _fresh()
    s = plan.state
    a = s.allocation
    a["factory_workers"] = 9
    a["gatherers"] += 5
    a["keepers"] += 6
    for _ in range(consulting.SEASON_LIMIT):
        ef = plan.tree.effects()
        for b, cap in (("sanitation_works", 4), ("shelter", 99), ("hearth", 99)):
            while s.can_build(b) and s.buildings[b] < cap:
                if b == "hearth" and s.culture_capacity(ef) >= s.population:
                    break
                if b == "shelter" and s.housing_capacity(ef) >= s.population + 3:
                    break
                s.build(b)
        s.clamp_allocation()
        s.advance_season(ef)
        entry = consulting.step(plan, ef)
        if entry["result"]:
            break
    assert entry["result"] == "turned_around"
    assert "turned around" in consulting.status_text(entry, s)


def test_step_stops_updating_after_a_result():
    c = _fresh()
    c.ui["consulting"]["result"] = "missed"
    before = copy.deepcopy(c.ui["consulting"])
    consulting.step(c, c.tree.effects())
    assert c.ui["consulting"] == before


def test_clean_rejects_malformed_entries():
    for bad in (None, 3, "x", {}, {"case": "nope", "start_season": 1}, {"case": "smokestack", "start_season": 0},
                {"case": "smokestack", "start_season": "1"}, {"case": "smokestack", "start_season": True}):
        assert consulting.clean(bad) is None
    e = consulting.clean({"case": "smokestack", "start_season": 1, "streak": 99, "result": "bogus"})
    assert e["streak"] == consulting.HOLD_SEASONS and e["result"] is None
    assert consulting.get("not a dict") is None


def test_round_trips_through_the_save_dict_and_survives_tampering():
    c = _fresh()
    data = copy.deepcopy(c.to_dict())
    other = save.Campaign()
    assert other.load_dict(data)
    assert consulting.get(other.ui)["case"] == "smokestack"
    data["ui"]["consulting"] = {"case": ["x"], "start_season": float("nan")}
    third = save.Campaign()
    assert third.load_dict(data)
    assert consulting.get(third.ui) is None


def test_abandon_returns_to_a_fresh_start():
    c = _fresh()
    assert consulting.abandon(c)
    assert consulting.get(c.ui) is None
    assert c.state.era == sim.FIRST_ERA and c.furthest_era == sim.FIRST_ERA
    assert c.state.population == sim.START_POPULATION and not c.tree.researched
    assert consulting.is_pristine(c)
    assert not consulting.abandon(c)


def test_ui_start_lock_status_and_abandon(game_env):
    e = game_env
    assert e.elements["consulting-case-smokestack-button"].disabled is False
    e.elements["consulting-case-smokestack-button"].dispatch("click", None)
    assert e.state.era == "industrial"
    assert "Smokestack" in e.elements["consulting-status-display"].innerText
    assert e.elements["consulting-abandon-button"].hidden is False
    assert e.elements["consulting-case-sprawl-button"].disabled is True
    # the normal scenario picker cannot overwrite the inherited city
    e.elements["scenario-frontier-button"].dispatch("click", None)
    assert e.state.population == consulting.CASES["smokestack"]["population"]
    e.advance_season()
    assert "so far" in e.elements["consulting-status-display"].innerText
    e.elements["consulting-abandon-button"].dispatch("click", None)
    assert e.state.era == "tribal"
    assert e.elements["consulting-abandon-button"].hidden is True


def test_inherited_eras_do_not_earn_era_achievements(game_env):
    e = game_env
    e.elements["consulting-case-smokestack-button"].dispatch("click", None)
    earned = e.module.achievement_ids_earned()
    for era in ("agrarian", "classical", "medieval", "industrial"):
        assert f"reached_{era}" not in earned
    assert "craft_specialist" not in earned
