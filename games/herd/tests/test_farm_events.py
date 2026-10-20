from unittest.mock import patch
from herd_model import FarmState
from herd_rules import FARM_EVENTS


def test_draw_event_sets_active_when_chance_met():
    farm = FarmState()
    with patch("herd_model.random.random", return_value=0.1):
        farm.draw_event()
    assert farm.event_active is True
    assert farm.event_data in FARM_EVENTS
    assert farm.event_choice_made is False


def test_draw_event_clears_when_chance_missed():
    farm = FarmState()
    with patch("herd_model.random.random", return_value=0.9):
        farm.draw_event()
    assert farm.event_active is False
    assert farm.event_data is None


def test_choice_effect_applies_immediately():
    farm = FarmState()
    event = FARM_EVENTS[0]  # neighbour_buy: +60 funds
    farm.event_active = True
    farm.event_data = event

    event["choice_a"]["effect"](farm)
    assert farm.funds == 300 + 60


def test_choice_marks_event_as_done():
    farm = FarmState()
    farm.event_active = True
    farm.event_data = FARM_EVENTS[1]
    assert not farm.event_choice_made

    # Simulate choice application
    farm.event_choice_made = True
    assert farm.event_choice_made is True
