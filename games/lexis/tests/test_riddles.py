"""Test that riddles are correctly attached to achievements."""

from achievements import ACHIEVEMENTS, view


def test_achievements_have_riddles():
    for ach in ACHIEVEMENTS:
        assert len(ach) == 4, f"Achievement {ach[0]} should have (id, label, desc, riddle)"
        assert ach[3], f"Riddle for {ach[0]} must not be empty"


def test_view_includes_riddles():
    class MockState:
        spoken = False
        compound_spoken = False
        bridge_spoken = False
        flags = {}
        notebook = type("N", (), {"entries": {}})()
        compound_notebook = type("N", (), {"entries": {}})()
        contact = {}
        bridge_notebook = type("N", (), {"entries": {}})()
        scenes_seen = 0
        compound_scenes_seen = 0

    class MockStation:
        lamps = 0

    class MockTray:
        items = ()

    result = view(MockState(), MockStation(), MockTray())
    for ach in result:
        assert "riddle" in ach, f"Achievement {ach['id']} missing riddle in view"
