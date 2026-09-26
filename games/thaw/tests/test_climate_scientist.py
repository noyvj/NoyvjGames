"""G7: an optional "Climate Scientist" deeper-data view alongside the
in-game graph -- real published atmospheric methane growth-rate data
(NOAA Global Monitoring Laboratory), not a live backend call. Static
real-world data, so unlike the community-compare panel (G11) this needs
no JS hook and no Z1 dependency."""


def _toggle(game_env):
    game_env.elements["climate-scientist-toggle-button"].dispatch("click", None)


def test_panel_starts_closed(game_env):
    module = game_env.module
    module.render()
    assert module.climate_scientist_open is False
    assert game_env.elements["climate-scientist-panel"].hidden is True
    assert "\U0001F52C" in game_env.elements["climate-scientist-toggle-button"].innerText


def test_opening_shows_the_framing_chart_and_source(game_env):
    module = game_env.module
    _toggle(game_env)
    assert module.climate_scientist_open is True
    panel = game_env.elements["climate-scientist-panel"]
    assert panel.hidden is False
    assert "1983" in panel.innerHTML
    assert "not a permafrost-only figure" in panel.innerHTML
    assert "<svg" in panel.innerHTML
    assert module.CLIMATE_SCIENTIST_SOURCE_URL in panel.innerHTML
    assert "Hide Climate Scientist" in game_env.elements["climate-scientist-toggle-button"].innerText


def test_closing_hides_it_again(game_env):
    _toggle(game_env)
    _toggle(game_env)
    assert game_env.elements["climate-scientist-panel"].hidden is True


def test_panel_stays_live_across_an_ordinary_render(game_env):
    module = game_env.module
    _toggle(game_env)
    module.render()
    assert game_env.elements["climate-scientist-panel"].hidden is False
    assert "<svg" in game_env.elements["climate-scientist-panel"].innerHTML


def test_real_data_table_is_a_genuine_multi_decade_series(game_env):
    module = game_env.module
    data = module.REAL_METHANE_GROWTH_PPB_PER_YEAR
    years = [y for y, _ in data]
    assert years == sorted(years)
    assert years[0] == 1984
    assert years[-1] - years[0] >= 40
    # Every value is a plausible annual ppb/year growth figure, not a
    # placeholder -- real atmospheric methane growth has never been
    # negative by more than a few ppb or positive by more than ~20.
    for _, value in data:
        assert -10.0 < value < 25.0


def test_chart_svg_has_one_point_per_year_and_a_baseline_line(game_env):
    module = game_env.module
    svg = module.real_methane_growth_chart_svg()
    assert svg.count(",") >= len(module.REAL_METHANE_GROWTH_PPB_PER_YEAR)
    assert "methane-chart-baseline" in svg
    assert "1984" in svg and "2025" in svg


def test_edge_year_labels_anchor_inward_so_they_never_clip(game_env):
    """The first/last tick sits right at the SVG's own edge -- a centered
    anchor there would clip half the label outside the viewBox (a real
    bug caught live, not just in a fake-DOM test)."""
    module = game_env.module
    svg = module.real_methane_growth_chart_svg()
    assert 'style="text-anchor:start"' in svg
    assert 'style="text-anchor:end"' in svg


def test_chart_is_deterministic(game_env):
    module = game_env.module
    assert module.real_methane_growth_chart_svg() == module.real_methane_growth_chart_svg()
