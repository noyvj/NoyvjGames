"""Batch A #15: shareable goals code and the strict import."""

import base64
import json

from .helpers import click, known_state


def _code(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return "WFG1." + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _mine(m):
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 2}}, inventory={"Ferrite": {"built": 5000}})
    return m.calculate()


def test_export_holds_only_builds_and_needs(game_env):
    m = game_env.module
    components, resources = _mine(m)
    m.add_goal("secret goal")
    m.state["notes"]["Rahn Prism"] = "private note"
    code = m.export_goals_code(components, resources)
    assert code.startswith("WFG1.") and "=" not in code
    data = json.loads(base64.urlsafe_b64decode(code[5:] + "=" * (-len(code[5:]) % 4)))
    assert set(data) == {"v", "b", "n"} and data["v"] == 1
    assert data["b"] == [["Rahn Prism", 2]]
    assert all(isinstance(q, int) for _, q in data["n"])
    raw = base64.urlsafe_b64decode(code[5:] + "=" * (-len(code[5:]) % 4)).decode()
    assert "secret" not in raw and "private" not in raw


def test_round_trip(game_env):
    m = game_env.module
    components, resources = _mine(m)
    parsed, error = m.parse_goals_code(m.export_goals_code(components, resources))
    assert error == "" and parsed["builds"] == [("Rahn Prism", 2)]
    assert dict(parsed["needs"])["Iradite"] > 0
    parsed, _ = m.parse_goals_code("  " + m.export_goals_code(components, resources) + "\n")
    assert parsed is not None  # surrounding whitespace is fine


def test_strict_validation_rejects_bad_codes(game_env):
    m = game_env.module
    good = {"v": 1, "b": [["Rahn Prism", 1]], "n": [["Iradite", 5]]}
    assert m.parse_goals_code(_code(good))[0] is not None
    bad = [
        "", None, 5, "hello", "WFG2." + _code(good)[5:], "WFG1.", "WFG1.!!!!", "WFG1.abc def",
        "WFG1." + "A" * 9000,
        _code({"v": 2, "b": [], "n": []}),
        _code({"v": True, "b": [], "n": []}),
        _code({"v": 1, "b": [], "n": [], "extra": 1}),
        _code({"v": 1, "b": []}),
        _code([1, 2]), _code("str"), _code(None),
        _code({"v": 1, "b": [["Nope", 1]], "n": []}),
        _code({"v": 1, "b": [], "n": [["Nope", 1]]}),
        _code({"v": 1, "b": [["Rahn Prism", 0]], "n": []}),
        _code({"v": 1, "b": [["Rahn Prism", -3]], "n": []}),
        _code({"v": 1, "b": [["Rahn Prism", 1.5]], "n": []}),
        _code({"v": 1, "b": [["Rahn Prism", True]], "n": []}),
        _code({"v": 1, "b": [["Rahn Prism", 10 ** 9]], "n": []}),
        _code({"v": 1, "b": [["Rahn Prism", 1], ["Rahn Prism", 2]], "n": []}),
        _code({"v": 1, "b": [["Rahn Prism"]], "n": []}),
        _code({"v": 1, "b": [["Rahn Prism", 1, 2]], "n": []}),
        _code({"v": 1, "b": ["Rahn Prism"], "n": []}),
        _code({"v": 1, "b": [[["x"], 1]], "n": []}),
        _code({"v": 1, "b": "x", "n": []}),
        _code({"v": 1, "b": [], "n": [["Iradite", 1]] * 2}),
        "WFG1." + base64.urlsafe_b64encode(b"\xff\xfe\xfd").decode(),
        "WFG1." + base64.urlsafe_b64encode(b"not json").decode(),
    ]
    for text in bad:
        data, error = m.parse_goals_code(text)
        assert data is None and error, repr(text)[:60]


def test_size_limits(game_env):
    m = game_env.module
    names = list(m.RECIPES)
    too_many = {"v": 1, "b": [[names[i % 33], 1] for i in range(61)], "n": []}
    assert m.parse_goals_code(_code(too_many))[0] is None


def test_comparison_shows_who_can_help_with_what(game_env):
    m = game_env.module
    _components, resources = _mine(m)
    friend = {"builds": [("Shwaak Prism", 1)], "needs": [("Ferrite", 800), ("Iradite", 60), ("Rubedo", 10)]}
    text = m.goals_comparison_text(friend, resources)
    assert "Their list: 1 build(s), 3 resource need(s)." in text
    assert "Ferrite (they need 800, you have 5000 spare)" in text  # you hold plenty and need none
    assert "Iradite (they need 60, you are short" in text  # you are short of it too
    assert "Rubedo" not in text.split("You both still need")[0]
    empty = m.goals_comparison_text({"builds": [], "needs": []}, resources)
    assert "nothing from your current stock" in empty and "no shared shortfalls" in empty


def test_spare_excludes_what_you_need_yourself(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}}, inventory={"Iradite": {"built": 80}})
    _c, resources = m.calculate()  # Rahn needs 50 Iradite, so 30 are spare
    text = m.goals_comparison_text({"builds": [], "needs": [("Iradite", 100)]}, resources)
    assert "Iradite (they need 100, you have 30 spare)" in text


def test_ui_export_and_import(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}})
    els = game_env.elements
    assert els["share-export-text"].value.startswith("WFG1.")
    click(els["share-copy-button"])
    assert game_env.js.navigator.clipboard.written[-1] == els["share-export-text"].value
    els["share-import-input"].value = "garbage"
    click(els["share-import-button"])
    assert "not a goals code" in els["share-result"].textContent
    els["share-import-input"].value = els["share-export-text"].value
    click(els["share-import-button"])
    assert "Their list: 1 build(s)" in els["share-result"].textContent
    assert "share" not in m.get_state()  # an imported friend's code is never saved
