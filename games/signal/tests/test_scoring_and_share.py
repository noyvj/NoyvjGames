"""Reading levels, glyphs and the spoiler-free share text."""

import re


def test_levels_span_zero_to_seven(game):
    top = 5
    assert game.reading_level(0, top) == 0
    assert game.reading_level(1, top) == 2
    assert game.reading_level(5, top) == 7
    assert game.reading_level(99, top) == 7  # above the display ceiling
    assert game.reading_level(1, 100) == 1  # any signal is at least level 1
    levels = [game.reading_level(v, 12) for v in range(0, 13)]
    assert levels == sorted(levels)


def test_fill_is_clamped_and_rounded(game):
    assert game.reading_fill(0, 5) == 0.0
    assert game.reading_fill(3, 5) == 0.6
    assert game.reading_fill(50, 5) == 1.0


def test_glyphs_have_a_text_fallback(game):
    assert game.glyph_for(0) == "▁" and game.glyph_for(7) == "█"
    assert [game.glyph_for(i, ascii_mode=True) for i in range(8)] == list("..::++##")


def _rec(kind="daily", result="won", readings=(0, 3, 5), mode="easy", code=None):
    rec = {
        "mode": mode, "kind": kind, "pings": [[i, i, v] for i, v in enumerate(readings)],
        "marks": [], "guess": [], "result": result, "pings_used": len(readings), "par": 4,
    }
    if code:
        rec["code"] = code
    return rec


def test_share_text_daily_win(game):
    text = game.build_share_text(_rec(), "easy", 37)
    assert text == "Signal #37 easy 3/8 ⚡\n▁▆█ ✔"


def test_share_text_loss_uses_x_and_cross(game):
    text = game.build_share_text(_rec(result="lost"), "hard", 5)
    assert text.splitlines()[0] == "Signal #5 hard X/9 ⚡"
    assert text.endswith("✖")


def test_share_text_ascii_fallback_has_no_emoji_or_blocks(game):
    text = game.build_share_text(_rec(), "easy", 37, ascii_mode=True)
    assert text == "Signal #37 easy 3/8\n.+# OK"
    assert text.isascii()


def test_share_text_archive_and_practice_are_labelled(game):
    assert "(archive)" in game.build_share_text(_rec(kind="archive"), "easy", 12)
    practice = game.build_share_text(_rec(kind="practice", code="P-E12345"), "easy", 0)
    assert practice.startswith("Signal practice P-E12345 easy 3/8")
    assert "#" not in practice.splitlines()[0]


def test_share_text_never_leaks_positions_or_readings(game):
    rec = _rec(readings=(7, 2, 0, 5))
    rec["marks"] = rec["guess"] = [[3, 4], [5, 6]]
    text = game.build_share_text(rec, "easy", 9)
    assert not re.search(r"[A-O][0-9]", text)
    body = text.splitlines()[1]
    assert not any(ch.isdigit() for ch in body)


def test_empty_ping_list_still_shares(game):
    rec = _rec(readings=())
    assert game.build_share_text(rec, "easy", 1).splitlines()[1].startswith("- ")


def test_flavour_lines_are_deterministic_and_cover_the_range(game):
    assert game.flavour_for_reading(0, 4, 3) == game.flavour_for_reading(0, 4, 3)
    seen = {game.flavour_for_reading(v, 4, s) for v in range(0, 8) for s in range(6)}
    assert len(seen) >= 12
    assert game.flavour_for_reading(6, 4, 0) in game._LINES["stacked"]
    assert game.flavour_for_reading(0, 4, 0) in game._LINES["zero"]
    assert sum(len(v) for v in game._LINES.values()) >= 40
