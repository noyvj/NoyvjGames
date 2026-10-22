"""Slingshot is split into small files so a small local AI (it holds about 24k tokens and must read a whole file to
edit it) can edit them. These tests keep it that way: no editable file passes about 14,000 estimated tokens
(bytes / 4). See "File map" in CLAUDE.md."""

from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
MAX_TOKENS = 14_000

# Not edited by hand by the AI: CLAUDE.md is documentation for the main session (data files such as .json are not
# checked at all).
EXEMPT = {"CLAUDE.md"}
SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".txt"}


def _tokens(path):
    return len(path.read_bytes().replace(b"\r\n", b"\n")) // 4


def _editable_files():
    for path in sorted(GAME_DIR.rglob("*")):
        rel = path.relative_to(GAME_DIR)
        if not path.is_file() or "__pycache__" in rel.parts or ".pytest_cache" in rel.parts:
            continue
        if path.suffix not in SUFFIXES or path.name in EXEMPT:
            continue
        yield rel, path


def test_no_editable_file_is_over_the_token_limit():
    too_big = {str(rel): _tokens(path) for rel, path in _editable_files() if _tokens(path) > MAX_TOKENS}
    assert not too_big, f"split these files (limit {MAX_TOKENS} tokens, about {MAX_TOKENS * 4} bytes): {too_big}"
