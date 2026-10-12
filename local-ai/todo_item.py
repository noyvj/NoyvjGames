"""Find one item in planning/TODO.md without reading the whole file.

    python local-ai/todo_item.py show GD-15     print the item and its section
    python local-ai/todo_item.py tick GD-15     mark it done ([ ] -> [x])
"""
import re
import sys
from pathlib import Path

TODO = Path(__file__).resolve().parent.parent / "planning" / "TODO.md"


def find(lines, item_id):
    pattern = re.compile(r"^\s*- \[( |x)\] " + re.escape(item_id) + r"\b")
    for i, line in enumerate(lines):
        if pattern.match(line):
            return i
    return None


def section_of(lines, index):
    for line in reversed(lines[:index]):
        if line.startswith("## "):
            return line[3:].strip()
    return ""


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("show", "tick"):
        print(__doc__)
        return 2
    action, item_id = sys.argv[1], sys.argv[2]
    # newline="" keeps the file's own line endings exactly as they are
    with open(TODO, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    index = find(lines, item_id)
    if index is None:
        print(f"No TODO item {item_id} found.")
        return 1
    if action == "show":
        print(f"Section: {section_of(lines, index)}")
        print(lines[index].strip())
        return 0
    if "- [x] " in lines[index]:
        print(f"{item_id} is already ticked.")
        return 0
    lines[index] = lines[index].replace("- [ ] ", "- [x] ", 1)
    with open(TODO, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))
    print(f"Ticked {item_id}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
