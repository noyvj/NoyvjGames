"""Edge-case tests for why.py: empty inputs, zero values, and boundary conditions."""

import json
import pytest
import game as game_module
import lessons
import why


@pytest.fixture(autouse=True)
def fresh():
    game_module.handle(json.dumps({"action": "reset"}))
    yield
    game_module.handle(json.dumps({"action": "reset"}))


def _lesson():
    """Return a copy of a real lesson from the game's data, ensuring required keys for why.py."""
    base = dict(lessons.SHELVES[0]["lessons"][0])
    if "by_id" not in base:
        base["by_id"] = {f["id"]: f for f in base["features"]}
    if "fids" not in base:
        base["fids"] = [f["id"] for f in base["features"]]
    if "train_cases" not in base or not base["train_cases"]:
        base["train_cases"] = [{"id": "T1", "name": "Case 1", "v": {f["id"]: 0 for f in base["features"]}, "label": 0} for _ in range(3)]
    if "bins" not in base:
        base["bins"] = ["No", "Yes"]
    if "noun" not in base:
        base["noun"] = "crate"
    base.setdefault("shortcuts", [])
    base.setdefault("mislabelled", [])
    return base


def _case():
    """Return a valid case dict matching the lesson's features, all values zero."""
    lesson = _lesson()
    return {
        "id": "U1",
        "name": "Unseen Case",
        "v": {f["id"]: 0 for f in lesson["features"]},
        "label": 0
    }


def test_checks_handles_empty_on_list():
    """checks should process an empty list of on features without raising."""
    lesson = _lesson()
    case = _case()
    result = why.checks(lesson, [], case)
    assert len(result) == 4
    assert all(isinstance(item, tuple) and len(item) == 2 for item in result)


def test_checks_handles_all_features_on():
    """checks should process a full set of on features without raising."""
    lesson = _lesson()
    case = _case()
    all_on = [f["id"] for f in lesson["features"]]
    result = why.checks(lesson, all_on, case)
    assert len(result) == 4
    # With all features on, 'missing' rule should never trigger because needs - on is empty
    missing_hits = [hit for cid, hit in result if cid == "missing"]
    assert not any(missing_hits)


def test_categorise_returns_valid_category_for_zero_values():
    """categorise should return a valid category ID even when all case values are zero."""
    lesson = _lesson()
    case = _case()
    on = [f["id"] for f in lesson["features"]]
    category = why.categorise(lesson, on, case)
    assert category in why.CATEGORY_IDS


def test_chips_marks_all_off_when_on_is_empty():
    """chips should correctly mark every feature as off when on is an empty list."""
    lesson = _lesson()
    case = _case()
    chips = why.chips(lesson, [], case)
    assert len(chips) == len(lesson["features"])
    for chip in chips:
        assert chip["on"] is False


def test_explain_returns_complete_structure_with_valid_inputs():
    """explain should return a dict with all expected keys when given valid inputs."""
    lesson = _lesson()
    case = _case()
    import lessonkit
    tree = lessonkit.fit(lesson, set([f["id"] for f in lesson["features"]]))
    explanation = why.explain(lesson, [f["id"] for f in lesson["features"]], tree, case)
    assert "case" in explanation
    assert "category" in explanation
    assert "steps" in explanation
    assert isinstance(explanation["steps"], list)


def test_checks_shortcut_rule_ignores_empty_shortcuts_list():
    """checks should not trigger the shortcut rule when the lesson has no shortcuts defined."""
    lesson = _lesson()
    case = _case()
    lesson["shortcuts"] = []
    on = [f["id"] for f in lesson["features"]]
    result = why.checks(lesson, on, case)
    shortcut_hits = [hit for cid, hit in result if cid == "shortcut"]
    assert not any(shortcut_hits)
