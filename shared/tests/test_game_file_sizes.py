"""SP-2b: no game file the personal AI may edit grows past about 14,000 estimated tokens (bytes / 4).

The local model reads a whole file to edit it and holds about 24k tokens, so every Python, JS and CSS file in a game folder
(and index.html) must stay small. The SP-1 splits (2026-10-17) cut every game's files down; this test keeps it that way.
Each game also has its own tests/test_file_sizes.py; this one is the site-wide net, including games that have none yet.

Exempt: generated pages (pc.html), the data JSON files, markdown notes, and the small documented list below. `index.html` of the
big games is mostly real markup, so it has a per-game cap (never raise one without writing why).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIMIT_BYTES = 14_000 * 4
CODE_SUFFIXES = {".py", ".js", ".css", ".html"}

# index.html of the games whose markup is bigger than the limit (bytes). Documented in each game's tests/test_file_sizes.py.
INDEX_CAPS = {
    "aftermath": 15_000 * 4, "canopy": 15_000 * 4, "champ-de-mots": 78_000, "continuum": 17_500 * 4, "drift": 15_000 * 4,
    "grid": 16_500 * 4, "herd": 14_800 * 4, "sol": 21_500 * 4, "thaw": 15_000 * 4,
    "tide": 16_000 * 4, "trade-empire": 27_500 * 4,
}
# Games not split yet: listed so the list shrinks. Remove an entry when its split lands (SP-0a Loop).
NOT_SPLIT_YET = {"drift": 5}   # (game -> how many files may still be over the limit)
# Other files over the limit on purpose: path (relative to the repo root) -> why.
EXEMPT = {
    "games/champ-de-mots/study-table.html": "generated page of every word (scripts/generate-champ-study-table.py)",
    "games/continuum/info_content.py": "data-like content module just under the limit, left whole on purpose (SP-1a)",
}


def size(path):
    """Bytes with LF line endings: a Windows checkout has CRLF (one extra byte per line) and must not fail the cap."""
    return len(path.read_bytes().replace(b"\r\n", b"\n"))


def editable_files(game_dir):
    for p in sorted(game_dir.iterdir()):
        if not p.is_file() or p.suffix not in CODE_SUFFIXES:
            continue
        if p.name in {"pc.html"}:
            continue
        yield p


def test_no_game_file_the_ai_may_edit_is_over_the_limit():
    too_big = []
    for game_dir in sorted((ROOT / "games").iterdir()):
        if not game_dir.is_dir() or game_dir.name in NOT_SPLIT_YET:
            continue
        for path in editable_files(game_dir):
            rel = path.relative_to(ROOT).as_posix()
            limit = INDEX_CAPS.get(game_dir.name, LIMIT_BYTES) if path.name == "index.html" else LIMIT_BYTES
            if rel in EXEMPT:
                continue
            if size(path) > limit:
                too_big.append(f"{rel}: {size(path)} bytes (limit {limit})")
    assert not too_big, "Files too big for the local AI (split them, see TODO section SP): %s" % too_big


def test_the_not_split_yet_list_stays_honest():
    for game, allowed in NOT_SPLIT_YET.items():
        game_dir = ROOT / "games" / game
        if not game_dir.is_dir():
            continue
        over = [p for p in editable_files(game_dir) if size(p) > LIMIT_BYTES]
        assert over, f"{game} has no file over the limit any more: remove it from NOT_SPLIT_YET"
        assert len(over) <= allowed + 5, f"{game}: {len(over)} files over the limit"
