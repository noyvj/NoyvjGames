"""Tidy brand-new test files the local AI wrote, so flake8 does not fail them over layout.

    python local-ai/tidy_new_tests.py games/<game>/tests/test_x.py [more files]

- one import per line (E401), via autopep8
- unused imports and variables removed (F401, F841), via autoflake
- an import that comes after setup code (usually a sys.path line the model did not need, since every
  game's conftest.py already puts the game folder on the path) gets "# noqa: E402", the same marker the
  games' own conftest files use (E402)

Only for new test files: game code and existing tests are never touched.
"""
import ast
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


def main():
    for name in sys.argv[1:]:
        path = Path(name)
        if not path.is_file():
            continue
        subprocess.run([PY, "-m", "autopep8", "--in-place", "--select=E401,E1,E2,E3,W2,W3", str(path)], capture_output=True)
        subprocess.run([PY, "-m", "autoflake", "--in-place", "--remove-all-unused-imports",
                        "--remove-unused-variables", str(path)], capture_output=True)
        mark_late_imports(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
