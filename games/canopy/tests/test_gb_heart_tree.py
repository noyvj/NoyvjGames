"""GB-8: a hidden Heart Tree grows at the centre of a ring of mature plots.
There is no UI hint; finding it gives a wildlife-log style entry and a toast."""

import json
from pathlib import Path

from .gb_helpers import log_kinds, make_mature, ring_around, tile, tile_marks, toast_text

CENTRE = 14  # row 2, col 2 on the 6x6 grid: all 8 neighbours exist


def _ring(m, centre=CENTRE, how_many=7):
    for index in ring_around(m, centre)[:how_many]:
        make_mature(m, index)


def _fresh_low_plots(m):
    """Keep the rest of the grid quiet so only the ring matters."""
    for plot in m.plots:
        plot.ticks_intact = 0
        plot.value = 1.0


def test_seven_mature_neighbours_wake_the_heart_tree(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick()
    assert m.heart_tree_index == CENTRE


def test_six_mature_neighbours_are_not_enough(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m, how_many=6)
    game_env.tick()
    assert m.heart_tree_index is None


def test_an_edge_plot_can_never_be_the_centre(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    for index in m._neighbour_indices(0):
        make_mature(m, index)
    game_env.tick()
    assert m.heart_tree_index is None


def test_the_centre_must_be_standing(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    m.plots[CENTRE].state = m.BARE
    game_env.tick()
    assert m.heart_tree_index is None


def test_finding_it_logs_a_wildlife_style_entry_and_toasts(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick()
    assert "discovery" in log_kinds(m)
    assert "Heart Tree is awake" in toast_text(game_env)  # shares the toast with any achievement
    game_env.toggle_session_summary()
    assert "Heart Tree" in game_env.elements["wildlife-log-list"].innerText


def test_the_heart_tree_tile_is_distinct_but_does_not_explain_itself(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick()
    element = tile(game_env, CENTRE)
    assert "plot-heart-tree" in element.className
    marks = tile_marks(game_env, CENTRE)
    assert "heart-tree-aura" in marks and "heart-tree-mark" in marks
    label = element.getAttribute("aria-label").lower()
    assert "heart" not in label and "ancient" not in label
    neighbour = ring_around(m, CENTRE)[0]
    assert "plot-heart-aura" in tile(game_env, neighbour).className


def test_no_hint_anywhere_in_the_page_markup():
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8").lower()
    assert "heart tree" not in html and "heart-tree" not in html


def test_the_heart_tree_cannot_be_cleared(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick()
    game_env.select(CENTRE)
    assert game_env.elements["clear-button"].disabled is True
    income = m.total_income
    game_env.clear()
    assert m.plots[CENTRE].state != m.BARE and m.total_income == income


def test_requests_never_target_the_heart_tree(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick()
    m.plots[CENTRE].value = 10_000.0  # the most valuable plot by far
    assert m._most_established_plot_index() != CENTRE


def test_a_pending_clear_request_on_the_centre_is_dropped_on_discovery(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    m.pending_stakeholder_request = {"plot_index": CENTRE, "reason": "housing", "kind": "clear"}
    m._check_heart_tree()
    assert m.pending_stakeholder_request is None


def test_the_aura_adds_ten_percent_growth_to_the_ring(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick()
    ring_plot = m.plots[ring_around(m, CENTRE)[0]]
    outsider = m.plots[35]
    ring_plot.ticks_intact = outsider.ticks_intact = 10
    ring_plot.value = outsider.value = 0.0
    game_env.tick()
    ratio = ring_plot.value / outsider.value
    assert abs(ratio - (1 + m.HEART_TREE_AURA_BONUS)) < 1e-9


def test_discovery_is_saved_only_once_found_and_validated_on_load(game_env):
    m = game_env.module
    assert "heart_tree_index" not in m.get_state()
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick()
    state = m.get_state()
    assert state["heart_tree_index"] == CENTRE
    m.heart_tree_index = None
    m.load_state(state)
    assert m.heart_tree_index == CENTRE
    for bad in (999, -1, True, "14", None, 0, [14], 5.5):  # 0 is an edge plot
        data = dict(state, heart_tree_index=bad)
        json.dumps(data) if not isinstance(bad, float) else None
        m.load_state(data)
        assert m.heart_tree_index is None


def test_reset_forgets_the_discovery(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick()
    game_env.reset_session()
    assert m.heart_tree_index is None


def test_found_only_once(game_env):
    m = game_env.module
    _fresh_low_plots(m)
    _ring(m)
    game_env.tick(3)
    assert log_kinds(m).count("discovery") == 1


def test_small_grid_can_grow_one_too(game_env):
    m = game_env.module
    game_env.change_grid_size("small")
    _fresh_low_plots(m)
    centre = 5  # row 1, col 1 on the 4x4 grid
    for index in ring_around(m, centre)[:7]:
        make_mature(m, index)
    game_env.tick()
    assert m.heart_tree_index == centre
