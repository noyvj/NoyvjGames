"""Keeps Le Champ de Mots' files small enough for the personal AI, which holds about 24k tokens and has to read a whole
file to edit it. Size is estimated as bytes divided by 4. Exempt: the generated pages (pc.html from index.html by
scripts/generate-pc-pages.py, study-table.html from scripts/generate-champ-study-table.py), the notes file and the data
files (.json, never edited by hand). index.html alone has its own, documented cap: see INDEX_HTML_MAX_BYTES."""
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
MAX_TOKENS = 14_000
EDITABLE_SUFFIXES = {".py", ".js", ".css", ".html"}
EXEMPT = {"pc.html", "study-table.html"}  # generated, never edited by hand
SKIP_DIRS = {"__pycache__", ".pytest_cache"}
# index.html is about 75 KB of markup: one page with some forty panels, no function or rule inside it to cut out (its
# scripts and the stylesheet were already moved into their own files). Cutting it further would mean loading panels
# from fragments at run time, which changes when the page's elements exist. Keep it from growing past this.
INDEX_HTML_MAX_BYTES = 78_000


def _editable_files():
    for path in sorted(GAME_DIR.rglob("*")):
        if not path.is_file() or path.suffix not in EDITABLE_SUFFIXES:
            continue
        if SKIP_DIRS & set(path.relative_to(GAME_DIR).parts):
            continue
        if path.name in EXEMPT:
            continue
        yield path


def test_no_editable_file_is_over_the_token_limit():
    too_big = []
    for path in _editable_files():
        size = len(path.read_bytes().replace(b"\r\n", b"\n"))
        if path.name == "index.html":
            if size > INDEX_HTML_MAX_BYTES:
                too_big.append(f"index.html: {size} bytes (cap {INDEX_HTML_MAX_BYTES})")
        elif size // 4 > MAX_TOKENS:
            too_big.append(f"{path.relative_to(GAME_DIR)}: about {size // 4} tokens")
    assert not too_big, (
        "Split these files (see 'File map' in CLAUDE.md for the recipe), the AI cannot read a file this big: "
        + "; ".join(too_big)
    )


def test_the_check_sees_the_files_it_should():
    names = {path.name for path in _editable_files()}
    assert {"game.py", "minigames.py", "index.html", "style.css", "boot.js", "champ_model.py", "champ_minigames_cafe.py"} <= names
    assert "pc.html" not in names and "study-table.html" not in names
