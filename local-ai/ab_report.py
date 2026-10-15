"""Compare tasks run with the model's thinking on and off (config.txt: think = ab alternates them).

    python local-ai/ab_report.py

Reads the run reports in local-ai/.history/reports (each says "- Thinking: on" or "off") and prints, per mode,
how many tasks ran, how many passed, and the average minutes. TODO tasks (anything but T-/EDGE- test tasks)
are shown separately, since they are what the local AI is for. Decide with at least ~15 TODO tasks per mode.
"""
import re
from collections import defaultdict
from pathlib import Path

REPORTS = Path(__file__).resolve().parent / ".history" / "reports"
# Only runs from here on count: before 2026-10-15 10:30 "off" never reached the model (every run thought) and
# "on" had a 64k context its own reasoning could fill, so older reports compare on with on.
SINCE = "261015-103000"   # yymmdd-HHMMSS, as in the report file names


def main():
    rows = defaultdict(lambda: {"runs": 0, "passed": 0, "minutes": 0.0})
    for path in REPORTS.glob("*.md"):
        stamp = re.search(r"-(\d{6}-\d{6})\.md$", path.name)
        if not stamp or stamp.group(1) < SINCE:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        mode = re.search(r"^- Thinking: (on|off)", text, re.M)
        if not mode:
            continue
        head = re.search(r"^# (PASSED|FAILED): (\S+)", text, re.M)
        took = re.search(r"^- Took: ([\d.]+) minutes", text, re.M)
        if not head:
            continue
        kind = "test tasks" if re.match(r"(T|EDGE)-", head.group(2)) else "TODO tasks"
        for key in ((mode.group(1), kind), (mode.group(1), "all")):
            r = rows[key]
            r["runs"] += 1
            r["passed"] += head.group(1) == "PASSED"
            r["minutes"] += float(took.group(1)) if took else 0.0
    if not rows:
        print("No reports with a Thinking line yet: set think = ab in config.txt and let the queue run.")
        return
    print(f"{'thinking':9} {'tasks':11} {'runs':>5} {'passed':>7} {'pass %':>7} {'avg min':>8}")
    for kind in ("TODO tasks", "test tasks", "all"):
        for mode in ("on", "off"):
            r = rows.get((mode, kind))
            if r and r["runs"]:
                print(f"{mode:9} {kind:11} {r['runs']:5} {r['passed']:7} {100 * r['passed'] / r['runs']:6.0f}% {r['minutes'] / r['runs']:8.1f}")


if __name__ == "__main__":
    main()
