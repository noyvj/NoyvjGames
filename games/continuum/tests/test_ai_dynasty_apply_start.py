"""Tests for dynasty.apply_start()."""


import dynasty


def test_apply_start_delivers_bonuses_on_first_season(game_env):
    """Normal case: applies starting perks when Dynasty is on and it is season 1."""
    game_env.module.campaign.ui[dynasty.KEY] = {
        "earned": 10, "owned": ["heirloom_granary", "heirloom_toolkit"]
    }
    campaign = game_env.module.campaign
    state = game_env.state

    assert state.season == 1
    bonuses = dynasty.apply_start(campaign)

    assert bonuses is not None
    assert bonuses["food"] == 4.0
    assert bonuses["tools"] == 1.0
    assert state.resources["food"] >= 4.0
    assert state.resources["tools"] >= 1.0
    assert dynasty.get_run(campaign.ui)["start"] is True


def test_apply_start_does_not_apply_when_dynasty_is_off(game_env):
    """Normal case: returns empty dict and marks start=True even when perks are switched off."""
    game_env.module.campaign.ui[dynasty.KEY] = {
        "earned": 10, "owned": ["heirloom_granary"], "off": True
    }
    campaign = game_env.module.campaign

    bonuses = dynasty.apply_start(campaign)

    assert bonuses == {}
    assert dynasty.get_run(campaign.ui)["start"] is True


def test_apply_start_does_not_apply_after_first_season(game_env):
    """Edge case: returns None and marks start=True when past season 1, preventing future application."""
    game_env.module.campaign.ui[dynasty.KEY] = {
        "earned": 10, "owned": ["heirloom_granary"]
    }
    campaign = game_env.module.campaign

    game_env.advance_season()
    assert game_env.state.season == 2

    bonuses = dynasty.apply_start(campaign)

    assert bonuses is None
    assert dynasty.get_run(campaign.ui)["start"] is True
