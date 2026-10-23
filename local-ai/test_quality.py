"""Fail a local-AI step whose new or changed test file tests nothing.

    python local-ai/test_quality.py <game_dir> <test file> [<test file> ...]

From the 2026-10-21 audits (local-ai/FOR-NOY2.md, "Runner check"): Grid R4-GRPC-8 step 1 pushed an empty
test_plan_table.py as a finished step, and Chronicle LA7-CHRONICLE-1 pushed a test file whose every test was skipped.
ai.ps1 runs this in the final check on every test file the task added or changed. Findings, one per line:

  empty-test     the file has no test function at all
  no-assert      a test function the task added has no assert, pytest.raises or expect(...) in it
  all-skipped    running the file passed nothing and skipped something (a skip because the browser or the network
                 is missing does not count: the browser check runs elsewhere)

Only test functions that are new against git HEAD are checked for asserts, so older helper-style tests in a file the
task touched are left alone. Exits 1 if there are findings.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

ASSERTING_CALL = re.compile(r"^(?:pytest\.raises|pytest\.fail|expect|assert_\w*|check\w*|_check\w*|_assert\w*)$")
OK_SKIP = re.compile(r"CDN is not reachable|could not import 'playwright|No module named 'playwright|browser", re.I)


def _call_name(node):
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value.id if isinstance(func.value, ast.Name) else ""
        return (base + "." if base == "pytest" else "") + func.attr
    return func.id if isinstance(func, ast.Name) else ""


def asserts_something(func):
    for node in ast.walk(func):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call) and ASSERTING_CALL.match(_call_name(node)):
            return True
    return False


def test_functions(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            found[node.name] = node
    return found


def head_text(path):
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path.parent, capture_output=True,
                             text=True, check=True).stdout.strip()
        rel = path.resolve().relative_to(Path(top).resolve()).as_posix()
        return subprocess.run(["git", "show", "HEAD:" + rel], cwd=top, capture_output=True, text=True,
                              check=True).stdout
    except (OSError, ValueError, subprocess.CalledProcessError):
        return ""


def static_findings(path, old_text):
    rel = path.name
    funcs = test_functions(path.read_text(encoding="utf-8"))
    if funcs is None:
        return []                      # a syntax error already fails the tests themselves
    if not funcs:
        return ["%s empty-test: no test function in the file" % rel]
    old = test_functions(old_text) or {}
    return ["%s no-assert: %s checks nothing (no assert, pytest.raises or expect)" % (rel, name)
            for name, func in sorted(funcs.items()) if name not in old and not asserts_something(func)]


def run_findings(game_dir, paths):
    findings = []
    for path in paths:
        out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", str(path)],
                             cwd=game_dir, capture_output=True, text=True).stdout
        summary = out.strip().splitlines()[-1] if out.strip() else ""
        if " skipped" not in summary or re.search(r"\d+ (passed|failed|errors?)\b", summary):
            continue
        skips = [line for line in out.splitlines() if line.startswith("SKIPPED")]
        if skips and all(OK_SKIP.search(line) for line in skips):
            continue
        findings.append("%s all-skipped: %s" % (path.name, summary))
    return findings


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    game_dir = Path(argv[0])
    paths = [Path(p) for p in argv[1:] if Path(p).is_file()]
    findings = []
    for path in paths:
        findings += static_findings(path, head_text(path))
    if paths:
        findings += run_findings(game_dir, paths)
    for line in findings:
        print(line)
    if not findings:
        print("test_quality: every test file tests something")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
