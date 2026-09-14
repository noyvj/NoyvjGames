"""Milestone 30: "Café Rush" -- a shop-rush minigame over sequence 19-23
(FREN152 Ch.9: food & drink, partitive, passé composé). Same order-rush
structure as Boutique Dash (an order, a patience clock, 15 customers, a
final tally), with one content twist: every CAFE_TWIST_INTERVAL-th customer
also asks the player to confirm the order in the passé composé, reusing
generate_question()'s own blank-word/conjugation-swap machinery on a
passé-composé grammar plot -- see minigames.py's own Milestone 30 build
note for the fuller design reasoning.

Sequence 19-23 is not the permanent catch-up zone, so whether it's actually
unlocked depends on how far this particular farm's plots have grown --
same posture test_minigame_verb_racer.py and test_minigame_boutique_dash.py
already take for their own non-catch-up-zone content.
"""

from pathlib import Path

CATALOG_TEXT = Path(__file__).resolve().parent.parent.joinpath(
    "fren_combined_catalog.json"
).read_text(encoding="utf-8")


def _range_unlocked(state, mg):
    return all(state.is_row_unlocked(seq) for seq in range(mg.CAFE_LO, mg.CAFE_HI + 1))


def _unlock_cafe_range(state, mg):
    """Force sequence 19-23 open by sprouting every plot in every row up to
    (and including) row 22, mirroring test_row_unlock.py's own approach."""
    for sequence in range(1, mg.CAFE_HI):
        for plot in state.row_plots(sequence):
            state.review(plot.plot_id, True)


def _play_until_twist(mg):
    """Advance customers (always answering correctly) until a twist round's
    item pick has just been made, leaving cafe_stage == CAFE_STAGE_TWIST.
    Bounded by CAFE_TOTAL_CUSTOMERS so it can never spin forever."""
    for _ in range(mg.CAFE_TOTAL_CUSTOMERS):
        if mg.cafe_order is None:
            return False
        mg.submit_cafe_item_choice(mg.cafe_order["answer"])
        if mg.cafe_stage == mg.CAFE_STAGE_TWIST:
            return True
    return False


def test_toggle_reflects_whether_its_range_is_fully_unlocked(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    assert mg.cafe_available() == _range_unlocked(state, mg)
    assert game_env.elements["cafe-toggle-button"].disabled == (not mg.cafe_available())


def test_panel_is_hidden_until_toggled_open(game_env):
    module = game_env.module
    assert game_env.elements["cafe-panel"].hidden is True
    module.minigames.on_toggle_cafe()
    assert game_env.elements["cafe-panel"].hidden is False


def test_starting_a_shift_resets_counters_and_rolls_an_order(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    order = mg.start_cafe()
    assert order is not None
    assert mg.cafe_active is True
    assert mg.cafe_served == 0
    assert mg.cafe_missed == 0
    assert mg.cafe_score == 0
    assert mg.cafe_stage == mg.CAFE_STAGE_PICK
    assert order["answer"] in order["choices"]
    assert len(order["choices"]) <= mg.CAFE_OPTION_COUNT
    assert order["answer"] in CATALOG_TEXT


def test_every_order_answer_and_choice_is_real_catalog_text(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    for _ in range(30):
        if mg.cafe_order is None:
            mg.start_cafe()
        for choice in mg.cafe_order["choices"]:
            assert choice in CATALOG_TEXT
        mg.submit_cafe_item_choice(mg.cafe_order["answer"])


def test_a_correct_pick_with_no_twist_scores_and_speeds_up(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    # customer #1 is never a twist round (index 1 % interval != 0 for the
    # default interval of 3)
    assert mg.cafe_is_twist_round is False
    starting_patience_max = mg.cafe_patience_max
    result = mg.submit_cafe_item_choice(mg.cafe_order["answer"])
    assert result is True
    assert mg.cafe_served == 1
    assert mg.cafe_score == mg.CAFE_BASE_POINTS
    assert mg.cafe_patience_max == starting_patience_max - mg.CAFE_PATIENCE_STEP
    assert mg.cafe_stage == mg.CAFE_STAGE_PICK  # already rolled the next customer


def test_a_wrong_pick_misses_without_ever_reaching_the_twist(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    wrong = next((c for c in mg.cafe_order["choices"] if c != mg.cafe_order["answer"]), None)
    if wrong is None:
        return  # a pool too small to have a distractor this round -- nothing to test
    result = mg.submit_cafe_item_choice(wrong)
    assert result is False
    assert mg.cafe_missed == 1
    assert mg.cafe_served == 0
    assert mg.cafe_twist_question is None


def test_a_twist_round_shows_a_grammar_confirmation_after_the_right_pick(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    if not mg._cafe_twist_candidate_plots():
        return  # nothing in range currently offers a blank/conjugation variant
    reached = _play_until_twist(mg)
    assert reached, "expected a twist round within one session"
    assert mg.cafe_twist_question is not None
    plot = state.plots_by_id[mg.cafe_twist_question["plot_id"]]
    assert plot.topic_type == "grammar"
    assert plot.topic_id in mg.CAFE_PASSE_COMPOSE_TOPIC_IDS
    assert mg.cafe_twist_question["variant"] in mg.CAFE_TWIST_VARIANTS
    assert mg.CAFE_LO <= plot.sequence <= mg.CAFE_HI


def test_a_correct_twist_confirmation_serves_the_customer_with_a_bonus(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    if not mg._cafe_twist_candidate_plots():
        return
    if not _play_until_twist(mg):
        return
    served_before = mg.cafe_served
    result = mg.submit_cafe_twist_choice(mg.cafe_twist_question["answer"])
    assert result is True
    assert mg.cafe_served == served_before + 1
    assert mg.cafe_stage == mg.CAFE_STAGE_PICK  # moved on to the next customer


def test_a_wrong_twist_confirmation_still_counts_as_a_miss(game_env):
    """Design decision pinned by test: the brief frames the twist as an
    *additional* requirement, not a softer alternative -- getting the item
    right but the passé composé confirmation wrong still counts as a missed
    customer overall (see the Milestone 30 build note in minigames.py)."""
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    if not mg._cafe_twist_candidate_plots():
        return
    if not _play_until_twist(mg):
        return
    wrong = next(
        c for c in mg.cafe_twist_question["choices"] if c != mg.cafe_twist_question["answer"]
    )
    missed_before = mg.cafe_missed
    result = mg.submit_cafe_twist_choice(wrong)
    assert result is False
    assert mg.cafe_missed == missed_before + 1
    assert mg.cafe_stage == mg.CAFE_STAGE_PICK


def test_twist_cadence_is_fixed_not_random(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    if not mg._cafe_twist_candidate_plots():
        return
    mg.start_cafe()
    for customer_index in range(1, mg.CAFE_TOTAL_CUSTOMERS + 1):
        if mg.cafe_order is None:
            break
        expected_twist = customer_index % mg.CAFE_TWIST_INTERVAL == 0
        assert mg.cafe_is_twist_round == expected_twist
        mg.submit_cafe_item_choice(mg.cafe_order["answer"])
        if mg.cafe_stage == mg.CAFE_STAGE_TWIST:
            mg.submit_cafe_twist_choice(mg.cafe_twist_question["answer"])


def test_a_timeout_during_the_pick_stage_counts_as_a_miss(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    for _ in range(mg.CAFE_STARTING_PATIENCE):
        mg.cafe_tick()
    assert mg.cafe_missed == 1
    assert mg.cafe_served == 0
    assert mg.cafe_active is True


def test_a_timeout_during_the_twist_stage_also_counts_as_a_miss(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    if not mg._cafe_twist_candidate_plots():
        return
    if not _play_until_twist(mg):
        return
    missed_before = mg.cafe_missed
    remaining = mg.cafe_patience_remaining
    for _ in range(remaining):
        mg.cafe_tick()
    assert mg.cafe_missed == missed_before + 1
    assert mg.cafe_stage == mg.CAFE_STAGE_PICK  # moved on to a fresh customer


def test_cafe_tick_is_a_no_op_when_no_shift_is_active(game_env):
    module = game_env.module
    mg = module.minigames
    assert mg.cafe_active is False
    result = mg.cafe_tick()
    assert result is None


def test_the_session_ends_after_the_total_customer_cap_with_a_tally(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    for _ in range(mg.CAFE_TOTAL_CUSTOMERS * 2):  # generous upper bound (twist rounds take 2 steps)
        if mg.cafe_order is None:
            break
        mg.submit_cafe_item_choice(mg.cafe_order["answer"])
        if mg.cafe_stage == mg.CAFE_STAGE_TWIST:
            mg.submit_cafe_twist_choice(mg.cafe_twist_question["answer"])
    assert mg.cafe_active is False
    assert mg.cafe_order is None
    assert mg.cafe_served + mg.cafe_missed == mg.CAFE_TOTAL_CUSTOMERS


def test_summary_reads_as_neutral_not_shaming(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    for _ in range(mg.CAFE_TOTAL_CUSTOMERS):
        if mg.cafe_order is None:
            break
        wrong = next((c for c in mg.cafe_order["choices"] if c != mg.cafe_order["answer"]), None)
        mg.submit_cafe_item_choice(wrong if wrong is not None else mg.cafe_order["answer"])
    module.render()
    summary = game_env.elements["cafe-summary"].innerText.lower()
    assert summary != ""
    for banned in ("fail", "you lose", "game over", "you failed", "🔥"):
        assert banned not in summary


def test_patience_bar_width_reflects_remaining_over_max(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    module.render()
    assert game_env.elements["cafe-patience-fill"].style.width == "100%"
    mg.cafe_tick()
    module.render()
    expected = round((mg.cafe_patience_remaining / mg.cafe_patience_max) * 100)
    assert game_env.elements["cafe-patience-fill"].style.width == f"{expected}%"


def test_twist_panel_only_shows_during_the_twist_stage(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    module.render()
    assert game_env.elements["cafe-twist-panel"].hidden is True
    if not mg._cafe_twist_candidate_plots():
        return
    if not _play_until_twist(mg):
        return
    module.render()
    assert game_env.elements["cafe-twist-panel"].hidden is False
    choices_box = game_env.elements["cafe-twist-choices"]
    assert len(choices_box.children) == len(mg.cafe_twist_question["choices"])


def test_closing_the_panel_ends_any_active_shift_and_hides_it(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    mg.close_cafe()
    assert mg.cafe_open is False
    assert mg.cafe_active is False
    assert mg.cafe_order is None
    assert game_env.elements["cafe-panel"].hidden is True


def test_start_button_click_starts_a_shift(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    game_env.elements["cafe-toggle-button"].dispatch("click", None)
    game_env.elements["cafe-start-button"].dispatch("click", None)
    assert mg.cafe_active is True


def test_choice_buttons_are_rendered_and_clickable(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    mg.start_cafe()
    module.render()
    options_box = game_env.elements["cafe-options"]
    assert len(options_box.children) == len(mg.cafe_order["choices"])
    game_env.elements["cafe-choice-0"].dispatch("click", None)
    assert mg.cafe_served + mg.cafe_missed == 1


def test_cafe_would_be_locked_if_its_range_were_not_fully_unlocked(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    real_is_row_unlocked = state.is_row_unlocked
    state.is_row_unlocked = lambda sequence: sequence != 21 and real_is_row_unlocked(sequence)
    try:
        assert mg.cafe_available() is False
        assert mg.cafe_lock_reason() == mg._lock_reason(mg.CAFE_HI)
        assert mg.start_cafe() is None
    finally:
        state.is_row_unlocked = real_is_row_unlocked


def test_cafe_never_draws_a_twist_plot_from_outside_its_topic_list(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_cafe_range(state, mg)
    for plot in mg._cafe_twist_candidate_plots():
        assert plot.topic_id in mg.CAFE_PASSE_COMPOSE_TOPIC_IDS
        assert state.is_row_unlocked(plot.sequence) is True
