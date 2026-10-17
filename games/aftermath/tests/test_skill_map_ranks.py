"""E-2 skill-tree map, E-11 skill ranks, GE-16 unlock reveal (2026-10-11).

The map is a second view of the skill list: the rules come from the shared skill-tree module
(shared/skill_tree.py), the state is the unchanged SkillTreeState, and the list stays the plain-text version."""

import json
from pathlib import Path

import skill_tree as shared
from .pagefiles import game_css, page_text

GAME_DIR = Path(__file__).resolve().parent.parent


def _own(m, *skills, knowledge=0):
    m.skill_tree.unlocked = set(skills)
    m.skill_tree.knowledge_points = knowledge


def _entry(kind, damage, severity=1.0):
    return {"type": kind, "damage": damage, "severity": severity}


def _finish(env):
    while not env.run.is_complete():
        env.resolve_event()


def _node(env, skill_id):
    return env.elements[f"skill-map-node-{skill_id}"]


def _classes(env, skill_id):
    return set((_node(env, skill_id).getAttribute("class") or "").split())


# ------------------------------------------------------------------------------ the shared module
def test_the_tree_data_is_valid_for_the_shared_module_and_matches_skills(game_env):
    m = game_env.module
    assert shared.validate(m.SKILL_TREE_DATA) == []
    nodes = {n["id"]: n for n in m.SKILL_TREE_DATA["nodes"]}
    assert set(nodes) == set(m.SKILLS)
    for skill_id, skill in m.SKILLS.items():
        assert nodes[skill_id]["cost"] == skill["cost"]
        assert nodes[skill_id]["requires"] == skill.get("prereqs", [])


def test_status_agrees_with_the_existing_unlock_rules_in_every_state(game_env):
    m = game_env.module
    for owned in ((), ("reinforced_infrastructure",), ("reinforced_infrastructure", "community_reserves"),
                  ("reinforced_infrastructure", "early_warning"), tuple(m.SKILLS)):
        for knowledge in (0, 3, 5, 6, 40):
            _own(m, *owned, knowledge=knowledge)
            for skill_id in m.SKILLS:
                status = m.skill_status(skill_id)
                assert (status == "available") == m.skill_tree.can_unlock(skill_id)
                assert (status == "owned") == (skill_id in owned)
                assert (status == "locked") == bool(m.skill_tree.missing_prereqs(skill_id) and skill_id not in owned)


def test_a_move_or_a_reset_keeps_the_shared_balance_equal_to_the_knowledge_in_hand(game_env):
    m = game_env.module
    _own(m, "adaptive_growth", knowledge=5)
    m.skill_tree.move("adaptive_growth", "early_warning")
    owned = m._tree_owned()
    assert shared.points_left(m.SKILL_TREE_DATA, owned, m._tree_earned()) == m.skill_tree.knowledge_points
    m.reset_skill_tree()
    assert shared.points_left(m.SKILL_TREE_DATA, m._tree_owned(), m._tree_earned()) == m.skill_tree.knowledge_points


def test_the_skill_tree_state_and_its_storage_format_are_unchanged(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", knowledge=4)
    m.skill_tree.lifetime_knowledge = 9
    m.skill_tree.save()
    stored = json.loads(game_env.local_storage.getItem(m.SKILL_TREE_STORAGE_KEY))
    assert set(stored) == {"knowledge_points", "unlocked", "lifetime_knowledge"}
    assert stored == {"knowledge_points": 4, "unlocked": ["reinforced_infrastructure"], "lifetime_knowledge": 9}
    reloaded = m.SkillTreeState.load()
    assert reloaded.unlocked == {"reinforced_infrastructure"} and reloaded.knowledge_points == 4


# ------------------------------------------------------------------------------ the route
def test_a_locked_skill_routes_through_every_missing_prerequisite_in_buy_order(game_env):
    m = game_env.module
    _own(m, knowledge=0)
    assert m.route_to("climate_hardening") == ["reinforced_infrastructure", "early_warning", "climate_hardening"]
    info = m.route_info("climate_hardening")
    assert info["total"] == 3 + 5 + 6 and info["short"] == 14 and info["have"] == 0
    assert [s["running_total"] for s in info["steps"]] == [3, 8, 14]


def test_the_route_skips_what_you_own_and_is_empty_for_an_owned_or_unknown_skill(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", knowledge=4)
    assert m.route_to("climate_hardening") == ["early_warning", "climate_hardening"]
    assert m.route_info("climate_hardening")["short"] == 11 - 4
    assert m.route_to("reinforced_infrastructure") == []
    assert m.route_to("nonsense") == []


def test_the_route_is_the_cheapest_there_is(game_env):
    """A skill needs ALL its prerequisites, so the cheapest way in is exactly the closure of what is missing: no
    smaller set of purchases can ever unlock it, and the route has no step it does not need."""
    m = game_env.module
    _own(m, knowledge=0)
    for skill_id in m.SKILLS:
        route = m.route_to(skill_id)
        # every step is the skill or something it (transitively) needs
        needed, stack = set(), [skill_id]
        while stack:
            current = stack.pop()
            if current not in needed:
                needed.add(current)
                stack.extend(m.SKILLS[current].get("prereqs", []))
        assert set(route) == needed
        # buying the steps in order is always allowed, with no knowledge limit
        owned = set()
        for step in route:
            assert all(p in owned for p in m.SKILLS[step].get("prereqs", []))
            owned.add(step)
        # dropping any step makes the skill unreachable
        for step in route:
            if step == skill_id:
                continue
            rest = set(route) - {step}
            assert not all(p in rest for p in m.SKILLS[skill_id].get("prereqs", [])) or step not in m.SKILLS[skill_id].get("prereqs", [])


def test_the_detail_text_names_the_route_the_total_and_how_short_you_are(game_env):
    m = game_env.module
    _own(m, knowledge=8)
    text = m.skill_map_detail_text("climate_hardening")
    assert "Reinforced Infrastructure (3), then Early Warning Systems (5), then Climate Hardening (6)" in text
    assert "Total knowledge needed: 14" in text and "you have 8" in text and "6 short" in text
    assert "all of its prerequisites" in text


def test_available_unaffordable_and_owned_details_each_say_so(game_env):
    m = game_env.module
    _own(m, knowledge=3)
    assert "You can unlock it now for 3 knowledge" in m.skill_map_detail_text("reinforced_infrastructure")
    assert "short" in m.skill_map_detail_text("early_warning")
    _own(m, "reinforced_infrastructure", knowledge=0)
    owned = m.skill_map_detail_text("reinforced_infrastructure")
    assert "Yours already" in owned and "Climate Hardening" in owned and "Mutual Aid Network" in owned
    assert "Select a skill" in m.skill_map_detail_text(None)


# ------------------------------------------------------------------------------ layout
def test_every_skill_has_its_own_place_and_prerequisites_sit_to_the_left(game_env):
    m = game_env.module
    layout = m.skill_map_layout()
    assert set(layout) == set(m.SKILLS)
    boxes = [(x, y, x + m.MAP_NODE_W, y + m.MAP_NODE_H) for x, y, _t in layout.values()]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (a, b)
    for skill_id, skill in m.SKILLS.items():
        for pre in skill.get("prereqs", []):
            assert layout[pre][0] + m.MAP_NODE_W < layout[skill_id][0]
    width, height = m.skill_map_size()
    assert all(x + m.MAP_NODE_W <= width and y + m.MAP_NODE_H <= height for x, y, _t in layout.values())


# ------------------------------------------------------------------------------ the model and the DOM
def test_selecting_a_locked_skill_lights_the_route_nodes_links_and_numbers(game_env):
    m = game_env.module
    _own(m, knowledge=8)
    m.select_skill_on_map("climate_hardening")
    model = m.skill_map_model()
    assert model["route"] == ["reinforced_infrastructure", "early_warning", "climate_hardening"]
    for step in model["route"]:
        assert "skill-map-node--route" in model["nodes"][step]["classes"]
    assert "skill-map-node--route" not in model["nodes"]["community_reserves"]["classes"]
    assert "skill-map-node--selected" in model["nodes"]["climate_hardening"]["classes"]
    lit = {k for k, v in model["links"].items() if "skill-map-link--route" in v["classes"]}
    assert lit == {("reinforced_infrastructure", "climate_hardening"), ("early_warning", "climate_hardening")}
    assert [model["nodes"][s]["step"] for s in model["route"]] == [1, 2, 3]
    # the DOM shows it too, as words and not only as styling
    assert "skill-map-node--route" in _classes(game_env, "early_warning")
    assert "step 2 of 3 on the route" in _node(game_env, "early_warning").getAttribute("aria-label")
    assert "Total knowledge needed: 14" in game_env.elements["skill-map-detail"].innerText
    assert _node(game_env, "climate_hardening").getAttribute("aria-pressed") == "true"


def test_clearing_the_selection_drops_the_route(game_env):
    m = game_env.module
    _own(m, knowledge=0)
    m.select_skill_on_map("mutual_aid_network")
    assert m.skill_map_model()["route"]
    m.clear_skill_map_selection()
    assert m.skill_map_model()["route"] == [] and m.skill_map_selected is None
    assert not any("skill-map-node--route" in _classes(game_env, s) for s in m.SKILLS)
    assert game_env.elements["skill-map-clear-button"].disabled is True
    assert m.select_skill_on_map("nonsense") is False


def test_every_node_says_its_state_in_words_and_with_a_glyph(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", knowledge=3)
    m.render()
    for skill_id in m.SKILLS:
        status = m.skill_status(skill_id)
        label = _node(game_env, skill_id).getAttribute("aria-label")
        assert m.SKILL_STATE_WORD[status] in label, label
        assert str(m.SKILLS[skill_id]["cost"]) in label
    assert len({m.SKILL_STATE_GLYPH[s] for s in ("owned", "available", "unaffordable", "locked")}) == 4
    assert "needs Reinforced Infrastructure (owned)" in _node(game_env, "climate_hardening").getAttribute("aria-label")


def test_the_map_and_the_list_agree_for_every_filter_and_search(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", knowledge=5)
    m.meta["pinned_skills"] = ["mutual_aid_network"]
    for status in ("all", "affordable", "pinned", "owned"):
        for group in ("any", "weather", "social", "mitigation", "starting"):
            for query in ("", "mitigation", "retrofit", "zzz"):
                m.skill_filter_status, m.skill_filter_group, m.skill_search_text = status, group, query
                m.render()
                shown_in_list = {s for s in m.SKILLS if not game_env.elements[f"skill-{s}-row"].hidden}
                on_map = {s for s in m.SKILLS if _node(game_env, s).getAttribute("data-filtered") == "false"}
                assert shown_in_list == on_map == set(m.visible_skill_ids()), (status, group, query)
                for skill_id in m.SKILLS:
                    assert ("skill-map-node--filtered" in _classes(game_env, skill_id)) == (skill_id not in on_map)


def test_a_filtered_out_node_says_so_and_keeps_its_links_dimmed(game_env):
    m = game_env.module
    m.skill_filter_group = "weather"
    m.render()
    assert "does not match the current filters" in _node(game_env, "civic_preparedness").getAttribute("aria-label")
    assert "does not match" not in _node(game_env, "climate_hardening").getAttribute("aria-label")
    model = m.skill_map_model()
    assert "skill-map-link--filtered" in model["links"][("community_reserves", "civic_preparedness")]["classes"]
    # a link is dimmed when EITHER end is filtered out: early_warning is not weather, so its link to Climate Hardening dims too
    assert "skill-map-link--filtered" in model["links"][("early_warning", "climate_hardening")]["classes"]


def test_the_maps_own_chips_and_search_drive_the_same_filters(game_env):
    m = game_env.module
    chips = [c for g in game_env.elements["skill-map-chips"].children for c in g.children]
    assert len(chips) == 4 + 5
    weather = next(c for c in chips if c.getAttribute("data-filter-value") == "weather")
    weather.dispatch("click", None)
    assert m.skill_filter_group == "weather"
    list_chips = [c for g in game_env.elements["skill-filter-chips"].children for c in g.children]
    assert next(c for c in list_chips if c.getAttribute("data-filter-value") == "weather").getAttribute("aria-pressed") == "true"
    assert weather.getAttribute("aria-pressed") == "true"
    game_env.elements["skill-map-search-input"].value = "retrofit"
    game_env.elements["skill-map-search-input"].dispatch("input", None)
    assert m.skill_search_text == "retrofit"
    assert game_env.elements["skill-search-input"].value == "retrofit"
    m.on_skill_filter_clear()
    assert game_env.elements["skill-map-search-input"].value == "" and m.skill_filter_group == "any"
    assert game_env.elements["skill-map-filter-clear"].hidden is True


def test_buying_from_the_map_uses_the_same_unlock_and_keeps_the_saved_format(game_env):
    m = game_env.module
    _own(m, knowledge=5)
    m.select_skill_on_map("reinforced_infrastructure")
    unlock = game_env.elements["skill-map-unlock-button"]
    assert unlock.hidden is False and "Reinforced Infrastructure (3)" in unlock.innerText
    unlock.dispatch("click", None)
    assert m.skill_tree.unlocked == {"reinforced_infrastructure"} and m.skill_tree.knowledge_points == 2
    assert game_env.elements["skill-map-unlock-button"].hidden is True      # nothing left to buy for it
    m.select_skill_on_map("early_warning")                                   # costs 5, only 2 in hand
    assert game_env.elements["skill-map-unlock-button"].hidden is True
    assert "short" in game_env.elements["skill-map-detail"].innerText


def test_pinning_from_the_map_matches_the_list(game_env):
    m = game_env.module
    m.select_skill_on_map("civic_preparedness")
    pin = game_env.elements["skill-map-pin-button"]
    assert pin.hidden is False
    pin.dispatch("click", None)
    assert "civic_preparedness" in m.meta["pinned_skills"]
    assert "Pinned" in game_env.elements["skill-map-pin-button"].innerText


def test_selecting_announces_the_detail_text(game_env):
    m = game_env.module
    m.select_skill_on_map("early_warning")
    assert "Early Warning Systems" in game_env.elements["event-announcer"].innerText


def test_the_map_in_words_lists_every_skill_with_its_links(game_env):
    m = game_env.module
    lines = m.skill_map_text_lines()
    assert len(lines) == len(m.SKILLS) == len(game_env.elements["skill-map-text"].children)
    joined = " ".join(lines)
    assert "Climate Hardening (Weather): locked" in joined and "needs Reinforced Infrastructure and Early Warning Systems" in joined
    assert any("leads to Mutual Aid Network and Climate Hardening" in line for line in lines)
    assert any("has no prerequisites" in line for line in lines)


# ------------------------------------------------------------------------------ GE-16 reveal
def test_newly_available_children_are_the_ones_that_just_stopped_being_locked(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", "early_warning", knowledge=0)
    assert m.newly_available_children("early_warning") == ["climate_hardening"]
    assert m.newly_available_children("reinforced_infrastructure") == ["climate_hardening"]
    _own(m, "reinforced_infrastructure", knowledge=0)
    assert m.newly_available_children("reinforced_infrastructure") == []        # the others still miss a prerequisite
    _own(m, "reinforced_infrastructure", "community_reserves", knowledge=0)
    assert set(m.newly_available_children("community_reserves")) == {"civic_preparedness", "mutual_aid_network"}


def test_buying_a_skill_pulses_it_and_lights_the_links_to_what_it_opened(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", knowledge=5)
    game_env.unlock_skill("early_warning")
    assert m.skill_tree.unlocked == {"reinforced_infrastructure", "early_warning"}
    assert m.skill_map_reveal == {"skill": "early_warning", "children": ["climate_hardening"]}
    assert "skill-map-node--just-bought" in _classes(game_env, "early_warning")
    assert "skill-map-node--now-available" in _classes(game_env, "climate_hardening")
    model = m.skill_map_model()
    assert [k for k, v in model["links"].items() if "skill-map-link--lit" in v["classes"]] == [("early_warning", "climate_hardening")]
    reveal = game_env.elements["skill-map-reveal"]
    assert reveal.hidden is False and reveal.innerText == "Early Warning Systems unlocked. Now available: Climate Hardening."
    assert reveal.innerText in game_env.elements["event-announcer"].innerText
    # the list highlights the same skill, in words
    assert "skill-row--now-available" in game_env.elements["skill-climate_hardening-row"].classList
    assert game_env.elements["skill-climate_hardening-eta"].innerText.startswith("Now available.")
    assert "skill-row--now-available" not in game_env.elements["skill-civic_preparedness-row"].classList


def test_a_skill_that_opens_nothing_says_so_in_words(game_env):
    m = game_env.module
    _own(m, knowledge=3)
    game_env.unlock_skill("reinforced_infrastructure")
    assert m.skill_map_reveal["children"] == []
    assert game_env.elements["skill-map-reveal"].innerText == "Reinforced Infrastructure unlocked. No new skills open up from it."
    assert not any("skill-map-node--now-available" in _classes(game_env, s) for s in m.SKILLS)


def test_the_reveal_clears_on_the_next_map_action_and_never_outlives_the_skill(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", knowledge=5)
    game_env.unlock_skill("early_warning")
    m.select_skill_on_map("community_reserves")
    assert m.skill_map_reveal is None and game_env.elements["skill-map-reveal"].hidden is True
    assert not any("skill-map-node--just-bought" in _classes(game_env, s) for s in m.SKILLS)
    _own(m, "reinforced_infrastructure", knowledge=5)
    game_env.unlock_skill("early_warning")
    m.reset_skill_tree()
    m.render()
    assert m.skill_map_reveal is None
    assert game_env.elements["skill-climate_hardening-eta"].innerText.startswith("Now available.") is False


def test_moving_a_point_reveals_too(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", "adaptive_growth", knowledge=5)
    game_env.elements["skill-move-from"].value = "adaptive_growth"
    game_env.elements["skill-move-to"].value = "early_warning"
    m.on_skill_move()
    assert m.skill_tree.unlocked == {"reinforced_infrastructure", "early_warning"}
    assert m.skill_map_reveal["children"] == ["climate_hardening"]
    assert "Now available: Climate Hardening" in game_env.elements["event-announcer"].innerText


def test_the_reveal_has_a_static_highlight_and_the_animation_respects_reduced_motion():
    css = game_css()
    static = [b for b in css.split("}") if ".skill-map-node--just-bought {" in b and "outline" in b]
    assert static, "a highlight that does not depend on motion"
    assert 'html[data-reduced-motion="true"] .skill-map-node--just-bought' in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    reduced = css[css.index('html[data-reduced-motion="true"] .skill-map-node--just-bought'):]
    assert "animation: none" in reduced[:200]
    media = css[css.index("@media (prefers-reduced-motion: reduce) {\n  .skill-map-node--just-bought"):]
    assert "animation: none" in media[:150]


# ------------------------------------------------------------------------------ E-11 ranks
def test_every_skill_has_three_rising_thresholds_and_a_written_rule(game_env):
    m = game_env.module
    assert set(m.SKILL_RANK_RULES) == set(m.SKILLS)
    for skill_id, rule in m.SKILL_RANK_RULES.items():
        a, b, c = rule["thresholds"]
        assert 0 < a < b < c and all(isinstance(x, int) for x in (a, b, c))
        assert rule["unit"] and rule["how"]
    assert len(m.skill_rank_rule_lines()) == len(m.SKILLS)
    assert len(game_env.elements["skill-rank-rules"].children) == len(m.SKILLS)


def test_a_rank_is_read_from_the_count_at_each_threshold(game_env):
    m = game_env.module
    for skill_id, rule in m.SKILL_RANK_RULES.items():
        a, b, c = rule["thresholds"]
        for count, rank in ((0, 0), (a - 1, 0), (a, 1), (b - 1, 1), (b, 2), (c - 1, 2), (c, 3), (c * 5, 3)):
            m.meta["skill_progress"] = {skill_id: count} if count else {}
            assert m.skill_rank(skill_id) == rank, (skill_id, count)


def test_early_warning_counts_every_event_faced_with_it_owned(game_env):
    gains = game_env.module.skill_rank_gains
    log = [_entry("flood", 10)] * 7
    assert gains(log, 0, 0, 0, {"early_warning"}) == {"early_warning": 7}
    assert gains(log, 0, 0, 0, set()) == {}


def test_an_accurate_preview_is_exact_in_every_scenario_and_run_number(game_env):
    """Early Warning's rule rests on this: the damage in the Expected damage line is the figure the event then
    deals, whatever the scenario, run number or build."""
    m = game_env.module
    for scenario in m.SCENARIOS:
        for run_number in (1, 2, 7, 23):
            run = m.RunState(run_number=run_number, scenario=scenario)
            for step in range(len(run.schedule)):
                run.resilience_capacity += step % 3
                expected, _severity = m.expected_next_event_damage(run)
                run.resolve_next_event()
                assert run.event_log[-1]["damage"] == expected


def test_mutual_aid_counts_events_that_prevented_at_least_half(game_env):
    m = game_env.module
    log = [_entry("flood", 20.0), _entry("flood", 20.1), _entry("storm", 0.0), _entry("storm", 50.0)]
    # flood 40 base: 20.0 damage = exactly half prevented (held); 20.1 less than half; storm 50: all prevented / none
    assert m.skill_rank_gains(log, 0, 0, 0, {"mutual_aid_network"}) == {"mutual_aid_network": 2}


def test_climate_hardening_counts_weather_damage_prevented_only(game_env):
    m = game_env.module
    log = [_entry("flood", 10.0), _entry("heatwave", 20.0), _entry("civil_unrest", 0.0), _entry("supply_chain", 0.0)]
    assert m.skill_rank_gains(log, 0, 0, 0, {"climate_hardening"}) == {"climate_hardening": 30 + 15}


def test_civic_preparedness_counts_unrest_damage_prevented_only(game_env):
    m = game_env.module
    log = [_entry("flood", 0.0), _entry("civil_unrest", 12.0), _entry("civil_unrest", 12.0, severity=1.1)]
    assert m.skill_rank_gains(log, 0, 0, 0, {"civic_preparedness"}) == {"civic_preparedness": round(20 + (32 * 1.1 - 12))}


def test_the_three_starting_build_skills_count_runs_that_used_the_build(game_env):
    m = game_env.module
    owned = {"reinforced_infrastructure", "community_reserves", "adaptive_growth"}
    assert m.skill_rank_gains([], 4, 3, 50, owned) == {s: 1 for s in owned}
    assert m.skill_rank_gains([], 3, 2, 49.9, owned) == {}
    assert m.skill_rank_gains([], 4, 0, 0, owned) == {"reinforced_infrastructure": 1}
    assert m.skill_rank_gains([], 0, 3, 0, owned) == {"adaptive_growth": 1}
    assert m.skill_rank_gains([], 0, 0, 80, owned) == {"community_reserves": 1}


def test_progress_is_the_same_for_the_same_run_so_no_luck_is_involved(game_env):
    m = game_env.module
    log = [_entry("flood", 12.0, 1.07), _entry("storm", 22.0, 0.93)]
    first = m.skill_rank_gains(log, 5, 1, 60, set(m.SKILLS))
    assert first == m.skill_rank_gains(list(log), 5, 1, 60, set(m.SKILLS))


def test_a_finished_run_adds_progress_for_owned_skills_only_and_once(game_env):
    m = game_env.module
    _own(m, "early_warning", knowledge=0)
    game_env.start_new_run()
    _finish(game_env)
    assert m.meta["skill_progress"] == {"early_warning": 7}
    assert m.skill_rank("early_warning") == 0
    # the same finished run cannot be paid out twice (the stale-save guard covers it)
    snapshot = dict(m.meta["skill_progress"])
    m.run.event_index -= 1
    m.run.event_log.pop()
    m.run.resolve_next_event()
    assert m.meta["skill_progress"] == snapshot
    # a second run takes it past rank 1 and says so
    game_env.start_new_run()
    _finish(game_env)
    assert m.meta["skill_progress"] == {"early_warning": 14} and m.skill_rank("early_warning") == 1
    assert m.skill_ranks_just_gained == [("early_warning", 1)]
    assert m.skill_rank_callout_text() == "Skill rank up: Early Warning Systems reached rank 1."
    panel = game_env.elements["run-summary-panel"]
    assert any(c.className == "skill-rank-callout" and "rank 1" in c.innerText for c in panel.children)
    assert "Skill rank up" in game_env.elements["event-announcer"].innerText
    # starting the next run drops the one-time callout
    game_env.start_new_run()
    assert m.skill_ranks_just_gained == []


def test_skills_you_do_not_own_collect_nothing(game_env):
    m = game_env.module
    _own(m, knowledge=0)
    game_env.start_new_run()
    _finish(game_env)
    assert m.meta["skill_progress"] == {}
    assert m.skill_rank_line("early_warning") == ""


def test_a_challenge_run_and_a_custom_schedule_do_not_count(game_env):
    m = game_env.module
    _own(m, "early_warning", knowledge=0)
    run = m.RunState(run_number=50, normalised=True, draw=4)
    m.run = run
    _finish(game_env)
    assert m.meta["skill_progress"] == {}
    m.run = m.RunState(run_number=m.highest_awarded_run + 1, custom_events=["flood", "storm", "heatwave"], custom_name="x")
    _finish(game_env)
    assert m.meta["skill_progress"] == {}


def test_ranks_survive_a_reset_and_a_move_and_are_never_lowered(game_env):
    m = game_env.module
    _own(m, "early_warning", "adaptive_growth", knowledge=5)
    m.meta["skill_progress"] = {"early_warning": 30, "adaptive_growth": 2}
    m.reset_skill_tree()
    assert m.skill_rank("early_warning") == 2 and m.skill_rank("adaptive_growth") == 1
    _own(m, "adaptive_growth", knowledge=5)
    m.skill_tree.move("adaptive_growth", "early_warning")
    assert m.skill_rank("adaptive_growth") == 1 and m.skill_rank("early_warning") == 2


def test_progress_is_saved_validated_and_travels_with_the_progress_code(game_env):
    m = game_env.module
    m.meta["skill_progress"] = {"early_warning": 12}
    m.save_meta()
    assert json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))["skill_progress"] == {"early_warning": 12}
    assert m.load_meta()["skill_progress"] == {"early_warning": 12}
    code = m.export_progress_code()
    m.meta["skill_progress"] = {}
    assert m.import_progress_code(code) is True
    assert m.meta["skill_progress"] == {"early_warning": 12}


def test_damaged_progress_data_cannot_invent_a_rank(game_env):
    m = game_env.module
    bad = {
        "nonsense": 5, "early_warning": "lots", "mutual_aid_network": True, "civic_preparedness": -3,
        "climate_hardening": 99999999999, "community_reserves": 4.9, "adaptive_growth": None,
    }
    clean = m._sanitize_skill_progress(bad)
    assert clean == {"climate_hardening": m.SKILL_PROGRESS_MAX, "community_reserves": 4}
    assert m._sanitize_skill_progress(["early_warning"]) == {}
    assert m._sanitize_skill_progress(None) == {}
    assert m._sanitize_meta({"skill_progress": bad})["skill_progress"] == clean
    assert m._sanitize_meta({})["skill_progress"] == {}              # an older save without the field
    assert m._default_meta()["skill_progress"] == {}


def test_rank_lines_show_the_count_the_next_goal_and_a_pip_row(game_env):
    m = game_env.module
    _own(m, "early_warning", knowledge=0)
    assert m.skill_rank_line("early_warning") == "○○○ No rank yet: 0/10 accurate previews toward rank 1"
    m.meta["skill_progress"] = {"early_warning": 12}
    assert m.skill_rank_line("early_warning") == "●○○ Rank 1 of 3: 12/25 accurate previews toward rank 2"
    assert m.skill_rank_short("early_warning") == "●○○ Rank 1/3 · 12/25"
    m.meta["skill_progress"] = {"early_warning": 60}
    assert "top rank" in m.skill_rank_line("early_warning") and m.skill_rank_short("early_warning").endswith("Rank 3/3")
    m.render()
    assert "top rank" in game_env.elements["skill-early_warning-rank"].innerText
    rank_span = game_env.elements["skill-map-node-early_warning"].children[4]
    assert rank_span.innerText.endswith("Rank 3/3")


def test_the_ranks_summary_counts_every_possible_rank(game_env):
    m = game_env.module
    assert m.skill_ranks_total() == (0, 21)
    m.meta["skill_progress"] = {"early_warning": 10, "mutual_aid_network": 40}
    assert m.skill_ranks_total() == (4, 21)
    m.render()
    assert game_env.elements["skill-ranks-summary"].innerText.startswith("Skill ranks: 4 of 21")
    assert "nothing needs them" in game_env.elements["skill-ranks-summary"].innerText


def test_ranks_never_change_a_number_in_a_run(game_env):
    m = game_env.module
    _own(m, "early_warning", "reinforced_infrastructure", knowledge=0)
    plain = m.RunState(run_number=3)
    m.meta["skill_progress"] = {s: 10_000 for s in m.SKILLS}
    ranked = m.RunState(run_number=3)
    for run in (plain, ranked):
        run.resolve_next_event()
    assert plain.event_log == ranked.event_log and plain.resources == ranked.resources
    assert plain.mitigation_fraction() == ranked.mitigation_fraction()


def test_ranks_are_not_needed_to_unlock_anything(game_env):
    m = game_env.module
    assert m.meta["skill_progress"] == {}
    _own(m, knowledge=40)
    for skill_id in ("reinforced_infrastructure", "community_reserves", "early_warning", "mutual_aid_network", "climate_hardening"):
        game_env.unlock_skill(skill_id)
    assert m.skill_status("climate_hardening") == "owned"


# ------------------------------------------------------------------------------ the pages
def test_both_pages_carry_the_map_the_rank_lines_and_the_shared_module():
    classic = page_text("index.html")
    desktop = page_text("pc.html")
    assert '"skill_tree.py"' in classic and '"skill_tree.py"' in desktop
    for page in (classic, desktop):
        for element_id in ("skill-map-panel", "skill-map-viewport", "skill-map-canvas", "skill-map-detail", "skill-map-reveal",
                           "skill-map-search-input", "skill-map-chips", "skill-rank-rules", "skill-map-text", "skill-ranks-summary",
                           "skill-map-zoom-in", "skill-map-zoom-out", "skill-map-fit", "skill-map-clear-button"):
            assert f'id="{element_id}"' in page, element_id
        for skill_id in ("early_warning", "climate_hardening", "community_reserves"):
            assert f'id="skill-{skill_id}-rank"' in page
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert any(c["id"] == "pc-skillmap-panel" and "#skill-map-panel" in c["members"] for c in cfg["composites"])
    assert "M — open the skill map" in classic


def test_the_map_keys_are_in_the_page_script():
    ui = (GAME_DIR / "ui.js").read_text(encoding="utf-8")
    for needle in ("ArrowRight", "ArrowDown", '"Escape"', 'key === "+"', 'key === "0"', "openSkillMap", "ctrlKey"):
        assert needle in ui, needle


def test_the_changelog_announces_the_map_the_ranks_and_the_reveal():
    changelog = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    today = [c["entry"].lower() for c in changelog if c["date"] == "2026-10-11"]
    assert any("skill map" in e and "rank" in e and "now available" in e for e in today)


def test_claude_md_documents_every_rank_rule_with_its_thresholds(game_env):
    notes = (GAME_DIR / "CLAUDE.md").read_text(encoding="utf-8")
    for skill_id, rule in game_env.module.SKILL_RANK_RULES.items():
        a, b, c = rule["thresholds"]
        assert f"{a} / {b} / {c}" in notes, skill_id
