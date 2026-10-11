"""Batch 3 (2026-10-11): GE-20 mood strip, GE-25 settlement looks, GE-14 hit effects, GE-26 countdown pulse,
GE-23 run timer, E-31 achievements strip, E-7 settlement chronicle, E-26 tap targets."""

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
