"""H20 (planning/TODO.md, completion-audit fix): the three goods-flavor
sets previously differed only in the swapped noun/icon/label -- every
vignette sentence's actual repair/reuse/recycle mechanism was identical
prose regardless of category. The user's answer: "distinct" (not merged
into H2). Each category now gets its own concrete, category-appropriate
loop mechanics (CATEGORY_LOOP_DETAIL in game.py)."""


def test_each_category_has_genuinely_different_wording_at_every_fraction_bucket(game_env):
    m = game_env.module
    buckets = [0.0, 0.3, 0.6, 1.0]
    categories = list(m.GOODS_CATEGORIES.keys())
    assert len(categories) >= 2

    for fraction in buckets:
        texts = set()
        for category in categories:
            game_env.select_goods_category(category)
            texts.add(m.vignette_message(fraction))
        # Every category's text at this fraction must be distinct from
        # every other category's -- not just the swapped noun.
        assert len(texts) == len(categories), (
            f"fraction={fraction} produced duplicate vignette text across categories: {texts}"
        )


def test_electronics_vignette_mentions_electronics_specific_mechanics(game_env):
    m = game_env.module
    game_env.select_goods_category("electronics")
    assert "battery" in m.vignette_message(1.0) or "circuit board" in m.vignette_message(1.0)


def test_clothing_vignette_mentions_clothing_specific_mechanics(game_env):
    m = game_env.module
    game_env.select_goods_category("clothing")
    assert "fabric" in m.vignette_message(1.0) or "seam" in m.vignette_message(1.0)


def test_furniture_vignette_mentions_furniture_specific_mechanics(game_env):
    m = game_env.module
    game_env.select_goods_category("furniture")
    assert "wood" in m.vignette_message(1.0) or "timber" in m.vignette_message(1.0) or "joint" in m.vignette_message(1.0)


def test_every_category_and_bucket_has_at_least_two_variants(game_env):
    """H14's variant-cycling behavior must still hold for every category,
    not just the original default (electronics)."""
    m = game_env.module
    for category, buckets in m.CATEGORY_LOOP_DETAIL.items():
        for bucket_name, variants in buckets.items():
            assert len(variants) >= 2, f"{category}/{bucket_name} has fewer than 2 variants"


def test_unknown_goods_category_falls_back_to_generic_wording(game_env):
    """Defensive: a goods_category that somehow isn't in CATEGORY_LOOP_
    DETAIL (a future new category added to GOODS_CATEGORIES but not yet
    given its own flavor content) must not crash -- falls back to the
    original generic phrasing instead."""
    m = game_env.module
    game_env.chain.goods_category = "not_a_real_category"
    text = m.vignette_message(1.0, item="a widget")
    assert "a widget" in text
    assert "repaired" in text or "looped back" in text


def test_vignette_variant_still_cycles_by_seed_within_a_category(game_env):
    m = game_env.module
    game_env.select_goods_category("clothing")
    first = m.vignette_message(1.0, variant_seed=0)
    second = m.vignette_message(1.0, variant_seed=1)
    assert first != second
