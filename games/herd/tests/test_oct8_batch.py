"""Herd batch of 2026-10-08 (planning/TODO.md "GF + F. Herd"): F-19 bulk buying, F-20 round-delta
chips, GF-18 undo the last round, F-21 season calendar, F-22 poultry vs cattle card, F-23 breeding
rings, GF-13 named cows with a hall of fame, F-28 pace note and save nudge."""

import json


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


# ---- F-19 bulk buying --------------------------------------------------------------------
def test_x5_plan_adds_up_the_rising_growth_costs(game_env):
    m = game_env.module
    game_env.farm.funds = 1000.0
    units, total = game_env.farm.bulk_plan("herd", 5)
    expected = sum(m.HERD_GROWTH_COST + i * m.HERD_GROWTH_COST_SLOPE for i in range(5))
    assert (units, total) == (5, expected)


def test_a_plan_never_changes_the_farm(game_env):
    farm = game_env.farm
    farm.funds = 1000.0
    before = (farm.funds, farm.herd_size, dict(farm.decoupling_investment), list(farm.lever_log))
    farm.bulk_plan("herd", "max")
    farm.bulk_plan("feed", 5)
    assert (farm.funds, farm.herd_size, dict(farm.decoupling_investment), list(farm.lever_log)) == before


def test_plan_stops_at_what_funds_allow(game_env):
    m = game_env.module
    game_env.farm.funds = 50.0
    units, total = game_env.farm.bulk_plan("herd", "max")
    assert units == 2 and total == m.HERD_GROWTH_COST * 2 + m.HERD_GROWTH_COST_SLOPE


def test_plan_stops_at_the_regional_cap(game_env):
    farm = game_env.farm
    farm.funds = 10000.0
    farm.regional_cap_enabled = True
    units, _total = farm.bulk_plan("herd", "max")
    assert units == 20  # the cap is 20 methane/round at ratio 1.0
    assert farm.cap_blocks_growth(herd=units + 1)


def test_max_stops_before_buying_levers_that_save_nothing(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 100000.0
    units, _total = farm.bulk_plan("capture", "max")
    # Capture takes the efficiency ratio from 1.0 to the 0.1 floor; no unit past that is bought.
    per_unit = m.DECOUPLING_MEASURES["capture"]["ratio_reduction"]
    assert units == int((1.0 - m.MIN_COUPLING_RATIO) / per_unit + 1e-9)
    farm.decoupling_investment["capture"] = units
    assert farm.bulk_plan("capture", 5)[0] == 0
    assert farm.bulk_plan("capture", 1)[0] == 1  # a single unit is still allowed, as before


def test_buy_bulk_matches_clicking_one_at_a_time(game_env):
    m = game_env.module
    a, b = game_env.farm, m.FarmState()
    a.funds = b.funds = 1000.0
    assert a.buy_bulk("herd", 5) == 5
    for _ in range(5):
        b.grow_herd()
    assert (a.funds, a.herd_size, a.lever_log) == (b.funds, b.herd_size, b.lever_log)
    assert len([e for e in a.lever_log if e[1] == "herd"]) == 5


def test_stepper_buttons_set_the_mode_and_relabel_the_buttons(game_env):
    m = game_env.module
    game_env.farm.funds = 1000.0
    m.render()
    assert game_env.elements["grow-herd-button"].innerText == "Grow Herd (20)"
    _click(game_env, "bulk-5-button")
    assert m.bulk_mode == 5
    assert game_env.elements["grow-herd-button"].innerText == "Grow Herd x5 (120 total)"
    assert game_env.elements["bulk-5-button"].getAttribute("aria-pressed") == "true"
    assert game_env.elements["bulk-1-button"].getAttribute("aria-pressed") == "false"
    assert game_env.elements["bulk-5-button"].classList.contains("selected")
    assert "x5" in game_env.elements["feed-invest-button"].innerText
    _click(game_env, "bulk-1-button")
    assert game_env.elements["grow-herd-button"].innerText == "Grow Herd (20)"


def test_clicking_grow_with_x5_buys_five(game_env):
    game_env.farm.funds = 1000.0
    _click(game_env, "bulk-5-button")
    game_env.grow_herd()
    assert game_env.farm.herd_size == 5


def test_x5_investing_buys_five_levers_and_all_are_logged(game_env):
    farm = game_env.farm
    farm.funds = 1000.0
    _click(game_env, "bulk-5-button")
    game_env.invest_decoupling("feed")
    assert farm.decoupling_investment["feed"] == 5
    assert len([e for e in farm.lever_log if e[1] == "feed"]) == 5


def test_bulk_button_disables_when_nothing_is_affordable(game_env):
    game_env.farm.funds = 5.0
    _click(game_env, "bulk-max-button")
    assert game_env.elements["grow-herd-button"].disabled is True
    assert game_env.elements["grow-herd-button"].innerText == "Grow Herd (20)"


def test_a_maxed_lever_says_so_in_bulk_mode(game_env):
    farm = game_env.farm
    farm.funds = 1000.0
    farm.decoupling_investment["capture"] = 9
    _click(game_env, "bulk-5-button")
    assert game_env.elements["capture-invest-button"].innerText == "Capture Systems (maxed out)"
    assert game_env.elements["capture-invest-button"].disabled is True


def test_bulk_note_shows_the_total_and_the_methane_effect(game_env):
    farm = game_env.farm
    farm.funds = 1000.0
    farm.herd_size = 2
    assert "x5" in game_env.elements["bulk-note"].innerText
    _click(game_env, "bulk-5-button")
    note = game_env.elements["bulk-note"].innerText
    assert "Grow Herd x5" in note and "herd 2" in note and "7" in note


# ---- F-20 round-delta chips ---------------------------------------------------------------
def test_chips_are_hidden_until_a_round_is_played(game_env):
    game_env.module.render()
    assert game_env.elements["round-delta-strip"].hidden is True


def test_chips_show_the_change_with_a_shape_and_a_sign(game_env):
    farm = game_env.farm
    farm.herd_size = 10
    farm.funds = 100.0
    before = farm.funds
    game_env.advance_round()
    assert game_env.elements["round-delta-strip"].hidden is False
    funds_text = game_env.elements["delta-chip-funds"].innerText
    assert funds_text.startswith("▲ Funds +") and f"{farm.funds - before:+.0f}" in funds_text
    assert game_env.elements["delta-chip-methane"].innerText.startswith("▲ Methane +10.0")
    assert game_env.elements["delta-chip-welfare"].innerText.startswith("■ Welfare +0")
    assert game_env.elements["delta-chip-pressure"].innerText.startswith("▲ Pressure +")


def test_a_falling_number_gets_a_down_triangle(game_env):
    m = game_env.module
    text = m.delta_chip_text("funds", -12.0)
    assert text == "▼ Funds -12"


def test_chips_fade_after_a_few_seconds_unless_pinned(game_env):
    farm = game_env.farm
    farm.herd_size = 5
    game_env.advance_round()
    _click(game_env, "delta-chip-funds")
    assert game_env.elements["delta-chip-funds"].getAttribute("aria-pressed") == "true"
    assert game_env.module.DELTA_FADE_MS in [delay for _cb, delay in game_env.timers.pending]
    game_env.timers.flush()
    assert game_env.elements["delta-chip-methane"].classList.contains("delta-chip--faded")
    assert not game_env.elements["delta-chip-funds"].classList.contains("delta-chip--faded")
    _click(game_env, "delta-chip-funds")  # unpin: it fades right away
    assert game_env.elements["delta-chip-funds"].classList.contains("delta-chip--faded")


def test_an_old_fade_timer_does_not_fade_newer_chips(game_env):
    game_env.farm.herd_size = 5
    game_env.advance_round()
    game_env.advance_round()
    first_timer = game_env.timers.pending[-2][0]
    first_timer()  # the first round's timer fires after the second round began
    assert not game_env.elements["delta-chip-methane"].classList.contains("delta-chip--faded")


def test_chips_are_not_saved(game_env):
    game_env.farm.herd_size = 5
    game_env.advance_round()
    assert "last_deltas" not in game_env.module.get_state()


# ---- GF-18 undo the last round -------------------------------------------------------------
def _play_a_round_after_buying(env):
    farm = env.farm
    farm.funds = 500.0
    farm.herd_size = 5
    env.invest_decoupling("feed")
    return farm


def test_undo_is_not_available_before_a_round_is_played(game_env):
    game_env.module.render()
    assert game_env.elements["undo-round-button"].disabled is True
    assert "after you advance a round" in game_env.elements["undo-note"].innerText
    assert game_env.module.undo_last_round() is False


def test_undo_rewinds_the_round_and_charges_the_fee(game_env):
    m = game_env.module
    farm = _play_a_round_after_buying(game_env)
    funds_at_start, methane_at_start = farm.funds, farm.methane
    game_env.advance_round()
    assert farm.round_number == 2
    assert game_env.elements["undo-round-button"].disabled is False
    assert m.undo_last_round() is True
    assert farm.round_number == 1
    assert farm.funds == funds_at_start - m.UNDO_PENALTY_FUNDS
    assert farm.methane == methane_at_start
    assert farm.funds_history == [farm.funds] or farm.funds_history[-1] == farm.funds
    assert len(farm.methane_history) == 1


def test_undo_works_once_per_game(game_env):
    m = game_env.module
    _play_a_round_after_buying(game_env)
    game_env.advance_round()
    assert m.undo_last_round() is True
    game_env.advance_round()
    assert game_env.elements["undo-round-button"].disabled is True
    assert m.undo_last_round() is False
    assert "used" in game_env.elements["undo-note"].innerText


def test_undo_also_undoes_purchases_made_after_the_round(game_env):
    m = game_env.module
    farm = _play_a_round_after_buying(game_env)
    game_env.advance_round()
    farm.funds = 500.0
    game_env.invest_decoupling("caps")
    assert farm.decoupling_investment["caps"] == 1
    m.undo_last_round()
    assert farm.decoupling_investment["caps"] == 0 and farm.decoupling_investment["feed"] == 1


def test_undo_restores_the_baseline_farm_too(game_env):
    m = game_env.module
    farm = _play_a_round_after_buying(game_env)
    baseline = (farm.counterfactual_funds, farm.counterfactual_methane)
    game_env.advance_round()
    assert (farm.counterfactual_funds, farm.counterfactual_methane) != baseline
    m.undo_last_round()
    assert (farm.counterfactual_funds, farm.counterfactual_methane) == baseline


def test_undo_keeps_legacy_points_and_collected_breeds(game_env):
    m = game_env.module
    _play_a_round_after_buying(game_env)
    game_env.advance_round()
    m.legacy_points = 3
    m.generation = 2
    m.breeds_collected.append("sage_grazer") if "sage_grazer" not in m.breeds_collected else None
    m.undo_last_round()
    assert m.legacy_points == 3 and m.generation == 2 and "sage_grazer" in m.breeds_collected


def test_undo_needs_enough_funds_for_the_fee(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 10.0
    game_env.advance_round()
    assert m.can_undo() is False
    assert game_env.elements["undo-round-button"].disabled is True
    assert "Not enough funds" in game_env.elements["undo-note"].innerText


def test_undo_used_is_saved_only_when_true(game_env):
    m = game_env.module
    _play_a_round_after_buying(game_env)
    assert "undo_used" not in m.get_state()
    game_env.advance_round()
    m.undo_last_round()
    state = m.get_state()
    assert state["undo_used"] is True
    m.load_state(json.loads(json.dumps(state)))
    assert game_env.farm.undo_used is True
    assert game_env.farm.undo_snapshot is None


def test_loading_a_save_clears_the_pending_undo(game_env):
    m = game_env.module
    _play_a_round_after_buying(game_env)
    game_env.advance_round()
    assert game_env.farm.undo_snapshot is not None
    m.load_state(m.get_state())
    assert game_env.farm.undo_snapshot is None
    assert game_env.elements["undo-round-button"].disabled is True


def test_a_handover_starts_a_new_game_with_a_fresh_undo(game_env):
    m = game_env.module
    _play_a_round_after_buying(game_env)
    game_env.advance_round()
    m.undo_last_round()
    game_env.farm.certified = True
    m.hand_over_farm()
    assert m.farm.undo_used is False and m.farm.undo_snapshot is None


# ---- F-21 season calendar ------------------------------------------------------------------
def test_calendar_is_hidden_when_variation_is_off(game_env):
    game_env.module.render()
    assert game_env.elements["season-calendar"].hidden is True


def test_calendar_lists_the_next_twelve_rounds_in_order(game_env):
    m = game_env.module
    game_env.farm.variation_enabled = True
    game_env.farm.round_number = 5
    cells = m.season_calendar_cells()
    assert [c["round"] for c in cells] == list(range(5, 17))
    for cell in cells:
        name, mod = m.season_for_round(cell["round"])
        assert (cell["name"], cell["mod"]) == (name, mod)
        assert cell["surge"] == m.demand_surge_active(cell["round"])


def test_calendar_cells_carry_shape_percent_and_surge_marks(game_env):
    m = game_env.module
    game_env.farm.variation_enabled = True
    m.render()
    page = game_env.elements["season-calendar"].innerHTML
    assert game_env.elements["season-calendar"].hidden is False
    assert page.count("<li ") == 12
    assert "season-cell--now" in page and "season-pct" in page
    assert any(mark in page for mark in ("▲", "▼", "■"))
    assert "plant-based demand surge" in page  # a surge falls inside any 12-round window


def test_calendar_follows_the_round(game_env):
    m = game_env.module
    game_env.farm.variation_enabled = True
    m.render()
    first = game_env.elements["season-calendar"].innerHTML
    game_env.advance_round()
    assert game_env.elements["season-calendar"].innerHTML != first


# ---- F-22 poultry vs cattle -----------------------------------------------------------------
def test_compare_rows_use_the_live_numbers(game_env):
    m = game_env.module
    game_env.farm.decoupling_investment["feed"] = 3
    rows = {label: (c, p) for label, c, p in m.poultry_compare_rows()}
    ratio = game_env.farm.coupling_ratio()
    assert rows["Methane-equivalent per unit"] == (f"{ratio:.2f}", f"{m.POULTRY_BASE_RATIO:.2f}")
    assert rows["Income per unit (before pressure)"][1].startswith(
        f"{m.POULTRY_INCOME_PER_UNIT - m.POULTRY_UPKEEP_PER_UNIT:.2f}")
    assert "welfare" in rows["Welfare effect"][1].lower()


def test_compare_card_is_a_labelled_table(game_env):
    game_env.module.render()
    card = game_env.elements["poultry-compare"].innerHTML
    assert "<caption>" in card and 'scope="col"' in card and 'scope="row"' in card
    assert "Cattle" in card and "Poultry" in card


def test_compare_card_follows_litter_and_biofilter_levers(game_env):
    farm = game_env.farm
    game_env.module.render()
    before = game_env.elements["poultry-compare"].innerHTML
    farm.poultry_investment["litter"] = 2
    game_env.module.render()
    assert game_env.elements["poultry-compare"].innerHTML != before


# ---- F-23 breeding rings -----------------------------------------------------------------
def test_no_ring_when_nothing_is_maturing(game_env):
    game_env.module.render()
    assert "No line maturing" in game_env.elements["genetics-rings"].innerHTML


def test_one_ring_per_line_with_rounds_left_written_in_it(game_env):
    m = game_env.module
    game_env.farm.funds = 500.0
    game_env.farm.invest_genetics()
    game_env.module.render()
    ring = game_env.elements["genetics-rings"].innerHTML
    assert ring.count("<svg") == 1
    assert f"{m.GENETICS_MATURE_ROUNDS} rounds left of {m.GENETICS_MATURE_ROUNDS}" in ring
    assert ">3</text>" in ring
    game_env.advance_round()
    ring = game_env.elements["genetics-rings"].innerHTML
    assert "2 rounds left" in ring and ">2</text>" in ring


def test_ring_fill_grows_each_round_and_the_last_round_says_round_singular(game_env):
    m = game_env.module
    game_env.farm.genetics_pending = [1]
    ring = m.genetics_rings_html()
    assert "1 round left" in ring and "1 rounds" not in ring
    fraction = (m.GENETICS_MATURE_ROUNDS - 1) / m.GENETICS_MATURE_ROUNDS
    import math
    assert f"{fraction * 2 * math.pi * 11:.2f}" in ring


def test_ring_disappears_once_the_line_matures(game_env):
    farm = game_env.farm
    farm.funds = 500.0
    farm.invest_genetics()
    for _ in range(game_env.module.GENETICS_MATURE_ROUNDS):
        game_env.advance_round()
    assert farm.genetics_active == 1
    assert "No line maturing" in game_env.elements["genetics-rings"].innerHTML


# ---- GF-13 named cows and the hall of fame -----------------------------------------------
def test_names_are_fixed_by_position_and_unique_in_a_generation(game_env):
    m = game_env.module
    names = [m.cow_name(i) for i in range(len(m.COW_NAMES) * 2)]
    assert len(set(names)) == len(names)
    assert names[0] == m.COW_NAMES[0] and names[len(m.COW_NAMES)].endswith(" II")
    assert [m.cow_name(i) for i in range(5)] == names[:5]  # same every time


def test_each_generation_starts_further_along_the_list(game_env):
    m = game_env.module
    assert m.cow_name(0, 1) != m.cow_name(0, 2)


def test_roster_counts_rounds_on_the_farm(game_env):
    farm = game_env.farm
    farm.funds = 1000.0
    game_env.grow_herd()
    game_env.advance_round()
    game_env.advance_round()
    game_env.grow_herd()
    roster = game_env.module.cow_roster()
    assert [served for _name, served in roster] == [2, 0]


def test_units_missing_from_the_log_count_from_round_one(game_env):
    farm = game_env.farm
    farm.herd_size = 4
    farm.round_number = 9
    assert farm.herd_unit_rounds() == [1, 1, 1, 1]
    assert [s for _n, s in game_env.module.cow_roster()] == [8, 8, 8, 8]


def test_pasture_cow_hover_names_the_animal(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.herd_size = 6
    farm.round_number = 4
    m.render()
    assert game_env.elements["pasture-cow-a"].title.startswith(m.cow_name(0))
    assert game_env.elements["pasture-cow-c"].title.startswith(m.cow_name(5))
    assert "animal #6" in game_env.elements["pasture-cow-c"].title
    farm.herd_size = 2
    m.render()
    assert game_env.elements["pasture-cow-c"].title == ""


def test_handover_honours_the_three_longest_serving(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 10000.0
    for _ in range(5):
        game_env.grow_herd()
        game_env.advance_round()
    farm.certified = True
    first_name = m.cow_name(0)
    m.hand_over_farm()
    assert len(m.hall_of_fame) == m.HALL_PER_HANDOVER
    assert m.hall_of_fame[0][0] == first_name and m.hall_of_fame[0][1] == 5
    assert [e[1] for e in m.hall_of_fame] == sorted((e[1] for e in m.hall_of_fame), reverse=True)
    assert all(e[2] == 1 for e in m.hall_of_fame)
    m.render()
    assert first_name in game_env.elements["hall-of-fame-list"].innerHTML


def test_hall_keeps_only_the_best_five(game_env):
    m = game_env.module
    for generation in range(1, 4):
        farm = game_env.module.farm
        farm.herd_size = 6
        farm.round_number = 10 * generation
        farm.certified = True
        m.hand_over_farm()
    assert len(m.hall_of_fame) == m.HALL_OF_FAME_SIZE
    assert m.hall_of_fame[0][1] >= m.hall_of_fame[-1][1]


def test_empty_hall_explains_itself(game_env):
    game_env.module.render()
    assert "No animals retired yet" in game_env.elements["hall-of-fame-list"].innerHTML


def test_hall_saves_only_when_it_has_entries_and_round_trips(game_env):
    m = game_env.module
    assert "hall_of_fame" not in m.get_state()
    m.hall_of_fame = [["Beyonmoo", 14, 1], ["Hay Z", 9, 2]]
    state = json.loads(json.dumps(m.get_state()))
    assert state["hall_of_fame"] == [["Beyonmoo", 14, 1], ["Hay Z", 9, 2]]
    m.hall_of_fame = []
    m.load_state(state)
    assert m.hall_of_fame == [["Beyonmoo", 14, 1], ["Hay Z", 9, 2]]


def test_bad_hall_data_is_dropped_and_names_are_escaped(game_env):
    m = game_env.module
    state = m.get_state()
    state["hall_of_fame"] = [
        "junk", [1, 2, 3], ["ok", "x", 1], ["ok", float("nan"), 1], ["<b>Bold</b>", 4, 1],
        ["x" * 100, 3, 2], ["neg", -5, 0], ["a", 1, 1], ["b", 1, 1], ["c", 1, 1], ["d", 1, 1],
    ]
    m.load_state(state)
    assert all(isinstance(e[0], str) and e[1] >= 0 and e[2] >= 1 for e in m.hall_of_fame)
    assert len(m.hall_of_fame) <= m.HALL_OF_FAME_SIZE
    page = m.hall_of_fame_html()
    assert "<b>" not in page and "&lt;b&gt;" in page
    assert all(len(e[0]) <= 40 for e in m.hall_of_fame)


def test_an_old_save_has_an_empty_hall(game_env):
    m = game_env.module
    state = m.get_state()
    state.pop("hall_of_fame", None)
    m.hall_of_fame = [["Old", 3, 1]]
    m.load_state(state)
    assert m.hall_of_fame == []


# ---- F-28 pace note and save nudge ----------------------------------------------------------
def test_no_pace_note_at_the_start(game_env):
    game_env.module.render()
    assert game_env.elements["pace-note"].hidden is True
    assert game_env.module.pace_note_message() == ""


def test_pace_note_counts_rounds_and_minutes(game_env):
    m = game_env.module
    m.session_started = m.time.time() - 125
    game_env.advance_round()
    assert game_env.elements["pace-note"].hidden is False
    assert game_env.elements["pace-note"].innerText == "This sitting: 1 round, about 2 min."
    game_env.advance_round()
    assert "2 rounds" in game_env.elements["pace-note"].innerText


def test_no_nudge_before_ten_rounds(game_env):
    for _ in range(9):
        game_env.advance_round()
    assert game_env.module.save_nudge_message() == ""
    assert game_env.elements["milestone-toast"].hidden is True


def test_nudge_every_ten_rounds_in_one_sitting(game_env):
    m = game_env.module
    for _ in range(10):
        game_env.advance_round()
    assert "10 rounds this sitting" in m.save_nudge_message()
    assert game_env.elements["milestone-toast"].hidden is False
    assert "save" in game_env.elements["milestone-toast-text"].innerText.lower()
    for _ in range(9):
        game_env.advance_round()
    assert m.save_nudge_message() == ""
    game_env.advance_round()
    assert "20 rounds this sitting" in m.save_nudge_message()


def test_loading_a_late_save_does_not_fire_the_nudge(game_env):
    m = game_env.module
    state = m.get_state()
    state["round_number"] = 40
    m.load_state(state)
    assert m.save_nudge_message() == ""


def test_nudge_joins_a_streak_toast_instead_of_replacing_it(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.seen_half_decoupled_callout = farm.seen_pressure_callout = farm.seen_methane_penalty_nudge = True
    farm.funds = 5000.0
    farm.herd_size = 10
    game_env.advance_round()
    game_env.invest_decoupling("capture")
    game_env.advance_round()
    game_env.invest_decoupling("capture")
    game_env.advance_round()
    assert farm.perfect_streak == 2
    m.session_rounds = 9  # the next round is the tenth of this sitting
    game_env.invest_decoupling("capture")
    game_env.advance_round()
    assert farm.perfect_streak == 3
    text = game_env.elements["milestone-toast-text"].innerText
    assert "streak of 3" in text and "10 rounds this sitting" in text
