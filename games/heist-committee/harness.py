"""Text-only harness: run one heist and print the log.

    python3 harness.py [target_id] [seed] [--random]
"""

import sys

import bots
import content as content_mod
import engine


def format_log(result, content):
    lines = []
    for ev in result["events"]:
        if ev["type"] == "beat":
            lines.append("")
            lines.append("== " + ev["text"] + " ==")
            continue
        tag = " {" + ",".join(ev["tags"]) + "}" if ev["tags"] else ""
        mark = {"complication": "!", "absorb": "+", "goal": "*", "pair": "~", "trait": "t"}.get(ev["type"], "-")
        lines.append("%s %s%s %s%s" % (mark, ev["text"], tag, "(cause #%d)" % ev["cause"] if ev["cause"] is not None else "", ""))
        if ev["why"]:
            lines.append("      why: " + ev["why"])
    out = result["outcome"]
    lines.append("")
    lines.append("Completed: %s" % ", ".join(out["completed"]))
    lines.append("Loot %d + souvenirs %d, heat %d, damages %d, bonuses %s, net %d" % (
        out["loot"], out["souvenirs"], out["heat"], out["damages"], [b["id"] for b in out["bonuses"]], out["net"]))
    lines.append("Chain links: %d, absorbed %d" % (out["chain_links"], out["absorbed"]))
    return "\n".join(lines)


def main(argv):
    content = content_mod.load()
    target = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else content.target_order[0]
    seed = int(argv[2]) if len(argv) > 2 and not argv[2].startswith("--") else 1
    crew = ["dot", "pip", "bea", "tomasz", "hank"]
    plan = bots.random_plan(content, target, crew, seed) if "--random" in argv else bots.greedy_plan(content, target, crew)
    result = engine.simulate(content, target, crew, plan, seed=seed)
    print(format_log(result, content))


if __name__ == "__main__":
    main(sys.argv)
