"""setup(): wires every button and starts the game."""

from js import document
from pyodide.ffi import create_proxy

from canopy_achievements import on_toggle_achievements
from canopy_almanac import on_toggle_almanac
from canopy_charts import on_toggle_ghost, render_timeline_chart
from canopy_comfort import on_dismiss_away_chip, on_dismiss_coach_hints, on_visibility_change
from canopy_contracts import _fill_contract_board, on_toggle_contracts
from canopy_expedition import _load_expedition_meta
from canopy_handlers_core import (
    cancel_survey, on_clear, on_clear_cut, on_forest_name_change, on_highland_clear, on_highland_replant,
    on_pace_change, on_plot_nickname_change, on_replant, on_tend, on_wetland_clear, on_wetland_mangrove,
    on_wetland_replant, undo_last_clear,
)
from canopy_handlers_modes import (
    commit_survey, on_dampen, on_expedition_copy, on_expedition_new_seed, on_expedition_start,
    on_leave_expedition, on_leave_level, on_next_level, on_rival_buyout, on_rival_lock, on_survey_decline,
    on_survey_remove_last, on_toggle_expedition, on_toggle_survey, on_toggle_vault,
)
from canopy_handlers_panels import (
    counter_stakeholder_request, decline_stakeholder_request, grant_stakeholder_request, on_adopt_plot,
    on_challenge_change, on_difficulty_change, on_grid_size_change, on_lab_apply, on_layout_apply,
    on_layout_clear, on_plot_contextmenu, on_plot_sheet_action, on_reset_session, on_save_plot_note,
    on_scenario_change, on_sell_carbon_all, on_sell_carbon_half, on_specialize_biodiversity,
    on_specialize_economic,
)
from canopy_helpers import _el
from canopy_infopanels import on_toggle_changelog, on_toggle_example, on_toggle_info_page
from canopy_labui import on_lab_load_variant, on_lab_save_variant, on_lab_slider, reset_lab_to_normal
from canopy_layout import (
    LAYOUT_PRESET_LABELS, on_layout_grid_click, on_layout_load, on_layout_preset, on_layout_save,
)
from canopy_levels import _note_vault_progress
from canopy_lifetime import on_forest_frame_change, on_forest_palette_change, on_my_forests_change
from canopy_plotsheet import close_plot_sheet
from canopy_renderer import _setup_levels_bridge, render
from canopy_rules import LAB_KEYS
from canopy_sessionview import on_save_playstyle_run_a, on_save_playstyle_run_b, on_toggle_session_summary
from canopy_stakeholders import render_request_history
from canopy_summary import on_download_forest_card, on_replay_scrub
from canopy_survey import load_species_choice, on_species_change, render_species_note
from canopy_tick import _start_tick_loop
from canopy_vault import _load_meta


def setup():
    clear_button = document.getElementById("clear-button")
    replant_button = document.getElementById("replant-button")
    clear_button.innerText = "Clear"
    replant_button.innerText = "Replant"
    clear_button.addEventListener("click", create_proxy(on_clear))
    replant_button.addEventListener("click", create_proxy(on_replant))
    counter_button = _el("stakeholder-counter-button")  # B-25
    if counter_button is not None:
        counter_button.addEventListener("click", create_proxy(counter_stakeholder_request))
    coach_button = _el("coach-dismiss")  # B-27
    if coach_button is not None:
        coach_button.addEventListener("click", create_proxy(on_dismiss_coach_hints))
    card_button = _el("forest-card-download")  # B-4
    if card_button is not None:
        card_button.addEventListener("click", create_proxy(on_download_forest_card))
    scenario_select = _el("scenario-select")  # B-11
    if scenario_select is not None:
        scenario_select.addEventListener("change", create_proxy(on_scenario_change))
    for select_id in ("my-forests-a", "my-forests-b"):  # B-1
        select = _el(select_id)
        if select is not None:
            select.addEventListener("change", create_proxy(on_my_forests_change))
    for select_id, handler in (("forest-frame-select", on_forest_frame_change), ("forest-palette-select", on_forest_palette_change)):
        select = _el(select_id)  # B-19
        if select is not None:
            select.addEventListener("change", create_proxy(handler))
    for lab_key in LAB_KEYS:  # B-5
        lab_slider = _el(f"lab-{lab_key}")
        if lab_slider is not None:
            lab_slider.addEventListener("input", create_proxy(lambda event=None, k=lab_key: on_lab_slider(k)))
    for lab_id, lab_handler in (("lab-apply-button", on_lab_apply), ("lab-reset-button", reset_lab_to_normal),
                                ("lab-save-variant-button", on_lab_save_variant), ("lab-load-variant-button", on_lab_load_variant)):
        lab_button = _el(lab_id)
        if lab_button is not None:
            lab_button.addEventListener("click", create_proxy(lab_handler))
    species_select = _el("species-select")  # GB-6
    if species_select is not None:
        load_species_choice()
        species_select.addEventListener("change", create_proxy(on_species_change))
        render_species_note()
    dampen_button = _el("dampen-button")  # GB-1
    if dampen_button is not None:
        dampen_button.addEventListener("click", create_proxy(on_dampen))
    for carbon_id, carbon_handler in (("carbon-sell-button", on_sell_carbon_all), ("carbon-sell-half-button", on_sell_carbon_half)):  # GB-29
        carbon_button = _el(carbon_id)
        if carbon_button is not None:
            carbon_button.addEventListener("click", create_proxy(carbon_handler))
    layout_grid = _el("layout-grid")  # B-29
    if layout_grid is not None:
        layout_grid.addEventListener("click", create_proxy(on_layout_grid_click))
    for layout_id, layout_handler in (("layout-apply-button", on_layout_apply), ("layout-save-button", on_layout_save),
                                      ("layout-load-button", on_layout_load), ("layout-clear-button", on_layout_clear)):
        layout_button = _el(layout_id)
        if layout_button is not None:
            layout_button.addEventListener("click", create_proxy(layout_handler))
    for preset_kind in LAYOUT_PRESET_LABELS:
        preset_button = _el(f"layout-preset-{preset_kind}")
        if preset_button is not None:
            preset_button.addEventListener("click", create_proxy(lambda event=None, k=preset_kind: on_layout_preset(k)))
    for rival_id, rival_handler in (("rival-lock-button", on_rival_lock), ("rival-buyout-button", on_rival_buyout)):  # GB-12
        rival_button = _el(rival_id)
        if rival_button is not None:
            rival_button.addEventListener("click", create_proxy(rival_handler))
    for survey_id, survey_handler in (("survey-toggle-button", on_toggle_survey), ("survey-commit-button", commit_survey),
                                      ("survey-remove-button", on_survey_remove_last), ("survey-decline-button", on_survey_decline),
                                      ("survey-cancel-button", cancel_survey)):  # B-13
        survey_button = _el(survey_id)
        if survey_button is not None:
            survey_button.addEventListener("click", create_proxy(survey_handler))
    for sheet_name in ("clear", "cut", "replant", "adopt", "note"):  # B-28
        sheet_button = _el(f"plot-sheet-{sheet_name}")
        if sheet_button is not None:
            sheet_button.addEventListener("click", create_proxy(lambda event=None, n=sheet_name: on_plot_sheet_action(n)))
    sheet_close = _el("plot-sheet-close")
    if sheet_close is not None:
        sheet_close.addEventListener("click", create_proxy(close_plot_sheet))
    replay_slider = _el("replay-slider")  # B-3
    if replay_slider is not None:
        replay_slider.addEventListener("input", create_proxy(on_replay_scrub))
    timeline_select = _el("timeline-metric")  # B-21
    if timeline_select is not None:
        timeline_select.addEventListener("change", create_proxy(lambda event=None: render_timeline_chart()))
    ghost_toggle = _el("ghost-toggle")  # Z-3e
    if ghost_toggle is not None:
        ghost_toggle.addEventListener("change", create_proxy(on_toggle_ghost))
    for select_id in ("request-history-sort", "request-history-kind"):  # B-14
        select = _el(select_id)
        if select is not None:
            select.addEventListener("change", create_proxy(lambda event=None: render_request_history()))
    note_button, note_box, grid_for_notes = _el("plot-note-save"), _el("plot-note-input"), _el("plot-grid")
    if note_button is not None:  # B-24
        note_button.addEventListener("click", create_proxy(on_save_plot_note))
    if note_box is not None:
        note_box.addEventListener(
            "keydown", create_proxy(lambda event: on_save_plot_note() if getattr(event, "key", "") == "Enter" else None)
        )
    if grid_for_notes is not None:
        grid_for_notes.addEventListener("contextmenu", create_proxy(on_plot_contextmenu))
    away_chip = _el("away-chip")
    if away_chip is not None:
        away_chip.addEventListener("click", create_proxy(on_dismiss_away_chip))
    document.addEventListener("visibilitychange", create_proxy(on_visibility_change))  # B-22
    document.getElementById("stakeholder-grant-button").addEventListener(
        "click", create_proxy(grant_stakeholder_request)
    )
    document.getElementById("stakeholder-decline-button").addEventListener(
        "click", create_proxy(decline_stakeholder_request)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("example-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_example)
    )
    document.getElementById("reset-session-button").addEventListener(
        "click", create_proxy(on_reset_session)
    )
    document.getElementById("session-summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_session_summary)
    )
    document.getElementById("specialize-economic-button").addEventListener(
        "click", create_proxy(on_specialize_economic)
    )
    document.getElementById("specialize-biodiversity-button").addEventListener(
        "click", create_proxy(on_specialize_biodiversity)
    )
    document.getElementById("adopt-plot-button").addEventListener(
        "click", create_proxy(on_adopt_plot)
    )
    document.getElementById("save-playstyle-run-a-button").addEventListener(
        "click", create_proxy(on_save_playstyle_run_a)
    )
    document.getElementById("save-playstyle-run-b-button").addEventListener(
        "click", create_proxy(on_save_playstyle_run_b)
    )
    document.getElementById("grid-size-select").addEventListener(
        "change", create_proxy(on_grid_size_change)
    )
    document.getElementById("difficulty-select").addEventListener(
        "change", create_proxy(on_difficulty_change)
    )
    for element_id, handler in (("challenge-select", on_challenge_change), ("request-pace-select", on_pace_change)):
        element = _el(element_id)  # GB-17 / B-6
        if element is not None:
            element.addEventListener("change", create_proxy(handler))
    document.getElementById("highland-clear-button").addEventListener(
        "click", create_proxy(on_highland_clear)
    )
    document.getElementById("highland-replant-button").addEventListener(
        "click", create_proxy(on_highland_replant)
    )
    document.getElementById("wetland-clear-button").addEventListener(
        "click", create_proxy(on_wetland_clear)
    )
    # GB batch 1: optional elements (a page or test DOM without them just skips the wiring).
    for element_id, event_name, handler in (
        ("tend-button", "click", on_tend),
        ("clear-cut-button", "click", on_clear_cut),  # GB-21
        ("undo-clear-button", "click", undo_last_clear),
        ("almanac-toggle-button", "click", on_toggle_almanac),
        ("contracts-toggle-button", "click", on_toggle_contracts),
        ("vault-toggle-button", "click", on_toggle_vault),
        ("expedition-toggle-button", "click", on_toggle_expedition),  # GB-3
        ("expedition-new-seed-button", "click", on_expedition_new_seed),
        ("expedition-copy-button", "click", on_expedition_copy),
        ("expedition-start-button", "click", on_expedition_start),
        ("expedition-leave-button", "click", on_leave_expedition),
        ("level-leave-button", "click", on_leave_level),
        ("level-next-button", "click", on_next_level),
        ("forest-name-input", "change", on_forest_name_change),
        ("plot-nickname-input", "change", on_plot_nickname_change),
    ):
        element = _el(element_id)
        if element is not None:
            element.addEventListener(event_name, create_proxy(handler))
    mangrove_button = _el("wetland-mangrove-button")  # GB-24
    if mangrove_button is not None:
        mangrove_button.addEventListener("click", create_proxy(on_wetland_mangrove))
    document.getElementById("wetland-replant-button").addEventListener(
        "click", create_proxy(on_wetland_replant)
    )
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast element is only otherwise touched by show_achievement_toast()/
    # its own hide callback (unlike every *panel*, which gets its `hidden`
    # state re-set on every render()), so it needs its own starting state
    # set here rather than trusting markup alone.
    toast = document.getElementById("achievement-toast")
    if toast is not None:
        toast.hidden = True
    _fill_contract_board()  # GB-9: the module starts without a reset_session(), so seed the board here
    _load_meta()  # GB batch 3: this browser's level progress and Seed Vault
    _load_expedition_meta()  # GB-3: this browser's Expedition bests
    _note_vault_progress(silent=True)
    _setup_levels_bridge()
    _start_tick_loop()
    render()


setup()
