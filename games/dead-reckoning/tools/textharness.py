"""Text harness: sail a plan from the command line and print the true track.

    python3 tools/textharness.py                      # the demo chart, steering straight at the flag
    python3 tools/textharness.py 45:5:3 120:4:2       # your own legs, as heading:speed:hours

It exists so the simulation can be read and argued with before any picture exists."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from charts import get_chart  # noqa: E402
from sim import clean_leg, describe, estimate, naive_legs, sail, score  # noqa: E402


def main(argv):
    chart = get_chart("open-02")
    legs = [clean_leg(chart, dict(zip(("heading", "speed", "hours"), (float(p) for p in a.split(":"))))) for a in argv] \
        or naive_legs(chart)
    res = sail(chart, legs)
    print(describe(chart, legs, res))
    est = estimate(chart, legs, allow=True)
    print("  believed end (allowing for the chart): (%.2f, %.2f)" % (est[-1][1], est[-1][2]))
    sc = score(chart, legs, res)
    for c in sc["criteria"]:
        print("  [%s] %s" % ("x" if c["ok"] else " ", c["text"]))
    print("  stars: %d   naive plan would miss by %.1f nm" % (sc["stars"], sc["naive_miss_nm"]))


if __name__ == "__main__":
    main(sys.argv[1:])
