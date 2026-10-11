"""Rule Finder -- turn specs.py into the frozen cases_<drawer>.py files (a dev tool).

    python3 tools/build_cases.py            # rewrite every cases file
    python3 tools/build_cases.py numbers    # one drawer

For each spec it draws the starting examples (author.choose, seeded), runs the whole fairness proof (finder.analyse) and writes the
case with its par tests. A case whose rule is not as short as declared, whose examples already identify it, or whose par set was
not proved minimal is reported and stops the build, because the game would not be fair.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import author  # noqa: E402
import finder  # noqa: E402
import lang  # noqa: E402
import specs  # noqa: E402


def build_case(spec):
    kind = spec["domain"]
    rule = lang.parse_rule(kind, spec["rule"])
    assert rule is not None, spec["id"]
    table = lang.rule_table(kind, rule)
    assert len(rule.lits) == spec["size"], spec["id"]
    assert finder.min_size(kind, table) == spec["size"], "%s: the rule is shorter than declared" % spec["id"]
    if "yes" in spec:
        yes, no = list(spec["yes"]), list(spec["no"])
        m = author.measure(kind, spec["rule"], spec["size"], yes, no)
    else:
        pool = author.friendly(kind) - set(spec.get("exclude", ()))
        found = author.choose(kind, spec["rule"], spec["size"], spec["ny"], spec["nn"], tries=spec.get("tries", 200), pool=pool,
                              par_floor=spec.get("par_floor", 0))
        assert found is not None, "%s: no usable examples" % spec["id"]
        m, yes, no = found
    assert m["competitors"] > 0, "%s: the examples already identify the rule" % spec["id"]
    assert m["proved"], "%s: par set not proved minimal" % spec["id"]
    return {"id": spec["id"], "name": spec["name"], "domain": kind, "rule": spec["rule"], "size": spec["size"],
            "yes": yes, "no": no, "par": m["order"], "line": spec["line"]}


def emit(drawer, cases):
    j = json.dumps
    out = ['"""Rule Finder -- %s: %d cases (frozen by tools/build_cases.py from tools/specs.py; do not edit by hand)."""\n' % (drawer["name"], len(cases)),
           "KEY = %s" % j(drawer["key"]), "NAME = %s" % j(drawer["name"]), "BLURB = %s" % j(drawer["blurb"]), "MAX_CLAUSES = %d\n" % drawer["max_clauses"],
           "CASES = ("]
    for c in cases:
        out.append("    {")
        out.append("        \"id\": %s, \"name\": %s, \"domain\": %s, \"rule\": %s, \"size\": %d," % (j(c["id"]), j(c["name"]), j(c["domain"]), j(c["rule"]), c["size"]))
        out.append("        \"yes\": %s, \"no\": %s," % (j(c["yes"]), j(c["no"])))
        out.append("        \"par\": %s," % j(c["par"]))
        out.append("        \"line\": %s," % j(c["line"], ensure_ascii=False))
        out.append("    },")
    out.append(")")
    return "\n".join(out) + "\n"


def main():
    wanted = set(sys.argv[1:])
    for drawer in specs.DRAWERS:
        if wanted and drawer["key"] not in wanted:
            continue
        cases = []
        for spec in drawer["cases"]:
            case = build_case(spec)
            print("%-10s %-8s par %d  yes=%s no=%s par=%s" % (drawer["key"], case["id"], len(case["par"]), case["yes"], case["no"], case["par"]), flush=True)
            cases.append(case)
        (HERE.parent / ("cases_%s.py" % drawer["key"])).write_text(emit(drawer, cases), encoding="utf-8")


if __name__ == "__main__":
    main()
