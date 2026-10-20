"""Tests for postmortem.livability_series()."""

import save
import statlog
import sustainability
import trajectory
import postmortem


def _season(c):
    effects = c.tree.effects()
    report = c.state.advance_season(effects)
    c.state.record_score(sustainability.score(c.state, effects))
    trajectory.record(c.state, report, sustainability.livability(c.state, effects) * 100.0)
    statlog.record(c.ui, c.state, effects, report, len(c.tree.researched))


def test_livability_series_returns_empty_when_no_seasons_played():
    """Edge case: a fresh campaign has no trajectory points."""
    c = save.Campaign()
    series = postmortem.livability_series(c)
    assert series == []


def test_livability_series_has_consecutive_season_numbers_starting_at_one():
    """Normal case: after playing several seasons, season numbers are 1, 2, 3..."""
    c = save.Campaign()
    for _ in range(5):
        _season(c)
    series = postmortem.livability_series(c)
    assert len(series) >= 2
    seasons = [s[0] for s in series]
    assert seasons == list(range(1, len(seasons) + 1))


def test_livability_series_values_are_correct_types():
    """Normal case: each tuple contains (season: int, livability: float, population: int)."""
    c = save.Campaign()
    _season(c)
    series = postmortem.livability_series(c)
    assert len(series) == 1
    season, liv, pop = series[0]
    assert isinstance(season, int) and season >= 1
    assert isinstance(liv, float)
    assert isinstance(pop, int)
