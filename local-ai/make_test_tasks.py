"""Write queue lines asking the local AI to test functions that no test mentions yet.

    python local-ai/make_test_tasks.py            print the queue lines
    python local-ai/make_test_tasks.py --append   also add them to local-ai/queue.txt

Only the small games, only plain-Python modules (no browser code), and only when the module
plus an example test file fit the local model comfortably. Each task asks for a NEW test file,
so tasks never touch game code and never collide with one another.
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAMES = ["lighthouse", "rule-finder", "hull-repair", "lexis", "mirror-lab", "stranded",
         "station-medic", "reaction-bench", "picture-grid", "robot-script", "pocket-bazaar",
         "constellations", "logic-gates", "evidence-hunt", "dead-reckoning", "heist-committee",
         "signal",
         # big games whose game.py is too large, but which also have small plain-Python modules
         "continuum", "chronicle", "sol", "champ-de-mots"]
SKIP_MODULES = {"game", "render", "harness", "info"}
BUDGET = 14000          # tokens for the module + example test, leaving room for rules and answers


def tokens(path):
    return len(path.read_text(encoding="utf-8")) * 2 // 7


def browser_code(text):
    return re.search(r"^\s*(import js|from js |import pyodide|from pyodide)", text, re.M) is not None


def public_functions(text):
    """Top-level functions as "name", and methods of top-level classes as "Class.name"."""
    found = []
    for n in ast.parse(text).body:
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"):
            found.append(n.name)
        elif isinstance(n, ast.ClassDef) and not n.name.startswith("_"):
            found += [f"{n.name}.{m.name}" for m in n.body
                      if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")]
    return found


def example_test(tests, module):
    importing = [t for t in tests
                 if re.search(rf"^\s*(import {module}\b|from {module} import)", t.read_text(encoding="utf-8"), re.M)]
    pool = importing or tests
    return min(pool, key=tokens) if pool else None


def tasks_for(game):
    gdir = ROOT / "games" / game
    tests = sorted((gdir / "tests").glob("test_*.py"))
    test_text = "\n".join(t.read_text(encoding="utf-8") for t in tests)
    lines = []
    for mod in sorted(gdir.glob("*.py")):
        name = mod.stem
        text = mod.read_text(encoding="utf-8")
        if name in SKIP_MODULES or browser_code(text):
            continue
        example = example_test(tests, name)
        if example is None or tokens(mod) + tokens(example) > BUDGET:
            continue
        for fn in public_functions(text):
            short = fn.split(".")[-1]
            if re.search(rf"\b{re.escape(short)}\b", test_text):
                continue
            slug = fn.replace(".", "_")
            item = "T-" + slug.replace("_", "-")[:30]
            new_file = f"tests/test_ai_{name}_{slug}.py"
            kind = "method" if "." in fn else "function"
            task = (f"Write pytest tests for the {kind} {fn}() in {name}.py. Put them in a NEW file "
                    f"{new_file} and change no other file. Import modules the same way "
                    f"tests/{example.name} does. Read {fn}() carefully and test what it really does: "
                    f"two or three normal cases and one edge case, each with a short docstring. "
                    f"Every test must pass.")
            lines.append(f"{game} | {item} | {name}.py, tests/{example.name} | {task}")
    return lines


def main():
    per_game = {g: tasks_for(g) for g in GAMES}
    # interleave games so one game's trouble never blocks a long stretch of the queue
    out = []
    while any(per_game.values()):
        for g in GAMES:
            if per_game[g]:
                out.append(per_game[g].pop(0))
    for line in out:
        print(line)
    print(f"# {len(out)} test tasks", file=sys.stderr)
    if "--append" in sys.argv:
        queue = ROOT / "local-ai" / "queue.txt"
        with open(queue, "a", encoding="utf-8") as f:
            f.write("\n# Batch 2: tests for functions no test mentions yet (make_test_tasks.py)\n")
            f.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
