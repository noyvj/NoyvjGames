"""Canopy TODO batch 2: B3 forest history, B4 maturity leaf burst, B9/B18
playstyle badge, B13 report card, B16 select-request shortcut, B22 veteran
plots, B23 wildlife log, B27 adopted plot."""

import json


def _texts(element):
    out = [element.innerText]
    for c in element.children:
        out.extend(_texts(c))
    return out


# --- B3 forest history ------------------------------------------------------

def test_clear_and_replant_are_logged(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.select(2)
    game_env.clear()
    game_env.replant()
    kinds = [e["kind"] for e in m.forest_log]
    assert "clear" in kinds and "replant" in kinds
    assert m.forest_log[-1]["plot"] == 2


def test_declining_a_request_is_logged_as_preserve(game_env):
    m = game_env.module
    game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS)
    assert m.pending_stakeholder_request is not None
    game_env.decline_stakeholder()
    assert m.forest_log[-1]["kind"] == "preserve"


def test_log_is_capped(game_env):
    m = game_env.module
    for i in range(m.FOREST_LOG_MAX_ENTRIES + 25):
        m._log_event("clear", f"x{i}", 0)
    assert len(m.forest_log) == m.FOREST_LOG_MAX_ENTRIES
    assert m.forest_log[-1]["text"] == f"x{m.FOREST_LOG_MAX_ENTRIES + 24}"


def test_forest_history_panel_lists_newest_first(game_env):
    game_env.select(0)
    game_env.clear()
    game_env.tick(2)
    game_env.select(0)
    game_env.replant()
    game_env.toggle_session_summary()
    text = game_env.elements["forest-history-list"].innerText
    assert text.index("Replanted") < text.index("Cleared")


def test_empty_history_shows_prompt(game_env):
    game_env.toggle_session_summary()
    assert "No decisions yet" in game_env.elements["forest-history-list"].innerText


def test_log_and_adoption_round_trip_through_save(game_env):
    m = game_env.module
    game_env.select(1)
    game_env.clear()
    m.on_adopt_plot()
    game_env.tick(4)
    state = json.loads(json.dumps(m.get_state()))
    m.reset_session()
    assert m.forest_log == []
    m.load_state(state)
    assert [e["kind"] for e in m.forest_log][:2] == ["clear", "adopt"]
    assert m.forest_tick == 4
    assert m.adopted_plot_index == 1


def test_old_save_without_log_fields_loads(game_env):
    m = game_env.module
    state = m.get_state()
    for key in ("forest_log", "forest_tick", "adopted_plot_index"):
        del state[key]
    for plot in state["plots"]:
        del plot["mature_celebrated"], plot["requests_survived"]
    m.load_state(state)
    assert m.forest_log == []
    assert m.adopted_plot_index is None
    assert m.plots[0].requests_survived == 0


def test_load_state_sanitises_bad_log_entries_and_adoption(game_env):
    m = game_env.module
    state = m.get_state()
    state["forest_log"] = ["junk", {"tick": 3, "kind": "clear", "plot": 0, "text": "ok"}]
    state["adopted_plot_index"] = 999
    m.load_state(state)
    assert len(m.forest_log) == 1
    assert m.adopted_plot_index is None


# --- B4 leaf burst ----------------------------------------------------------

def test_leaf_burst_fires_once_when_plot_first_reaches_maturity(game_env):
    m = game_env.module
    for _ in range(m.MATURITY_TICKS - 1):
        m.plots[0].accrue_tick()
    m.plots[0].ticks_intact = m.MATURITY_TICKS - 1
    game_env.tick(1)
    tile = game_env.elements["plot-0"]
    assert "plot-mature-burst" in tile.className
    assert sum(1 for c in tile.children if c.className.startswith("leaf-burst")) == m.LEAF_BURST_COUNT
    assert m.plots[0].mature_celebrated
    game_env.tick(1)
    assert "plot-mature-burst" not in game_env.elements["plot-0"].className


def test_maturity_is_logged(game_env):
    m = game_env.module
    m.plots[0].ticks_intact = m.MATURITY_TICKS - 1
    game_env.tick(1)
    assert any(e["kind"] == "mature" and e["plot"] == 0 for e in m.forest_log)


# --- B9/B18 badge -----------------------------------------------------------

def test_badge_undecided_before_any_play(game_env):
    assert game_env.module.playstyle_badge() == "Undecided"


def test_badge_preservationist_when_nothing_cleared(game_env):
    game_env.tick(3)
    assert game_env.module.playstyle_badge() == "Preservationist"


def test_badge_balanced_and_harvester_thresholds(game_env):
    m = game_env.module
    game_env.tick(1)
    n = len(m.plots)
    for i in range(int(n * 0.3)):
        m.plots[i].clear_count = 1
    assert m.playstyle_badge() == "Balanced"
    for i in range(int(n * 0.8)):
        m.plots[i].clear_count = 1
    assert m.playstyle_badge() == "Harvester"


def test_badge_shows_in_summary_and_share_text(game_env):
    game_env.tick(2)
    game_env.toggle_session_summary()
    assert "Preservationist" in game_env.elements["session-summary-badge"].innerText
    assert "Preservationist" in game_env.module.badge_share_text()


# --- B13 report card ---------------------------------------------------------

def test_report_card_graphs_render_after_ticks(game_env):
    game_env.tick(5)
    game_env.toggle_session_summary()
    for eid in ("report-card-biodiversity", "report-card-standing", "report-card-relations"):
        assert "<svg" in game_env.elements[eid].innerHTML


def test_report_card_placeholder_before_ticks(game_env):
    game_env.toggle_session_summary()
    assert "Not enough time" in game_env.elements["report-card-standing"].innerText


def test_report_history_is_capped_and_reset(game_env):
    m = game_env.module
    game_env.tick(m.VALUE_HISTORY_MAX_POINTS + 10)
    assert len(m._report_history) == m.VALUE_HISTORY_MAX_POINTS
    m.reset_session()
    assert m._report_history == []


# --- B16 ---------------------------------------------------------------------

def test_select_stakeholder_plot_selects_requested_plot(game_env):
    m = game_env.module
    assert m.select_stakeholder_plot() is None
    game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS)
    target = m.pending_stakeholder_request["plot_index"]
    assert m.select_stakeholder_plot() == target
    assert m.selected_index == target


# --- B22 ---------------------------------------------------------------------

def test_veteran_after_three_declined_requests(game_env):
    m = game_env.module
    plot = m.plots[0]
    for _ in range(3):
        plot.value = 999.0  # make it the most established plot
        m.pending_stakeholder_request = {"plot_index": 0, "reason": "housing", "kind": "clear"}
        m.decline_stakeholder_request()
    assert plot.requests_survived == 3
    assert plot.is_veteran()
    m.render()
    tile = game_env.elements["plot-0"]
    assert "plot-veteran" in tile.className
    assert "veteran" in tile.getAttribute("data-tooltip")


def test_clearing_disqualifies_veteran(game_env):
    m = game_env.module
    m.plots[0].requests_survived = 5
    m.plots[0].clear_count = 1
    assert not m.plots[0].is_veteran()


def test_declining_an_incentive_does_not_count_toward_veteran(game_env):
    m = game_env.module
    m.plots[0].value = 5.0
    m.pending_stakeholder_request = {"plot_index": 0, "reason": "ecotourism", "kind": "incentive"}
    m.decline_stakeholder_request()
    assert m.plots[0].requests_survived == 0


# --- B23 ---------------------------------------------------------------------

def test_wildlife_appearance_is_logged_with_species(game_env):
    m = game_env.module
    game_env.tick(11)
    wildlife = [e for e in m.forest_log if e["kind"] == "wildlife"]
    assert len(wildlife) == len(m.plots)
    assert "owl" in wildlife[0]["text"]
    assert len({e["plot"] for e in wildlife}) == len(m.plots)


def test_species_seen_and_panel(game_env):
    m = game_env.module
    assert m.species_seen() == []
    game_env.tick(11)
    assert len(m.species_seen()) == len(m.WILDLIFE_SPECIES)
    game_env.toggle_session_summary()
    assert "Species seen (6/6)" in game_env.elements["wildlife-log-list"].innerText


# --- B27 ---------------------------------------------------------------------

def test_adopt_requires_selection(game_env):
    assert game_env.module.on_adopt_plot() is False
    assert game_env.elements["adopt-plot-button"].disabled is True


def test_adopt_and_release_toggle(game_env):
    m = game_env.module
    game_env.select(4)
    m.on_adopt_plot()
    assert m.adopted_plot_index == 4
    assert game_env.elements["adopted-plot-panel"].hidden is False
    assert "plot-adopted" in game_env.elements["plot-4"].className
    assert "Release" in game_env.elements["adopt-plot-button"].innerText
    m.on_adopt_plot()
    assert m.adopted_plot_index is None
    assert game_env.elements["adopted-plot-panel"].hidden is True


def test_adopted_panel_shows_only_that_plots_history(game_env):
    m = game_env.module
    game_env.select(4)
    game_env.clear()
    game_env.select(5)
    game_env.clear()
    game_env.select(4)
    m.on_adopt_plot()
    text = game_env.elements["adopted-plot-panel"].innerText
    assert m.plot_coordinate_label(4) in text
    assert m.plot_coordinate_label(5) not in text.split("History:")[-1]


def test_reset_clears_adoption_and_log(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    m.on_adopt_plot()
    m.reset_session()
    assert m.adopted_plot_index is None and m.forest_log == []
