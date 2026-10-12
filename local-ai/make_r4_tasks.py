"""Queue Round 4 items (planning/TODO-NEXT.md) for the local AI, as written.

    python local-ai/make_r4_tasks.py                      small items in the small games (the first batch)
    python local-ai/make_r4_tasks.py --big                also "(big)" items in the small games
    python local-ai/make_r4_tasks.py --views              also small PC-view and mobile-view items in the big games
    python local-ai/make_r4_tasks.py --big --views --append   add everything new to local-ai/queue.txt

Items already waiting in queue.txt or already run (queue-done.txt) are skipped, so it is safe to run again.
Nothing that needs accounts, the hub, other players, other games or live data. Big games only get view items,
told to stay out of their game.py (75k-146k tokens, too big for the local model). Passing branches still go
through Claude's review before anything reaches main, and no item is ticked automatically.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODO_NEXT = ROOT / "planning" / "TODO-NEXT.md"
SMALL = {
    "SI": "signal", "PU": "signal", "SIPC": "signal", "SIMO": "signal",
    "LE": "lexis", "PX": "lexis", "LEPC": "lexis", "LEMO": "lexis",
    "HC": "heist-committee", "HCP": "heist-committee", "HCPC": "heist-committee", "HCMO": "heist-committee",
    "LH": "lighthouse", "LHP": "lighthouse", "LHPC": "lighthouse", "LHMO": "lighthouse",
    "PB": "pocket-bazaar", "PBP": "pocket-bazaar", "PBPC": "pocket-bazaar", "PBMO": "pocket-bazaar",
    "DE": "dead-reckoning", "DEP": "dead-reckoning", "DEPC": "dead-reckoning", "DEMO": "dead-reckoning",
    "LGPC": "logic-gates", "LGMO": "logic-gates", "RSPC": "robot-script", "RSMO": "robot-script",
    "HRPC": "hull-repair", "HRMO": "hull-repair", "SMPC": "station-medic", "SMMO": "station-medic",
    # Chronicle was split into small files on 2026-10-12, so all of it fits now
    "CLP": "chronicle", "CLPC": "chronicle", "CLMO": "chronicle",
}
BIG_VIEWS = {   # big games: only their PC-view and mobile-view sections
    "SOPC": "sol", "SOMO": "sol", "CAPC": "canopy", "CAMO": "canopy", "GRPC": "grid", "GRMO": "grid",
    "TIPC": "tide", "TIMO": "tide", "AFPC": "aftermath", "AFMO": "aftermath", "HEPC": "herd", "HEMO": "herd",
    "THPC": "thaw", "THMO": "thaw", "LOPC": "loop", "LOMO": "loop", "DRPC": "drift", "DRMO": "drift",
    "TEPC": "trade-empire", "TEMO": "trade-empire", "COPC": "continuum", "COMO": "continuum",
    "CHPC": "champ-de-mots", "CHMO": "champ-de-mots",
}
OUT_OF_SCOPE = re.compile(r"account|leaderboard|friend|online|other players|community|\bhub\b|every game|"
                          r"across the site|site-wide|read live|live from|server|backend|share (a|your) link",
                          re.I)
ITEM = re.compile(r"^- \[ \] (R4-([A-Z]+)-\d+): \((small|big)\) (.+)$")


def where(section):
    if section.endswith("PC"):
        return ("This is a PC (Desktop) view idea: it belongs in pc.css, pc.js or pc-config.json, "
                "and never in pc.html, which is generated.")
    if section.endswith("MO"):
        return ("This is a mobile view idea: put layout in style.css under a narrow-screen media query "
                "(max-width: 600px) and behaviour in the game's own .js file.")
    return "Put it where similar features already live in this game."


def already_queued():
    seen = set()
    for name in ("queue.txt", "queue-done.txt", "queue-next.txt"):
        path = ROOT / "local-ai" / name
        if path.exists():
            seen |= set(re.findall(r"\| (R4-[A-Z]+-\d+) \|", path.read_text(encoding="utf-8-sig")))
    return seen


def tasks(big, views):
    seen = already_queued()
    out = []
    for line in TODO_NEXT.read_text(encoding="utf-8").splitlines():
        m = ITEM.match(line.strip())
        if not m:
            continue
        item, section, size, text = m.groups()
        if item in seen or OUT_OF_SCOPE.search(text):
            continue
        if section in SMALL and (size == "small" or big):
            game, extra = SMALL[section], ""
        elif section in BIG_VIEWS and size == "small" and views:
            game = BIG_VIEWS[section]
            extra = (" This game's game.py is far too large to open: do not add it to the chat or edit it. "
                     "Do this view change in pc.css, pc.js, pc-config.json, style.css or index.html only; if it "
                     "cannot be done without game.py, make no changes and say so.")
        else:
            continue
        scope = "a simple first version" if size == "big" else "a small, simple first version"
        task = (f"Round 4 idea {item}: {text.replace('|', '/')} Build {scope} of this inside games/{game} only. "
                f"{where(section)}{extra} Read the files the idea touches before editing and keep the change small. "
                f"Anything new stays optional for the player and must respect reduced motion. Do not break existing "
                f"tests; add a pytest test for any Python you add.")
        out.append(f"{game} | {item} |  | {task}")
    return out


def main():
    big, views = "--big" in sys.argv, "--views" in sys.argv
    lines = tasks(big, views)
    for line in lines:
        print(line)
    print(f"# {len(lines)} new Round 4 tasks", file=sys.stderr)
    if "--append" in sys.argv and lines:
        label = "small games" + (" incl. big items" if big else "") + (" + big-game PC/mobile views" if views else "")
        with open(ROOT / "local-ai" / "queue.txt", "a", encoding="utf-8") as f:
            f.write(f"\n# Round 4 items ({label}), as written (make_r4_tasks.py)\n")
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
