"""Z-1e: a runtime use of randomness must be either seeded (shared/seed.py) or listed here with a reason.

Scans the files a player's browser actually runs (each game's own top-level .py/.js files and shared/),
for `random.` draws, `import random` and `Math.random`. Build-time tools (`tools/`) and tests are not
scanned. A new file that uses randomness fails this test until the game draws from the run seed
(`shared/seed.py`, planning/SHARED-COMPONENTS.md section "Seeded runs") or the use is added to
EXEMPT with the reason it does not need a seed. A stale entry (the file no longer uses randomness)
also fails, so the list stays honest. Reads about 300 small files; well under a second.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

USES = re.compile(
    r"(^|[^A-Za-z_.])random\.(random|choice|choices|randint|shuffle|sample|uniform|randrange|Random|seed|gauss)\("
    r"|^\s*import random\b|^\s*from random import|Math\.random\("
)

# path (relative to the repo root) -> why it needs no run seed
EXEMPT = {
    "games/champ-de-mots/formats.py": "study tool, not a seeded run (Z-1d records the exemption)",
    "games/champ-de-mots/game.py": "study tool: question and drill order, not a seeded run (Z-1d)",
    "games/champ-de-mots/minigames.py": "study tool: minigame draws (Z-1d decides seeding or records the exemption)",
    "games/continuum/naming.py": "random.Random(seed): settlement-name suggestions are a pure function of their seed argument",
    "games/dead-reckoning/app.js": "only picks a NEW practice seed; the chart and the sail are pure functions of that seed",
    "games/grid/game.py": "random.randrange is only the entropy for a new run seed; every gameplay draw is a seeded stream",
    "games/herd/settings.js": "cosmetic confetti position and delay, no gameplay",
    "games/lighthouse/app.js": "the fallback entropy for a new run seed when crypto is missing",
    "games/loop/game.py": "a cosmetic starting offset for which flavour vignette shows, no gameplay",
    "games/signal/game.py": "entropy for a NEW practice code only; every puzzle is a pure function of its code or date",
    "games/trade-empire/game.py": "random.Random(seed) from the saved founding_seed integer: deterministic",
    "shared/save-widget.js": "random suffix of a local snapshot or file id, no gameplay",
    "shared/seed.js": "the entropy fallback of newSeed when crypto is missing",
}


def runtime_files():
    for pattern in ("games/*/*.py", "games/*/*.js", "shared/*.py", "shared/*.js"):
        yield from sorted(ROOT.glob(pattern))


def files_using_random():
    found = set()
    for path in runtime_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(USES.search(line) for line in text.splitlines()):
            found.add(path.relative_to(ROOT).as_posix())
    return found


def test_every_runtime_use_of_randomness_is_exempt_or_seeded():
    unlisted = sorted(files_using_random() - set(EXEMPT))
    assert not unlisted, (
        "These files use randomness at runtime without being on the exemption list. Draw from the run "
        "seed (shared/seed.py) or add the file to EXEMPT with a reason: %s" % unlisted
    )


def test_the_exemption_list_has_no_stale_entries():
    stale = sorted(set(EXEMPT) - files_using_random())
    assert not stale, "These exempt files no longer use randomness; remove them from EXEMPT: %s" % stale
    for path in EXEMPT:
        assert (ROOT / path).exists(), path
        assert EXEMPT[path].strip(), path


def test_the_scan_sees_the_known_unseeded_forms():
    for line in ("x = random.random()", "import random", "from random import choice",
                 "rng = random.Random()", "Math.floor(Math.random() * 9)"):
        assert USES.search(line), line
    for line in ("rng.random()", "seed_lib.Rng(seed).random()", "self.random()", "# a randomly chosen card"):
        assert not USES.search(line), line
