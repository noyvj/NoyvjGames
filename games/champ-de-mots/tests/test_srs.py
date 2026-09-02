"""Milestone 2: plant-state data model + SRS scheduling logic (design doc §6).

Correct recall grows the interval, incorrect resets it short, crossing the
14-day threshold flips a plot to Automated, and — the wellbeing constraint
from §3 — nothing about an incorrect answer ever visually demotes a plant.
"""

import pytest


def test_catalog_loads_the_real_continuous_timeline(game_env):
    catalog = game_env.module.CATALOG
    assert catalog["courses"] == ["FREN151", "FREN152"]
    assert len(catalog["weeks"]) == 23
    assert [w["sequence"] for w in catalog["weeks"]] == list(range(1, 24))
    assert sum(len(t["items"]) for w in catalog["weeks"] for t in w["topics"]) == 966
    assert sum(len(w["topics"]) for w in catalog["weeks"]) == 129


def test_rows_run_continuously_across_both_courses(game_env):
    rows = game_env.state.rows
    assert [r.sequence for r in rows] == list(range(1, 24))
    assert [r.course for r in rows[:11]] == ["FREN151"] * 11
    assert [r.course for r in rows[11:]] == ["FREN152"] * 12
    # Sequence 11 -> 12 is the FREN151/FREN152 boundary and must not reset.
    assert rows[10].sequence + 1 == rows[11].sequence


def test_plot_granularity_is_per_item_except_grammar_rules(game_env):
    """A vocab word is a plot; a whole grammar rule is a single plot whose
    example items feed its question variants (design doc §5)."""
    state = game_env.state
    expected = 0
    for week in game_env.module.CATALOG["weeks"]:
        for topic in week["topics"]:
            expected += 1 if topic["topic_type"] == "grammar" else len(topic["items"])
    assert len(state.plots) == expected == 722
    assert len(state.plots_by_id) == len(state.plots)


def test_every_plot_carries_its_syllabus_placement(game_env):
    plot = game_env.state.plots[0]
    assert plot.sequence == 1
    assert plot.course == "FREN151"
    assert plot.week == 1
    assert plot.chapter == 1
    assert plot.topic_type in {"vocab", "phrase", "grammar", "phonetic"}
    assert plot.topic_title
    assert plot.items and all("fr" in i and "en" in i for i in plot.items)


def test_fresh_plots_start_as_unreviewed_seeds(game_env):
    for plot in game_env.state.plots:
        assert plot.ease_factor == game_env.module.DEFAULT_EASE
        assert plot.interval_days == 0
        assert plot.last_reviewed is None
        assert plot.next_due is None
        assert plot.correct_streak == 0
        assert plot.stage == game_env.module.STAGE_SEED


def test_first_correct_review_sprouts_the_plot(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]

    state.review(plot.plot_id, True)

    assert plot.correct_streak == 1
    assert plot.interval_days == module.FIRST_INTERVAL_DAYS == 1
    assert plot.last_reviewed == 0
    assert plot.next_due == 1
    assert plot.ease_factor == pytest.approx(2.6)
    assert plot.stage == module.STAGE_SPROUT


def test_growth_ladder_across_a_clean_review_sequence(game_env):
    """Four spaced correct recalls take a plot Seed -> Sprout -> Budding ->
    Blooming -> Automated, with the interval growing 1 -> 3 -> 7+ -> 14+."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    seen = []

    for _ in range(4):
        state.review(plot.plot_id, True)
        seen.append((plot.interval_days, plot.stage))
        state.advance_day(plot.interval_days)

    intervals = [i for i, _ in seen]
    stages = [s for _, s in seen]
    assert intervals[0] == 1
    assert intervals[1] == module.SECOND_INTERVAL_DAYS == 3
    assert intervals[2] >= module.BLOOMING_INTERVAL_DAYS
    assert intervals[3] >= module.AUTOMATION_INTERVAL_DAYS
    assert intervals == sorted(intervals)
    assert stages == [
        module.STAGE_SPROUT,
        module.STAGE_BUDDING,
        module.STAGE_BLOOMING,
        module.STAGE_AUTOMATED,
    ]


def test_next_due_tracks_the_day_the_review_happened(game_env):
    state = game_env.state
    plot = state.plots[0]

    state.advance_day(5)
    state.review(plot.plot_id, True)
    assert plot.last_reviewed == 5
    assert plot.next_due == 6

    state.advance_day(1)
    state.review(plot.plot_id, True)
    assert plot.last_reviewed == 6
    assert plot.next_due == 9


def test_incorrect_recall_resets_the_interval_short(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    for _ in range(3):
        state.review(plot.plot_id, True)
    assert plot.interval_days >= module.BLOOMING_INTERVAL_DAYS

    ease_before = plot.ease_factor
    state.review(plot.plot_id, False)

    assert plot.interval_days == module.RESET_INTERVAL_DAYS == 1
    assert plot.correct_streak == 0
    assert plot.next_due == state.current_day + 1
    assert plot.ease_factor == pytest.approx(ease_before - module.EASE_INCORRECT_PENALTY)


def test_incorrect_recall_never_demotes_the_plant(game_env):
    """§3's wellbeing constraint: a wrong answer means 'needs water again',
    never a visual demotion or a lost plant."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    for _ in range(4):
        state.review(plot.plot_id, True)
    assert plot.stage == module.STAGE_AUTOMATED

    for _ in range(5):
        state.review(plot.plot_id, False)

    assert plot.stage == module.STAGE_AUTOMATED
    assert plot in state.plots  # nothing is ever removed/killed


def test_ease_factor_is_clamped_at_both_ends(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]

    for _ in range(30):
        state.review(plot.plot_id, True)
    assert plot.ease_factor == pytest.approx(module.MAX_EASE)

    for _ in range(30):
        state.review(plot.plot_id, False)
    assert plot.ease_factor == pytest.approx(module.MIN_EASE)


def test_mixed_review_sequence_transitions(game_env):
    """A realistic wobbly sequence: correct, correct, wrong, correct, correct."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    outcomes = [True, True, False, True, True]
    intervals = []

    for correct in outcomes:
        state.review(plot.plot_id, correct)
        intervals.append(plot.interval_days)
        state.advance_day(plot.interval_days)

    assert intervals == [1, 3, 1, 1, 3]
    assert plot.correct_streak == 2
    assert plot.stage == module.STAGE_BUDDING


def test_seeds_are_due_immediately_but_never_wilting(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]

    assert module.is_due(plot, state.current_day) is True
    assert module.is_wilting(plot, state.current_day) is False

    state.advance_day(40)
    assert module.is_due(plot, state.current_day) is True
    assert module.is_wilting(plot, state.current_day) is False


def test_watered_plot_is_not_due_until_its_interval_elapses(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    state.review(plot.plot_id, True)
    state.review(plot.plot_id, True)  # interval 3

    assert module.is_due(plot, state.current_day) is False
    state.advance_day(2)
    assert module.is_due(plot, state.current_day) is False
    state.advance_day(1)
    assert module.is_due(plot, state.current_day) is True
    assert module.is_wilting(plot, state.current_day) is False


def test_a_plot_wilts_only_once_it_is_past_due(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    state.review(plot.plot_id, True)  # due tomorrow

    state.advance_day(1)
    assert module.is_wilting(plot, state.current_day) is False
    state.advance_day(1)
    assert module.is_wilting(plot, state.current_day) is True

    state.review(plot.plot_id, True)
    assert module.is_wilting(plot, state.current_day) is False


def test_automated_plots_resurface_far_less_often(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    for _ in range(4):
        state.review(plot.plot_id, True)
        state.advance_day(plot.interval_days)
    assert plot.stage == module.STAGE_AUTOMATED

    # It still comes back around eventually — SRS never truly stops (§2).
    assert module.is_due(plot, state.current_day) is True
    state.review(plot.plot_id, True)
    assert plot.interval_days > module.AUTOMATION_INTERVAL_DAYS


def test_due_plots_reports_everything_needing_water_today(game_env):
    state = game_env.state
    assert len(state.due_plots()) == len(state.available_plots())

    watered = state.due_plots()[0]
    state.review(watered.plot_id, True)
    assert watered not in state.due_plots()

    state.advance_day(1)
    assert watered in state.due_plots()


def test_next_due_plot_prefers_the_longest_overdue(game_env):
    state = game_env.state
    first, second = state.plots[0], state.plots[1]
    for plot in state.plots:
        state.review(plot.plot_id, True)
    state.advance_day(1)
    assert state.next_due_plot() is first

    state.review(first.plot_id, True)
    assert state.next_due_plot() is second


def test_review_of_an_unknown_plot_is_a_no_op(game_env):
    assert game_env.state.review("not-a-real-plot", True) is None


def test_advance_day_moves_the_calendar_forward_only(game_env):
    state = game_env.state
    assert state.current_day == 0
    state.advance_day()
    assert state.current_day == 1
    state.advance_day(6)
    assert state.current_day == 7
    state.advance_day(0)
    assert state.current_day == 7
