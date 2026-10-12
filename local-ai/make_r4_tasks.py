"""Stress test: queue Round 4 items (planning/TODO-NEXT.md) for the small games, as written.

    python local-ai/make_r4_tasks.py            print the queue lines
    python local-ai/make_r4_tasks.py --append   also add them to local-ai/queue.txt

These are design items, not exact steps, so expect many to fail. That is the point: it measures
what the local model can do unaided. Only "(small)" items, only games whose files fit the model,
and nothing that needs accounts, the hub, other players, other games or live data. Passing
branches still go through Claude's review before anything reaches main, and no item is ticked.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODO_NEXT = ROOT / "planning" / "TODO-NEXT.md"
SECTION_GAME = {
    "SI": "signal", "PU": "signal", "SIPC": "signal", "SIMO": "signal",
    "LE": "lexis", "PX": "lexis", "LEPC": "lexis", "LEMO": "lexis",
    "HC": "heist-committee", "HCP": "heist-committee", "HCPC": "heist-committee", "HCMO": "heist-committee",
    "LH": "lighthouse", "LHP": "lighthouse", "LHPC": "lighthouse", "LHMO": "lighthouse",
    "PB": "pocket-bazaar", "PBP": "pocket-bazaar", "PBPC": "pocket-bazaar", "PBMO": "pocket-bazaar",
    "DE": "dead-reckoning", "DEP": "dead-reckoning", "DEPC": "dead-reckoning", "DEMO": "dead-reckoning",
    "LGPC": "logic-gates", "LGMO": "logic-gates", "RSPC": "robot-script", "RSMO": "robot-script",
    "HRPC": "hull-repair", "HRMO": "hull-repair", "SMPC": "station-medic", "SMMO": "station-medic",
}
OUT_OF_SCOPE = re.compile(r"account|leaderboard|friend|online|other players|community|\bhub\b|every game|"
                          r"across the site|site-wide|read live|live from|server|backend|share (a|your) link",
                          re.I)
ITEM = re.compile(r"^- \[ \] (R4-([A-Z]+)-\d+): \(small\) (.+)$")


def where(section):
    if section.endswith("PC"):
        return ("This is a PC (Desktop) view idea: it belongs in pc.css, pc.js or pc-config.json, "
                "and never in pc.html, which is generated.")
    if section.endswith("MO"):
        return ("This is a mobile view idea: put layout in style.css under a narrow-screen media query "
                "(max-width: 600px) and behaviour in the game's own .js file.")
    return "Put it where similar features already live in this game."


def tasks():
    out = []
    for line in TODO_NEXT.read_text(encoding="utf-8").splitlines():
        m = ITEM.match(line.strip())
        if not m:
            continue
        item, section, text = m.groups()
        game = SECTION_GAME.get(section)
        if not game or OUT_OF_SCOPE.search(text):
            continue
        task = (f"Round 4 idea {item}: {text.replace('|', '/')} Build a small, simple first version of this "
                f"inside games/{game} only. {where(section)} Read the files the idea touches before editing and "
                f"keep the change small. Anything new stays optional for the player and must respect reduced "
                f"motion. Do not break existing tests; add a pytest test for any Python you add.")
        out.append(f"{game} | {item} |  | {task}")
    return out


def main():
    lines = tasks()
    for line in lines:
        print(line)
    print(f"# {len(lines)} Round 4 stress-test tasks", file=sys.stderr)
    if "--append" in sys.argv:
        with open(ROOT / "local-ai" / "queue.txt", "a", encoding="utf-8") as f:
            f.write("\n# Stress test: Round 4 small items for the small games, as written (make_r4_tasks.py)\n")
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
