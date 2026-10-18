"""Bring newly possible TODO work into local-ai/queue.txt. ai-queue.ps1 runs this after every GitHub sync.

    python local-ai/refresh_queue.py          add what is new, print what changed
    python local-ai/refresh_queue.py --dry    only print what it would add

Noy2 (on the Mac) audits, splits big items into steps and splits big games' files, which makes more of the
current TODO doable. queue.txt is not in git, so this script is how that work reaches the queue:

1. local-ai/incoming-tasks.txt (committed by Noy2): queue lines in the usual format. A comment line
   "# replaces: ID, ID" above a group takes those whole items out of queue.txt and queue-parked.txt, since
   their steps replace them.
2. Open items in planning/TODO.md and TODO-NEXT.md that are labeled (or now label as) [local AI: yes] and
   have never been queued or run. Items that were parked earlier but are now possible (for example after a
   game's files were split) come back the same way.

New TODO.md work goes at the end of the "2. CURRENT TODO.md" section of queue.txt, so it runs right after the
tests and before Round 4 ideas; TODO-NEXT.md work goes at the end of section 3. Nothing is ever removed except
what a "# replaces:" line names, and a line is never added twice.
"""
import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import label_todo as lt  # noqa: E402
import make_todo_tasks as mt  # noqa: E402

QUEUE, PARKED, DONE, NEXT = (HERE / n for n in ("queue.txt", "queue-parked.txt", "queue-done.txt", "queue-next.txt"))
INCOMING = HERE / "incoming-tasks.txt"
TODO_MARK = "# --- 2. CURRENT TODO.md"
NEXT_MARK = "# --- 3. TODO-NEXT.md"


def read(path):
    return io.open(path, encoding="utf-8-sig").read().splitlines() if path.exists() else []


def write(path, lines):
    io.open(path, "w", encoding="utf-8-sig").write("\n".join(lines) + "\n")


def is_task(line):
    return bool(line.strip()) and not line.startswith("#") and line.count("|") >= 3


def key(line):
    parts = line.split("|")
    return parts[0].split()[-1].strip() if parts[0].split() else "", parts[1].strip()


def done_key(line):
    m = re.match(r"(?:PASSED|FAILED)  \S+ \S+  (.*)", line)
    return key(m.group(1)) if m and m.group(1).count("|") >= 3 else None


def current_labels():
    """item id -> (label, list file name) for every open item, labeling unlabeled ones the same way label_todo does."""
    out = {}
    for path in lt.LISTS:
        section = ""
        for line in read(path):
            if line.startswith("## "):
                section = line[3:].strip()
            m = lt.OPEN.match(line)
            if m:
                tag = (m.group(5) or "").strip() or lt.label(section, m.group(2), m.group(3), m.group(4))
                out[m.group(2)] = (tag, path.name)
    return out


def insert_at_section_end(queue, mark, lines):
    if not lines:
        return queue
    start = next((i for i, x in enumerate(queue) if x.startswith(mark)), None)
    if start is None:
        return queue + ["# --- added by refresh_queue.py ---"] + lines
    end = next((i for i in range(start + 1, len(queue)) if queue[i].startswith("# --- ")), len(queue))
    return queue[:end] + lines + queue[end:]


def main(argv):
    queue, parked = read(QUEUE), read(PARKED)
    seen = {key(x) for x in queue + read(NEXT) if is_task(x)} | {k for k in map(done_key, read(DONE)) if k}
    report = []

    # 1. Noy2's split steps
    replaced, incoming_todo, incoming_next = set(), [], []
    for line in read(INCOMING):
        m = re.match(r"#\s*replaces:\s*(.+)$", line.strip(), re.I)
        if m:
            replaced |= {x.strip() for x in m.group(1).split(",") if x.strip()}
        elif is_task(line) and key(line) not in seen:
            (incoming_next if "TODO-NEXT" in line or key(line)[1].startswith("R4-") else incoming_todo).append(line.strip())
            seen.add(key(line))
    if replaced:
        before = len(queue) + len(parked)
        queue = [x for x in queue if not (is_task(x) and key(x)[1] in replaced)]
        parked = [x for x in parked if not (is_task(x) and key(x)[1] in replaced)]
        report.append("removed %d whole items that steps replace" % (before - len(queue) - len(parked)))

    # 2. TODO items that are possible now and have never been queued or run
    labels = current_labels()
    by_game, _ = mt.collect()   # lines for items never queued or run (it skips queue, done and next)
    new_todo, new_next, revived = [], [], set()
    for lines in by_game.values():
        for line in lines:
            item = key(line)[1]
            tag, source = labels.get(item, ("", ""))
            if tag != "[local AI: yes]" or key(line) in seen:
                continue
            (new_todo if source == "TODO.md" else new_next).append(line)
            seen.add(key(line))
            revived.add(item)
    parked_now = [x for x in parked if not (is_task(x) and key(x)[1] in revived)]
    if len(parked_now) != len(parked):
        report.append("%d parked items are possible now" % (len(parked) - len(parked_now)))
    parked = parked_now

    queue = insert_at_section_end(queue, TODO_MARK, incoming_todo + new_todo)
    queue = insert_at_section_end(queue, NEXT_MARK, incoming_next + new_next)
    report.append("TODO.md: +%d (%d from incoming-tasks.txt)" % (len(incoming_todo) + len(new_todo), len(incoming_todo)))
    report.append("TODO-NEXT.md: +%d (%d from incoming-tasks.txt)" % (len(incoming_next) + len(new_next), len(incoming_next)))
    print("refresh_queue: " + "; ".join(report))
    if "--dry" not in argv:
        write(QUEUE, queue)
        write(PARKED, parked)


if __name__ == "__main__":
    main(sys.argv[1:])
