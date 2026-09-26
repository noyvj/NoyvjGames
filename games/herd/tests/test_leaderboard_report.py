"""F21: the decoupling gap (score vs the pure-growth counterfactual) is sent
to the shared opt-in leaderboard widget after each round."""

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


def test_no_report_without_a_positive_gap(game_env):
    board = _install_board()
    game_env.advance_round()
    assert board.calls == []


def test_reports_the_gap_after_a_round(game_env):
    m = game_env.module
    board = _install_board()
    farm = game_env.farm
    farm.counterfactual_funds = 0.0
    farm.funds = 500.0
    game_env.advance_round()
    gap = m.farm.score() - m.farm.counterfactual_score()
    assert gap > 0
    assert board.calls == [("herd", "decoupling_gap", round(gap, 1), f"round {m.farm.round_number}")]


def test_missing_widget_is_harmless(game_env):
    game_env.farm.counterfactual_funds = 0.0
    game_env.farm.funds = 500.0
    game_env.advance_round()
    assert game_env.farm.round_number == 2
