"""Regenerates tests/fixtures/daily_v1.json (the frozen daily puzzles).

Run ONLY when the generator is changed on purpose, and in the same change
bump SEED_VERSION in game.py to "v2": the fixture pins every past daily
puzzle so an accidental generator edit cannot silently alter them.

    cd games/signal && python3 tests/make_fixture.py
"""

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import game  # noqa: E402

DAYS = 365


def build():
    start = datetime.date.fromisoformat(game.EPOCH)
    puzzles = {}
    for i in range(DAYS):
        date = (start + datetime.timedelta(days=i)).isoformat()
        for mode in game.DAILY_MODES:
            p = game.daily_puzzle(date, mode)
            n = game.board_for(mode).n
            puzzles["%s:%s" % (date, mode)] = {
                "t": [[c // n, c % n] for c in p.transmitters], "par": p.par,
            }
    return {"seed_version": game.SEED_VERSION, "epoch": game.EPOCH, "days": DAYS, "puzzles": puzzles}


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "fixtures" / "daily_v1.json"
    out.write_text(json.dumps(build(), separators=(",", ":")) + "\n")
    print("wrote", out)
