"""AN-17: Easy / Normal / Hard. Mirror Lab's only lever is the hint ladder (see hints.py); benches, rules, clears and tags never change.
Normal is the game exactly as designed (pinned below)."""

import json
import re
from pathlib import Path

import benches
import game
import hints

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def setup_function(_fn):
    game.game.__init__()
    call(action="difficulty", level="normal")


def teardown_function(_fn):
    call(action="difficulty", level="normal")
    game.game.__init__()


def script():
    out = [call(action="open")]
    for _ in range(3):
        out.append(call(action="hint"))
    out.append(call(action="place_answer"))
    out.append(call(action="clear_bench"))
    out.append(call(action="pick", bench="c1-1"))
    out.append(call(action="place", r=3, c=4, piece="mirror"))
    return json.dumps(out, sort_keys=True), json.dumps(game.get_state(), sort_keys=True)


def test_normal_is_byte_for_byte_the_same_with_or_without_being_told():
    plain = script()
    game.game.__init__()
    call(action="difficulty", level="normal")
    assert script() == plain


def test_a_detour_through_hard_and_easy_leaves_no_trace():
    plain = script()
    game.game.__init__()
    for level in ("hard", "easy", "normal"):
        call(action="difficulty", level=level)
    assert script() == plain


def test_the_helper_defaults_are_the_normal_ladder():
    for b in benches.ALL_BENCHES:
        for rung in range(4):
            assert hints.view(b, rung) == hints.view(b, rung, "normal")
        assert hints.rung_cap("normal") == 3 and hints.next_rung(0, "normal") == 1 and hints.next_rung(3, "normal") is None


def test_the_level_is_not_saved_and_a_bad_level_is_refused():
    call(action="difficulty", level="hard")
    assert "difficulty" not in json.dumps(game.get_state())
    v = call(action="difficulty", level="impossible")
    assert v["ok"] is False and v["difficulty"] == "hard"
    assert call(action="difficulty", level=None)["ok"] is False


def test_records_are_never_lowered_by_the_level():
    for level in ("hard", "easy", "normal"):
        call(action="difficulty", level=level)
        game.game._enter("c1-1")
        for r, c, piece, _s in benches.BY_ID["c1-1"].solution:
            call(action="place", r=r, c=c, piece=piece)
        assert len(game.game.cleared["c1-1"]) == benches.BY_ID["c1-1"].par
        call(action="pickup", r=3, c=4)
        assert "c1-1" in game.game.cleared                                           # picking up never un-clears, on any level
        call(action="open")
    assert call(action="open")["totals"]["fewest"] == 1


def test_every_level_sees_the_same_benches_and_chapters_and_goals():
    base = call(action="open")
    for level in ("easy", "hard"):
        v = call(action="difficulty", level=level)
        assert v["chapters"] == base["chapters"] and v["goals"] == base["goals"] and v["totals"] == base["totals"]
        assert v["bench"]["rows"] == base["bench"]["rows"] and v["bench"]["tray"] == base["bench"]["tray"]


def test_the_page_mounts_the_shared_picker_and_tells_the_engine():
    assert 'id="difficulty-slot"' in HTML and "shared/difficulty.js" in HTML and "shared/difficulty.css" in HTML
    assert "NoyvjDifficulty.mount" in APP and "NoyvjDifficulty.onChange" in APP and "NoyvjDifficulty.get" in APP and '"difficulty"' in APP
    assert "easy:" in APP and "normal:" in APP and "hard:" in APP
    assert not re.search(r"localStorage[^;]*difficulty", APP)                       # the shared component owns the stored choice
