"""E23: a survived run's average event severity is sent to the shared opt-in
'hardest schedule survived' leaderboard."""

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


def _finish_run(env):
    while not env.run.is_complete():
        env.resolve_event()


def test_a_survived_run_reports_its_average_severity(game_env):
    m = game_env.module
    board = _install_board()
    game_env.run.resources = 10 ** 9
    _finish_run(game_env)
    assert len(board.calls) == 1
    game, name, score, detail = board.calls[0]
    assert (game, name, detail) == ("aftermath", "hardest_schedule", "run 1")
    assert score == round(m.average_severity(game_env.run.event_log), 3) == 1.0


def test_a_run_that_ends_with_nothing_left_reports_nothing(game_env):
    board = _install_board()
    game_env.run.resources = 0.0
    game_env.run.growth_capacity = 0
    _finish_run(game_env)
    assert game_env.run.resources <= 0
    assert board.calls == []


def test_missing_widget_is_harmless(game_env):
    game_env.run.resources = 10 ** 9
    _finish_run(game_env)
    assert game_env.run.is_complete()
