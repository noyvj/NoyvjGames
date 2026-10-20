"""Tests for ResearchTree.era_reached()."""

import research
import sim


def test_era_reached_returns_true_for_current_and_past_eras():
    tree = research.build_tree(current_era="classical")
    current_idx = sim.ERA_ORDER.index("classical")
    for era in sim.ERA_ORDER[:current_idx + 1]:
        assert tree.era_reached(era) is True


def test_era_reached_returns_false_for_future_eras():
    tree = research.build_tree(current_era="classical")
    current_idx = sim.ERA_ORDER.index("classical")
    for era in sim.ERA_ORDER[current_idx + 1:]:
        assert tree.era_reached(era) is False


def test_era_reached_at_first_era_boundary():
    tree = research.build_tree(current_era=sim.FIRST_ERA)
    assert tree.era_reached(sim.FIRST_ERA) is True
    if len(sim.ERA_ORDER) > 1:
        assert tree.era_reached(sim.ERA_ORDER[1]) is False
