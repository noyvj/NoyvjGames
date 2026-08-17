"""Iteration Pass 2: multi-region comparison. Two more player-managed
regions (region_b, region_c) run alongside the original "Region A"
(left entirely unchanged — same object, same element IDs, same
behavior), each independently invested and advanced in lockstep with
the primary region's Advance Round button, each with its own compact
mini-graph so divergence between strategies is visible within one
session.
"""


def test_secondary_regions_start_independent_of_primary(game_env):
    assert game_env.module.region_b is not game_env.module.region
    assert game_env.module.region_c is not game_env.module.region
    assert game_env.module.region_b is not game_env.module.region_c


def test_secondary_regions_start_at_zero_temperature(game_env):
    assert game_env.module.region_b.temperature == 0.0
    assert game_env.module.region_c.temperature == 0.0


def test_advance_round_advances_all_three_regions_together(game_env):
    game_env.advance_round()
    assert game_env.region.round_number == 2
    assert game_env.module.region_b.round_number == 2
    assert game_env.module.region_c.round_number == 2


def test_regions_diverge_with_different_strategies(game_env):
    # Region B invests nothing (fastest warming); Region C invests
    # heavily in preservation (slowest). Same background trajectory,
    # different outcomes — the whole point of the comparison.
    for _ in range(3):
        game_env.invest_secondary("c", "preserve")
    for _ in range(15):
        game_env.advance_round()
    assert game_env.module.region_c.temperature < game_env.module.region_b.temperature


def test_secondary_region_invest_button_dispatches(game_env):
    game_env.invest_secondary("b", "output")
    assert game_env.module.region_b.capacity["output"] == 1
    assert game_env.module.region_c.capacity["output"] == 0


def test_temperature_history_grows_each_round(game_env):
    game_env.advance_round()
    game_env.advance_round()
    assert len(game_env.region.temperature_history) == 2
    assert len(game_env.module.region_b.temperature_history) == 2


def test_mini_temp_graph_svg_empty_with_fewer_than_two_points(game_env):
    assert game_env.module.mini_temp_graph_svg([]) == ""
    assert game_env.module.mini_temp_graph_svg([5.0]) == ""


def test_mini_temp_graph_svg_renders_a_polyline(game_env):
    svg = game_env.module.mini_temp_graph_svg([0.0, 1.0, 2.0])
    assert "<polyline" in svg
    assert "mini-temp-line" in svg


def test_render_populates_primary_region_graph(game_env):
    game_env.advance_round()
    game_env.advance_round()
    assert "<svg" in game_env.elements["graph"].innerHTML


def test_render_populates_secondary_region_graphs(game_env):
    game_env.advance_round()
    game_env.advance_round()
    game_env.module.render()
    assert "<svg" in game_env.elements["b-graph"].innerHTML
    assert "<svg" in game_env.elements["c-graph"].innerHTML


def test_render_shows_secondary_region_temperature(game_env):
    game_env.advance_round()
    game_env.module.render()
    text = game_env.elements["b-temperature-display"].innerText
    assert "+" in text and "°" in text


def test_secondary_region_melt_status_updates_when_melting(game_env):
    game_env.module.region_b.temperature = 999.0
    game_env.module.render()
    assert game_env.elements["b-melt-status-display"].innerText == "Melting"
    assert "melt-status--active" in game_env.elements["b-melt-status-display"].className


def test_secondary_region_card_flashes_on_tipping_point(game_env):
    game_env.module.region_b.temperature = game_env.module.MELT_THRESHOLD - 0.5
    game_env.module.region_b.advance_round()
    game_env.module.render()
    assert "tipping-flash" in game_env.elements["b-region-card"].className


def test_secondary_region_card_flash_clears_on_next_render(game_env):
    game_env.module.region_b.temperature = game_env.module.MELT_THRESHOLD - 0.5
    game_env.module.region_b.advance_round()
    game_env.module.render()
    game_env.module.render()
    assert game_env.elements["b-region-card"].className == "region-card"


def test_primary_region_unaffected_by_secondary_regions(game_env):
    # A sanity check that the Pass 1 primary region's own state genuinely
    # doesn't reference or get mutated by the two new ones.
    for _ in range(5):
        game_env.invest_secondary("b", "preserve")
        game_env.invest_secondary("c", "monitor")
    assert game_env.region.capacity == {"output": 0, "preserve": 0, "monitor": 0}
