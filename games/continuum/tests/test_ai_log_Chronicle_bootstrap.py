"""Tests for Chronicle.bootstrap() in log.py."""

import unittest.mock as mock

import log
import sustainability


class FakeState:
    """Minimal state object matching what bootstrap and sustainability expect."""

    def __init__(self, population=6, hard_mode=False, food=0, materials=0, knowledge=0, fed_fraction=1.0):
        self.population = population
        self.hard_mode = hard_mode
        self.food = food
        self.materials = materials
        self.knowledge = knowledge
        self.fed_fraction = fed_fraction


class FakeTree:
    """Minimal tree object matching what bootstrap expects."""

    def __init__(self, researched=None):
        self.researched = researched or []


def test_bootstrap_captures_empty_baseline_for_new_campaign():
    """Normal case: brand-new campaign starts with low population and no research."""
    state = FakeState(population=6)
    tree = FakeTree()
    effects = {}

    chronicle = log.Chronicle()
    with mock.patch("sustainability.score", return_value=50.0):
        chronicle.bootstrap(state, tree, effects)

    assert chronicle._population_milestones_hit == set()
    assert chronicle._researched_seen == set()
    assert chronicle._last_score_label in sustainability.SCORE_LABELS


def test_bootstrap_captures_existing_progress_from_save():
    """Normal case: loading a save that already passed milestones and researched nodes."""
    state = FakeState(population=40)
    tree = FakeTree(researched=["node_a", "node_b"])
    effects = {}

    chronicle = log.Chronicle()
    with mock.patch("sustainability.score", return_value=50.0):
        chronicle.bootstrap(state, tree, effects)

    assert chronicle._population_milestones_hit == {10, 15, 25, 40}
    assert chronicle._researched_seen == {"node_a", "node_b"}


def test_bootstrap_respects_hard_mode_flag():
    """Edge case: hard mode changes the sustainability score label calculation."""
    state_normal = FakeState(population=6, hard_mode=False)
    state_hard = FakeState(population=6, hard_mode=True)
    tree = FakeTree()
    effects = {}

    chronicle_normal = log.Chronicle()
    with mock.patch("sustainability.score", return_value=50.0):
        chronicle_normal.bootstrap(state_normal, tree, effects)

    chronicle_hard = log.Chronicle()
    with mock.patch("sustainability.score", return_value=50.0):
        chronicle_hard.bootstrap(state_hard, tree, effects)

    expected_normal = sustainability.score_label(50.0, False)
    expected_hard = sustainability.score_label(50.0, True)

    assert chronicle_normal._last_score_label == expected_normal
    assert chronicle_hard._last_score_label == expected_hard
