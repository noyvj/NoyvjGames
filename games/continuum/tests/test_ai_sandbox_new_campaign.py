"""Tests for sandbox.new_campaign()."""

import sandbox
import sim


def test_new_campaign_sets_correct_era_and_research():
    """Normal case: a valid era produces a campaign with matching eras and all nodes known."""
    campaign = sandbox.new_campaign("industrial")
    assert campaign.state.era == "industrial"
    assert campaign.furthest_era == "industrial"
    assert campaign.tree.current_era == "industrial"
    assert sorted(campaign.tree.researched) == sorted(campaign.tree.nodes)


def test_new_campaign_works_for_all_valid_eras():
    """Normal case: every era in sim.ERA_ORDER is accepted and applied correctly."""
    for era in sim.ERA_ORDER:
        campaign = sandbox.new_campaign(era)
        assert campaign.state.era == era
        assert campaign.furthest_era == era
        assert campaign.tree.current_era == era


def test_new_campaign_falls_back_on_invalid_era():
    """Edge case: an unknown era string falls back to sim.FIRST_ERA."""
    campaign = sandbox.new_campaign("nonsense")
    assert campaign.state.era == sim.FIRST_ERA
    assert campaign.furthest_era == sim.FIRST_ERA
