"""Edge-case tests for banners.py."""

import banners


def test_clean_handles_edge_cases():
    """clean() should fall back to defaults for invalid or missing inputs."""
    assert banners.clean(None) == banners.DEFAULT_CHOICE
    assert banners.clean({}) == banners.DEFAULT_CHOICE
    assert banners.clean({"banner": 123, "flourish": []}) == banners.DEFAULT_CHOICE
    assert banners.clean({"banner": "unknown", "flourish": "unknown"}) == banners.DEFAULT_CHOICE


def test_get_handles_missing_or_invalid_ui():
    """get() returns defaults when ui is not a dict or lacks the key."""
    assert banners.get(None) == banners.DEFAULT_CHOICE
    assert banners.get("not a dict") == banners.DEFAULT_CHOICE
    assert banners.get({}) == banners.DEFAULT_CHOICE


def test_choose_rejects_locked_or_invalid_inputs():
    """choose() refuses locked items and invalid IDs, returning (False, reason)."""
    ui = {}
    ok, reason = banners.choose(ui, "nope", None, [], 0)
    assert ok is False and "catalogue" in reason.lower()
    ok, reason = banners.choose(ui, "sheaf", None, [], 0)
    assert ok is False and "not unlocked" in reason.lower()
    ok, _ = banners.choose(ui, "sheaf", None, ["reached_agrarian"], 0)
    assert ok is True
    ok, reason = banners.choose(ui, None, "pennants", ["reached_agrarian"], 0)
    assert ok is False and "not unlocked" in reason.lower()


def test_effective_falls_back_when_unlocks_are_lost():
    """effective() reverts to defaults if the current choice is no longer unlocked."""
    ui = {banners.KEY: {"banner": "chevron", "flourish": "pennants"}}
    assert banners.effective(ui, [], 1)["banner"] == "chevron"
    assert banners.effective(ui, [], 0)["banner"] == "plain"
    assert banners.effective(ui, [], 0)["flourish"] == "none"


def test_banner_svg_handles_extreme_widths_and_unknown_ids():
    """banner_svg() produces valid SVG for extreme widths and falls back gracefully."""
    svg = banners.banner_svg("plain", 0)
    assert svg.startswith("<svg") and 'width="0"' in svg
    svg_neg = banners.banner_svg("plain", -10)
    assert svg_neg.startswith("<svg")
    svg_unknown = banners.banner_svg("nonexistent_banner", 60)
    assert "Plain Cloth" in svg_unknown


def test_card_payload_handles_none_and_empty_inputs():
    """card_payload() returns safe defaults for None or empty choice."""
    payload_none = banners.card_payload(None)
    assert payload_none["banner_svg"] == "" and payload_none["flourish_svg"] == ""
    payload_empty = banners.card_payload({})
    assert payload_empty["banner_label"] == "Plain Cloth"
    assert payload_empty["flourish_label"] == "No flourish"
