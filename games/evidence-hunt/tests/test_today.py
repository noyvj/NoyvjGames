"""Z-5c, "Today's run": a practice house chosen by the UTC date's shared seed text (EVIDENCEHUNT-K7F2Q). The house is a pure function
of that text; the engine knows no date. Nothing is saved unless a house was opened this way, and a bad saved entry is dropped."""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import gen
from tests.helpers import call, solve_with_hints

SHARED = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))
import seed as noyvj_seed  # noqa: E402


def days(n, start=date(2026, 10, 12)):
    return [(start + timedelta(days=i)).isoformat() for i in range(n)]


def fresh():
    import game
    game.game.__init__()
    return call(action="open")


def saved():
    import game
    return json.loads(json.dumps(game.get_state()))


def test_every_date_of_two_years_makes_a_valid_fair_house_of_a_middle_size():
    sizes, codes = [], set()
    for day in days(120):
        text = noyvj_seed.daily_seed("evidence-hunt", day)
        assert gen.is_daily_text(text) and noyvj_seed.is_valid(text, "evidence-hunt")
        d, s = gen.daily_house(text)
        assert d in gen.DAILY_SIZES and 0 <= s < gen.SEED_LIMIT
        assert gen.daily_house(text) == (d, s)
        assert gen.make(d, s) is not None
        sizes.append(d)
        codes.add(gen.code_of(d, s))
    assert set(sizes) == {2, 3, 4} and len(codes) == 120


def test_only_a_well_formed_text_for_this_game_makes_a_house():
    for bad in (None, 5, "", "TIDE-K7F2Q", "EVIDENCEHUNT-K7F2", "EVIDENCEHUNT-K7F2Q1", "evidencehunt-k7f2q", "EVIDENCEHUNT-K7F2I", "EVIDENCEHUNTK7F2Q", "EH3-1K9X2"):
        assert gen.daily_house(bad) is None, bad
    assert gen.daily_house("EVIDENCEHUNT-K7F2Q") is not None


def test_opening_todays_house_gives_the_same_house_and_remembers_the_text():
    text = noyvj_seed.daily_seed("evidence-hunt", "2026-10-20")
    house = gen.daily_house(text)
    fresh()
    v = call(action="practice", today=text)
    assert v["ok"] and v["case"]["practice"] and v["case"]["code"] == gen.code_of(*house) and v["case"]["today_seed"] == text
    again = call(action="practice", today=text)
    assert again["case"]["id"] == v["case"]["id"] and again["case"]["today_seed"] == text
    assert saved()["sb"]["today"] == {gen.code_of(*house): text}
    # an ordinary practice house does not carry a text, even when it is the same code typed by hand
    other = call(action="practice", difficulty=1)
    assert other["case"]["today_seed"] == ""
    typed = call(action="practice", code=gen.code_of(*house))
    assert typed["case"]["today_seed"] == text      # the same code is the same house, so it is still today's


def test_a_bad_text_changes_nothing_and_says_why():
    fresh()
    before = call(action="open")["case"]["id"]
    v = call(action="practice", today="TIDE-K7F2Q")
    assert not v["ok"] and "seed of the day" in v["message"] and v["case"]["id"] == before
    assert "sb" not in saved()


def test_solving_todays_house_shows_the_result_and_never_touches_an_authored_seal():
    fresh()
    best_before = saved().get("best", {})
    v = call(action="practice", today=noyvj_seed.daily_seed("evidence-hunt", "2026-10-21"))
    assert not v["result"]
    done = solve_with_hints()
    assert done["result"] and done["result"]["grade_name"] and done["case"]["today_seed"]
    assert saved().get("best", {}) == best_before


def test_a_new_save_has_no_key_and_an_old_save_loads_unchanged():
    import game
    fresh()
    assert "sb" not in saved()
    call(action="practice", difficulty=2)
    data = saved()
    assert "today" not in data["sb"]
    game.load_state(json.loads(json.dumps(data)))
    assert saved() == data


def test_the_saved_entry_survives_a_reload_and_a_hand_edited_one_is_dropped():
    import game
    fresh()
    text = noyvj_seed.daily_seed("evidence-hunt", "2026-10-22")
    code = gen.code_of(*gen.daily_house(text))
    call(action="practice", today=text)
    data = saved()
    game.load_state(json.loads(json.dumps(data)))
    assert call(action="open")["case"]["today_seed"] == text
    for bad in ({code: "EVIDENCEHUNT-AAAAA"}, {"EH2-1": text}, {code: 5}, {5: text}, {code: "TIDE-K7F2Q"}, [text], "x"):
        edited = json.loads(json.dumps(data))
        edited["sb"]["today"] = bad
        game.load_state(edited)
        assert call(action="open")["case"]["today_seed"] == "", bad


def test_only_the_four_newest_texts_are_kept():
    fresh()
    texts = [noyvj_seed.daily_seed("evidence-hunt", day) for day in days(7)]
    for text in texts:
        call(action="practice", today=text)
    kept = saved()["sb"]["today"]
    assert len(kept) == 4 and set(kept.values()) == set(texts[-4:])
