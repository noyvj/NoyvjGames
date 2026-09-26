"""L4b -- the placement test: an opt-in mixed test that lets a returning player
skip weeks they already know. It must only ever raise plot state, be
confirmable before anything is written, save/validate its one key, and feed the
practice ledger."""

import random


def _current(m):
    return m.placement_queue[m.placement_index]["question"]


def _answer(m, right=True):
    q = _current(m)
    if right:
        return m.submit_placement_answer(q["answer"])
    if q["mode"] == "choice":
        return m.submit_placement_answer(next(c for c in q["choices"] if c != q["answer"]))
    return m.submit_placement_answer("zzz definitely wrong zzz")


def _start(game_env):
    m = game_env.module
    m.start_placement()
    m.begin_placement_test()
    return m


def _run(m, pattern):
    """Answer questions per `pattern` (a function of the question index)."""
    guard = 0
    while m.placement_phase == "testing" and guard < 100:
        _answer(m, pattern(m.placement_index))
        m.next_placement_question()
        guard += 1


def _pass_bands(bands_to_pass):
    """Right in the first N bands, wrong from then on."""
    return lambda index: index < bands_to_pass * 4


def _snapshot(m):
    return {
        p.plot_id: (p.stage, p.ease_factor, p.interval_days, p.last_reviewed, p.next_due, p.correct_streak, p.in_weeds)
        for p in m.state.plots
    }


def test_it_is_a_practice_mode(game_env):
    m = game_env.module
    assert "placement" in m.PRACTICE_MODES
    assert set(m.practice_ledger) == set(m.PRACTICE_MODES)


def test_bands_cut_the_23_rows_into_six_consecutive_groups(game_env):
    m = game_env.module
    bands = m.placement_bands()
    assert [len(b) for b in bands] == [4, 4, 4, 4, 4, 3]
    assert [s for band in bands for s in band] == list(range(1, 24))


def test_locked_rows_are_never_probed(game_env):
    m = game_env.module
    game_env.state.is_row_unlocked = lambda sequence: sequence <= 5
    bands = m.placement_bands()
    assert [s for band in bands for s in band] == [1, 2, 3, 4, 5]
    queue = m.build_placement_test(rng=random.Random(1))
    assert {entry["sequence"] for entry in queue} <= {1, 2, 3, 4, 5}


def test_the_ladder_has_24_questions_in_increasing_bands(game_env):
    m = game_env.module
    queue = m.build_placement_test(rng=random.Random(3))
    assert len(queue) == 24
    assert [entry["band"] for entry in queue] == [b for b in range(6) for _ in range(4)]
    sequences = [entry["sequence"] for entry in queue]
    assert sequences[0] <= 4 and sequences[-1] >= 20
    for band, rows in enumerate(m.placement_bands()):
        assert {e["sequence"] for e in queue if e["band"] == band} <= set(rows)


def test_a_perfect_run_places_through_the_last_week_and_shows_a_confirmable_plan(game_env):
    m = _start(game_env)
    before = _snapshot(m)
    _run(m, lambda index: True)
    assert m.placement_phase == "summary"
    plan = m.placement_plan_data
    assert plan["through"] == 23 and plan["start_sequence"] is None
    assert len(plan["plots"]) == len(m.state.plots)
    assert "past the last week" in game_env.elements["placement-plan"].innerText
    # nothing is written until Apply
    assert _snapshot(m) == before
    assert m.placement_through == 0
    assert game_env.elements["placement-apply-button"].hidden is False
    assert game_env.elements["placement-apply-button"].disabled is False


def test_the_test_stops_when_a_band_can_no_longer_be_passed(game_env):
    m = _start(game_env)
    _run(m, _pass_bands(2))
    # two bands passed (8 answers), then the third fails after two misses
    assert m.placement_phase == "summary"
    assert m.placement_index == 10
    assert m.placement_through_from_results() == 8
    plan = m.placement_plan_data
    assert plan["through"] == 8 and plan["start_sequence"] == 9
    text = game_env.elements["placement-plan"].innerText
    assert text.startswith("You will start at week 9; ") and "Sprout" in text


def test_a_failed_first_band_places_nobody(game_env):
    m = _start(game_env)
    _run(m, lambda index: False)
    assert m.placement_phase == "summary"
    assert m.placement_index == 2  # stopped as soon as the first band was lost
    assert m.placement_plan_data["through"] == 0
    assert game_env.elements["placement-apply-button"].hidden is True
    assert "No placement" in game_env.elements["placement-plan"].innerText


def test_one_slip_in_a_band_still_passes_it(game_env):
    m = _start(game_env)
    _run(m, lambda index: index != 1 and index < 8)
    assert m.placement_through_from_results() == 8


def test_apply_makes_modest_staggered_sprouts_and_only_in_placed_rows(game_env):
    m = _start(game_env)
    _run(m, _pass_bands(2))
    moved = m.on_apply_placement()
    plan_ids = {pid for pid, _ in m.placement_plan_data["plots"]}
    assert moved == len(plan_ids) > 0
    offsets = set()
    for plot in m.state.plots:
        if plot.sequence <= 8:
            assert plot.stage == m.STAGE_SPROUT and plot.correct_streak == 1
            assert m.candidate_stage(plot) == m.STAGE_SPROUT
            assert plot.last_reviewed == m.state.current_day
            assert 1 <= plot.next_due - m.state.current_day <= m.PLACEMENT_SPREAD_DAYS
            assert plot.interval_days == plot.next_due - m.state.current_day
            assert plot.ease_factor == m.DEFAULT_EASE
            offsets.add(plot.next_due)
        else:
            assert plot.stage == m.STAGE_SEED and plot.last_reviewed is None
    assert len(offsets) == m.PLACEMENT_SPREAD_DAYS  # spread, not one due wall
    assert m.placement_through == 8
    assert "Placement applied" in game_env.elements["placement-status"].innerText


def test_apply_never_lowers_or_touches_existing_progress(game_env):
    m = game_env.module
    plots = m.state.row_plots(2)
    bloom, wrong, weedy, watered = plots[0], plots[1], plots[2], plots[3]
    m.state.review(bloom.plot_id, True)
    bloom.stage, bloom.interval_days, bloom.correct_streak = m.STAGE_BLOOMING, 9, 4
    m.state.review(wrong.plot_id, False)
    weedy.in_weeds = True
    m.state.review(watered.plot_id, True)
    ranks = {p.plot_id: m.STAGE_RANK[p.stage] for p in m.state.plots}
    untouched = {p.plot_id: _snapshot_one(p) for p in (bloom, wrong, weedy, watered)}
    m.start_placement()
    m.begin_placement_test()
    _run(m, _pass_bands(1))
    m.on_apply_placement()
    for pid, rank in ranks.items():
        assert m.STAGE_RANK[m.state.plots_by_id[pid].stage] >= rank
    for plot in (bloom, wrong, weedy, watered):
        assert _snapshot_one(plot) == untouched[plot.plot_id]


def _snapshot_one(p):
    return (p.stage, p.ease_factor, p.interval_days, p.last_reviewed, p.next_due, p.correct_streak, p.in_weeds)


def test_cancel_writes_nothing(game_env):
    m = _start(game_env)
    before = _snapshot(m)
    _run(m, _pass_bands(3))
    assert game_env.elements["placement-cancel-button"].innerText == "Cancel"
    game_env.elements["placement-cancel-button"].dispatch("click", None)
    assert m.placement_active is False and game_env.elements["placement-panel"].hidden is True
    assert _snapshot(m) == before and m.placement_through == 0
    assert "placement_through" not in m.get_state()


def test_applying_twice_is_a_no_op_and_the_record_only_rises(game_env):
    m = _start(game_env)
    _run(m, _pass_bands(3))
    assert m.on_apply_placement() > 0
    assert m.on_apply_placement() == 0  # already applied this session
    assert m.placement_through == 12
    # a later, weaker test can never lower the saved placement
    m.start_placement()
    m.begin_placement_test()
    _run(m, _pass_bands(1))
    assert m.placement_plan_data["through"] == 4
    assert game_env.elements["placement-apply-button"].disabled is True  # nothing left to change
    m.apply_placement()
    assert m.placement_through == 12
    assert "week 5" in game_env.elements["placement-plan"].innerText


def test_a_locked_row_is_never_placed_even_from_a_forced_plan(game_env):
    m = game_env.module
    game_env.state.is_row_unlocked = lambda sequence: sequence <= 5
    plan = m.build_placement_plan(23)
    assert {m.state.plots_by_id[pid].sequence for pid, _ in plan["plots"]} <= {1, 2, 3, 4, 5}


def test_answers_feed_the_practice_ledger(game_env):
    m = _start(game_env)
    before = m.practice_score()
    _answer(m, True)
    assert m.practice_ledger["placement"]["total"] == 1
    assert m.practice_ledger["placement"]["correct"] == 1
    assert m.practice_score() == before + 1
    m.next_placement_question()
    _answer(m, False)
    assert m.practice_ledger["placement"]["total"] == 2
    assert m.practice_ledger["placement"]["correct"] == 1
    assert m.practice_score() == before + 1
    assert _answer(m, True) is None  # already answered


def test_a_test_that_is_not_applied_never_touches_srs_state(game_env):
    m = _start(game_env)
    before = _snapshot(m)
    _run(m, lambda index: True)
    assert _snapshot(m) == before


def test_save_writes_the_key_only_when_non_default_and_validates_on_load(game_env):
    m = game_env.module
    assert "placement_through" not in m.get_state()
    m.start_placement()
    m.begin_placement_test()
    _run(m, _pass_bands(2))
    m.on_apply_placement()
    saved = m.get_state()
    assert saved["placement_through"] == 8
    assert sum(1 for r in saved["plots"].values() if r["stage"] == m.STAGE_SPROUT) > 0
    m.placement_through = 0
    m.load_state(saved)
    assert m.placement_through == 8
    for bad, expected in ((True, 0), ("8", 0), (-4, 0), (10_000, 23), (7.5, 0), (None, 0), ([3], 0)):
        m.load_state({"version": 1, "current_day": 0, "plots": {}, "placement_through": bad})
        assert m.placement_through == expected, bad
    m.load_state({"version": 1, "current_day": 0, "plots": {}})
    assert m.placement_through == 0 and "placement_through" not in m.get_state()


def test_loading_a_save_closes_an_open_placement_session(game_env):
    m = _start(game_env)
    m.load_state({"version": 1, "current_day": 0, "plots": {}})
    assert m.placement_active is False and game_env.elements["placement-panel"].hidden is True


def test_button_flow_intro_start_choices_and_typed_answers(game_env):
    m = game_env.module
    els = game_env.elements
    assert els["placement-hint"].hidden is False  # fresh farm invites a placement
    els["placement-button"].dispatch("click", None)
    assert els["placement-panel"].hidden is False
    assert els["placement-intro"].hidden is False and els["placement-start-button"].hidden is False
    assert els["placement-card"].hidden is True and els["placement-hint"].hidden is True
    els["placement-start-button"].dispatch("click", None)
    assert els["placement-card"].hidden is False and els["placement-intro"].hidden is True
    assert els["placement-progress"].innerText.startswith("1 of up to 24")
    saw_choice = saw_typed = False
    for _ in range(24):
        if m.placement_phase != "testing":
            break
        q = _current(m)
        if q["mode"] == "choice":
            saw_choice = True
            button = els[f"placement-choice-{q['choices'].index(q['answer'])}"]
            button.dispatch("click", None)
        else:
            saw_typed = True
            els["placement-answer-input"].value = q["answer"]
            els["placement-submit-button"].dispatch("click", None)
        assert els["placement-feedback"].innerText == m.PLACEMENT_CORRECT
        assert els["placement-next-button"].hidden is False
        els["placement-next-button"].dispatch("click", None)
    assert saw_choice or saw_typed
    assert m.placement_phase == "summary" and els["placement-summary"].hidden is False
    assert "24/24" in els["placement-summary"].innerText
    els["placement-apply-button"].dispatch("click", None)
    assert m.placement_through == 23
    assert els["placement-cancel-button"].innerText == "Close"
    assert els["placement-retry-button"].hidden is True
    els["placement-close-button"].dispatch("click", None)
    assert els["placement-panel"].hidden is True and els["placement-hint"].hidden is True


def test_a_wrong_answer_shows_the_real_one(game_env):
    m = _start(game_env)
    _answer(m, False)
    answer = _current(m)["answer"]
    assert answer in game_env.elements["placement-feedback"].innerText


def test_retry_builds_a_fresh_test(game_env):
    m = _start(game_env)
    _run(m, _pass_bands(1))
    assert m.placement_phase == "summary"
    game_env.elements["placement-retry-button"].dispatch("click", None)
    assert m.placement_phase == "testing" and m.placement_index == 0 and m.placement_band_scores == {}
    assert game_env.elements["placement-plan"].hidden is True


def test_no_unlocked_rows_says_so_instead_of_starting(game_env):
    m = game_env.module
    game_env.state.is_row_unlocked = lambda sequence: False
    m.start_placement()
    m.begin_placement_test()
    assert m.placement_queue == [] and m.placement_phase == "intro"
    assert game_env.elements["placement-intro"].innerText.startswith(m.PLACEMENT_EMPTY_MESSAGE)
    assert game_env.elements["placement-start-button"].hidden is True


def test_plan_text_reads_naturally_for_one_plot(game_env):
    m = game_env.module
    plan = {"through": 4, "start_sequence": 5, "stage": m.STAGE_SPROUT, "plots": [("a", 1)]}
    assert m.placement_plan_text(plan) == (
        "You will start at week 5; 1 plot moves to Sprout. "
        "Plots you have already watered are left alone, and nothing is ever lowered."
    )
