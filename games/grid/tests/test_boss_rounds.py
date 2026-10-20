from grid_rules import boss_for_round
from grid_state import GridState


def test_boss_for_round_returns_none_before_interval():
    assert boss_for_round(0) is None
    assert boss_for_round(7) is None


def test_boss_for_round_cycles_correctly():
    expected_ids = ["heatwave", "polar_vortex", "dry_summer", "heatwave"]
    for i, round_num in enumerate([8, 16, 24, 32]):
        boss = boss_for_round(round_num)
        assert boss is not None
        assert boss["id"] == expected_ids[i]


def test_fresh_state_boss_fields():
    state = GridState()
    assert state.boss_rounds_enabled is False
    assert state.bosses_beaten == 0
    assert state.last_boss_message == ""
