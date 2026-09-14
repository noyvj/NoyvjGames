"""Milestone 29: "Boutique Dash" -- a shop-rush minigame over sequence
16-18 (FREN152 Ch.6: shopping for clothes, colours, demonstratives). A
customer's order is a genuine colour + garment combination built from real
catalog vocab; the player picks the matching item from a small display of
options before that customer's patience runs out. 15 customers per
session, one shot each (no retry), ending in a final tally -- see
minigames.py's own Milestone 29 build note for the fuller design reasoning
(especially why plural garments and multi-item "/" records are excluded
from the combo pool).

Sequence 16-18 is not the permanent catch-up zone (unlike Blitz's 1-11), so
whether it's actually unlocked depends on how far this particular farm's
plots have grown -- same posture test_minigame_verb_racer.py already takes
for its own non-catch-up-zone content.
"""

from pathlib import Path

CATALOG_TEXT = Path(__file__).resolve().parent.parent.joinpath(
    "fren_combined_catalog.json"
).read_text(encoding="utf-8")


def _range_unlocked(state, mg):
    return all(state.is_row_unlocked(seq) for seq in range(mg.BOUTIQUE_LO, mg.BOUTIQUE_HI + 1))


def _unlock_boutique_range(state, mg):
    """Force sequence 16-18 open by sprouting every plot in every row up to
    (and including) row 17, mirroring test_row_unlock.py's own approach to
    driving the farm's real unlock gate rather than reaching around it."""
    for sequence in range(1, mg.BOUTIQUE_HI):
        for plot in state.row_plots(sequence):
            state.review(plot.plot_id, True)


def test_toggle_reflects_whether_its_range_is_fully_unlocked(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    assert mg.boutique_available() == _range_unlocked(state, mg)
    assert game_env.elements["boutique-toggle-button"].disabled == (
        not mg.boutique_available()
    )


def test_panel_is_hidden_until_toggled_open(game_env):
    module = game_env.module
    assert game_env.elements["boutique-panel"].hidden is True
    module.minigames.on_toggle_boutique()
    assert game_env.elements["boutique-panel"].hidden is False


def test_starting_a_shift_resets_counters_and_rolls_an_order(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    order = mg.start_boutique()
    assert order is not None
    assert mg.boutique_active is True
    assert mg.boutique_served == 0
    assert mg.boutique_missed == 0
    assert mg.boutique_score == 0
    assert mg.boutique_patience_remaining == mg.BOUTIQUE_STARTING_PATIENCE
    assert order["answer"] in order["choices"]
    assert len(order["choices"]) == mg.BOUTIQUE_OPTION_COUNT


def test_every_order_recombines_real_catalog_garment_and_colour_text(game_env):
    """Copyright/no-fabrication spot check: every generated order's answer
    must be a garment fragment and a colour fragment that both appear
    verbatim somewhere in the catalog, glued together with a space -- never
    invented French."""
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    for _ in range(30):
        if mg.boutique_order is None:
            mg.start_boutique()
        answer = mg.boutique_order["answer"]
        found = False
        for garment_fr, _garment_en, _gender in mg._boutique_garment_entries():
            if answer.startswith(garment_fr + " "):
                colour_fragment = answer[len(garment_fr) + 1:]
                colours = mg._boutique_colour_entries()
                if any(colour_fragment in (masc, fem) for masc, fem, _en in colours):
                    found = True
                    break
        assert found, f"could not decompose {answer!r} into a known garment + colour"
        mg.submit_boutique_choice(answer)


def test_no_answer_ever_uses_a_plural_garment_or_a_slash_record(game_env):
    """Design decision pinned by test: plural garments ("des ...") and
    multi-item "/" records are excluded from the combo pool entirely,
    since the catalog stores no plural colour form to correctly agree with
    one, and a "/" record packs two real garments into a single string --
    see the Milestone 29 build note in minigames.py."""
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    for _ in range(30):
        if mg.boutique_order is None:
            mg.start_boutique()
        for choice in mg.boutique_order["choices"]:
            assert not choice.startswith("des ")
            assert " / " not in choice
        mg.submit_boutique_choice(mg.boutique_order["answer"])


def test_a_correct_sale_scores_points_and_speeds_up_the_pace(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    starting_patience_max = mg.boutique_patience_max
    result = mg.submit_boutique_choice(mg.boutique_order["answer"])
    assert result is True
    assert mg.boutique_served == 1
    assert mg.boutique_missed == 0
    assert mg.boutique_score == mg.BOUTIQUE_BASE_POINTS
    assert mg.boutique_patience_max == starting_patience_max - mg.BOUTIQUE_PATIENCE_STEP
    assert mg.boutique_order is not None  # a fresh customer rolled


def test_pace_never_speeds_up_past_the_floor(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    for _ in range(mg.BOUTIQUE_TOTAL_CUSTOMERS - 1):
        mg.submit_boutique_choice(mg.boutique_order["answer"])
        assert mg.boutique_patience_max >= mg.BOUTIQUE_MIN_PATIENCE


def test_a_miss_does_not_speed_up_the_pace(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    starting_patience_max = mg.boutique_patience_max
    wrong = next(c for c in mg.boutique_order["choices"] if c != mg.boutique_order["answer"])
    result = mg.submit_boutique_choice(wrong)
    assert result is False
    assert mg.boutique_served == 0
    assert mg.boutique_missed == 1
    assert mg.boutique_patience_max == starting_patience_max
    assert mg.boutique_order is not None  # a fresh customer rolled anyway -- no retry


def test_a_timeout_counts_as_a_missed_customer(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    for _ in range(mg.BOUTIQUE_STARTING_PATIENCE):
        mg.boutique_tick()
    assert mg.boutique_missed == 1
    assert mg.boutique_served == 0
    assert mg.boutique_active is True  # the shift itself continues


def test_boutique_tick_is_a_no_op_when_no_shift_is_active(game_env):
    module = game_env.module
    mg = module.minigames
    assert mg.boutique_active is False
    result = mg.boutique_tick()
    assert result is None


def test_the_session_ends_after_the_total_customer_cap_with_a_tally(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    for i in range(mg.BOUTIQUE_TOTAL_CUSTOMERS):
        if i % 2 == 0:
            mg.submit_boutique_choice(mg.boutique_order["answer"])
        else:
            wrong = next(c for c in mg.boutique_order["choices"] if c != mg.boutique_order["answer"])
            mg.submit_boutique_choice(wrong)
    assert mg.boutique_active is False
    assert mg.boutique_order is None
    assert mg.boutique_served + mg.boutique_missed == mg.BOUTIQUE_TOTAL_CUSTOMERS


def test_summary_reads_as_neutral_not_shaming(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    for _ in range(mg.BOUTIQUE_TOTAL_CUSTOMERS):
        wrong = next(c for c in mg.boutique_order["choices"] if c != mg.boutique_order["answer"])
        mg.submit_boutique_choice(wrong)
    module.render()
    summary = game_env.elements["boutique-summary"].innerText.lower()
    assert summary != ""
    for banned in ("fail", "you lose", "game over", "you failed", "🔥"):
        assert banned not in summary


def test_patience_bar_width_reflects_remaining_over_max(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    module.render()
    assert game_env.elements["boutique-patience-fill"].style.width == "100%"
    mg.boutique_tick()
    module.render()
    expected = round((mg.boutique_patience_remaining / mg.boutique_patience_max) * 100)
    assert game_env.elements["boutique-patience-fill"].style.width == f"{expected}%"


def test_closing_the_panel_ends_any_active_shift_and_hides_it(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    mg.close_boutique()
    assert mg.boutique_open is False
    assert mg.boutique_active is False
    assert mg.boutique_order is None
    assert game_env.elements["boutique-panel"].hidden is True


def test_start_button_click_starts_a_shift(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    game_env.elements["boutique-toggle-button"].dispatch("click", None)
    game_env.elements["boutique-start-button"].dispatch("click", None)
    assert mg.boutique_active is True


def test_choice_buttons_are_rendered_and_clickable(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    module.render()
    options_box = game_env.elements["boutique-options"]
    assert len(options_box.children) == len(mg.boutique_order["choices"])
    game_env.elements["boutique-choice-0"].dispatch("click", None)
    assert mg.boutique_served + mg.boutique_missed == 1


def test_shop_would_be_locked_if_its_range_were_not_fully_unlocked(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    real_is_row_unlocked = state.is_row_unlocked
    state.is_row_unlocked = lambda sequence: sequence != 17 and real_is_row_unlocked(sequence)
    try:
        assert mg.boutique_available() is False
        assert mg.boutique_lock_reason() == mg._lock_reason(mg.BOUTIQUE_HI)
        assert mg.start_boutique() is None
    finally:
        state.is_row_unlocked = real_is_row_unlocked


def test_boutique_never_draws_from_a_locked_row(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    # Lock row 18 back down after unlocking through it, and confirm nothing
    # from its own topics (accessories & toiletries) leaks into the pool.
    real_is_row_unlocked = state.is_row_unlocked
    state.is_row_unlocked = lambda sequence: sequence != 18 and real_is_row_unlocked(sequence)
    try:
        garments = mg._boutique_garment_entries()
        # "un maillot de bain" is deliberately excluded from this set -- the
        # catalog lists it in both row16's Clothing topic and row18's
        # Accessories & toiletries topic, so it's legitimately still
        # reachable via row16 alone.
        row18_only = {"une serviette", "une crème solaire",
                      "un sèche-cheveux", "une brosse à dents", "une montre"}
        assert not any(fr in row18_only for fr, _en, _g in garments)
    finally:
        state.is_row_unlocked = real_is_row_unlocked


def test_garment_and_colour_pools_come_from_real_catalog_text(game_env):
    """Every pooled garment/colour fragment must be a verbatim substring of
    the real catalog file, not authored text."""
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_boutique_range(state, mg)
    mg.start_boutique()
    for garment_fr, _garment_en, _gender in mg._boutique_garment_entries():
        assert garment_fr in CATALOG_TEXT
    for masc, fem, _en in mg._boutique_colour_entries():
        assert masc in CATALOG_TEXT
        assert fem in CATALOG_TEXT
