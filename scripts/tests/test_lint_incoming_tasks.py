"""scripts/lint_incoming_tasks.py (LA-9): the rules for local-AI queue lines, and every committed incoming file passes them."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lint", ROOT / "scripts" / "lint_incoming_tasks.py")
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

GOOD = "signal | chain:T-1:1 | game.py | In games/signal/game.py add a function f; test: tests/test_t.py proves it with 2 cases (a, b)."


def test_a_good_line_passes():
    assert lint.lint_lines([GOOD]) == []


def test_rules_catch_the_usual_mistakes():
    bad = [
        "nosuchgame | T-1 | game.py | text text text text text text text text test",
        "signal | T-1 | missing.py | text text text text text text text text test",
        "signal | T-1 | game.py | too short",
        "signal | T-1 | game.py | edit shared/seed.js and add the test text text text text",
        "signal | chain:A-1:1 | game.py | a long enough text with a test inside it for the rule",
        "signal | chain:A-1:3 | game.py | a long enough text with a test inside it for the rule",
    ]
    problems = lint.lint_lines(bad)
    assert len(problems) >= 6
    assert any("chain A-1" in p for p in problems)


def test_a_new_file_step_may_name_a_file_that_does_not_exist_yet():
    line = "signal | T-2 | signal_new_thing.py | Create a NEW file signal_new_thing.py with a function g; test: tests/test_g.py has 2 cases."
    assert lint.lint_lines([line]) == []


def test_every_committed_incoming_file_is_clean():
    files = [ROOT / "local-ai" / "incoming-tasks.txt", *sorted((ROOT / "local-ai" / "incoming").glob("*.txt"))]
    for f in files:
        if f.exists():
            assert lint.lint_lines(f.read_text(encoding="utf-8-sig").splitlines(), f.name) == [], f.name


def test_the_generated_queue_files_are_up_to_date_with_the_drafts():
    import subprocess
    import sys

    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_incoming_tasks.py"), "--check"])
    assert result.returncode == 0, "run: python3 scripts/build_incoming_tasks.py"
