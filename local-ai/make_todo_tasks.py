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


EXTRA_NAMES = {"slingshot": "slingshot", "zero-g shift": "zero-g-shift"}   # games started since GAMES was written


def folder_names():
    """Every game folder's name, from the first heading of its CLAUDE.md (new games scaffolded by
    scripts/new_game.py included), plus its slug read as words."""
    out = {}
    for notes in (ROOT / "games").glob("*/CLAUDE.md"):
        slug = notes.parent.name
        out[slug.replace("-", " ")] = slug
        first = next((ln[2:].strip() for ln in notes.read_text(encoding="utf-8").splitlines() if ln.startswith("# ")), "")
        if first:
            out[re.sub(r"\s*\(.*\)$", "", first).lower().replace("'", "")] = slug
    return out


def game_of(section, text=""):
    """The game a section is about; failing that, the one existing game the item's own text names."""
    names = {**GAMES, **EXTRA_NAMES, **folder_names()}
    low = section.lower()
    for name in sorted(names, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", low):
            return names[name]
    hits = {names[n] for n in names if re.search(rf"\b{re.escape(n)}\b", text.lower())}
    hits = {g for g in hits if (ROOT / "games" / g).is_dir()}
    return hits.pop() if len(hits) == 1 else None


def milestone_done(game, text):
    """True when the game's own CLAUDE.md milestone table already marks this milestone Done."""
    m = re.search(r"\bmilestone (\d+)\b", text, re.I)
    notes = ROOT / "games" / game / "CLAUDE.md"
    if not m or not notes.exists():
        return False
    for row in notes.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] == m.group(1):
            return cells[-1].lower().startswith("done")
    return False


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
            game = game_of(section, text)
            if not game:
                skipped["not tied to one game"] += 1
                continue
            low = (section + " " + text).lower()
            reason = next((why for pattern, why in SKIP if re.search(pattern, low if pattern != "^qa" else section.lower())), None)
            milestone = reason == "new-game milestone" and "register in the hub" not in low and (ROOT / "games" / game).is_dir()
            if reason and not milestone:
                skipped[reason] += 1
                continue
            if milestone and milestone_done(game, text):
                skipped["milestone already Done in the game's CLAUDE.md (only the tick is missing)"] += 1
                continue
            if milestone:
                # a game whose folder already exists: build the milestone from its plan (ai.ps1 adds the plan file)
                task = (f"TODO item {item} ({path.name}): {text.replace('|', '/')} This is a milestone of a game that is "
                        f"already being built in games/{game}: read planning/{game}-plan.md (in the chat) and "
                        f"games/{game}/CLAUDE.md, follow the design there exactly, and build this milestone on top of what "
                        f"exists, in games/{game} only. Content follows the existing pattern (same data format, every "
                        f"level or puzzle proved by the game's solver or checker tests). When it works, set this "
                        f"milestone's Status to Done in the milestone table of games/{game}/CLAUDE.md. Keep every existing "
                        f"test passing and add tests for what you build.")
            else:
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
    for line in lines:
        print(line)
    for g in sorted(by_game):
        print(f"{len(by_game[g]):4}  {g}", file=sys.stderr)
    print(f"# {len(lines)} new TODO tasks; skipped: {dict(skipped)}", file=sys.stderr)
    if "--append" in sys.argv and lines:
        with open(ROOT / "local-ai" / "queue.txt", "a", encoding="utf-8") as f:
            f.write("\n# TODO items now possible, incl. big games via long-context mode (make_todo_tasks.py), grouped by game\n")
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
