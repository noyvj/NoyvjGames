"""Iteration Pass 2: adaptation tech tree — dampening no longer scales
continuously with adaptation capacity. Sustained investment (cumulative
capacity, which never decays) crosses thresholds that unlock discrete,
stronger tiers, each with its own visible coastline seawall signature.
"""


def test_starts_at_tier_zero(game_env):
    assert game_env.state.current_tier_index() == 0
    assert game_env.state.current_tier()["name"] == "No adaptation"


def test_tier_unchanged_below_first_threshold(game_env):
    game_env.invest("adaptation")
    game_env.invest("adaptation")  # 2 < threshold of 3
    assert game_env.state.current_tier_index() == 0


def test_tier_advances_at_first_threshold(game_env):
    for _ in range(3):
        game_env.invest("adaptation")
    assert game_env.state.current_tier_index() == 1
    assert game_env.state.current_tier()["name"] == "Sandbag berms"


def test_tier_advances_at_second_threshold(game_env):
    for _ in range(6):
        game_env.invest("adaptation")
    assert game_env.state.current_tier_index() == 2
    assert game_env.state.current_tier()["name"] == "Seawalls"


def test_tier_advances_at_final_threshold(game_env):
    for _ in range(10):
        game_env.invest("adaptation")
    assert game_env.state.current_tier_index() == 3
    assert game_env.state.current_tier()["name"] == "Reinforced seawalls"
    assert game_env.state.dampening_fraction() == game_env.module.MAX_DAMPENING


def test_tier_never_regresses_below_investment(game_env):
    for _ in range(10):
        game_env.invest("adaptation")
    assert game_env.state.current_tier_index() == 3
    # Investment is cumulative and never spent back down elsewhere in the
    # game, so there's no path to losing a tier once reached.
    assert game_env.state.capacity["adaptation"] == 10


def test_next_tier_progress_text_before_any_investment(game_env):
    text = game_env.state.next_tier_progress_text()
    assert "0/3" in text
    assert "Sandbag berms" in text


def test_next_tier_progress_text_at_max_tier(game_env):
    for _ in range(10):
        game_env.invest("adaptation")
    text = game_env.state.next_tier_progress_text()
    assert "maximum" in text.lower()


def test_seawall_rows_grow_with_tier(game_env):
    assert game_env.module._is_seawall_row(game_env.module.COASTLINE_ROWS - 1, 0) is False
    assert game_env.module._is_seawall_row(game_env.module.COASTLINE_ROWS - 1, 1) is True
    assert game_env.module._is_seawall_row(game_env.module.COASTLINE_ROWS - 2, 1) is False
    assert game_env.module._is_seawall_row(game_env.module.COASTLINE_ROWS - 2, 2) is True


def test_render_shows_adaptation_tier(game_env):
    for _ in range(3):
        game_env.invest("adaptation")
    game_env.module.render()
    assert "Sandbag berms" in game_env.elements["adaptation-tier-display"].innerText


def test_render_applies_seawall_class_to_bottom_rows(game_env):
    for _ in range(3):
        game_env.invest("adaptation")
    game_env.module.render()
    bottom_tile = game_env.elements[f"coastline-tile-{game_env.module.COASTLINE_ROWS - 1}-0"]
    assert "coastline-seawall" in bottom_tile.className


def test_render_does_not_apply_seawall_class_at_tier_zero(game_env):
    game_env.module.render()
    bottom_tile = game_env.elements[f"coastline-tile-{game_env.module.COASTLINE_ROWS - 1}-0"]
    assert "coastline-seawall" not in bottom_tile.className
