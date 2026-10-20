import importlib.util
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
ROOT = GAME.parent.parent


def _load_content():
    """Load real game content using the same path resolution as other tests."""
    spec = importlib.util.spec_from_file_location("content", GAME / "content.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data = getattr(mod, "DATA", None) or getattr(mod, "CONTENT", None)
    if data is not None:
        return data
    loader = getattr(mod, "load", None)
    if callable(loader):
        return loader()
    return mod


def _make_plan(n=5):
    """Create a valid empty plan structure for testing."""
    return {"lanes": [[None] * n for _ in range(5)]}


def test_place_out_of_bounds_lane():
    """place should reject negative or too-large lane indices."""
    import planops
    content = _load_content()
    plan = _make_plan(5)
    new_plan, err = planops.place(content, plan, 5, -1, 0, "lockpick")
    assert err is not None
    new_plan, err = planops.place(content, plan, 5, 5, 0, "lockpick")
    assert err is not None


def test_place_out_of_bounds_beat():
    """place should reject negative or too-large beat indices."""
    import planops
    content = _load_content()
    plan = _make_plan(5)
    new_plan, err = planops.place(content, plan, 5, 0, -1, "lockpick")
    assert err is not None
    new_plan, err = planops.place(content, plan, 5, 0, 5, "lockpick")
    assert err is not None


def test_place_zero_beats():
    """place with n=0 should reject any placement."""
    import planops
    content = _load_content()
    plan = _make_plan(0)
    new_plan, err = planops.place(content, plan, 0, 0, 0, "lockpick")
    assert err is not None


def test_clear_out_of_bounds():
    """clear should handle negative or too-large lane/beat gracefully without crashing."""
    import planops
    content = _load_content()
    plan = _make_plan(5)
    new_plan = planops.clear(content, plan, 5, -1, 0)
    assert new_plan is not None
    new_plan = planops.clear(content, plan, 5, 0, 5)
    assert new_plan is not None


def test_move_lane_out_of_bounds():
    """move_lane should return the original plan when lane or direction is out of bounds."""
    import planops
    plan = _make_plan(5)
    new_plan, new_idx = planops.move_lane(plan, -1, 1)
    assert new_plan is plan
    new_plan, new_idx = planops.move_lane(plan, 5, -1)
    assert new_plan is plan


def test_move_cell_out_of_bounds():
    """move_cell should reject moves starting from or ending at invalid coordinates."""
    import planops
    content = _load_content()
    plan = _make_plan(5)
    new_plan, err = planops.move_cell(content, plan, 5, -1, 0, 0, 0)
    assert err is not None
    new_plan, err = planops.move_cell(content, plan, 5, 0, 5, 0, 0)
    assert err is not None
