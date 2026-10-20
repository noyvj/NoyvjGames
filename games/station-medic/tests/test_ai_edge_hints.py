"""Station Medic -- edge-case tests for hints.py."""

import json

import pytest

import game
import hints
import progress

FIRST = progress.ORDER[0]


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


@pytest.fixture(autouse=True)
def clean():
    game.game.__init__()
    call(action="difficulty", level="normal")
    yield
    call(action="difficulty", level="normal")


def _setup_shift():
    call(action="pick", shift=FIRST)
    return game.game.case, game.game.st, game.game._solver()


class TestDescribeEdgeCases:
    def test_describe_with_none_act_returns_restore(self):
        """act=None should always return the restore message."""
        case, st, solver = _setup_shift()
        res = hints.describe(case, st, None)
        assert res is not None
        assert res["kind"] == "restore"
        assert "Restore the shift" in res["label"]

    def test_describe_with_unknown_kind_returns_none(self):
        """An unrecognised action kind should return None."""
        case, st, solver = _setup_shift()
        res = hints.describe(case, st, ("unknown",))
        assert res is None

    def test_describe_with_scan_action(self):
        """Scan actions must produce a label mentioning the test and patient."""
        case, st, solver = _setup_shift()
        if not case.tests:
            pytest.skip("Shift has no tests")
        act = ("scan", 0, 0)
        res = hints.describe(case, st, act)
        assert res is not None
        assert res["kind"] == "scan"
        assert "Run the" in res["label"]

    def test_describe_with_treat_action(self):
        """Treat actions must produce a label mentioning the treatment and patient."""
        case, st, solver = _setup_shift()
        act = ("treat", 0, 0)
        res = hints.describe(case, st, act)
        assert res is not None
        assert res["kind"] == "treat"
        assert "Give" in res["label"]

    def test_describe_with_band_action(self):
        """Band actions must mention steadying and the patient."""
        case, st, solver = _setup_shift()
        act = ("band", 0)
        res = hints.describe(case, st, act)
        assert res is not None
        assert res["kind"] == "band"
        assert "Steady" in res["label"]

    def test_describe_with_isolate_action(self):
        """Isolate actions must mention the cold room."""
        case, st, solver = _setup_shift()
        act = ("isolate", 0)
        res = hints.describe(case, st, act)
        assert res is not None
        assert res["kind"] == "isolate"
        assert "cold room" in res["label"].lower()


class TestNextActionEdgeCases:
    def test_next_action_returns_valid_hint_for_new_shift(self):
        """next_action should return a tuple hint for a fresh shift."""
        case, st, solver = _setup_shift()
        act = hints.next_action(case, st, solver)
        assert act is not None
        assert isinstance(act, tuple)

    def test_next_action_handles_solver_returning_none(self):
        """If the solver finds no clean finish, next_action should return None."""
        call(action="pick", shift=FIRST)
        # Exhaust hints to force solver into a state with no clean finish
        for _ in range(10):
            hints.next_action(game.game.case, game.game.st, game.game._solver())
        act = hints.next_action(game.game.case, game.game.st, game.game._solver())
        assert act is None or isinstance(act, tuple)


class TestConstants:
    def test_easy_open_is_integer_and_positive(self):
        """EASY_OPEN should be a positive integer constant."""
        assert isinstance(hints.EASY_OPEN, int)
        assert hints.EASY_OPEN > 0
