"""Canopy's own achievements catalog (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md,
"roll achievements out everywhere" in planning/TODO.md). SOL is the
reference integration; this exercises the same shape against Canopy's real
mechanics (plot management, biodiversity, community relations) rather than
poking synthetic flags."""


def _ids(entries):
    return {entry["id"] for entry in entries}


# --- Catalog sanity -----------------------------------------------------


def test_catalog_loaded_and_nonempty(game_env):
    m = game_env.module
    assert 5 <= len(m.ACHIEVEMENTS) <= 30


def test_every_catalog_id_is_unique(game_env):
    m = game_env.module
    ids = [entry["id"] for entry in m.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))


def test_every_catalog_id_has_a_checker(game_env):
    m = game_env.module
    for entry in m.ACHIEVEMENTS:
        assert entry["id"] in m.ACHIEVEMENT_CHECKS, entry["id"]


def test_every_progress_id_refers_to_a_real_achievement(game_env):
    m = game_env.module
    catalog_ids = _ids(m.ACHIEVEMENTS)
    for progress_id in m.ACHIEVEMENT_PROGRESS:
        assert progress_id in catalog_ids


def test_nothing_earned_on_a_fresh_game(game_env):
    m = game_env.module
    assert m.achievement_ids_earned() == []


# --- Individual achievements, driven through real game actions ----------


def test_first_clear(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    assert "first_clear" in m.achievement_ids_earned()


def test_first_replant(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    game_env.select(0)
    game_env.replant()
    assert "first_replant" in m.achievement_ids_earned()


def test_first_recovery(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    game_env.select(0)
    game_env.replant()
    game_env.tick(m.RECOVERY_TICKS)
    assert m.plots[0].state == m.RECOVERED
    assert "first_recovery" in m.achievement_ids_earned()


def test_standing_tall_needs_full_maturity(game_env):
    m = game_env.module
    game_env.tick(m.MATURITY_TICKS - 1)
    assert "standing_tall" not in m.achievement_ids_earned()
    game_env.tick(1)
    assert "standing_tall" in m.achievement_ids_earned()


def test_old_growth_grove_needs_five_mature_plots(game_env):
    m = game_env.module
    game_env.tick(m.MATURITY_TICKS)
    # Every plot starts PRESERVED and ticks in lockstep, so a plain
    # full-grid tick already matures all 36 at once -- well over 5.
    assert "old_growth_grove" in m.achievement_ids_earned()
    current, target = m.ACHIEVEMENT_PROGRESS["old_growth_grove"]()
    assert current >= target == m.OLD_GROWTH_GROVE_MATURE_COUNT


def test_wildlife_returns(game_env):
    m = game_env.module
    ticks_needed = int(m.BIODIVERSITY_WILDLIFE_THRESHOLD / m.BIODIVERSITY_ACCRUAL_PER_TICK) + 1
    game_env.tick(ticks_needed)
    assert any(p.has_wildlife() for p in m.plots)
    assert "wildlife_returns" in m.achievement_ids_earned()


def test_wildlife_returns_persists_after_the_plot_is_cleared(game_env):
    """plots_with_wildlife_ever must survive the source plot's biodiversity
    resetting to 0 on clear -- the whole reason this needed new tracked
    state instead of a live has_wildlife() scan."""
    m = game_env.module
    ticks_needed = int(m.BIODIVERSITY_WILDLIFE_THRESHOLD / m.BIODIVERSITY_ACCRUAL_PER_TICK) + 1
    game_env.tick(ticks_needed)
    assert m.plots[0].has_wildlife()
    game_env.select(0)
    game_env.clear()
    assert not m.plots[0].has_wildlife()
    assert "wildlife_returns" in m.achievement_ids_earned()


def test_biodiversity_haven_needs_ten_plots_with_active_wildlife(game_env):
    m = game_env.module
    ticks_needed = int(m.BIODIVERSITY_WILDLIFE_THRESHOLD / m.BIODIVERSITY_ACCRUAL_PER_TICK) + 1
    game_env.tick(ticks_needed)
    assert sum(1 for p in m.plots if p.has_wildlife()) >= 10
    assert "biodiversity_haven" in m.achievement_ids_earned()


def test_thriving_forest_total_biodiversity_threshold(game_env):
    m = game_env.module
    ticks_needed = int(
        m.THRIVING_FOREST_BIODIVERSITY_THRESHOLD / (36 * m.BIODIVERSITY_ACCRUAL_PER_TICK)
    ) + 1
    game_env.tick(ticks_needed)
    assert m.total_biodiversity() >= m.THRIVING_FOREST_BIODIVERSITY_THRESHOLD
    assert "thriving_forest" in m.achievement_ids_earned()


def test_standing_fortune_threshold(game_env):
    m = game_env.module
    for plot in m.plots:
        plot.value = m.STANDING_FORTUNE_THRESHOLD
    assert "standing_fortune" in m.achievement_ids_earned()


def test_quick_money_threshold(game_env):
    m = game_env.module
    m.total_income = m.QUICK_MONEY_THRESHOLD
    assert "quick_money" in m.achievement_ids_earned()


def test_balanced_ledger_needs_both_sides(game_env):
    m = game_env.module
    m.total_income = m.BALANCED_LEDGER_THRESHOLD
    m.plots[0].value = 0  # standing value still short
    assert "balanced_ledger" not in m.achievement_ids_earned()
    for plot in m.plots:
        plot.value = m.BALANCED_LEDGER_THRESHOLD
    assert "balanced_ledger" in m.achievement_ids_earned()


def test_true_conservationist_requires_zero_clears(game_env):
    m = game_env.module
    for plot in m.plots:
        plot.value = m.TRUE_CONSERVATIONIST_STANDING_THRESHOLD
    assert "true_conservationist" in m.achievement_ids_earned()
    game_env.select(0)
    game_env.clear()
    for plot in m.plots:
        plot.value = m.TRUE_CONSERVATIONIST_STANDING_THRESHOLD
    assert "true_conservationist" not in m.achievement_ids_earned()


def test_resourceful_extractor_counts_clears_across_the_forest(game_env):
    m = game_env.module
    for i in range(m.RESOURCEFUL_EXTRACTOR_CLEAR_COUNT):
        idx = i % len(m.plots)
        m.plots[idx].state = m.PRESERVED
        game_env.select(idx)
        game_env.clear()
    assert "resourceful_extractor" in m.achievement_ids_earned()


def test_soil_scarred_same_plot_five_times(game_env):
    m = game_env.module
    for _ in range(m.SOIL_SCARRED_CLEAR_COUNT):
        m.plots[0].state = m.PRESERVED
        m.plots[0].value = 1.0
        game_env.select(0)
        game_env.clear()
    assert m.plots[0].clear_count == m.SOIL_SCARRED_CLEAR_COUNT
    assert "soil_scarred" in m.achievement_ids_earned()


def test_community_ally_max_relations(game_env):
    m = game_env.module
    m.community_relations = 100
    assert "community_ally" in m.achievement_ids_earned()


def test_rebuilt_trust_needs_a_real_low_point_first(game_env):
    m = game_env.module
    m.community_relations = 60
    assert "rebuilt_trust" not in m.achievement_ids_earned()
    # Drive relations down for real via decline_stakeholder_request (not by
    # poking community_relations_min_ever directly) so this exercises the
    # actual code path that maintains it.
    for _ in range(10):
        m.plots[0].state = m.PRESERVED
        m.plots[0].value = 1.0
        m.pending_stakeholder_request = {"plot_index": 0, "reason": "housing"}
        game_env.decline_stakeholder()
    assert m.community_relations_min_ever <= m.REBUILT_TRUST_LOW_WATERMARK
    m.community_relations = m.REBUILT_TRUST_HIGH_WATERMARK
    assert "rebuilt_trust" in m.achievement_ids_earned()


def test_generous_host_ten_grants(game_env):
    m = game_env.module
    for _ in range(m.GENEROUS_HOST_GRANT_COUNT):
        m.plots[0].state = m.PRESERVED
        m.plots[0].value = 1.0
        m.pending_stakeholder_request = {"plot_index": 0, "reason": "housing"}
        game_env.grant_stakeholder()
    assert m.stakeholder_grants_count == m.GENEROUS_HOST_GRANT_COUNT
    assert "generous_host" in m.achievement_ids_earned()


def test_principled_refusal_ten_declines(game_env):
    m = game_env.module
    for _ in range(m.PRINCIPLED_REFUSAL_DECLINE_COUNT):
        m.plots[0].state = m.PRESERVED
        m.plots[0].value = 1.0
        m.pending_stakeholder_request = {"plot_index": 0, "reason": "housing"}
        game_env.decline_stakeholder()
    assert m.stakeholder_declines_count == m.PRINCIPLED_REFUSAL_DECLINE_COUNT
    assert "principled_refusal" in m.achievement_ids_earned()


def test_flourishing_canopy_needs_no_bare_or_replanting_plus_value(game_env):
    m = game_env.module
    for plot in m.plots:
        plot.value = m.FLOURISHING_CANOPY_STANDING_THRESHOLD
    assert "flourishing_canopy" in m.achievement_ids_earned()
    m.plots[0].state = m.BARE
    assert "flourishing_canopy" not in m.achievement_ids_earned()


def test_every_stage_at_once(game_env):
    m = game_env.module
    m.plots[0].state = m.BARE
    m.plots[1].state = m.REPLANTING
    m.plots[2].state = m.RECOVERED
    m.plots[3].state = m.PRESERVED
    assert "every_stage_at_once" in m.achievement_ids_earned()


# --- Progress readouts ----------------------------------------------------


def test_progress_readout_shape(game_env):
    m = game_env.module
    m.total_income = 250
    current, target = m.ACHIEVEMENT_PROGRESS["quick_money"]()
    assert current == 250
    assert target == int(m.QUICK_MONEY_THRESHOLD)


# --- No-mutation guarantee -------------------------------------------------


def test_checking_achievements_never_mutates_other_state(game_env):
    m = game_env.module
    game_env.tick(5)
    before = m.get_state()
    m.achievement_ids_earned()
    m.achievements_summary()
    after = m.get_state()
    # achievements_earned is deliberately always-fresh; everything else
    # must be byte-identical.
    before.pop("achievements_earned")
    after.pop("achievements_earned")
    assert before == after


# --- Panel toggle/render ---------------------------------------------------


def test_achievements_panel_hidden_by_default(game_env):
    assert game_env.elements["achievements-panel"].hidden is True


def test_achievements_panel_toggle_opens_and_closes(game_env):
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is False
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is True


def test_achievements_toggle_button_shows_earned_count(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    game_env.toggle_achievements()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert f"1/{len(m.ACHIEVEMENTS)}" in text


def test_achievements_panel_renders_every_catalog_entry(game_env):
    m = game_env.module
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    assert len(panel.children) == len(m.ACHIEVEMENTS) + 1  # +1 for the hub-dashboard link


def test_achievements_panel_marks_an_earned_card_distinctly(game_env):
    game_env.select(0)
    game_env.clear()
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    earned_cards = [c for c in panel.children if "achievement-card--earned" in c.className]
    assert len(earned_cards) == 1


def test_achievements_panel_includes_hub_dashboard_link(game_env):
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    assert any(getattr(child, "href", None) == "../../index.html#account-achievements-dashboard" for child in panel.children)


def test_achievements_panel_stays_live_across_a_tick(game_env):
    m = game_env.module
    game_env.toggle_achievements()
    game_env.tick(m.MATURITY_TICKS)
    text = game_env.elements["achievements-toggle-button"].innerText
    earned = len(m.achievement_ids_earned())
    assert f"{earned}/{len(m.ACHIEVEMENTS)}" in text


# --- Unlock toast -----------------------------------------------------------


def test_toast_fires_on_a_fresh_unlock(game_env):
    game_env.select(0)
    game_env.clear()
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    assert "First Harvest" in toast.innerText


def test_toast_does_not_fire_for_already_earned_achievements(game_env):
    # A tick first, so the cleared plot actually holds a nonzero payout --
    # clearing at tick 0 would pay out 0.0, which never beats a starting
    # personal_best of 0.0 and so wouldn't schedule Z6's flash at all. That
    # tick schedules its own unrelated value-pop timer, so clear it out
    # before counting the ones the clear itself schedules.
    game_env.tick(1)
    game_env.timers.pending.clear()
    game_env.select(0)
    game_env.clear()
    # Two timers from this one real unlock: the achievement toast's
    # auto-hide, plus Z6's personal-best badge flash (this clear's income
    # beats the session's starting personal_best of zero).
    assert len(game_env.timers.pending) == 2

    # A second, unrelated render (a plain tick) must not re-toast
    # first_clear, and must not re-flash the personal-best badge either
    # (nothing new was beaten) -- only genuinely *new* events should
    # schedule timers, so no third timeout should get scheduled.
    game_env.tick(1)
    assert len(game_env.timers.pending) == 2


def test_no_toast_on_a_freshly_booted_game(game_env):
    # setup() itself calls render() once; that alone must never fire a
    # toast (there is nothing "new" about a fresh game's own zero
    # achievements).
    assert game_env.elements["achievement-toast"].hidden is True


def test_load_state_resets_toast_baseline_so_earned_saves_do_not_spam(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    data = m.get_state()
    assert "first_clear" in data["achievements_earned"]

    # Loading a save whose achievements_earned already includes
    # "first_clear" must not toast it again -- it's not a *new* unlock in
    # this render cycle, it's already-true state being restored. The one
    # real unlock (the clear() above) already scheduled exactly one
    # auto-hide timeout; load_state() must not schedule a second.
    assert len(game_env.timers.pending) == 1
    m.load_state(data)
    assert len(game_env.timers.pending) == 1


# --- Save/load round-trip of achievements' own new tracked state ----------


def test_new_tracked_fields_round_trip_through_save_load(game_env):
    m = game_env.module
    for _ in range(3):
        m.plots[0].state = m.PRESERVED
        m.plots[0].value = 1.0
        m.pending_stakeholder_request = {"plot_index": 0, "reason": "housing"}
        game_env.grant_stakeholder()
    game_env.select(1)
    game_env.clear()
    game_env.select(1)
    game_env.replant()
    game_env.tick(m.RECOVERY_TICKS)

    data = m.get_state()
    m.load_state(data)

    assert m.total_replants == data["total_replants"]
    assert m.total_recoveries == data["total_recoveries"]
    assert m.stakeholder_grants_count == data["stakeholder_grants_count"]
    assert set(m.plots_with_wildlife_ever) == set(data["plots_with_wildlife_ever"])


def test_old_save_missing_achievement_fields_does_not_crash(game_env):
    """A save written before this feature shipped lacks every new key --
    load_state() must fall back to current live values instead of
    KeyError-ing, same defensive convention as every other field here."""
    m = game_env.module
    old_save = {
        "plots": [],
        "selected_index": None,
        "total_income": 5.0,
        "community_relations": 50,
        "pending_stakeholder_request": None,
        "_ticks_since_last_request": 0,
        "_stakeholder_request_count": 0,
        "info_page_open": False,
    }
    assert m.load_state(old_save) is True
    assert m.total_replants == 0
    assert m.total_recoveries == 0
    assert m.plots_with_wildlife_ever == set()


def test_achievements_earned_is_never_read_back_on_load(game_env):
    m = game_env.module
    save_claiming_everything_earned = m.get_state()
    save_claiming_everything_earned["achievements_earned"] = [
        entry["id"] for entry in m.ACHIEVEMENTS
    ]
    m.load_state(save_claiming_everything_earned)
    # Nothing about the fresh game's real state changed, so the freshly
    # recomputed earned list must still be empty regardless of what the
    # (fabricated) save's achievements_earned claimed.
    assert m.achievement_ids_earned() == []
