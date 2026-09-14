"""C7: a plant-mix bar chart -- composition of total standing capacity by
plant type, so a player can see the grid's actual mix at a glance rather
than reading six separate count numbers."""


def test_capacity_share_is_zero_on_an_empty_grid(game_env):
    for plant_type in game_env.module.PLANT_TYPES:
        assert game_env.state.capacity_share(plant_type) == 0.0


def test_capacity_share_reflects_the_actual_mix(game_env):
    game_env.build("coal")  # 20 cap
    game_env.build("solar")  # 10 cap -- total 30
    assert game_env.state.capacity_share("coal") == 20 / 30
    assert game_env.state.capacity_share("solar") == 10 / 30
    assert game_env.state.capacity_share("gas") == 0.0


def test_capacity_shares_sum_to_one_across_a_mixed_grid(game_env):
    game_env.state.funds = 10_000
    for plant_type in game_env.module.PLANT_TYPES:
        game_env.build(plant_type)
    # Only generation types belong in a generation-mix chart -- battery is
    # storage, deliberately excluded (see GENERATION_TYPES' comment).
    total_share = sum(game_env.state.capacity_share(t) for t in game_env.module.GENERATION_TYPES)
    assert total_share == 1.0


def test_battery_has_no_share_of_the_generation_mix(game_env):
    """Battery capacity must never be counted as part of "what's
    generating" -- total_capacity() (the mix chart's denominator) is
    generation-only."""
    game_env.build("battery")
    game_env.build("coal")
    assert game_env.state.capacity_share("coal") == 1.0


def test_render_updates_the_mix_bar_widths_and_labels(game_env):
    game_env.build("coal")
    game_env.build("solar")
    game_env.module.render()
    assert game_env.elements["coal-mix-bar"].style.width == "67%"
    assert game_env.elements["coal-mix-pct"].innerText == "67%"
    assert game_env.elements["solar-mix-bar"].style.width == "33%"
    assert game_env.elements["gas-mix-pct"].innerText == "0%"


def test_render_shows_zero_mix_on_a_fresh_game(game_env):
    game_env.module.render()
    for plant_type in game_env.module.GENERATION_TYPES:
        assert game_env.elements[f"{plant_type}-mix-pct"].innerText == "0%"
