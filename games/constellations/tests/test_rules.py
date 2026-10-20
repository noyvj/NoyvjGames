"""Tests for the 'Rules in plain words' feature (FY-68)."""

import info


def test_info_view_contains_plain_rules():
    v = info.view()
    assert "plain_rules_heading" in v
    assert "plain_rules" in v
    assert isinstance(v["plain_rules"], list)
    assert len(v["plain_rules"]) >= 3
    for rule in v["plain_rules"]:
        assert isinstance(rule, str) and len(rule) > 0


def test_plain_rules_are_accessible():
    """Ensure the rules text is simple and does not rely on jargon."""
    v = info.view()
    text = " ".join(v["plain_rules"]).lower()
    for word in ("star", "line", "number"):
        assert word in text, "Rules should mention stars, lines, or numbers"
