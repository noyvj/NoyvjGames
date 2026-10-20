"""Edge-case tests for achievements.py."""

from achievements import ACHIEVEMENTS, earned, view, SCENES_PULSE, SCENES_COMPOUND


def _mock_state():
    return type("MockState", (), {
        "spoken": False, "compound_spoken": False, "bridge_spoken": False,
        "flags": {},
        "notebook": type("N", (), {"entries": {}})(),
        "compound_notebook": type("N", (), {"entries": {}})(),
        "contact": {},
        "bridge_notebook": type("N", (), {"entries": {}})(),
        "scenes_seen": 0,
        "compound_scenes_seen": 0,
    })()


def _mock_station():
    return type("MockStation", (), {"lamps": 0})()


def _mock_tray():
    return type("MockTray", (), {"items": ()})()


def test_earned_empty_state_returns_empty_list():
    """Test that zero input yields no achievements."""
    state = _mock_state()
    station = _mock_station()
    tray = _mock_tray()
    assert earned(state, station, tray) == []


def test_earned_lamp_keeper_boundary():
    """Test lamp_keeper at exactly 7 lamps and one below."""
    state = _mock_state()
    tray = _mock_tray()

    station_low = _mock_station()
    station_low.lamps = 6
    assert "lamp_keeper" not in earned(state, station_low, tray)

    station_high = _mock_station()
    station_high.lamps = 7
    assert "lamp_keeper" in earned(state, station_high, tray)


def test_earned_scenes_seen_thresholds():
    """Test patient_listener at SCENES_PULSE - 1 and SCENES_COMPOUND - 1."""
    state = _mock_state()
    station = _mock_station()
    tray = _mock_tray()

    # Just below threshold
    state.scenes_seen = SCENES_PULSE - 1
    state.compound_scenes_seen = SCENES_COMPOUND - 1
    assert "patient_listener" not in earned(state, station, tray)

    # At threshold
    state.scenes_seen = SCENES_PULSE
    state.compound_scenes_seen = SCENES_COMPOUND
    assert "patient_listener" in earned(state, station, tray)


def test_earned_contact_flags_truthiness():
    """Test first_contact and second_contact with truthy/falsy contact values."""
    state = _mock_state()
    station = _mock_station()
    tray = _mock_tray()

    # Falsy contact
    assert "first_contact" not in earned(state, station, tray)
    assert "second_contact" not in earned(state, station, tray)

    # Truthy contact
    state.contact["pulse"] = True
    assert "first_contact" in earned(state, station, tray)

    state.contact["compound"] = True
    assert "second_contact" in earned(state, station, tray)


def test_view_includes_riddles_for_all_achievements():
    """Test that view returns every achievement with its riddle when none are earned."""
    state = _mock_state()
    station = _mock_station()
    tray = _mock_tray()
    result = view(state, station, tray)

    assert len(result) == len(ACHIEVEMENTS)
    for ach in result:
        assert "id" in ach and "label" in ach and "description" in ach and "riddle" in ach
        assert ach["earned"] is False
