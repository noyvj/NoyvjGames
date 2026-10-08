"""shared/run_code.py: the compact run code (planning/TODO.md FY-7). Known values are pinned so an
accidental change to the format fails loudly; test_run_code_browser.py checks that shared/run-code.js
agrees with this module on the same inputs."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_code as rc  # noqa: E402
import seed as sd  # noqa: E402

FULL = {"game": "tide", "seed": "TIDE-K7F2Q", "mode": "hard", "score": 4210, "stats": [3, 12]}
FULL_CODE = "RUN-TIDE-7G0F4-1JE0H-M62WK-4Y8G0-630-EPX"
MINIMAL_CODE = "RUN-TRADEEMPIRE-4000-NH6"


def craft(prefix, data):
    """A syntactically valid code with a correct checksum around arbitrary body bytes."""
    body = rc._to_b32(data)
    return "RUN-%s-%s-%s" % (prefix, body, rc._checksum(prefix, body))


def test_pinned_codes():
    assert rc.encode(FULL) == FULL_CODE
    assert rc.encode({"game": "trade-empire"}) == MINIMAL_CODE
    assert rc.encode({"game": "sol", "seed": "sol-22222", "score": 0}) == rc.encode({"game": "sol", "seed": "SOL-22222", "score": 0, "stats": []})


def test_body_layout_is_the_documented_one():
    prefix, rest = rc._split(FULL_CODE, None)
    assert prefix == "TIDE"
    data = rc._from_b32(rest[:-3])
    assert data[0] == 0x3C                       # version 1, has seed, has result, 2 stats
    assert int.from_bytes(bytes(data[1:5]), "big") == rc._seed_to_int("K7F2Q")
    assert data[5] == 4 and bytes(data[6:10]) == b"hard"
    assert data[10:] == [0xF2, 0x20, 3, 12]      # 4210 as a little-endian varint, then the stats
    minimal = rc._from_b32(rc._split(MINIMAL_CODE, None)[1][:-3])
    assert minimal == [0x20, 0]                  # version only, empty mode


def test_round_trip_over_many_runs():
    r = sd.Rng("run-code-corpus")
    games = ["tide", "signal", "trade-empire", "champ-de-mots", "sol", "canopy", "continuum"]
    modes = ["", "hard", "easy", "daily", "a", "12345678", "z9"]
    for i in range(400):
        game = r.choice(games)
        fields = {"game": game}
        if r.chance(0.8):
            fields["seed"] = sd.new_seed(game, entropy=r)
        if r.chance(0.7):
            fields["mode"] = r.choice(modes)
        if r.chance(0.8):
            fields["score"] = r.choice([0, 1, 127, 128, 4210, r.below(10 ** 9), r.below(rc.MAX_VALUE + 1), rc.MAX_VALUE])
            fields["stats"] = [r.choice([0, 1, 3, 200, r.below(10 ** 6), rc.MAX_VALUE]) for _ in range(r.below(3))]
        code = rc.encode(fields)
        d = rc.decode(code, game)
        assert d["ok"], (fields, code, d)
        assert d["code"] == code
        assert d["game"] == sd.prefix_for(game)
        assert d["seed"] == fields.get("seed", "")
        assert d["mode"] == fields.get("mode", "")
        assert d["score"] == fields.get("score")
        assert d["stats"] == fields.get("stats", [])
        assert d["has_result"] == ("score" in fields)
        assert len(code.replace("-", "")) <= rc.MAX_COMPACT_LEN


def test_largest_possible_code_stays_within_the_bound():
    code = rc.encode({"game": "a-very-long-game-slug", "seed": sd.new_seed("a-very-long-game-slug"), "mode": "abcdefgh",
                      "score": rc.MAX_VALUE, "stats": [rc.MAX_VALUE, rc.MAX_VALUE]})
    assert len(code.replace("-", "")) <= rc.MAX_COMPACT_LEN
    assert rc.decode(code)["ok"]


def test_decoded_data_holds_only_the_documented_fields_and_is_never_verified():
    d = rc.decode(FULL_CODE)
    assert set(d) == {"ok", "error", "message", "code", "game", "seed", "mode", "score", "stats", "has_result", "verified"}
    assert d["verified"] is False
    assert rc.decode("nonsense")["verified"] is False
    assert not rc.decode(FULL_CODE.replace("630", "000"))["ok"]


@pytest.mark.parametrize("typed", [
    FULL_CODE,
    FULL_CODE.lower(),
    "  " + FULL_CODE.replace("-", " ") + "  ",
    FULL_CODE.replace("-", "–"),
    FULL_CODE.replace("-", "_"),
    FULL_CODE.replace("-", ""),
    FULL_CODE.replace("-", "\n"),
    "RUN TIDE 7G0F4-1JE0H M62WK 4Y8G0 630 EPX",
    FULL_CODE.replace("0", "O"),
    FULL_CODE.replace("1", "l"),
    FULL_CODE.replace("1", "I"),
])
def test_decode_forgives_case_spaces_dashes_and_lookalikes(typed):
    d = rc.decode(typed, "tide")
    assert d["ok"] and d["code"] == FULL_CODE, typed


def test_dashless_code_needs_the_game_to_find_the_prefix():
    bare = FULL_CODE.replace("-", "")
    assert rc.decode(bare, "tide")["ok"]
    assert rc.decode(bare)["error"] == "format"


def test_error_reasons():
    assert rc.decode("")["error"] == "empty"
    assert rc.decode("   \n")["error"] == "empty"
    assert rc.decode(None)["error"] == "empty"
    assert rc.decode(12345)["error"] == "empty"
    assert rc.decode("x" * 401)["error"] == "too-long"
    assert rc.decode("RUN-TIDE-" + "A" * 90)["error"] == "too-long"
    assert rc.decode("hello there")["error"] == "format"
    assert rc.decode("RUN-TIDE")["error"] == "format"
    assert rc.decode("RUN-TIDE-AB-C")["error"] == "format"          # too short to hold a body
    assert rc.decode("RUN-TIDE-UUUUU-UUUUU-UUU")["error"] == "format"  # U is not in the alphabet
    assert rc.decode("RUN-X-ABCDE-FGH")["error"] == "format"           # prefix too short
    assert rc.decode(FULL_CODE[:-1] + "Z")["error"] == "checksum"
    wrong = rc.decode(FULL_CODE, "signal")
    assert wrong["error"] == "wrong-game" and "TIDE" in wrong["message"] and not wrong["ok"]
    assert rc.decode(FULL_CODE, "tide")["ok"] and rc.decode(FULL_CODE)["ok"]
    for reason in ("empty", "too-long", "format", "version", "checksum"):
        assert rc.MESSAGES[reason]


def test_every_single_character_slip_is_caught():
    chars = [i for i, c in enumerate(FULL_CODE) if c != "-"][4:]       # skip the readable RUN/TIDE header? no: include body+check
    caught = missed = 0
    for i in chars:
        for ch in rc.B32:
            if ch == FULL_CODE[i]:
                continue
            bad = FULL_CODE[:i] + ch + FULL_CODE[i + 1:]
            if rc.decode(bad, "tide")["ok"]:
                missed += 1
            else:
                caught += 1
    assert caught > 600 and missed == 0


def test_newer_format_version_is_reported_not_guessed():
    assert rc.decode(craft("TIDE", [0x40 | 0x00, 0]))["error"] == "version"   # version 2
    assert rc.decode(craft("TIDE", [0x00, 0]))["error"] == "version"          # version 0


@pytest.mark.parametrize("data", [
    [0x20],                              # no mode length byte
    [0x20, 9] + [97] * 9,                # mode longer than 8
    [0x20, 3, 97, 98],                   # mode runs off the end
    [0x20, 2, 65, 66],                   # upper-case mode is not canonical
    [0x20, 0, 0],                        # trailing byte
    [0x21, 0],                           # reserved bit
    [0x20 | 0x10, 0, 0, 0],              # seed truncated
    [0x20 | 0x10, 0x01, 0xFF, 0xFF, 0xFF, 0],   # seed number above 31**5
    [0x20 | 0x08, 0],                    # result flag but no score
    [0x20 | 0x08, 0, 0x80],              # unfinished varint
    [0x20 | 0x08, 0, 0x80, 0x00],        # non-canonical varint (ends in a zero group)
    [0x20 | 0x04, 0],                    # stats without a result
    [0x20 | 0x08 | 0x06, 0, 1, 1, 1],    # three stats
    [0x20 | 0x08, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x7F],   # above MAX_VALUE
    [0x20 | 0x08, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x01],   # eight groups
])
def test_malformed_bodies_are_refused_even_with_a_good_checksum(data):
    assert rc.decode(craft("TIDE", data))["error"] == "format", data


def test_nonzero_padding_is_refused():
    body = rc._to_b32([0x20, 0])                    # 16 bits -> 4 chars, 4 padding bits
    last = rc.B32[rc.B32.index(body[-1]) | 1]
    forged = body[:-1] + last
    assert forged != body
    assert rc.decode("RUN-TIDE-%s-%s" % (forged, rc._checksum("TIDE", forged)))["error"] == "format"


def test_decoding_is_canonical_and_idempotent():
    for typed in (FULL_CODE.lower(), FULL_CODE.replace("-", " "), MINIMAL_CODE.replace("-", "")):
        once = rc.normalize(typed, "tide" if "TIDE" in typed.upper() else "trade-empire")
        assert once and rc.normalize(once) == once
    assert rc.normalize("nope") == ""
    assert rc.is_valid(FULL_CODE) and not rc.is_valid("nope")
    assert rc.validate(FULL_CODE, "tide") == {"ok": True, "code": FULL_CODE, "error": "", "message": ""}
    bad = rc.validate("RUN-TIDE-AAAAA-AAA", "tide")
    assert not bad["ok"] and bad["error"] in ("checksum", "format") and bad["message"]


@pytest.mark.parametrize("fields,reason", [
    ({}, "game"),
    ({"game": 5}, "game"),
    ({"game": "x"}, "game"),
    ({"game": "tide", "seed": "TIDE-K0F2Q"}, "seed"),
    ({"game": "tide", "seed": 12345}, "seed"),
    ({"game": "tide", "seed": "SIGNAL-K7F2Q"}, "wrong-game"),
    ({"game": "tide", "mode": "Hard Mode"}, "mode"),
    ({"game": "tide", "mode": "waytoolongmode"}, "mode"),
    ({"game": "tide", "mode": 3}, "mode"),
    ({"game": "tide", "score": -1}, "score"),
    ({"game": "tide", "score": 1.5}, "score"),
    ({"game": "tide", "score": True}, "score"),
    ({"game": "tide", "score": "9"}, "score"),
    ({"game": "tide", "score": rc.MAX_VALUE + 1}, "score"),
    ({"game": "tide", "stats": [1]}, "score"),
    ({"game": "tide", "score": 1, "stats": [1, 2, 3]}, "stats"),
    ({"game": "tide", "score": 1, "stats": [-1]}, "stats"),
    ({"game": "tide", "score": 1, "stats": "ab"}, "stats"),
])
def test_encode_refuses_with_a_clear_reason(fields, reason):
    with pytest.raises(rc.RunCodeError) as info:
        rc.encode(fields)
    assert info.value.reason == reason and str(info.value)
    assert isinstance(info.value, ValueError)


def test_encode_accepts_loose_seed_and_mode_case():
    assert rc.encode({"game": "tide", "seed": "k7f2q", "mode": "HARD", "score": 4210, "stats": [3, 12]}) == FULL_CODE
    assert rc.encode({"game": "tide", "seed": "", "mode": None, "score": None, "stats": None}) == rc.encode({"game": "tide"})


def test_describe_lines():
    d = rc.decode(FULL_CODE)
    opts = {"unit": "pts", "stats": [{"one": "storm", "many": "storms"}, "calm days"], "modes": {"hard": "Hard"}}
    assert rc.describe(d, opts) == "Their run: 4,210 pts, 3 storms, 12 calm days, Hard mode"
    assert rc.describe(d) == "Their run: 4,210, 3, 12, hard mode"
    one = rc.decode(rc.encode({"game": "tide", "score": 1000000, "stats": [1]}))
    assert rc.describe(one, {"unit": "pts", "stats": [{"one": "storm", "many": "storms"}]}) == "Their run: 1,000,000 pts, 1 storm"
    seed_only = rc.decode(rc.encode({"game": "tide", "seed": "TIDE-K7F2Q"}))
    assert rc.describe(seed_only) == "Their run: seed TIDE-K7F2Q"
    assert rc.describe(rc.decode(MINIMAL_CODE), {"prefix": "Ghost"}) == "Ghost"
    assert rc.describe(rc.decode("nope")) == ""
    assert rc.describe(None) == ""


def test_alphabets_and_limits_agree_with_the_seed_module():
    assert len(rc.B32) == 32 and len(set(rc.B32)) == 32 and not set("ILOU") & set(rc.B32)
    assert rc.SEED_BASE == len(sd.ALPHABET) == 31
    assert rc.SEED_LIMIT < 2 ** 32
    assert rc._int_to_seed(rc._seed_to_int("K7F2Q")) == "K7F2Q"
    assert rc._int_to_seed(0) == "22222" and rc._int_to_seed(rc.SEED_LIMIT - 1) == "ZZZZZ"
    assert rc.MAX_COMPACT_LEN >= len("RUN") + sd.PREFIX_MAX + 56 + 3
