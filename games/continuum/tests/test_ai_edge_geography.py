"""Edge-case tests for geography.py."""

import geography
import sim


def test_clean_seed_boundary_and_type_limits():
    """clean_seed must accept 1 and SEED_MAX, reject 0, negatives, floats, bools, strings, and None."""
    assert geography.clean_seed(1) == 1
    assert geography.clean_seed(geography.SEED_MAX) == geography.SEED_MAX
    assert geography.clean_seed(0) is None
    assert geography.clean_seed(-1) is None
    assert geography.clean_seed(geography.SEED_MAX + 1) is None
    assert geography.clean_seed(True) is None
    assert geography.clean_seed(False) is None
    assert geography.clean_seed(3.14) is None
    assert geography.clean_seed("1") is None
    assert geography.clean_seed(None) is None


def test_generate_extreme_valid_seeds():
    """generate must return a valid WIDTH x HEIGHT grid for the smallest and largest allowed seeds."""
    grid_min = geography.generate(1)
    grid_max = geography.generate(geography.SEED_MAX)
    assert len(grid_min) == geography.HEIGHT and all(len(row) == geography.WIDTH for row in grid_min)
    assert len(grid_max) == geography.HEIGHT and all(len(row) == geography.WIDTH for row in grid_max)
    valid_biomes = set(geography.BIOMES) | {geography.PLAINS}
    assert set(cell for row in grid_min for cell in row) <= valid_biomes
    assert set(cell for row in grid_max for cell in row) <= valid_biomes


def test_level_of_zero_and_large_inputs():
    """level_of must return 0 for zero/negative, and clamp to 3 for inputs >= 8."""
    assert geography.level_of(0) == 0
    assert geography.level_of(-5) == 0
    assert geography.level_of(1) == 1
    assert geography.level_of(3) == 1
    assert geography.level_of(4) == 2
    assert geography.level_of(7) == 2
    assert geography.level_of(8) == 3
    assert geography.level_of(100) == 3


def test_effect_deltas_empty_and_plains_only():
    """effect_deltas must return an empty dict for no grid or a grid containing only plains."""
    assert geography.effect_deltas([]) == {}
    plains_grid = [[geography.PLAINS] * geography.WIDTH for _ in range(geography.HEIGHT)]
    assert geography.effect_deltas(plains_grid) == {}


def test_apply_effects_clamps_mult_and_storage_bonus():
    """apply_effects must clamp *_mult values to >= 0.1 and food_storage_bonus to >= -20.0."""
    base = dict(sim.NEUTRAL_EFFECTS)
    out = geography.apply_effects(base, 1)
    for k, v in out.items():
        if k.endswith("_mult"):
            assert v >= 0.1, f"{k} clamped below 0.1: {v}"
        elif k == "food_storage_bonus":
            assert v >= -20.0, f"food_storage_bonus clamped below -20.0: {v}"


def test_summary_text_empty_and_all_plains():
    """summary_text must return 'open land' for empty input and 'all plains' for a fully plains grid."""
    assert geography.summary_text([]) == "open land"
    plains_grid = [[geography.PLAINS] * geography.WIDTH for _ in range(geography.HEIGHT)]
    assert geography.summary_text(plains_grid) == "all plains"
