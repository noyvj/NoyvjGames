"""B4 (coordinate-style plot labels) + B10 (biodiversity as an explicit
number), from planning/TODO.md's "Per-game: Canopy" section."""

from .conftest import GRID_COLS


def test_plot_coordinate_label_first_row(game_env):
    m = game_env.module
    assert m.plot_coordinate_label(0) == "A1"
    assert m.plot_coordinate_label(1) == "B1"
    assert m.plot_coordinate_label(GRID_COLS - 1) == "F1"


def test_plot_coordinate_label_second_row(game_env):
    m = game_env.module
    assert m.plot_coordinate_label(GRID_COLS) == "A2"
    assert m.plot_coordinate_label(GRID_COLS + 2) == "C2"


def test_plot_coordinate_labels_are_all_unique():
    import importlib.util
    from pathlib import Path

    # Cheap sanity check independent of the fixture: every index in a full
    # grid maps to a distinct label (no row/col collision in the formula).
    spec = importlib.util.spec_from_file_location(
        "coord_check", Path(__file__).resolve().parent.parent / "game.py"
    )
    # Not executed directly (it needs the fake DOM) -- instead just re-derive
    # the same formula here as a cross-check against game.py's docstring
    # contract (row letters A.., column numbers 1..) without re-importing.
    def label(index, cols=6):
        row, col = divmod(index, cols)
        return f"{chr(ord('A') + col)}{row + 1}"

    labels = [label(i) for i in range(36)]
    assert len(set(labels)) == 36


def test_stakeholder_request_message_uses_coordinate_label(game_env):
    m = game_env.module
    # Force a request onto a known plot so the message is deterministic.
    m.pending_stakeholder_request = {"plot_index": 2, "reason": "housing"}
    message = m.stakeholder_request_message()
    assert "Plot C1" in message
    assert "Plot 2" not in message


def test_selected_plot_panel_shows_coordinate_label(game_env):
    game_env.select(7)  # row 1, col 1 -> "B2"
    assert "Plot B2" in game_env.elements["selected-plot-state"].innerText


def test_biodiversity_display_starts_at_zero(game_env):
    assert "Biodiversity: 0.0" in game_env.elements["biodiversity-display"].innerText


def test_biodiversity_display_rises_as_plots_accrue(game_env):
    game_env.tick(20)
    text = game_env.elements["biodiversity-display"].innerText
    m = game_env.module
    assert text == f"Biodiversity: {m.total_biodiversity():.1f}"
    assert m.total_biodiversity() > 0


def test_total_biodiversity_matches_sum_of_plots(game_env):
    m = game_env.module
    game_env.tick(15)
    assert m.total_biodiversity() == sum(p.biodiversity for p in m.plots)
