"""Edge-case tests for heritage.py."""


import heritage
import sim


def test_demolished_handles_non_dict_and_missing_key():
    assert heritage.demolished(None) == []
    assert heritage.demolished(0) == []
    assert heritage.demolished("") == []
    assert heritage.demolished({}) == []
    assert heritage.demolished({"other": "data"}) == []


def test_demolished_filters_invalid_items_in_list():
    ui = {heritage.KEY: {"demolished": [123, None, "bogus", 4.5]}}
    assert heritage.demolished(ui) == []


def test_sites_before_rejects_invalid_era_and_returns_empty_for_first_era():
    assert heritage.sites_before(None, {}) == []
    assert heritage.sites_before("nonexistent", {}) == []
    # Tribal is the first era, so nothing is before it.
    assert heritage.sites_before("tribal", {}) == []


def test_culture_delta_max_and_min_values():
    ui_all_kept = {}
    ui_all_demolished = {heritage.KEY: {"demolished": list(heritage.SITES.keys())}}

    max_delta = heritage.culture_delta(ui_all_kept, "relay")
    min_delta = heritage.culture_delta(ui_all_demolished, "relay")

    assert max_delta == round(len(heritage.SITES) * heritage.KEEP_BONUS, 4)
    assert min_delta == round(-len(heritage.SITES) * heritage.DEMOLISH_PENALTY, 4)


def test_apply_effects_clamps_culture_bonus_to_negative_half():
    effects = {"culture_bonus": -1.0}
    ui_all_demolished = {heritage.KEY: {"demolished": list(heritage.SITES.keys())}}

    out = heritage.apply_effects(effects, ui_all_demolished, "relay", False)
    assert out["culture_bonus"] == -0.5


def test_demolish_gain_bounds():
    min_gain = heritage.demolish_gain("tribal")
    max_gain = heritage.demolish_gain("space")

    assert min_gain == heritage.DEMOLISH_MATERIALS_BASE
    assert max_gain == heritage.DEMOLISH_MATERIALS_BASE + heritage.DEMOLISH_MATERIALS_PER_ERA * sim.era_index("space")


def test_preview_text_returns_empty_string_for_unknown_era():
    assert heritage.preview_text("bogus", {}) == ""
    assert heritage.preview_text(None, {}) == ""
