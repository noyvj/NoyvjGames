"""Tidy brand-new test files the local AI wrote, so flake8 does not fail them over layout.

    python local-ai/tidy_new_tests.py games/<game>/tests/test_x.py [more files]

- one import per line (E401), via autopep8
- unused imports and variables removed (F401, F841), via autoflake
- an import that comes after setup code (usually a sys.path line the model did not need, since every
  game's conftest.py already puts the game folder on the path) gets "# noqa: E402", the same marker the
  games' own conftest files use (E402)
- two mistakes the model keeps making in new tests, fixed mechanically (2026-10-20, Drift and Herd TODO tasks):
  `from games.<slug>.x import ...` / `import games.<slug>.x` (the game folder is already on the path, so
  "games" is not a module there) becomes `from x import ...` / `import x`, and Playwright's made-up
  `query_all(` becomes `query_selector_all(`

Only for new test files: game code and existing tests are never touched.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

PY = sys.executable


def mark_late_imports(path):
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    lines = src.splitlines(keepends=True)
    seen_code = False
    for i, node in enumerate(tree.body):
        if i == 0 and isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant):
            continue                                   # module docstring
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if seen_code:
                idx = node.lineno - 1
                line = lines[idx].rstrip("\r\n")
                if "noqa" not in line and not line.rstrip().endswith(("(", "\\")):
                    ending = lines[idx][len(line):] or "\n"
                    lines[idx] = line + "  # noqa: E402" + ending
        else:
            seen_code = True
    path.write_text("".join(lines), encoding="utf-8")


def fix_known_mistakes(path):
    src = path.read_text(encoding="utf-8")
    new = re.sub(r"(?m)^(\s*)from games\.[A-Za-z0-9_-]+\.([A-Za-z0-9_.]+) import ", r"\1from \2 import ", src)
    new = re.sub(r"(?m)^(\s*)import games\.[A-Za-z0-9_-]+\.([A-Za-z0-9_]+)", r"\1import \2", new)
    new = re.sub(r"\.query_all\(", ".query_selector_all(", new)
    if new != src:
        path.write_text(new, encoding="utf-8")


def main():
    for name in sys.argv[1:]:
        path = Path(name)
        if not path.is_file():
            continue
        fix_known_mistakes(path)
        subprocess.run([PY, "-m", "autopep8", "--in-place", "--select=E401,E1,E2,E3,W2,W3", str(path)], capture_output=True)
        subprocess.run([PY, "-m", "autoflake", "--in-place", "--remove-all-unused-imports",
                        "--remove-unused-variables", str(path)], capture_output=True)
        mark_late_imports(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
