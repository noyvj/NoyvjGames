"""G17: the "four regions, one story" shared-research thread."""


def _titles(env):
    return [c[1] for c in env.module.shared_research_chapters_reached()]


def test_first_chapter_always_shown(game_env):
    game_env.module.render()
    assert len(game_env.module.shared_research_chapters_reached()) == 1
    assert "shared station" in game_env.elements["shared-research-story"].innerHTML
    assert "0 monitoring units" in game_env.elements["shared-research-progress"].innerText
    assert "next chapter at 3" in game_env.elements["shared-research-progress"].innerText


def test_units_sum_monitor_across_a_b_c_only(game_env):
    m = game_env.module
    m.region.capacity["monitor"] = 1
    m.region_b.capacity["monitor"] = 2
    m.region_c.capacity["monitor"] = 3
    m.region_d.capacity["monitor"] = 50
    assert m.shared_research_units() == 6


def test_other_categories_do_not_count(game_env):
    m = game_env.module
    m.region.capacity["preserve"] = 20
    m.region.capacity["output"] = 20
    assert m.shared_research_units() == 0


def test_chapters_unlock_at_thresholds(game_env):
    m = game_env.module
    for units, expected in ((0, 1), (2, 1), (3, 2), (7, 2), (8, 3), (14, 3), (15, 4), (99, 4)):
        m.region.capacity["monitor"] = units
        assert len(m.shared_research_chapters_reached()) == expected, units


def test_contributions_from_different_regions_combine(game_env):
    m = game_env.module
    m.region_b.capacity["monitor"] = 2
    m.region_c.capacity["monitor"] = 1
    assert len(m.shared_research_chapters_reached()) == 2


def test_render_lists_every_reached_chapter(game_env):
    m = game_env.module
    m.region.capacity["monitor"] = 8
    m.render()
    html = game_env.elements["shared-research-story"].innerHTML
    assert "Chapter 1" in html and "Chapter 2" in html and "Chapter 3" not in html
    assert "next chapter at 15" in game_env.elements["shared-research-progress"].innerText


def test_final_chapter_reports_everything_unlocked(game_env):
    m = game_env.module
    m.region.capacity["monitor"] = 15
    m.render()
    assert "every chapter unlocked" in game_env.elements["shared-research-progress"].innerText
    assert "Region D" in game_env.elements["shared-research-story"].innerHTML


def test_investing_through_the_button_advances_the_story(game_env):
    m = game_env.module
    m.region.funds = 10000
    for _ in range(3):
        game_env.invest("monitor")
    assert "Chapter 1" in game_env.elements["shared-research-story"].innerHTML


def test_story_has_no_effect_on_mechanics_and_no_save_footprint(game_env):
    m = game_env.module
    before = m.region_b.feedback_dampening_fraction()
    m.region.capacity["monitor"] = 15
    m.render()
    assert m.region_b.feedback_dampening_fraction() == before
    assert "shared_research" not in m.get_state()
    assert set(m.get_state().keys()) >= {"region", "region_b", "region_c", "region_d"}


def test_chapters_are_ascending_and_start_at_zero(game_env):
    thresholds = [c[0] for c in game_env.module.SHARED_RESEARCH_CHAPTERS]
    assert thresholds[0] == 0
    assert thresholds == sorted(set(thresholds))
