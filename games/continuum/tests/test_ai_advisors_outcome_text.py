"""Tests for advisors.outcome_text()."""

import advisors


def test_outcome_text_sound_followed_food(game_env):
    """A sound advice that was taken reports the actual food value."""
    item = {
        "id": "marit",
        "quality": "sound",
        "status": "followed",
        "metric": "food",
        "net_before": 10.0,
        "net_gain": 5.0,
        "score_delta": 0.0,
    }
    state = game_env.module.state
    effects = {}
    text = advisors.outcome_text(item, state, effects)
    assert "Marit Oakhand (taken)" in text
    assert f"food went {item['net_before']:.1f} to" in text
    assert "predicted +5.0 over doing nothing." in text
    assert "Sound advice." in text


def test_outcome_text_narrow_not_taken_materials(game_env):
    """A narrow advice that was ignored reports the predicted gain and sustainability cost."""
    item = {
        "id": "ines",
        "quality": "narrow",
        "status": "not taken",
        "metric": "materials",
        "net_before": 20.0,
        "net_gain": -2.0,
        "score_delta": -3.5,
    }
    state = game_env.module.state
    effects = {}
    text = advisors.outcome_text(item, state, effects)
    assert "Inès Calder (not taken)" in text
    assert "would have been -2.0 materials for -3.5 sustainability." in text
    assert "Narrow advice: it helped their corner but cost the settlement as a whole." in text


def test_outcome_text_empty_not_taken_headroom(game_env):
    """An empty headroom advice that was ignored reports zero gain and uses the correct unit."""
    item = {
        "id": "teodor",
        "quality": "empty",
        "status": "not taken",
        "metric": "headroom",
        "net_before": 5.0,
        "net_gain": 0.0,
        "score_delta": 1.0,
    }
    state = game_env.module.state
    effects = {}
    text = advisors.outcome_text(item, state, effects)
    assert "Teodor Vance (not taken)" in text
    assert "would have been +0.0 places to live for +1.0 sustainability." in text
    assert "It would not have changed much." in text
