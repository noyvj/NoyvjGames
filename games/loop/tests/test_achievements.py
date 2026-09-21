"""Tests for the ACHIEVEMENTS-SYSTEM-DESIGN.md rollout to Loop: the
achievements.json catalog, the checkers/progress readouts in game.py, the
in-game toggle/panel, and the unlock toast + hub-dashboard link (the
site-wide "on top of the base rollout" requirements from
planning/TODO.md). Every achievement's earned status is meant to be a
pure function of state that already exists elsewhere in this module --
these tests exercise that by driving the real game systems (investing,
trading, advancing cycles, resetting the chain) rather than poking an
`_earned` flag that doesn't exist.

Also covers the H3/H12/H18 reactive-effect wiring (loop-closed banner,
funds-burst pulse, trade-network pulse) that shares the same
`_run_action`/timer plumbing as the achievement toast.
"""


def _close_the_loop(game_env, units=10):
    """Invest enough Recycling Loops (5.0 supply/unit) to exactly clear
    PRODUCTION_TARGET (50.0) -- a fully closed loop with zero surplus,
    so exportable_surplus() stays 0 and doesn't complicate funds math in
    tests that don't care about trade revenue."""
    game_env.chain.funds = 100_000
    for _ in range(units):
        game_env.chain.invest_circularity("recycle")


# --- the catalog itself -----------------------------------------------


def test_achievements_catalog_loads_from_json_with_a_reasonable_count(game_env):
    module = game_env.module
    assert 5 <= len(module.ACHIEVEMENTS) <= 30
    ids = [entry["id"] for entry in module.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))  # no duplicate ids


def test_every_catalog_entry_has_a_matching_checker(game_env):
    module = game_env.module
    for entry in module.ACHIEVEMENTS:
        assert entry["id"] in module.ACHIEVEMENT_CHECKS
        assert callable(module.ACHIEVEMENT_CHECKS[entry["id"]])


def test_every_progress_entry_refers_to_a_real_achievement(game_env):
    module = game_env.module
    catalog_ids = {entry["id"] for entry in module.ACHIEVEMENTS}
    assert set(module.ACHIEVEMENT_PROGRESS).issubset(catalog_ids)


# --- nothing earned on a fresh game ------------------------------------


def test_nothing_is_earned_on_a_fresh_game(game_env):
    assert game_env.module.achievement_ids_earned() == []


def test_summary_shows_every_entry_as_not_earned_initially(game_env):
    summary = game_env.module.achievements_summary()
    assert len(summary) == len(game_env.module.ACHIEVEMENTS)
    assert all(entry["earned"] is False for entry in summary)


# --- individual achievements, driven through real game systems --------


def test_first_fix_earned_after_any_first_circularity_investment(game_env):
    assert "first_fix" not in game_env.module.achievement_ids_earned()
    game_env.chain.invest_circularity("repair")
    assert "first_fix" in game_env.module.achievement_ids_earned()


def test_full_toolkit_requires_all_three_measures(game_env):
    module = game_env.module
    game_env.chain.invest_circularity("repair")
    game_env.chain.invest_circularity("reuse")
    assert "full_toolkit" not in module.achievement_ids_earned()
    game_env.chain.invest_circularity("recycle")
    assert "full_toolkit" in module.achievement_ids_earned()


def test_trade_partner_earned_by_either_partner(game_env):
    assert "trade_partner" not in game_env.module.achievement_ids_earned()
    game_env.chain.invest_trade_link()
    assert "trade_partner" in game_env.module.achievement_ids_earned()


def test_trade_partner_earned_via_regional_distributor_too(game_env):
    game_env.chain.funds = 1000
    assert "trade_partner" not in game_env.module.achievement_ids_earned()
    game_env.chain.invest_regional_trade()
    assert "trade_partner" in game_env.module.achievement_ids_earned()


def test_dual_sourcing_requires_both_trade_partners(game_env):
    module = game_env.module
    game_env.chain.funds = 1000
    game_env.chain.invest_trade_link()
    assert "dual_sourcing" not in module.achievement_ids_earned()
    game_env.chain.invest_regional_trade()
    assert "dual_sourcing" in module.achievement_ids_earned()


def test_fraction_tier_achievements_at_25_50_75_100_percent(game_env):
    module = game_env.module
    game_env.chain.funds = 100_000
    # 2 recycle units -> 10/50 = 20%, below the first tier.
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_circularity("recycle")
    earned = module.achievement_ids_earned()
    assert "quarter_loop" not in earned
    # 3 recycle units -> 15/50 = 30%, clears quarter_loop only.
    game_env.chain.invest_circularity("recycle")
    earned = module.achievement_ids_earned()
    assert "quarter_loop" in earned
    assert "half_loop" not in earned
    # 5 recycle units -> 25/50 = 50%, clears half_loop too.
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_circularity("recycle")
    earned = module.achievement_ids_earned()
    assert "half_loop" in earned
    assert "three_quarter_loop" not in earned
    # 10 recycle units -> 50/50 = 100%, closes the loop entirely.
    for _ in range(5):
        game_env.chain.invest_circularity("recycle")
    earned = module.achievement_ids_earned()
    assert "three_quarter_loop" in earned
    assert "loop_closed" in earned


def test_lifetime_majority_needs_both_the_fraction_and_the_cycle_count(game_env):
    module = game_env.module
    _close_the_loop(game_env)
    for _ in range(4):
        game_env.chain.advance_cycle()
    assert "lifetime_majority" not in module.achievement_ids_earned()  # only 4 cycles
    game_env.chain.advance_cycle()
    assert "lifetime_majority" in module.achievement_ids_earned()  # 5 cycles, 100% lifetime


def test_beyond_benchmark_compares_against_the_real_world_figure(game_env):
    module = game_env.module
    assert "beyond_benchmark" not in module.achievement_ids_earned()
    _close_the_loop(game_env)
    game_env.chain.advance_cycle()
    assert module.chain.lifetime_circular_fraction() > module.REAL_WORLD_CIRCULARITY_BENCHMARK
    assert "beyond_benchmark" in module.achievement_ids_earned()


def test_first_export_and_trade_surplus_500(game_env):
    module = game_env.module
    # 11 recycle units -> 55/cycle, 5 units over PRODUCTION_TARGET (50)
    # sold outward every cycle at EXPORT_PRICE_PER_UNIT (3.0) = 15/cycle.
    game_env.chain.funds = 100_000
    for _ in range(11):
        game_env.chain.invest_circularity("recycle")
    assert "first_export" not in module.achievement_ids_earned()
    game_env.chain.advance_cycle()
    assert module.chain.lifetime_export_revenue > 0.0
    assert "first_export" in module.achievement_ids_earned()
    assert "trade_surplus_500" not in module.achievement_ids_earned()
    for _ in range(40):  # comfortably clears the 500 lifetime-export target
        game_env.chain.advance_cycle()
    assert "trade_surplus_500" in module.achievement_ids_earned()


def test_streak_5_and_streak_10_track_best_ever_closed_loop_run(game_env):
    module = game_env.module
    _close_the_loop(game_env)
    for _ in range(5):
        game_env.chain.advance_cycle()
    assert module.chain.closed_loop_streak == 5
    assert "streak_5" in module.achievement_ids_earned()
    assert "streak_10" not in module.achievement_ids_earned()
    for _ in range(5):
        game_env.chain.advance_cycle()
    assert "streak_10" in module.achievement_ids_earned()


def test_streak_achievement_stays_earned_after_the_streak_breaks(game_env):
    module = game_env.module
    _close_the_loop(game_env)
    for _ in range(5):
        game_env.chain.advance_cycle()
    assert "streak_5" in module.achievement_ids_earned()
    # Breaking the streak (a straight-line cycle) resets the *current*
    # streak but best_closed_loop_streak -- what streak_5 is keyed off
    # of -- stays sticky.
    game_env.chain.circularity_investment["recycle"] = 0
    game_env.chain.advance_cycle()
    assert module.chain.closed_loop_streak == 0
    assert module.chain.best_closed_loop_streak == 5
    assert "streak_5" in module.achievement_ids_earned()


def test_clean_hands_requires_ten_cycles_with_zero_lifetime_extraction(game_env):
    module = game_env.module
    _close_the_loop(game_env)
    for _ in range(9):
        game_env.chain.advance_cycle()
    assert "clean_hands" not in module.achievement_ids_earned()  # only 9 cycles
    game_env.chain.advance_cycle()
    assert module.chain.total_extracted == 0.0
    assert "clean_hands" in module.achievement_ids_earned()


def test_clean_hands_is_never_earned_after_any_real_extraction(game_env):
    module = game_env.module
    game_env.chain.funds = 100_000
    for _ in range(10):
        game_env.chain.advance_cycle()  # straight-line: extraction every cycle
    assert module.chain.total_extracted > 0.0
    assert "clean_hands" not in module.achievement_ids_earned()


def test_capital_committed_tracks_lifetime_investment_spend(game_env):
    module = game_env.module
    game_env.chain.funds = 100_000
    assert "capital_committed" not in module.achievement_ids_earned()
    for _ in range(11):  # 11 * 30 = 330 >= CAPITAL_COMMITTED_TARGET (300)
        game_env.chain.invest_circularity("recycle")
    assert module.chain.lifetime_investment_spend >= module.CAPITAL_COMMITTED_TARGET
    assert "capital_committed" in module.achievement_ids_earned()


def test_score_pragmatist_and_score_master_need_score_fraction_and_cycles(game_env):
    module = game_env.module
    _close_the_loop(game_env)
    for _ in range(9):
        game_env.chain.advance_cycle()
    assert "score_pragmatist" not in module.achievement_ids_earned()  # only 9 cycles
    game_env.chain.advance_cycle()  # 10 cycles, fraction 1.0, score comfortably > 1000
    assert module.chain.score() >= module.SCORE_PRAGMATIST_TARGET
    assert "score_pragmatist" in module.achievement_ids_earned()
    assert "score_master" not in module.achievement_ids_earned()  # needs 15 cycles
    for _ in range(5):
        game_env.chain.advance_cycle()
    assert module.chain.score() >= module.SCORE_MASTER_TARGET
    assert "score_master" in module.achievement_ids_earned()


def test_serial_redesigner_counts_start_new_chain_uses(game_env):
    module = game_env.module
    assert "serial_redesigner" not in module.achievement_ids_earned()
    game_env.reset_chain()
    assert "serial_redesigner" not in module.achievement_ids_earned()  # only 1 so far
    game_env.reset_chain()
    assert module.chains_completed_count == 2
    assert "serial_redesigner" in module.achievement_ids_earned()


def test_goods_explorer_counts_distinct_categories_played(game_env):
    module = game_env.module
    assert "goods_explorer" not in module.achievement_ids_earned()
    game_env.select_goods_category("clothing")
    assert module.goods_categories_tried == {"electronics", "clothing"}
    assert "goods_explorer" in module.achievement_ids_earned()


# --- progress readouts --------------------------------------------------


def test_progress_readout_shape_for_full_toolkit(game_env):
    module = game_env.module
    game_env.chain.invest_circularity("repair")
    current, target = module.ACHIEVEMENT_PROGRESS["full_toolkit"]()
    assert current == 1
    assert target == len(module.CIRCULARITY_INVESTMENTS)


def test_progress_readout_for_streak_5_caps_at_target(game_env):
    module = game_env.module
    _close_the_loop(game_env)
    for _ in range(8):  # more than the target of 5
        game_env.chain.advance_cycle()
    current, target = module.ACHIEVEMENT_PROGRESS["streak_5"]()
    assert current == target == module.STREAK_5_TARGET


def test_progress_readout_for_goods_explorer(game_env):
    module = game_env.module
    current, target = module.ACHIEVEMENT_PROGRESS["goods_explorer"]()
    assert current == 1
    assert target == module.GOODS_EXPLORER_TARGET


# --- no mutation as a side effect ---------------------------------------


def test_checking_achievements_never_mutates_other_state(game_env):
    module = game_env.module
    game_env.chain.invest_circularity("repair")
    game_env.chain.invest_trade_link()
    before = module.get_state()
    module.achievement_ids_earned()
    module.achievement_ids_earned()
    module.achievements_summary()
    after = module.get_state()
    before.pop("achievements_earned")
    after.pop("achievements_earned")
    assert before == after


# --- toggle / panel ------------------------------------------------------


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def test_achievements_panel_is_hidden_by_default(game_env):
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_opens_and_closes_the_panel(game_env):
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is False
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_button_shows_earned_over_total_count(game_env):
    module = game_env.module
    game_env.chain.invest_circularity("repair")  # earns first_fix
    game_env.toggle_achievements()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert f"1/{len(module.ACHIEVEMENTS)}" in text or f"(1/{len(module.ACHIEVEMENTS)})" in text


def test_panel_renders_every_catalog_entrys_label_and_description(game_env):
    module = game_env.module
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    rendered = " ".join(text for card in panel.children for text in _all_texts(card))
    for entry in module.ACHIEVEMENTS:
        assert entry["label"] in rendered
        assert entry["description"] in rendered


def test_earned_card_is_marked_distinctly(game_env):
    game_env.chain.invest_circularity("repair")
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    earned_cards = [c for c in panel.children if "achievement-card--earned" in getattr(c, "className", "")]
    assert len(earned_cards) == 1


def test_panel_includes_a_link_to_the_hub_dashboard(game_env):
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    links = [c for c in panel.children if getattr(c, "className", "") == "achievements-hub-link"]
    assert len(links) == 1
    assert "index.html#account-achievements-dashboard" in links[0].href


def test_panel_stays_live_across_advance_cycle(game_env):
    game_env.toggle_achievements()
    game_env.chain.invest_circularity("repair")
    game_env.elements["advance-cycle-button"].dispatch("click", None)
    text = game_env.elements["achievements-toggle-button"].innerText
    assert "1/" in text


# --- unlock toast --------------------------------------------------------


def test_toast_shows_on_a_newly_earned_achievement(game_env):
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is True
    game_env.invest_circularity("repair")  # click-dispatched -> runs through _run_action
    assert toast.hidden is False
    assert "First Fix" in game_env.elements["achievement-toast-text"].innerText


def test_toast_auto_hides_after_its_timer_fires(game_env):
    game_env.invest_circularity("repair")
    assert game_env.elements["achievement-toast"].hidden is False
    game_env.timers.flush()
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_does_not_refire_for_an_already_earned_achievement(game_env):
    game_env.invest_circularity("repair")
    game_env.timers.flush()
    game_env.elements["achievement-toast"].hidden = True  # simulate it having closed
    game_env.invest_circularity("repair")  # first_fix already earned; nothing new
    assert game_env.elements["achievement-toast"].hidden is True


def test_loading_a_save_with_earned_achievements_does_not_flood_toasts(game_env):
    module = game_env.module
    game_env.chain.invest_circularity("repair")
    game_env.chain.invest_circularity("reuse")
    snapshot = module.get_state()
    game_env.elements["achievement-toast"].hidden = True  # reset from the direct calls above

    module.load_state(snapshot)

    assert game_env.elements["achievement-toast"].hidden is True


# --- H3: first-time-closed-loop banner ------------------------------------


def test_loop_closed_banner_fires_only_on_the_false_to_true_transition(game_env):
    banner = game_env.elements["loop-closed-banner"]
    game_env.chain.funds = 100_000
    for _ in range(9):
        game_env.invest_circularity("recycle")
    assert banner.hidden is True  # 45/50, not closed yet
    game_env.invest_circularity("recycle")  # 10th unit closes the loop
    assert banner.hidden is False
    banner.hidden = True  # simulate it auto-hiding
    game_env.invest_circularity("recycle")  # already closed -- no re-fire
    assert banner.hidden is True


def test_loop_closed_banner_auto_hides_after_its_timer_fires(game_env):
    game_env.chain.funds = 100_000
    for _ in range(10):
        game_env.invest_circularity("recycle")
    banner = game_env.elements["loop-closed-banner"]
    assert banner.hidden is False
    game_env.timers.flush()
    assert banner.hidden is True


# --- H13 audit fix (planning/TODO.md V-E-5): banner/toast never overlap ---


def test_achievement_toast_is_held_back_while_loop_closed_banner_is_showing(game_env):
    """Closing the loop for the first time earns the 'loop_closed'
    achievement in the exact same action that fires the H3 banner -- the
    two must not both be on screen at once. The banner should show right
    away; the achievement toast for that same action must stay hidden
    until the banner's own visible window has elapsed."""
    module = game_env.module
    banner = game_env.elements["loop-closed-banner"]
    toast = game_env.elements["achievement-toast"]
    game_env.chain.funds = 100_000
    for _ in range(9):
        game_env.invest_circularity("recycle")
    # Reset both to a clean slate regardless of whatever earlier
    # investment-click toast (e.g. "first_fix") may still be showing --
    # what this test cares about is the state transition caused by the
    # 10th click below, not anything that happened before it.
    banner.hidden = True
    toast.hidden = True

    game_env.invest_circularity("recycle")  # 10th unit closes the loop

    assert banner.hidden is False  # banner fires immediately
    assert toast.hidden is True  # toast deliberately held back, not shown at the same time
    # The delayed toast is queued for exactly the banner's own visible
    # duration, not some arbitrary/shorter gap that could still overlap.
    assert any(delay == module.LOOP_CLOSED_BANNER_DURATION_MS for _cb, delay in game_env.timers.pending)

    game_env.timers.flush()  # runs the banner's auto-hide timer + the toast's delayed show

    assert banner.hidden is True
    assert toast.hidden is False
    assert "Full Circle" in game_env.elements["achievement-toast-text"].innerText

    game_env.timers.flush()  # the now-visible toast's own auto-hide timer
    assert toast.hidden is True


def test_achievement_toast_still_shows_immediately_when_loop_does_not_close(game_env):
    """The delay is specific to the loop-closing transition -- an ordinary
    achievement earned any other way still shows its toast right away, no
    regression from the H13 sequencing fix."""
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is True
    game_env.invest_circularity("repair")  # earns "first_fix", loop stays open
    assert toast.hidden is False
    assert game_env.elements["loop-closed-banner"].hidden is True


# --- H12/H18: funds-burst / trade-network reactive pulses -----------------


def test_funds_display_bursts_when_export_revenue_is_earned(game_env):
    funds_el = game_env.elements["funds-display"]
    game_env.chain.funds = 100_000
    for _ in range(11):  # over-supplies -> exportable surplus every cycle
        game_env.invest_circularity("recycle")
    assert not funds_el.classList.contains("funds-display--burst")
    game_env.elements["advance-cycle-button"].dispatch("click", None)
    assert funds_el.classList.contains("funds-display--burst")
    game_env.timers.flush()
    assert not funds_el.classList.contains("funds-display--burst")


def test_trade_network_display_pulses_when_its_numbers_change(game_env):
    trade_el = game_env.elements["trade-network-display"]
    game_env.chain.funds = 1000
    assert not trade_el.classList.contains("trade-network-display--pulse")
    game_env.invest_trade_link()
    assert trade_el.classList.contains("trade-network-display--pulse")
    game_env.timers.flush()
    assert not trade_el.classList.contains("trade-network-display--pulse")
