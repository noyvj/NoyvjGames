"""A25: the captain's log, a light narrative thread (first arrivals and achievements)."""

import json


def test_every_world_has_an_arrival_line(game_env):
    m = game_env.module
    assert set(m.STORY_ARRIVAL_LINES) == set(m.PLANETS)
    assert all(line.strip() for line in m.STORY_ARRIVAL_LINES.values())


def test_a_new_game_starts_the_log_with_earth(game_env):
    m = game_env.module
    assert m.story_log == ["arrive:Earth"] or m.story_log == []
    m._mark_visited("Earth")
    assert m.story_log[0] == "arrive:Earth"
    assert game_env.elements["captains-log-latest"].hidden is False
    assert "Log opened" in game_env.elements["captains-log-latest"].innerText


def test_first_arrival_adds_one_line_and_a_revisit_adds_none(game_env):
    m = game_env.module
    m.story_log.clear()
    m._mark_visited("Mars")
    m._mark_visited("Mars")
    assert m.story_log == ["arrive:Mars"]
    assert "Mars" in game_env.elements["captains-log-latest"].innerText


def test_a_new_achievement_adds_its_own_description(game_env):
    m = game_env.module
    m.story_log.clear()
    m._achievements_seen_ids = set()
    m.total_manual_clicks = 1
    m.planet_state["Earth"]["resource_count"] = 5
    before = set(m.achievement_ids_earned())
    m._check_new_achievements_for_toast()
    earned = set(m.achievement_ids_earned()) - set()
    assert earned
    assert {e for e in m.story_log if e.startswith("ach:")} == {f"ach:{a}" for a in earned}
    assert before <= earned


def test_entries_are_unique_and_capped(game_env):
    m = game_env.module
    m.story_log.clear()
    assert m.story_note("arrive:Mars") is True and m.story_note("arrive:Mars") is False
    for i in range(m.STORY_LOG_MAX + 20):
        m.story_note(f"ach:fake{i}")
    assert len(m.story_log) == m.STORY_LOG_MAX


def test_unknown_ids_have_no_line(game_env):
    m = game_env.module
    assert m.story_line("ach:nope") is None and m.story_line("arrive:Krypton") is None
    assert m.story_line("garbage") is None
    m.story_log[:] = ["arrive:Mars", "ach:fake0"]
    assert m.story_log_lines() == [m.STORY_ARRIVAL_LINES["Mars"]]


def test_list_is_newest_first_and_panel_hidden_when_empty(game_env):
    m = game_env.module
    m.story_log[:] = ["arrive:Earth", "arrive:Mars"]
    m.render_story_log()
    items = game_env.elements["captains-log-list"].children
    assert [i.innerText for i in items] == [m.STORY_ARRIVAL_LINES["Mars"], m.STORY_ARRIVAL_LINES["Earth"]]
    m.story_log.clear()
    m.render_story_log()
    assert game_env.elements["captains-log"].hidden is True


def test_saved_only_when_non_empty_and_validated_on_load(game_env):
    m = game_env.module
    m.story_log.clear()
    assert "story_log" not in m.get_state()
    m.story_log[:] = ["arrive:Earth", "arrive:Mars"]
    state = json.loads(json.dumps(m.get_state()))
    assert state["story_log"] == ["arrive:Earth", "arrive:Mars"]
    m.story_log.clear()
    m.load_state(state)
    assert m.story_log == ["arrive:Earth", "arrive:Mars"]
    m.load_state({**state, "story_log": ["arrive:Mars", "arrive:Mars", 5, None, "junk", "ach:nope", "arrive:Venus"]})
    assert m.story_log == ["arrive:Mars", "arrive:Venus"]
    m.load_state({**state, "story_log": "nope"})
    assert m.story_log == []
    m.load_state({k: v for k, v in state.items() if k != "story_log"})
    assert m.story_log == []


def test_deeper_beats_for_terraforming_the_first_route_and_prestige(game_env):
    m = game_env.module
    m.story_log.clear()
    assert m._note_story_beats() is False
    m.planet_state["Mars"]["terraform_progress"] = m.TERRAFORM_MAX
    assert m._note_story_beats() is True
    assert m.story_log == ["terraform:Mars"]
    assert m._note_story_beats() is False  # idempotent
    m.planet_state["Earth"]["trade_routes"]["Mars"] = 1
    m.prestige_level = 1
    m._note_story_beats()
    assert m.story_log == ["terraform:Mars", "route:first", "prestige:1"]
    assert [len(line) > 60 for line in m.story_log_lines()] == [True, True, True]


def test_every_world_has_a_terraform_line_and_they_show_on_the_tick_check(game_env):
    m = game_env.module
    assert set(m.STORY_TERRAFORM_LINES) == set(m.PLANETS)
    m.story_log.clear()
    m.planet_state["Moon"]["terraform_progress"] = m.TERRAFORM_MAX
    m._check_new_achievements_for_toast()
    assert "terraform:Moon" in m.story_log
    assert m.STORY_TERRAFORM_LINES["Moon"] in m.story_log_lines()


def test_beat_ids_survive_a_save_round_trip(game_env):
    m = game_env.module
    m.story_log[:] = ["arrive:Earth", "terraform:Mars", "route:first", "prestige:1", "terraform:Krypton", "prestige:2"]
    state = m.get_state()
    m.story_log.clear()
    m.load_state(state)
    assert m.story_log == ["arrive:Earth", "terraform:Mars", "route:first", "prestige:1"]
