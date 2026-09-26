"""A29: the tick at which every world was first terraformed feeds the opt-in
community 'fastest full completion' leaderboard."""

import sys
import types


class _FakeBoard:
    def __init__(self):
        self.calls = []

    def report(self, game, board, score, detail):
        self.calls.append((game, board, score, detail))


def _install_board():
    board = _FakeBoard()
    sys.modules["js"].window = types.SimpleNamespace(NoyvjLeaderboard=board)
    return board


def _terraform_everything(m):
    for planet in m.PLANETS:
        m.planet_state[planet]["terraform_progress"] = m.TERRAFORM_MAX


def test_not_recorded_before_the_system_is_terraformed(game_env):
    m = game_env.module
    m._note_full_completion()
    assert m.full_system_completed_tick is None
    assert "full_system_completed_tick" not in m.get_state()


def test_records_the_tick_once_and_keeps_it(game_env):
    m = game_env.module
    _terraform_everything(m)
    m.total_ticks = 1234
    m._note_full_completion()
    assert m.full_system_completed_tick == 1234
    m.total_ticks = 9999
    m._note_full_completion()
    assert m.full_system_completed_tick == 1234


def test_reports_simulated_seconds_once_per_page_load(game_env):
    m = game_env.module
    board = _install_board()
    _terraform_everything(m)
    m.total_ticks = 600
    m._note_full_completion()
    m._note_full_completion()
    assert board.calls == [("sol", "fastest_completion", 600 * (m.TICK_INTERVAL_MS / 1000), "prestige 0")]


def test_no_leaderboard_script_means_no_error(game_env):
    m = game_env.module
    _terraform_everything(m)
    m._note_full_completion()
    assert m.full_system_completed_tick is not None


def test_tick_path_records_it(game_env):
    m = game_env.module
    _terraform_everything(m)
    m.total_ticks = 50
    m._check_new_achievements_for_toast()
    assert m.full_system_completed_tick == 50


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    m.full_system_completed_tick = 777
    state = m.get_state()
    assert state["full_system_completed_tick"] == 777
    m.full_system_completed_tick = None
    m.load_state(state)
    assert m.full_system_completed_tick == 777
    for bad in (True, -5, "9", 3.5, None):
        m.load_state({**state, "full_system_completed_tick": bad})
        assert m.full_system_completed_tick is None
    m.load_state({k: v for k, v in state.items() if k != "full_system_completed_tick"})
    assert m.full_system_completed_tick is None


def test_reload_lets_the_page_report_again(game_env):
    m = game_env.module
    board = _install_board()
    m.load_state({"full_system_completed_tick": 100})
    m._report_full_completion()
    m.load_state({"full_system_completed_tick": 100})
    m._report_full_completion()
    assert len(board.calls) == 2
