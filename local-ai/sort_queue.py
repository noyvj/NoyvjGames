"""Sort local-ai/queue.txt from easy to hard (the owner asked for the simple things first, 2026-10-15).

    python local-ai/sort_queue.py            show what the order would be
    python local-ai/sort_queue.py --write    rewrite queue.txt (and park ideas for games that have no code yet)

A rough difficulty score per task, lower is easier:
  - kind: a page-view idea (R4-..PC-n / R4-..MO-n) 1, a new-game milestone (QI-) 3, any other idea or TODO item 4
  - words: the audits found zoom, drag, swipe, sheets, new engine actions, animation and new modes fail most
    (+0.6 each); one key, button, setting or CSS change works best (-0.4 each, up to 3)
  - game size: the four biggest game files, ~bytes/3 tokens (bigger = a slower model with less room), up to +3
  - the game's past pass rate in queue-done.txt (smoothed)
  - long task text = more to build
The queue is then cut into EASY, MEDIUM and HARD thirds. Inside a tier a game's tasks stay together, because
switching between the 64k and 128k models reloads the model for a minute or two. A game's milestones stay one
block in number order (milestone 2 cannot come before 1). Ideas for a game whose folder has no code yet cannot
be built, so they go to queue-parked.txt until the game exists.
"""
import collections
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAMES = os.path.join(HERE, "..", "games")
HARD = (r"zoom|\bpan\b|drag|swipe|gesture|pinch|sheet|carousel|transform|animat|\b3d\b|three\.js|low-poly|drawn in code|"
        r"minigame|mini-game|multiplayer|generator|new mode|new chapter|campaign|missions|levels|puzzles|engine|simulat|"
        r"physics|replay|undo|redo|timeline|\bmap\b|graph|chart|filmstrip|scrub|editor|sandbox|tutorial|achievement|"
        r"profile|import|export|skill tree")
EASY = (r"\bkey\b|shortcut|keyboard|toggle|button|setting|font|colou?r|label|tooltip|title|hide|larger|bigger|print|"
        r"\bcss\b|contrast|spacing|badge|icon|counter|text size|focus|outline|hover")


def read(name):
    path = os.path.join(HERE, name)
    return io.open(path, encoding="utf-8-sig").read().splitlines() if os.path.exists(path) else []


def write(name, lines):
    io.open(os.path.join(HERE, name), "w", encoding="utf-8-sig").write("\n".join(lines) + "\n")


def is_task(line):
    return bool(line.strip()) and not line.startswith("#") and "|" in line


def game(line):
    return line.split("|")[0].strip()


def item(line):
    return line.split("|")[1].strip()


def text(line):
    return line.split("|", 3)[3] if line.count("|") >= 3 else ""


def milestone_key(line):
    return [int(x) for x in re.findall(r"\d+", item(line))]


def main(argv):
    queue = read("queue.txt")
    header = queue[0] if queue and queue[0].startswith("#") else "# game | ITEM-ID | files | what to do   (see ai-queue.ps1)"
    tasks = [line for line in queue if is_task(line)]

    size, no_code = {}, set()
    for d in os.listdir(GAMES):
        folder = os.path.join(GAMES, d)
        if not os.path.isdir(folder):
            continue
        files = [f for f in glob.glob(os.path.join(folder, "*")) if os.path.isfile(f)
                 and f.endswith((".py", ".js", ".html", ".css", ".json")) and not f.endswith("pc.html")]
        size[d] = sum(sorted((os.path.getsize(f) for f in files), reverse=True)[:4]) // 3
        if not glob.glob(os.path.join(folder, "*.py")) and not glob.glob(os.path.join(folder, "*.js")):
            no_code.add(d)

    runs = collections.defaultdict(lambda: [0, 0])
    for line in read("queue-done.txt"):
        m = re.match(r"(PASSED|FAILED)  \S+ \S+  (.*)", line)
        if m and "|" in m.group(2):
            runs[game(m.group(2))][0] += m.group(1) == "PASSED"
            runs[game(m.group(2))][1] += 1

    def score(line):
        it, words, g = item(line), text(line).lower(), game(line)
        s = 1.0 if re.search(r"(PC|MO)-\d+$", it) else 3.0 if it.startswith("QI-") else 4.0
        s += 0.6 * len(re.findall(HARD, words)) - 0.4 * min(3, len(re.findall(EASY, words)))
        s += min(3.0, size.get(g, 0) / 25000)
        passed, total = runs[g]
        s += 2.0 * (0.5 - (passed + 3 * 0.35) / (total + 3))
        return s + len(words) / 1200

    parked = [line for line in tasks if game(line) in no_code and not item(line).startswith("QI-")]
    tasks = [line for line in tasks if line not in parked]
    sc = {line: score(line) for line in tasks}
    blocks = collections.defaultdict(list)
    for line in tasks:
        if item(line).startswith("QI-"):
            blocks[game(line)].append(line)
    for g, block in blocks.items():
        average = sum(sc[line] for line in block) / len(block) + (5.0 if g in no_code else 0.0)
        for i, line in enumerate(sorted(block, key=milestone_key)):
            sc[line] = average + i * 0.001

    order = sorted(tasks, key=lambda line: sc[line])
    n = len(order)
    tiers = [("EASY", order[:n // 3]), ("MEDIUM", order[n // 3:2 * n // 3]), ("HARD", order[2 * n // 3:])]
    out = [header]
    for name, tier in tiers:
        out.append("# --- %s (%d tasks; sorted easy to hard by local-ai/sort_queue.py) ---" % (name, len(tier)))
        first = {}
        for line in tier:
            first.setdefault(game(line), sc[line])
        out += sorted(tier, key=lambda line: (first[game(line)], sc[line]))

    for name, tier in tiers:
        counts = collections.Counter(game(line) for line in tier)
        print("%s: %d tasks; %s" % (name, len(tier), ", ".join("%s %d" % gc for gc in counts.most_common(8))))
    print("parked (the game has no code yet): %d %s" % (len(parked), dict(collections.Counter(game(x) for x in parked))))
    print("\nEasiest 8:")
    for line in order[:8]:
        print("  %.1f  %s %s: %s" % (sc[line], game(line), item(line), text(line).strip()[:90]))

    if "--write" in argv:
        write("queue.txt", out)
        if parked:
            write("queue-parked.txt", read("queue-parked.txt")
                  + ["# Parked 2026-10-15: ideas for games with no code yet; queue again once the game is built"] + parked)
        print("\nqueue.txt rewritten.")


if __name__ == "__main__":
    main(sys.argv[1:])
