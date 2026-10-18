"""Keep every app/*.py small enough for the local AI (it holds about 24k tokens and reads a whole file to edit it).

Estimated tokens = bytes / 4. The limit is 14,000 (about 56,000 bytes). If a file gets near it, split it by
feature the way main.py was split (see app/CLAUDE.md) instead of raising the limit.
"""

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
MAX_ESTIMATED_TOKENS = 14_000


def test_no_app_module_is_too_big():
    too_big = []
    for path in sorted(APP_DIR.glob("*.py")):
        tokens = path.stat().st_size / 4
        if tokens > MAX_ESTIMATED_TOKENS:
            too_big.append(f"{path.name}: about {int(tokens)} tokens")
    assert not too_big, "split these files: " + "; ".join(too_big)


def test_main_py_is_only_the_app_assembly():
    # main.py creates the app and includes routers; routes live in routes_*.py.
    assert "@app." not in (APP_DIR / "main.py").read_text()
