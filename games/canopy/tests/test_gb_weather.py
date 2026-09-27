"""GB-23: rain shimmer boosts accrual for 8 ticks, drought tints tiles and slows
them; both shown on the season indicator."""


def _episodes(m, upto=800):
    """[(kind, start, length)] over ticks 0..upto."""
    result = []
    current = None
    for t in range(upto):
        kind = m.weather_at(t)
        if kind and current and current[0] == kind and current[1] + current[2] == t:
            current = (kind, current[1], current[2] + 1)
            result[-1] = current
        elif kind:
            current = (kind, t, 1)
            result.append(current)
        else:
            current = None
    return result


def test_weather_is_a_pure_function_of_the_tick(game_env):
    m = game_env.module
    assert [m.weather_at(t) for t in range(300)] == [m.weather_at(t) for t in range(300)]


def test_calm_opening(game_env):
    m = game_env.module
    assert all(m.weather_at(t) is None for t in range(m.WEATHER_FIRST_TICK))


def test_both_kinds_occur_and_episodes_last_up_to_eight_ticks(game_env):
    m = game_env.module
    episodes = _episodes(m)
    kinds = {kind for kind, _s, _n in episodes}
    assert kinds == {"rain", "drought"}
    assert all(1 <= n <= m.WEATHER_DURATION_TICKS for _k, _s, n in episodes)
    assert any(n == m.WEATHER_DURATION_TICKS for _k, _s, n in episodes)


def test_rain_in_spring_and_autumn_drought_in_summer_none_in_winter(game_env):
    m = game_env.module
    for kind, start, _n in _episodes(m):
        season = m._season_at(start)
        assert season != "winter"
        assert kind == ("drought" if season == "summer" else "rain")


def _first(m, kind):
    return next(start for k, start, _n in _episodes(m) if k == kind)


def test_rain_boosts_and_drought_slows_accrual(game_env):
    m = game_env.module
    for kind, factor in (("rain", m.WEATHER_RAIN_MULTIPLIER), ("drought", m.WEATHER_DROUGHT_MULTIPLIER)):
        start = _first(m, kind)
        m.forest_tick = start  # accrue_tick reads the live tick
        plot = m.Plot(0)
        plot.ticks_intact = 5
        with_weather = plot.accrue_tick()
        m.forest_tick = 0
        calm_plot = m.Plot(0)
        calm_plot.ticks_intact = 5
        calm_season = m.SEASON_GROWTH_MULTIPLIER[m._season_at(0)]
        weather_season = m.SEASON_GROWTH_MULTIPLIER[m._season_at(start)]
        without = calm_plot.accrue_tick()
        assert abs(with_weather / without - factor * weather_season / calm_season) < 1e-9


def test_indicator_reads_rain_and_grid_classes(game_env):
    m = game_env.module
    start = _first(m, "rain")
    m.forest_tick = start
    m.render()
    text = game_env.elements["weather-text"].innerText
    assert "Rain" in text and "+15%" in text and "8 ticks left" in text
    assert game_env.elements["weather-text"].hidden is False
    grid = game_env.elements["plot-grid"]
    assert grid.classList.contains("plot-grid--rain") and not grid.classList.contains("plot-grid--drought")


def test_indicator_reads_drought_and_clears_afterwards(game_env):
    m = game_env.module
    start = _first(m, "drought")
    m.forest_tick = start + 2
    m.render()
    assert "Drought" in game_env.elements["weather-text"].innerText
    assert "-15%" in game_env.elements["weather-text"].innerText
    assert game_env.elements["plot-grid"].classList.contains("plot-grid--drought")
    m.forest_tick = start + m.WEATHER_DURATION_TICKS
    m.render()
    assert game_env.elements["weather-text"].hidden is True
    assert not game_env.elements["plot-grid"].classList.contains("plot-grid--drought")


def test_season_indicator_names_season_and_countdown(game_env):
    m = game_env.module
    m.render()
    assert "Spring" in game_env.elements["season-text"].innerText
    assert "40 ticks to Summer" in game_env.elements["season-text"].innerText


def test_counterfactual_prices_in_the_same_weather_the_forest_saw(game_env):
    m = game_env.module
    m.legacy_multiplier = 1.0
    start = next(st for _k, st, _n in _episodes(m) if st % m.SEASON_CYCLE_TICKS <= 30)
    m.forest_tick = start - 1  # begin just before an episode, well inside a season
    game_env.tick(8)
    assert m.forest_tick == start + 7
    ideal = m._ideal_accrual_for_ticks(m._session_ticks)
    assert abs(m.plots[0].value - ideal) < 1e-6
    calm = sum(
        m.BASE_ACCRUAL * (1 + j * m.GROWTH_PER_TICK) * m.SEASON_GROWTH_MULTIPLIER[m._season_at(start - 1 + j)]
        for j in range(1, 9)
    )
    assert abs(ideal - calm) > 1e-6


def test_weather_effects_reach_highland_and_wetland_too(game_env):
    m = game_env.module
    m.forest_tick = _first(m, "rain")
    plot = m.Plot(0, region="highland")
    assert plot.accrue_tick() > 0
    assert m.current_weather_multiplier() == m.WEATHER_RAIN_MULTIPLIER
