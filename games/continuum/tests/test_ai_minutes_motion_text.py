"""Tests for motion_text() in minutes.py."""


import minutes


def test_research_motion_text():
    """Normal case: research kind produces study phrasing."""
    assert minutes.motion_text("research", "Fire-Keeping") == "Motion carried: the council resolves to study Fire-Keeping."


def test_build_motion_text():
    """Normal case: build kind produces build phrasing."""
    assert minutes.motion_text("build", "Shelter") == "Motion carried: the council resolves to build Shelter."


def test_era_motion_text():
    """Normal case: era kind produces enters phrasing."""
    assert minutes.motion_text("era", "Agrarian Age") == "Motion carried: the settlement enters Agrarian Age."


def test_order_motion_text():
    """Normal case: order kind produces standing order phrasing."""
    assert minutes.motion_text("order", "Clear the streets") == "Standing order: Clear the streets"


def test_empty_subject_edge_case():
    """Edge case: empty string subject leaves trailing space before punctuation."""
    assert minutes.motion_text("research", "") == "Motion carried: the council resolves to study ."
