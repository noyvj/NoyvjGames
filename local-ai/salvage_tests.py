"""Keep the good half of a test file the local AI wrote.

    python local-ai/salvage_tests.py games/<game> tests/test_ai_<x>.py [more new test files]

Runs each NEW test file on its own, deletes the test functions that fail (with their decorators),
tidies the file (unused imports and variables, layout), and runs it again. Succeeds only when every
file still has at least MIN_KEPT tests and they all pass; otherwise the files are left as they were
and it exits 1. Prints one line per file saying what was kept and dropped.

Only ever used on brand-new tests/test_ai_*.py files, never on game code or existing tests.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

MIN_KEPT = 2
PY = sys.executable


def run_pytest(game_dir, rel):
    out = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=no", "-rfE", rel],
                         cwd=game_dir, capture_output=True, text=True)
    return out.returncode, out.stdout + out.stderr


def failing_names(text):
    """Test function names (parametrize suffix stripped) from pytest's FAILED/ERROR summary lines."""
    names = set()
    for m in re.finditer(r"^(?:FAILED|ERROR) [^:\s]+::(?:\w+::)?(\w+)", text, re.M):
        names.add(m.group(1))
    return names


def drop_functions(source, names):
    """Remove top-level test functions (and test methods inside classes) with these names."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
            spans.append((start, node.end_lineno))
    for start, end in sorted(spans, reverse=True):
        del lines[start:end]
    return "".join(lines)


def count_tests(source):
    tree = ast.parse(source)
    return sum(1 for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"))


def tidy(path):
    subprocess.run([PY, "-m", "autoflake", "--in-place", "--remove-all-unused-imports",
                    "--remove-unused-variables", str(path)], capture_output=True)
    subprocess.run([PY, "-m", "autopep8", "--in-place", "--select=E1,E2,E3,W2,W3", str(path)], capture_output=True)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    game_dir = Path(sys.argv[1]).resolve()
    rels = sys.argv[2:]
    originals = {rel: (game_dir / rel).read_bytes() for rel in rels}
    ok = True
    for rel in rels:
        path = game_dir / rel
        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            print(f"{rel}: not salvageable, syntax error on line {e.lineno}")
            ok = False
            continue
        code, text = run_pytest(game_dir, rel)
        if code == 0:
            print(f"{rel}: all {count_tests(source)} tests already pass")
            continue
        bad = failing_names(text)
        if not bad:
            print(f"{rel}: not salvageable, the file fails as a whole (import or collection error)")
            ok = False
            continue
        trimmed = drop_functions(source, bad)
        path.write_text(trimmed, encoding="utf-8")
        tidy(path)
        kept = count_tests(path.read_text(encoding="utf-8"))
        code, _ = run_pytest(game_dir, rel)
        if code != 0 or kept < MIN_KEPT:
            print(f"{rel}: not salvageable, {kept} tests left after dropping {len(bad)} ({'still failing' if code else 'too few'})")
            ok = False
            continue
        print(f"{rel}: kept {kept} passing tests, dropped {len(bad)} failing: {', '.join(sorted(bad))}")
    if not ok:
        for rel, raw in originals.items():
            (game_dir / rel).write_bytes(raw)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
