"""local-ai/test_quality.py fails a local-AI step whose new test file is empty, asserts nothing or only skips."""

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "local-ai" / "test_quality.py"


def load():
    spec = importlib.util.spec_from_file_location("test_quality_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(game_dir, *files):
    return subprocess.run([sys.executable, str(SCRIPT), str(game_dir)] + [str(f) for f in files],
                          capture_output=True, text=True)


def test_an_empty_test_file_is_a_finding(tmp_path):
    f = tmp_path / "test_plan_table.py"
    f.write_text('"""Nothing here yet."""\nimport pytest\n')
    assert load().static_findings(f, "") == ["test_plan_table.py empty-test: no test function in the file"]


def test_a_new_test_without_an_assert_is_a_finding_but_an_old_one_is_left_alone(tmp_path):
    f = tmp_path / "test_x.py"
    f.write_text("def test_old():\n    print(1)\n\n\ndef test_new():\n    x = 1\n\n\ndef test_good():\n    assert 1 == 1\n")
    found = load().static_findings(f, "def test_old():\n    print(1)\n")
    assert found == ["test_x.py no-assert: test_new checks nothing (no assert, pytest.raises or expect)"]


def test_pytest_raises_and_playwright_expect_count_as_checks(tmp_path):
    f = tmp_path / "test_y.py"
    f.write_text("import pytest\n\n\ndef test_a():\n    with pytest.raises(ValueError):\n        int('x')\n\n\n"
                 "def test_b(page):\n    expect(page).to_have_title('x')\n")
    assert load().static_findings(f, "") == []


def test_a_file_whose_every_test_skips_fails_the_run_and_a_passing_one_does_not(tmp_path):
    skipped = tmp_path / "test_skipped.py"
    skipped.write_text("import pytest\n\n\n@pytest.mark.skip(reason='targets do not exist yet')\ndef test_a():\n    assert 1\n")
    fine = tmp_path / "test_fine.py"
    fine.write_text("def test_a():\n    assert 1 + 1 == 2\n")
    result = run(tmp_path, skipped, fine)
    assert result.returncode == 1
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("test_skipped.py all-skipped: 1 skipped in ")
    assert run(tmp_path, fine).returncode == 0


def test_a_skip_because_the_browser_or_network_is_missing_does_not_count(tmp_path):
    f = tmp_path / "test_browser_thing.py"
    f.write_text("import pytest\n\n\ndef test_a():\n    pytest.skip(\"Pyodide's CDN is not reachable\")\n    assert 1\n")
    assert run(tmp_path, f).returncode == 0
