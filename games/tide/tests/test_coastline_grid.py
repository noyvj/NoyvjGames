"""Milestone 4: tile-grid coastline — state layer only (thresholds), not
rendering. Water rises from the bottom row up as sea_level crosses each
row's threshold.
"""


def test_row_threshold_increases_toward_the_top(game_env):
    # Row 0 is the top (highest ground); the last row is the bottom
    # (lowest ground, lowest threshold, floods first).
    bottom_row = game_env.module.COASTLINE_ROWS - 1
    assert game_env.module.row_flood_threshold(0) > game_env.module.row_flood_threshold(bottom_row)


def test_bottom_row_threshold_equals_one_step(game_env):
    bottom_row = game_env.module.COASTLINE_ROWS - 1
    assert game_env.module.row_flood_threshold(bottom_row) == 15.0


def test_top_row_threshold_equals_full_height(game_env):
    assert game_env.module.row_flood_threshold(0) == 15.0 * game_env.module.COASTLINE_ROWS


def test_tile_is_land_below_its_threshold(game_env):
    bottom_row = game_env.module.COASTLINE_ROWS - 1
    assert game_env.module.tile_row_state(bottom_row, sea_level=14.9) == "land"


def test_tile_is_flooded_at_or_above_its_threshold(game_env):
    bottom_row = game_env.module.COASTLINE_ROWS - 1
    assert game_env.module.tile_row_state(bottom_row, sea_level=15.0) == "flooded"
    assert game_env.module.tile_row_state(bottom_row, sea_level=20.0) == "flooded"


def test_coastline_grid_is_all_land_at_zero_sea_level(game_env):
    grid = game_env.module.coastline_grid(0.0)
    assert all(tile == "land" for row in grid for tile in row)


def test_coastline_grid_dimensions(game_env):
    grid = game_env.module.coastline_grid(0.0)
    assert len(grid) == game_env.module.COASTLINE_ROWS
    assert all(len(row) == game_env.module.COASTLINE_COLS for row in grid)


def test_coastline_grid_partially_floods_as_sea_level_rises(game_env):
    # Enough to flood the bottom two rows (thresholds 15, 30) but not the rest.
    grid = game_env.module.coastline_grid(30.0)
    bottom_row = game_env.module.COASTLINE_ROWS - 1
    second_from_bottom = game_env.module.COASTLINE_ROWS - 2
    third_from_bottom = game_env.module.COASTLINE_ROWS - 3
    assert all(tile == "flooded" for tile in grid[bottom_row])
    assert all(tile == "flooded" for tile in grid[second_from_bottom])
    assert all(tile == "land" for tile in grid[third_from_bottom])


def test_coastline_grid_fully_floods_at_max_threshold(game_env):
    grid = game_env.module.coastline_grid(15.0 * game_env.module.COASTLINE_ROWS)
    assert all(tile == "flooded" for row in grid for tile in row)


def test_flooding_advances_as_seasons_pass(game_env):
    # advance_season() raises sea_level by 5/season; after 3 seasons
    # (sea_level=15) the bottom row should just barely flood.
    game_env.advance_season()
    game_env.advance_season()
    game_env.advance_season()
    bottom_row = game_env.module.COASTLINE_ROWS - 1
    grid = game_env.module.coastline_grid(game_env.state.sea_level)
    assert all(tile == "flooded" for tile in grid[bottom_row])


def test_render_creates_the_full_tile_count(game_env):
    game_env.module.render()
    expected = game_env.module.COASTLINE_ROWS * game_env.module.COASTLINE_COLS
    assert len(game_env.elements["coastline-grid"].children) == expected


def test_render_tiles_reflect_land_state_initially(game_env):
    game_env.module.render()
    tile = game_env.elements["coastline-tile-0-0"]
    assert "coastline-land" in tile.className


def test_render_tiles_reflect_flooded_state_after_rise(game_env):
    for _ in range(3):
        game_env.advance_season()  # sea_level = 15, bottom row floods
    game_env.module.render()
    bottom_row = game_env.module.COASTLINE_ROWS - 1
    tile = game_env.elements[f"coastline-tile-{bottom_row}-0"]
    assert "coastline-flooded" in tile.className
    top_tile = game_env.elements["coastline-tile-0-0"]
    assert "coastline-land" in top_tile.className
