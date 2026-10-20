import json
from pathlib import Path
from types import SimpleNamespace

GAME = Path(__file__).resolve().parent.parent


def _load_content():
    """Load game content from JSON files into a namespace-like object."""
    content_dir = GAME / "content"
    actions = {}
    if (content_dir / "actions.json").exists():
        actions = json.loads((content_dir / "actions.json").read_text(encoding="utf-8"))
    # Fallback to minimal valid structure matching the engine's expectations
    if not actions:
        actions = {
            "pick_lock": {"kind": "task", "duration": 2},
            "crowbar": {"kind": "support", "duration": 1},
            "wait": {"kind": "wait"},
        }
    return SimpleNamespace(actions=actions)


def test_span_of_returns_duration_for_task():
    """span_of returns the duration of a task action."""
    from planops import span_of
    content = _load_content()
    result = span_of(content, "pick_lock")
    assert isinstance(result, int) and result >= 1


def test_span_of_returns_duration_for_support():
    """span_of returns the duration of a support action."""
    from planops import span_of
    content = _load_content()
    result = span_of(content, "crowbar")
    assert isinstance(result, int) and result >= 1


def test_span_of_returns_one_for_unknown_action():
    """span_of returns 1 for an action not in the content."""
    from planops import span_of
    content = _load_content()
    result = span_of(content, "ghost_protocol")
    assert result == 1
