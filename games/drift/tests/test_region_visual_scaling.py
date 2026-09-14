"""Addendum I2: the region skyline previously rendered a fixed six
buildings regardless of real capacity. Now region_visual_building_count()
reveals one more of the six authored buildings per
REGION_VISUAL_CAPACITY_PER_BUILDING of total capacity, and
region_visual_height_scale() grows a shared vertical scale factor applied
to every revealed building's own authored height.
"""


def test_one_building_visible_at_zero_capacity(game_env):
    module = game_env.module
    assert module.region_visual_building_count(0.0) == 1


def test_building_count_grows_with_capacity(game_env):
    module = game_env.module
    per_building = module.REGION_VISUAL_CAPACITY_PER_BUILDING
    assert module.region_visual_building_count(per_building) == 2
    assert module.region_visual_building_count(per_building * 2) == 3


def test_building_count_caps_at_six(game_env):
    module = game_env.module
    assert module.region_visual_building_count(10_000.0) == len(module.REGION_VISUAL_BUILDING_IDS)


def test_height_scale_has_a_visible_floor_at_zero_capacity(game_env):
    module = game_env.module
    assert module.region_visual_height_scale(0.0) == module.REGION_VISUAL_MIN_HEIGHT_SCALE


def test_height_scale_caps_at_one(game_env):
    module = game_env.module
    assert module.region_visual_height_scale(10_000.0) == 1.0


def test_height_scale_grows_with_capacity(game_env):
    module = game_env.module
    low = module.region_visual_height_scale(10.0)
    high = module.region_visual_height_scale(100.0)
    assert high > low


def test_render_hides_buildings_beyond_current_capacity_tier(game_env):
    game_env.module.render()
    # Fresh region: zero capacity -> only the first building is visible.
    assert game_env.elements["region-visual-building-a"].hidden is False
    assert game_env.elements["region-visual-building-b"].hidden is True
    assert game_env.elements["region-visual-building-f"].hidden is True


def test_render_reveals_a_building_after_enough_investment(game_env):
    per_building = game_env.module.REGION_VISUAL_CAPACITY_PER_BUILDING
    # Housing gives +10 capacity/investment (CAPACITY_PER_INVESTMENT) --
    # enough clicks to clear one reveal tier.
    clicks = 0
    while game_env.region.total_capacity() < per_building and clicks < 20:
        game_env.invest("housing")
        clicks += 1
    game_env.module.render()
    assert game_env.elements["region-visual-building-b"].hidden is False


def test_render_sets_a_transform_style_on_every_building(game_env):
    game_env.module.render()
    for building_id in game_env.module.REGION_VISUAL_BUILDING_IDS:
        el = game_env.elements[f"region-visual-building-{building_id}"]
        assert "scaleY(" in el.style.transform
