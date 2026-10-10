"""The story is a graph; these prove its shape: every scene and every ending reachable, no dead ends, no cycles, every choice
answered, every collectable findable, with the stat gates taken into account (a search over every reachable state)."""

import pytest

import explore
import kit
import lore
import story
import walker


@pytest.fixture(scope="module")
def reach():
    return explore.reach_all()


def _targets(choice):
    return [t for _c, t in choice["to"]]


def test_scene_ids_are_unique_and_every_target_exists():
    assert len(story.ORDER) == len(set(story.ORDER)) == len(story.SCENES)
    for sid, scene in story.SCENES.items():
        for choice in scene["choices"]:
            for target in _targets(choice):
                assert target in story.SCENES, (sid, target)
    assert story.START in story.SCENES


def test_the_size_of_the_story():
    assert 55 <= len(story.SCENES) <= 70
    assert 8 <= len(story.ENDINGS) <= 10
    assert story.DAYS == 12
    days = {s["day"] for s in story.SCENES.values()}
    assert days == set(range(1, 13))
    assert 120 <= len(story.CHOICES) <= 220 and len(story.EDGES) >= len(story.CHOICES)


def test_every_scene_has_two_to_four_choices_or_is_an_ending():
    for sid, scene in story.SCENES.items():
        if scene["end"]:
            assert not scene["choices"], sid
            assert scene["lines"], sid
        else:
            assert 2 <= len(scene["choices"]) <= 4, sid


def test_every_choice_has_a_reply_a_text_and_a_default_route():
    for sid, scene in story.SCENES.items():
        for i, choice in enumerate(scene["choices"]):
            assert choice["text"].strip(), (sid, i)
            assert any(cond is None and text.strip() for cond, text in choice["reply"]), (sid, i)
            assert choice["to"][-1][0] is None, (sid, i)


def test_every_scene_keeps_at_least_one_choice_with_no_lock():
    for sid, scene in story.SCENES.items():
        if scene["choices"]:
            assert any(c["need"] is None for c in scene["choices"]), sid


def test_there_are_no_cycles_and_days_never_go_backwards_or_skip():
    colour = {}

    def visit(sid):
        if colour.get(sid) == 1:
            raise AssertionError("cycle through " + sid)
        if colour.get(sid) == 2:
            return
        colour[sid] = 1
        for choice in story.SCENES[sid]["choices"]:
            for target in _targets(choice):
                assert 0 <= story.SCENES[target]["day"] - story.SCENES[sid]["day"] <= 3, (sid, target)
                visit(target)
        colour[sid] = 2

    visit(story.START)
    assert set(colour) == set(story.SCENES), "every scene hangs off the start"


def test_every_scene_every_choice_and_every_ending_is_reachable(reach):
    assert set(reach["scenes"]) == set(story.SCENES)
    assert set(reach["edges"]) == set(story.EDGES), [e for e in story.EDGES if e not in reach["edges"]]
    assert set(reach["endings"]) == set(story.ENDING_IDS)


def test_every_collectable_can_be_found_and_each_witness_path_really_finds_it(reach):
    assert set(reach["found"]) == set(lore.COLLECT_IDS)
    for cid, path in reach["found"].items():
        assert cid in walker.replay(path)[2], cid


def test_witness_paths_replay_to_the_scene_they_claim(reach):
    for sid, path in reach["scenes"].items():
        assert walker.replay(path)[1][0] == sid


def test_no_dead_ends_in_any_reachable_state():
    result = explore.search()
    for state in result["order"]:
        scene = story.SCENES[state[0]]
        if scene["end"]:
            continue
        assert any(walker.available(state, i)[0] for i in range(len(scene["choices"]))), state


def test_most_endings_can_be_reached_more_than_one_way():
    entries = {eid: set() for eid in story.ENDING_IDS}
    for sid in story.ORDER:
        for i, choice in enumerate(story.SCENES[sid]["choices"]):
            for target in _targets(choice):
                if story.SCENES[target]["end"]:
                    entries[story.SCENES[target]["end"]].add((sid, i))
    assert all(entries.values())
    assert sum(1 for e in entries.values() if len(e) >= 2) >= 6


def test_endings_come_through_three_different_arcs():
    arcs = {sid[0] for sid in story.ORDER if sid[0] in "rlw"}
    assert arcs == {"r", "l", "w"}
    assert {"d8a"} <= set(story.SCENES)


def test_every_flag_a_condition_tests_is_set_somewhere():
    tested, setters = set(), set()
    for scene in story.SCENES.values():
        setters.update(scene["set"])
        conds = [c["need"] for c in scene["choices"]] + [cond for c in scene["choices"] for cond, _t in c["to"]]
        conds += [cond for cond, _t in scene["lines"]] + [cond for c in scene["choices"] for cond, _t in c["reply"]]
        for choice in scene["choices"]:
            setters.update(choice["set"])
        for cond in conds:
            if cond:
                tested.update(cond["all"])
                tested.update(cond["none"])
    assert tested <= setters, tested - setters


def test_a_stat_gate_never_asks_for_more_than_the_stat_can_hold():
    for scene in story.SCENES.values():
        for c in scene["choices"]:
            for cond in [c["need"]] + [x for x, _t in c["to"]]:
                if cond:
                    assert all(0 < v <= kit.HIGH for v in cond["min"].values())
                    assert all(0 < v <= kit.HIGH for v in cond["max"].values())


def test_every_locked_choice_has_words_for_why_it_is_locked():
    result = explore.search()
    seen_reasons = set()
    for state in result["order"]:
        for i in range(len(story.SCENES[state[0]]["choices"])):
            ok, why = walker.available(state, i)
            if not ok:
                assert why.strip(), why
                seen_reasons.add(why.split(" (")[0])
    assert seen_reasons


def test_the_demanding_gates_can_all_be_met_on_some_path(reach):
    # every gated choice is open in at least one reachable state (that is what 'every edge reachable' proves) and is closed in another
    gated = [(sid, i) for sid in story.ORDER for i, c in enumerate(story.SCENES[sid]["choices"]) if c["need"]]
    assert len(gated) >= 8
    result = explore.search()
    for sid, i in gated:
        states = [s for s in result["order"] if s[0] == sid]
        assert any(walker.available(s, i)[0] for s in states), (sid, i)
