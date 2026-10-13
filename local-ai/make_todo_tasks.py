"""Queue every TODO item the local AI can now attempt, from planning/TODO.md and planning/TODO-NEXT.md.

    python local-ai/make_todo_tasks.py            print what it would queue, with counts
    python local-ai/make_todo_tasks.py --append   add them to local-ai/queue.txt

An item qualifies when its section names one game (the big games included, now that ai.ps1 has a
long-context mode) and it is not: in the QA section (on hold until closing time), a whole new-game
milestone or hub registration, backend or other-player work, site-wide or shared-file work, waiting on
the owner, or in need of live web data. Items already waiting, run or parked are skipped. Tasks are
grouped by game so the model reloads (64k / 128k / 192k context) as rarely as possible.
"""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTS = [ROOT / "planning" / "TODO.md", ROOT / "planning" / "TODO-NEXT.md"]
GAMES = {
    "le champ de mots": "champ-de-mots", "trade empire": "trade-empire", "heist committee": "heist-committee",
    "pocket bazaar": "pocket-bazaar", "dead reckoning": "dead-reckoning", "logic gates": "logic-gates",
    "robot script": "robot-script", "hull repair": "hull-repair", "station medic": "station-medic",
    "evidence hunt": "evidence-hunt", "rule finder": "rule-finder", "mirror lab": "mirror-lab",
    "picture grid": "picture-grid", "reaction bench": "reaction-bench", "teach the machine": "teach-the-machine",
    "sol": "sol", "canopy": "canopy", "grid": "grid", "tide": "tide", "aftermath": "aftermath", "herd": "herd",
    "thaw": "thaw", "loop": "loop", "drift": "drift", "continuum": "continuum", "signal": "signal",
    "lexis": "lexis", "lighthouse": "lighthouse", "chronicle": "chronicle", "stranded": "stranded",
    "constellations": "constellations",
}
SKIP = [
    (r"^qa", "QA (on hold)"),
    (r"waits? on for-you|owner'?s? (input|answer|token|account)|needs (owner|your)|\[question", "needs the owner"),
    (r"\bmilestone \d|register in the hub", "new-game milestone"),
    (r"backend|\bapp/|leaderboard|account|friend|server|endpoint|\bpool\b|ghost|online|other players|community|multiplayer", "backend / other players"),
    (r"read live|live from|named source|wikipedia|iucn|noaa|our world in data", "live web data"),
    (r"shared/|\bhub\b|site-wide|every game|all games|across the site|sw\.js|whole site|every page", "site-wide / shared"),
]
ITEM = re.compile(r"^\s*- \[ \] ([A-Z0-9][A-Z0-9-]*[A-Z0-9]):?\s*(?:\((small|big)\)\s*)?(.+)$")


def game_of(section):
    low = section.lower()
    for name in sorted(GAMES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", low):
            return GAMES[name]
    return None


def where(section, item):
    tag = section.split(".")[0]
    if tag.endswith("PC"):
        return ("This is a PC (Desktop) view idea: it belongs in pc.css, pc.js or pc-config.json (never pc.html, "
                "which is generated); open game.py only if the change really needs it.")
    if tag.endswith("MO"):
        return ("This is a mobile view idea: layout in style.css under a narrow-screen media query (max-width: 600px), "
                "behaviour in the game's own .js file; open game.py only if the change really needs it.")
    return "Put it where similar features already live in this game."


def already():
    seen = set()
    for name in ("queue.txt", "queue-done.txt", "queue-next.txt"):
        p = ROOT / "local-ai" / name
        if p.exists():
            seen |= set(re.findall(r"\| ([A-Z0-9][A-Z0-9-]*[A-Z0-9]) \|", p.read_text(encoding="utf-8-sig")))
    return seen


def collect():
    seen, out, skipped = already(), {}, Counter()
    for path in LISTS:
        section = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                section = line[3:].strip()
                continue
            m = ITEM.match(line)
            if not m:
                continue
            item, size, text = m.groups()
            if item in seen:
                skipped["already queued or run"] += 1
                continue
            game = game_of(section)
            if not game:
                skipped["not tied to one game"] += 1
                continue
            low = (section + " " + text).lower()
            reason = next((why for pattern, why in SKIP if re.search(pattern, low if pattern != "^qa" else section.lower())), None)
            if reason:
                skipped[reason] += 1
                continue
            scope = "a simple first version" if size == "big" else "a small, simple first version"
            task = (f"TODO item {item} ({path.name}): {text.replace('|', '/')} Build {scope} of this inside games/{game} "
                    f"only. {where(section, item)} Read the files the item touches before editing and keep the change "
                    f"small. Anything new stays optional for the player and respects reduced motion. Keep every "
                    f"existing test passing and add a pytest test for any Python you change.")
            out.setdefault(game, []).append(f"{game} | {item} |  | {task}")
            seen.add(item)
    return out, skipped


def main():
    by_game, skipped = collect()
    lines = [t for g in sorted(by_game) for t in by_game[g]]
    for g in sorted(by_game):
        print(f"{len(by_game[g]):4}  {g}", file=sys.stderr)
    print(f"# {len(lines)} new TODO tasks; skipped: {dict(skipped)}", file=sys.stderr)
    if "--append" in sys.argv and lines:
        with open(ROOT / "local-ai" / "queue.txt", "a", encoding="utf-8") as f:
            f.write("\n# TODO items now possible, incl. big games via long-context mode (make_todo_tasks.py), grouped by game\n")
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
