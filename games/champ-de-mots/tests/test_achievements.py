"""Achievements retrofit (ACHIEVEMENTS-SYSTEM-DESIGN.md), reshaping this
game's own pre-existing Milestone 23 slice into the cross-game pattern: a
static achievements.json catalog (the single source of truth for
label/description), `achievement_ids_earned()` riding `get_state()`'s
"achievements_earned" field, an unlock toast, and a link to the hub-wide
dashboard. Every actual unlock condition below is unchanged from
Milestone 23 -- two independent tiers, total plots automated and full
syllabus weeks fully automated -- since a plot's stage never regresses
(Milestone 2), "currently Automated" and "ever reached Automated" are the
same count, so this still needs no new save state of its own beyond the
write-only projection.
"""


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def _fully_automate(state, plot):
    for _ in range(6):
        state.review(plot.plot_id, True)
        state.advance_day(plot.interval_days)


# --- catalog sanity ---------------------------------------------------------


def test_the_achievements_catalog_loads_and_is_non_empty(game_env):
    module = game_env.module
    assert len(module.ACHIEVEMENTS) == 10


def test_every_catalog_entry_has_a_stable_id_label_and_description(game_env):
    module = game_env.module
    for entry in module.ACHIEVEMENTS:
        assert entry["id"]
        assert entry["label"]
        assert entry["description"]


def test_catalog_ids_are_unique(game_env):
    module = game_env.module
    ids = [entry["id"] for entry in module.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))


def test_every_catalog_id_has_a_checker_and_a_progress_function(game_env):
    module = game_env.module
    for entry in module.ACHIEVEMENTS:
        assert entry["id"] in module.ACHIEVEMENT_CHECKS
        assert entry["id"] in module.ACHIEVEMENT_PROGRESS


def test_every_threshold_list_has_a_matching_catalog_entry(game_env):
    module = game_env.module
    for threshold in module.ACHIEVEMENT_AUTOMATED_THRESHOLDS:
        assert module.automated_achievement_id(threshold) in module.ACHIEVEMENTS_BY_ID
    for threshold in module.ACHIEVEMENT_ROW_THRESHOLDS:
        assert module.row_achievement_id(threshold) in module.ACHIEVEMENTS_BY_ID


# --- underlying farm reads (unchanged from Milestone 23) -------------------


def test_automated_plot_count_is_zero_on_a_fresh_farm(game_env):
    module = game_env.module
    assert module.automated_plot_count() == 0


def test_automated_plot_count_tracks_real_automated_plots(game_env):
    module, state = game_env.module, game_env.state
    _fully_automate(state, state.plots[0])
    assert state.plots[0].stage == module.STAGE_AUTOMATED
    assert module.automated_plot_count() == 1


def test_fully_automated_row_count_is_zero_on_a_fresh_farm(game_env):
    module = game_env.module
    assert module.fully_automated_row_count() == 0


def test_fully_automated_row_count_counts_a_row_only_once_every_plot_is_done(game_env):
    module, state = game_env.module, game_env.state
    row_plots = state.row_plots(1)
    for plot in row_plots[:-1]:
        _fully_automate(state, plot)
    assert module.fully_automated_row_count() == 0

    _fully_automate(state, row_plots[-1])
    assert module.fully_automated_row_count() == 1


# --- achievement_ids_earned() -- the cross-game save-state contract --------


def test_nothing_is_earned_on_a_fresh_farm(game_env):
    module = game_env.module
    assert module.achievement_ids_earned() == []


def test_crossing_the_first_automated_threshold_earns_its_id(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    assert "automated_25" in module.achievement_ids_earned()
    assert "automated_50" not in module.achievement_ids_earned()


def test_crossing_a_row_threshold_earns_its_id(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.row_plots(1):
        _fully_automate(state, plot)
    assert "row_1" in module.achievement_ids_earned()
    assert "row_5" not in module.achievement_ids_earned()


def test_achievement_ids_earned_is_in_catalog_order(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:50]:
        _fully_automate(state, plot)
    earned = module.achievement_ids_earned()
    catalog_order = [entry["id"] for entry in module.ACHIEVEMENTS]
    assert earned == [aid for aid in catalog_order if aid in earned]


def test_get_state_exposes_achievements_earned_and_never_reads_it_back(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    saved = module.get_state()
    assert saved["achievements_earned"] == module.achievement_ids_earned()

    # Write-only: a stale/forged list in a loaded save must not override
    # what the farm's own real state re-derives.
    module.load_state({**saved, "plots": {}, "achievements_earned": ["row_23"]})
    assert module.achievement_ids_earned() == []


# --- the tiered in-game summary (documented judgment call, §3) -------------


def test_no_thresholds_are_earned_on_a_fresh_farm(game_env):
    module = game_env.module
    summary = module.achievements_summary()
    assert summary["automated"]["earned"] == []
    assert summary["rows"]["earned"] == []


def test_the_next_automated_threshold_shows_progress(game_env):
    module, state = game_env.module, game_env.state
    _fully_automate(state, state.plots[0])
    summary = module.achievements_summary()
    next_up = summary["automated"]["next"]
    assert next_up["id"] == "automated_25"
    assert next_up["target"] == 25
    assert next_up["current"] == 1
    assert next_up["label"] == "25 plots automated"


def test_crossing_a_threshold_earns_it_and_advances_next(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    summary = module.achievements_summary()
    earned_ids = [entry["id"] for entry in summary["automated"]["earned"]]
    assert "automated_25" in earned_ids
    assert summary["automated"]["next"]["id"] == "automated_50"


def test_earned_thresholds_list_most_recent_first(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:50]:
        _fully_automate(state, plot)
    summary = module.achievements_summary()
    earned_ids = [entry["id"] for entry in summary["automated"]["earned"]]
    assert earned_ids == ["automated_50", "automated_25"]


def test_a_full_week_achievement_is_earned_once_a_row_is_entirely_automated(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.row_plots(1):
        _fully_automate(state, plot)
    summary = module.achievements_summary()
    earned_labels = [entry["label"] for entry in summary["rows"]["earned"]]
    assert module.ACHIEVEMENTS_BY_ID["row_1"]["label"] in earned_labels
    assert summary["rows"]["next"]["id"] == "row_5"


def test_achievements_never_mutate_srs_state(game_env):
    module, state = game_env.module, game_env.state
    stages_before = [p.stage for p in state.plots]
    module.on_toggle_achievements()
    module.achievements_summary()
    assert [p.stage for p in state.plots] == stages_before


# --- panel toggle/render ----------------------------------------------------


def test_the_panel_is_hidden_until_toggled(game_env):
    module = game_env.module
    assert module.achievements_open is False
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggling_opens_and_closes_the_panel(game_env):
    module = game_env.module
    module.on_toggle_achievements()
    assert module.achievements_open is True
    assert game_env.elements["achievements-panel"].hidden is False
    assert "Hide" in game_env.elements["achievements-toggle-button"].innerText

    module.on_toggle_achievements()
    assert module.achievements_open is False
    assert game_env.elements["achievements-panel"].hidden is True


def test_the_toggle_button_shows_an_earned_over_total_count(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    module.on_toggle_achievements()
    assert f"1/{len(module.ACHIEVEMENTS)}" in game_env.elements["achievements-toggle-button"].innerText


def test_the_panel_shows_the_next_target_before_anything_is_earned(game_env):
    module = game_env.module
    module.on_toggle_achievements()
    texts = _all_texts(game_env.elements["achievements-panel"])
    assert any("25 plots automated" in text and "0 of 25" in text for text in texts)


def test_the_panel_shows_an_earned_badge(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    module.on_toggle_achievements()
    texts = _all_texts(game_env.elements["achievements-panel"])
    assert any("25 plots automated" in text for text in texts)


def test_the_panel_links_to_the_hub_wide_dashboard(game_env):
    module = game_env.module
    module.on_toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    links = [child for child in panel.children if child.className == "achievements-hub-link"]
    assert len(links) == 1
    assert "every game" in links[0].innerText
    assert links[0].href == "../../index.html#account-achievements-dashboard"


# --- unlock toast ------------------------------------------------------------


def test_a_fresh_game_does_not_toast_on_first_render(game_env):
    module = game_env.module
    module.render()
    assert game_env.elements["achievement-toast"].hidden is True


def test_crossing_a_threshold_fires_a_toast_on_the_next_render(game_env):
    module, state = game_env.module, game_env.state
    module.render()  # establish the empty baseline, same as a real page load
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    module.render()
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    assert "achievement-toast--visible" in toast.classList
    assert "25 plots automated" in toast.innerText


def test_a_second_render_with_nothing_new_does_not_retoast(game_env):
    module, state = game_env.module, game_env.state
    module.render()
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    module.render()
    game_env.elements["achievement-toast"].innerText = "sentinel"
    module.render()
    assert game_env.elements["achievement-toast"].innerText == "sentinel"


def test_crossing_multiple_thresholds_in_one_render_reports_the_count(game_env):
    module, state = game_env.module, game_env.state
    module.render()  # establish the empty baseline
    # Row 1 alone (83 plots) crosses automated_25, automated_50 AND row_1 in
    # a single pass -- exactly the "several achievements clear at once"
    # case this test is after.
    for plot in state.row_plots(1):
        _fully_automate(state, plot)
    module.render()
    toast = game_env.elements["achievement-toast"]
    assert "3 achievements unlocked" in toast.innerText
    assert "25 plots automated" in toast.innerText
    assert "50 plots automated" in toast.innerText
    assert "A full week, automated" in toast.innerText
