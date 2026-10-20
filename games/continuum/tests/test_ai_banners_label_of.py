"""Tests for banners.label_of()."""

import banners


def test_normal_banner_labels():
    """label_of() returns the correct label for known banner IDs."""
    assert banners.label_of("cairn") == "Cairn Banner"
    assert banners.label_of("relay") == "Relay Chain"
    assert banners.label_of("plain") == "Plain Cloth"


def test_unknown_banner_falls_back_to_plain():
    """label_of() returns the plain cloth label for any unknown ID."""
    assert banners.label_of("nonexistent_id") == "Plain Cloth"
