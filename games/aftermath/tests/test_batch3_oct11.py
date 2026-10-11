"""Batch 3 (2026-10-11): GE-20 mood strip, GE-25 settlement looks, GE-14 hit effects, GE-26 countdown pulse,
GE-23 run timer, E-31 achievements strip, E-7 settlement chronicle, E-26 tap targets."""

import json
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------------------------------ GE-20
def test_mood_is_cheerful_for_a_comfortable_sheltered_settlement_and_grim_for_a_bare_one(game_env):
    m = game_env.module
    m.run.resources = 200.0
    m.run.resilience_capacity = 17  # 85% mitigation
    faces, label = m.mood_summary(m.run)
    assert faces[-1] == m.MOOD_FACES[0] and set(faces) <= set(m.MOOD_FACES[:2])
    assert "cheerful" in label and "citizens are smiling" in label
    m.run.resources = 0.0
    m.run.resilience_capacity = 0
    faces, label = m.mood_summary(m.run)
    assert faces[0] == m.MOOD_FACES[4] and faces[-1] == m.MOOD_FACES[4] and "frightened" in label and "0 of 5" in label


def test_mood_moves_one_face_at_a_time_and_never_leaves_the_face_range(game_env):
    m = game_env.module
    seen = set()
    for resources in range(0, 400, 10):
        for resilience in (0, 4, 9, 17, 40):
            m.run.resources = float(resources)
            m.run.resilience_capacity = resilience
            levels = m.mood_levels(m.settlement_mood_score(m.run))
            assert len(levels) == 5 and all(0 <= level < len(m.MOOD_FACES) for level in levels)
            assert levels == sorted(levels, reverse=True)  # the strip reads from the gloomiest citizen to the most hopeful, always in that order
            seen.update(levels)
    assert seen == {0, 1, 2, 3, 4}


def test_every_allocation_click_redraws_the_strip_and_its_words(game_env):
    m, e = game_env.module, game_env.elements
    before = e["mood-caption"].innerText
    assert before.startswith("Settlement mood:") and e["mood-strip"].getAttribute("aria-label") == before
    assert len(e["mood-strip"].children) == 5 and all(c.getAttribute("aria-hidden") == "true" for c in e["mood-strip"].children)
    m.run.resources = 25.0
    game_env.invest_resilience()
    after = e["mood-caption"].innerText
    assert after != before and e["mood-strip"].getAttribute("aria-label") == after
    assert len(e["mood-strip"].children) == 5  # built once, then updated in place


def test_a_page_without_the_strip_still_renders(game_env):
    m = game_env.module
    m._mood_parts.clear()
    m._el = lambda element_id: None
    m.render_mood_strip()  # no error


# ------------------------------------------------------------------------------------------ GE-25
def _finish_run(game_env):
    for _ in range(len(game_env.module.run.schedule)):
        game_env.resolve_event()


def test_look_thresholds_follow_the_real_size_of_the_tree(game_env):
    m = game_env.module
    assert len(m.SKILLS) == 7
    assert m.look_thresholds() == {"thatched": 0, "timber": 4, "concrete": 7}
    assert m.look_thresholds(10) == {"thatched": 0, "timber": 5, "concrete": 10}  # the TODO's "5, 10 and all" for a ten-skill tree
    assert [m.look_for_skill_count(n) for n in range(8)] == ["thatched"] * 4 + ["timber"] * 3 + ["concrete"]


def test_a_run_gets_its_look_when_it_starts_and_keeps_it(game_env):
    m = game_env.module
    assert m.run.look == "thatched"
    m.skill_tree.unlocked = set(list(m.SKILLS)[:4])
    m.run = m.RunState()
    assert m.run.look == "timber"
    m.skill_tree.unlocked = set()
    assert m.run.look == "timber"  # fixed at the start of the run
    m.skill_tree.unlocked = set(m.SKILLS)
    assert m.RunState().look == "concrete"
    assert m.RunState(normalised=True).look == "thatched"  # a friend's challenge run ignores your tree


def test_the_look_changes_no_number(game_env):
    m = game_env.module
    base = m.RunState()
    m.skill_tree.unlocked = set()
    plain = m.RunState()
    assert (plain.resources, plain.resilience_capacity, plain.growth_capacity) == (base.resources, base.resilience_capacity, base.growth_capacity)
    assert "look" not in json.dumps(m.get_state())  # nothing new in the run save


def test_history_records_a_non_default_look_only_and_old_runs_read_as_default(game_env):
    m = game_env.module
    _finish_run(game_env)
    assert "look" not in m.run_log_history[-1]
    game_env.start_new_run()
    m.skill_tree.unlocked = set(list(m.SKILLS)[:5])
    m.run = m.RunState(run_number=2)
    _finish_run(game_env)
    assert m.run_log_history[-1]["look"] == "timber"
    assert m.entry_look(m.run_log_history[0]) == "thatched" and m.entry_look({"look": "marble"}) == "thatched" and m.entry_look(None) == "thatched"
    assert m.looks_seen() == {"thatched", "timber"}


def test_the_look_shows_in_the_status_the_art_class_and_past_runs(game_env):
    m, e = game_env.module, game_env.elements
    text = e["settlement-look-display"].innerText
    assert "Thatched huts" in text and "Timber halls at 4" in text and "Looks seen: 1 of 3" in text
    assert e["settlement-visual"].classList.contains("settlement-visual--thatched")
    m.skill_tree.unlocked = set(m.SKILLS)
    m.run = m.RunState(run_number=5)
    m.render()
    assert e["settlement-visual"].classList.contains("settlement-visual--concrete")
    assert not e["settlement-visual"].classList.contains("settlement-visual--thatched")
    assert "Concrete and glass" in e["settlement-look-display"].innerText and "7 of 7 skills owned" in e["settlement-look-display"].innerText
    _finish_run(game_env)
    card = m._past_run_card(0, m.run_log_history[-1], False)
    assert "Concrete and glass" in card.children[0].innerText


def test_a_cached_page_without_the_look_elements_still_renders(game_env):
    m = game_env.module
    m._el = lambda element_id: None
    m.render_settlement_look()
