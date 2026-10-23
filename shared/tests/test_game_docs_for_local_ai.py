"""LA-9: every built game keeps the briefing the personal AI needs, so the readiness work (LA-1) cannot quietly rot.

A built game (it has an index.html) must have: a CLAUDE.md of at most 30,000 bytes (the AI reads it on every task; the long
history lives in NOTES.md), a "For the local AI" section in it, and tests/browser_helpers.py plus tests/test_example_browser.py
(the working example it copies for browser tests). Games listed in NOT_READY are still being prepared: remove an entry when its
readiness pass lands (Zero-G Shift: a paused partial build).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE_LIMIT = 30_000
NOT_READY = {"zero-g-shift"}


def built_games():
    for d in sorted((ROOT / "games").iterdir()):
        if d.is_dir() and (d / "index.html").exists() and d.name not in NOT_READY:
            yield d


def test_every_built_game_has_a_small_claude_md_with_a_local_ai_map():
    bad = []
    for d in built_games():
        md = d / "CLAUDE.md"
        if not md.exists():
            bad.append(f"{d.name}: no CLAUDE.md")
            continue
        text = md.read_text(encoding="utf-8")
        if len(text.encode("utf-8")) > CLAUDE_LIMIT:
            bad.append(f"{d.name}: CLAUDE.md is {len(text.encode('utf-8'))} bytes (limit {CLAUDE_LIMIT}); move history to NOTES.md")
        if "For the local AI" not in text:
            bad.append(f"{d.name}: CLAUDE.md has no 'For the local AI' section")
    assert not bad, bad


def test_every_built_game_has_the_browser_test_helper_and_an_example():
    bad = []
    for d in built_games():
        for name in ("browser_helpers.py", "test_example_browser.py"):
            if not (d / "tests" / name).exists():
                bad.append(f"{d.name}: tests/{name} missing")
    assert not bad, bad


def test_the_not_ready_list_stays_honest():
    for name in NOT_READY:
        d = ROOT / "games" / name
        if not d.is_dir():
            continue
        md = d / "CLAUDE.md"
        ready = (
            md.exists()
            and "For the local AI" in md.read_text(encoding="utf-8")
            and (d / "tests" / "browser_helpers.py").exists()
        )
        assert not ready, f"{name} is ready now: remove it from NOT_READY"
