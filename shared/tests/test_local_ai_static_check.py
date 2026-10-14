"""local-ai/static_check.py finds the mistakes the audits of the local AI's Round 4 work kept finding."""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


def load_checker(root):
    spec = importlib.util.spec_from_file_location("static_check_under_test", REPO / "local-ai" / "static_check.py")
    module = importlib.util.module_from_spec(spec)
    import os
    os.environ["NOYVJ_ROOT"] = str(root)
    try:
        spec.loader.exec_module(module)
    finally:
        del os.environ["NOYVJ_ROOT"]
    return module


def make_game(root, html="", app_js="", pc_js="", game_py=""):
    game = root / "games" / "demo"
    game.mkdir(parents=True)
    (root / "shared").mkdir()
    (game / "index.html").write_text(html)
    (game / "app.js").write_text(app_js)
    (game / "pc.js").write_text(pc_js)
    (game / "game.py").write_text(game_py)
    return game


def test_flags_each_known_mistake(tmp_path):
    make_game(
        tmp_path,
        html='<div id="board"></div>',
        app_js=(
            'var a = document.getElementById("ghost-panel");\n'
            'var b = document.querySelector("dialog[open], [role=\'dialog\']");\n'
            'send({ action: "swipe" });\n'
            'window.addEventListener("demo-ping", function () {});\n'
            'var d = el.dataset.mood;\n'
        ),
        pc_js=(
            'const board = document.getElementById("board");\n'
            'document.dispatchEvent(new CustomEvent("demo-ping"));\n'
        ),
        game_py='def handle(request):\n    return {"ok": request.get("action") == "tap"}\n',
    )
    findings = "\n".join(load_checker(tmp_path).check_game("demo"))
    assert 'missing-id: no HTML, JS or Python writes id "ghost-panel"' in findings
    assert "hidden-dialog" in findings
    assert 'unknown-action: sends engine action "swipe"' in findings
    assert "head-lookup" in findings
    assert '"demo-ping" is sent on document but only heard on window' in findings
    assert "data-never-set: reads data-mood" in findings


def test_clean_game_has_no_findings(tmp_path):
    make_game(
        tmp_path,
        html='<div id="board" data-mood="calm"></div>',
        app_js=(
            'var a = document.getElementById("board");\n'
            'var b = document.querySelector("dialog[open], [role=\'dialog\']:not([hidden])");\n'
            'send({ action: "tap" });\n'
            'var d = a.dataset.mood;\n'
        ),
        pc_js='window.addEventListener("load", function () { document.getElementById("board"); });\n',
        game_py='def handle(request):\n    return {"ok": request.get("action") == "tap"}\n',
    )
    assert load_checker(tmp_path).check_game("demo") == []


def test_ids_built_with_an_attribute_object_or_joined_names_are_known(tmp_path):
    make_game(
        tmp_path,
        html="",
        app_js=(
            'var g = part("g", { id: "room-chair", class: "x" });\n'
            'var h = document.createElement("button"); h.id = "task-" + name + "-button";\n'
            'var c = $("room-chair"); var d = $("task-rest-button");\n'
        ),
    )
    assert load_checker(tmp_path).check_game("demo") == []


def test_real_games_have_no_unexplained_findings():
    """Every game in the repo passes, except the one known open item (Heist Committee's brief toggle, R4-HCPC-8)."""
    checker = load_checker(REPO)
    findings = []
    for game_dir in sorted((REPO / "games").iterdir()):
        if game_dir.is_dir() and list(game_dir.glob("*.js")):
            findings.extend(checker.check_game(game_dir.name))
    assert [f for f in findings if "brief-toggle-button" not in f] == []
