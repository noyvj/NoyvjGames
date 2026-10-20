"""Tests for Campaign.revisitable_eras()."""

import save
import sim


def test_revisitable_eras_returns_completed_eras():
    campaign = save.Campaign()
    # Record snapshots for a subset of eras
    for era in sim.ERA_ORDER[:3]:
        campaign.record_era_snapshot(era)

    result = campaign.revisitable_eras()
    assert set(result) == set(sim.ERA_ORDER[:3])
    assert len(result) == 3


def test_revisitable_eras_returns_all_eras_when_all_completed():
    campaign = save.Campaign()
    for era in sim.ERA_ORDER:
        campaign.record_era_snapshot(era)

    result = campaign.revisitable_eras()
    assert result == list(sim.ERA_ORDER)


def test_revisitable_eras_returns_empty_list_when_no_eras_completed():
    campaign = save.Campaign()
    result = campaign.revisitable_eras()
    assert result == []
