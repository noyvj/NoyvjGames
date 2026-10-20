"""Tests for geography.levels()."""

import geography


def test_levels_returns_zero_for_empty_grid():
    assert geography.levels([]) == {b: 0 for b in geography.BIOMES}


def test_levels_tracks_cell_counts_correctly():
    grid = geography.generate(1234)
    counts = geography.counts(grid)
    expected = {biome: geography.level_of(n) for biome, n in counts.items()}
    assert geography.levels(grid) == expected


def test_levels_reaches_level_3_for_dense_biome():
    grid = [[geography.MOUNTAINS] * 8 + [geography.PLAINS]] * 5
    levels = geography.levels(grid)
    assert levels["mountains"] == 3
    assert levels["river"] == 0
