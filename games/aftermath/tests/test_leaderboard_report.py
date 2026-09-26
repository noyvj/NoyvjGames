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


def test_state_carries_the_write_only_skill_strength_number(game_env):
    """E9: the community resilience index reads this from saves; it is never loaded back."""
    m = game_env.module
    state = m.get_state()
    assert state["skill_tree_strength"] == m.skill_tree_strength() == 0
    m.skill_tree.unlocked.add(next(iter(m.SKILLS)))
    assert m.get_state()["skill_tree_strength"] == 1
    m.load_state(state)  # extra key is ignored, load still works
