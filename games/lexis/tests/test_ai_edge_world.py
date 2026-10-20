from pulse import PULSE, say_lamps, MAX_NUMBER
from world import Station, describe, react

import pytest


def test_station_to_dict_defaults():
    """Test to_dict with default (zero) values."""
    assert Station().to_dict() == {"lamps": 0, "door": "shut"}


def test_station_from_dict_accepts_boundary_lamp_counts():
    """Test from_dict accepts smallest and largest allowed lamp counts."""
    low = Station.from_dict({"lamps": 0, "door": "shut"})
    assert low.lamps == 0
    high = Station.from_dict({"lamps": MAX_NUMBER, "door": "open"})
    assert high.lamps == MAX_NUMBER


def test_station_from_dict_rejects_invalid_door_state():
    """Test from_dict rejects door states other than 'open' or 'shut'."""
    with pytest.raises(ValueError):
        Station.from_dict({"lamps": 0, "door": "ajar"})


def test_describe_handles_zero_and_max_lamp_counts():
    """Test describe wording for zero and MAX_NUMBER lamps."""
    assert "no lamps are lit" in describe(Station(0, "shut"))
    assert f"{MAX_NUMBER} lamps are lit" in describe(Station(MAX_NUMBER, "open"))


def test_react_valid_boundary_inputs():
    """Test react handles smallest and largest allowed lamp counts correctly."""
    r_low = react(say_lamps(0), Station(3, "shut"), PULSE)
    assert r_low.understood and r_low.station.lamps == 0
    r_high = react(say_lamps(MAX_NUMBER), Station(3, "shut"), PULSE)
    assert r_high.understood and r_high.station.lamps == MAX_NUMBER
