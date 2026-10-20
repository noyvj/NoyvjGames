import dsl
import rooms
import run


def _room():
    """Return a real room from the game data for consistent layout testing."""
    return rooms.BY_ID["wake-up"]


class TestRunEdgeCases:
    def test_run_empty_main_program(self):
        """Empty main program should yield 'short' status without crashing."""
        r = _room()
        result = run.run(r.layout, {"main": []})
        assert result.status == "short"

    def test_run_missing_main_key(self):
        """Missing 'main' key defaults to empty list and yields 'short'."""
        r = _room()
        result = run.run(r.layout, {})
        assert result.status == "short"

    def test_run_zero_action_limit(self):
        """Zero action limit should stop immediately with 'loop' status."""
        r = _room()
        prog = dsl.from_text("main: F")
        result = run.run(r.layout, prog, action_limit=0)
        assert result.status == "loop"

    def test_run_smallest_positive_action_limit(self):
        """Limit of 1 should allow exactly one step before stopping."""
        r = _room()
        prog = dsl.from_text("main: F F")
        result = run.run(r.layout, prog, action_limit=1)
        assert result.status == "loop"
        assert result.actions == 1

    def test_run_large_action_limit(self):
        """A very large action limit should not interfere with normal execution."""
        r = _room()
        prog = dsl.from_text("main: F")
        result = run.run(r.layout, prog, action_limit=10**9)
        assert result.status == "short"

    def test_result_final_goals_after_halt(self):
        """final_goals() should return goal dicts even when the run halts."""
        r = _room()
        result = run.run(r.layout, dsl.from_text("main: F"), action_limit=1)
        goals = result.final_goals()
        assert isinstance(goals, list)
        for g in goals:
            assert "label" in g and "met" in g

    def test_result_cleared_property(self):
        """cleared property should mirror status == 'cleared'."""
        r = _room()
        result_short = run.run(r.layout, {"main": []})
        assert result_short.cleared is False

        result_clear = run.run(r.layout, dsl.from_text("main: F"))
        assert result_clear.cleared == (result_clear.status == "cleared")
