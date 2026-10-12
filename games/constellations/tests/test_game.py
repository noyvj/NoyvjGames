"""The engine entry point: actions, the one-way gating, undo/redo, hidden names, determinism."""

import json
import re
from pathlib import Path

import pytest

import charts
import game as game_module
import sky

GAME_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def fresh():
    game_module.handle(json.dumps({"action": "reset"}))
    yield
    game_module.handle(json.dumps({"action": "reset"}))


def do(**request):
    return json.loads(game_module.handle(json.dumps(request)))


def draw_figure(cid):
    do(action="pick", chart=cid)
    for a, b in charts.BY_ID[cid]["figure"]:
        v = do(action="toggle", a=a, b=b)
    return v


def solve(cid):
    draw_figure(cid)
    return do(action="finish")


def open_spring():
    for cid in [c["id"] for c in charts.SEASONS[0]["charts"]][:5]:
        solve(cid)


def test_the_first_view_is_the_first_winter_chart():
    v = do(action="open")
    assert v["ok"] and v["chart"]["id"] == charts.ORDER[0] and v["chart"]["number"] == 1 and v["chart"]["status"] == "open"
    assert v["totals"]["done"] == 0 and v["totals"]["charts"] == 40 and v["valid"] is False
    assert [s["open"] for s in v["seasons"]] == [True, False, False, False, False]


def test_stars_are_lettered_left_to_right_and_a_view_carries_everything_the_page_draws():
    v = do(action="open")
    stars = v["chart"]["stars"]
    assert [s["letter"] for s in stars] == list(charts.LETTERS[: len(stars)])
    assert [s["x"] for s in stars] == sorted(s["x"] for s in stars)
    for key in ("w", "h", "allowed", "never", "lines", "moves"):
        assert key in v["chart"]
    for key in ("words", "problems", "seasons", "atlas", "cards", "totals", "tally", "info"):
        assert key in v


def test_an_unfinished_chart_never_tells_its_name_its_star_names_or_its_note():
    v = do(action="open")
    text = json.dumps(v)
    for c in charts.ALL:
        assert c["name"] not in text.replace(c["id"], ""), c["name"]
        assert c["note"] not in text
        assert c["meaning"] not in text
        for s in c["stars"]:
            assert s["name"] not in text
    atlas_unfinished = [i for i in v["atlas"]["items"] if not i["solved"]]
    assert len(atlas_unfinished) == 40 and all("pts" not in i and "name" not in i for i in atlas_unfinished)


def test_drawing_a_line_counts_and_erasing_it_counts():
    rules = charts.rules(charts.ORDER[0])
    a, b = rules.edges[0]
    v = do(action="toggle", a=a, b=b)
    assert v["ok"] and any(l["a"] == a and l["b"] == b for l in v["chart"]["lines"]) and v["tally"]["draws"] == 1
    assert v["can_undo"] and v["totals"]["lines"] == 1
    v = do(action="toggle", a=b, b=a)                                       # the same pair the other way round erases it
    assert not v["chart"]["lines"] and v["tally"] == {"draws": 1, "erases": 1, "hints": 0}


def test_only_allowed_pairs_can_be_joined_and_nothing_is_counted_for_a_refusal():
    c = charts.BY_ID[charts.ORDER[0]]
    allowed = {tuple(e) for e in c["edges"]}
    n = len(c["stars"])
    bad = next((a, b) for a in range(n) for b in range(a + 1, n) if (a, b) not in allowed)
    v = do(action="toggle", a=bad[0], b=bad[1])
    assert v["ok"] is False and "too far apart" in v["message"] and v["tally"]["draws"] == 0
    for junk in ({"a": 1, "b": 1}, {"a": -1, "b": 2}, {"a": 0, "b": 99}, {"a": "x", "b": 1}, {"a": True, "b": 2}, {"a": 0}):
        assert do(action="toggle", **junk)["ok"] is False


def test_given_lines_stay_and_crossed_out_pairs_cannot_be_drawn():
    cid = "columba"
    v = do(action="pick", chart=cid)
    c = charts.BY_ID[cid]
    must = c["clues"]["must"][0]
    never = c["clues"]["never"][0]
    assert any(l["a"] == must[0] and l["b"] == must[1] and l["given"] for l in v["chart"]["lines"])
    r = do(action="toggle", a=must[0], b=must[1])
    assert r["ok"] is False and "already drawn for you" in r["message"]
    r = do(action="toggle", a=never[0], b=never[1])
    assert r["ok"] is False and "crossed out" in r["message"]
    assert v["chart"]["never"] == [never]
    assert [m["given"] for m in do(action="open")["chart"]["lines"]].count(True) == len(c["clues"]["must"])


def test_undo_and_redo_walk_through_the_changes():
    rules = charts.rules(charts.ORDER[0])
    a, b = rules.edges[0]
    c, d = rules.edges[1]
    do(action="toggle", a=a, b=b)
    do(action="toggle", a=c, b=d)
    v = do(action="undo")
    assert len(v["chart"]["lines"]) == 1 and v["can_redo"]
    v = do(action="undo")
    assert not v["chart"]["lines"] and not v["can_undo"]
    assert do(action="undo")["ok"] is False
    v = do(action="redo")
    assert len(v["chart"]["lines"]) == 1
    v = do(action="toggle", a=c, b=d)
    assert not v["can_redo"], "a new change clears redo"


def test_clear_erases_only_my_lines_and_can_be_undone():
    do(action="pick", chart="columba")
    c = charts.BY_ID["columba"]
    given = len(c["clues"]["must"])
    rules = charts.rules("columba")
    free = [e for e in rules.edges if rules.index[e] not in rules.must and rules.index[e] not in rules.never][:3]
    for a, b in free:
        do(action="toggle", a=a, b=b)
    v = do(action="clear")
    assert len(v["chart"]["lines"]) == given and v["tally"]["erases"] == 3 and v["can_clear"] is False
    assert do(action="clear")["ok"] is False
    v = do(action="undo")
    assert len(v["chart"]["lines"]) == given + 3


def test_finish_is_refused_until_every_number_holds():
    assert do(action="finish")["ok"] is False
    v = draw_figure(charts.ORDER[0])
    assert v["valid"] is True and v["problems"].startswith("Every number holds")
    r = do(action="finish")
    assert r["ok"] and r["chart"]["status"] == "solved" and r["totals"]["done"] == 1
    assert r["just"]["id"] == charts.ORDER[0] and r["chart"]["name"] == charts.BY_ID[charts.ORDER[0]]["name"]
    assert do(action="finish")["ok"] is False


def test_a_wrong_figure_is_described_in_words_never_called_a_failure():
    do(action="pick", chart="auriga")
    c = charts.BY_ID["auriga"]
    # draw both diagonals of the pentagon that cross if the chart offers them, otherwise a lone line
    rules = charts.rules("auriga")
    pairs = [(a, b) for a, b in rules.edges]
    crossing = next(((p, q) for p in pairs for q in pairs if rules.edge(*p) is not None and rules.conflict[rules.index[p]] >> rules.index[q] & 1), None)
    assert crossing is not None
    for a, b in crossing:
        v = do(action="toggle", a=a, b=b)
    assert "cross" in v["problems"] and not v["valid"] and any(l["cross"] for l in v["chart"]["lines"])
    assert do(action="finish")["ok"] is False and "Not yet" in do(action="finish")["message"]
    assert "fail" not in json.dumps(v).lower() and "wrong" not in v["problems"].lower()


def test_the_view_says_which_stars_are_short_met_or_over():
    do(action="pick", chart="auriga")
    c = charts.BY_ID["auriga"]
    assert all(s["state"] in ("short", "free") for s in do(action="open")["chart"]["stars"])
    v = draw_figure("auriga")
    assert all(s["state"] in ("met", "free") for s in v["chart"]["stars"])
    extra = next(e for e in c["edges"] if e not in c["figure"])
    v = do(action="toggle", a=extra[0], b=extra[1])
    assert any(s["state"] == "over" for s in v["chart"]["stars"]) or v["chart"]["stars"][extra[0]]["need"] is None


def test_the_chart_text_names_every_star_by_letter_and_what_it_needs_and_can_join():
    v = do(action="open")
    words = v["words"]
    n = len(v["chart"]["stars"])
    assert len(words) >= n + 2 and f"{n} stars" in words[0]
    for i, s in enumerate(v["chart"]["stars"]):
        line = words[1 + i]
        assert line.startswith("Star %s," % s["letter"]) and "Can join:" in line
        assert ("needs %d" % s["need"] in line) if s["need"] is not None else ("no number" in line)
    assert any(line.startswith("Lines you have drawn") for line in words)
    assert not re.search(r"Betelgeuse|Capella|Auriga", " ".join(words))


def test_a_finished_chart_is_read_only_and_names_its_stars():
    solve(charts.ORDER[0])
    v = do(action="open")
    assert v["editable"] is False and all("name" in s for s in v["chart"]["stars"])
    r = do(action="toggle", a=0, b=1)
    assert r["ok"] is False and "atlas" in r["message"]
    assert do(action="undo")["ok"] is False and do(action="clear")["ok"] is False
    assert [l["a"] for l in v["chart"]["lines"]] and any("Star" in w and v["chart"]["stars"][0]["name"] in w for w in v["words"])


def test_the_next_season_opens_after_five_charts_in_any_order():
    first = [c["id"] for c in charts.SEASONS[0]["charts"]]
    for cid in first[:4]:
        solve(cid)
    v = do(action="open")
    assert v["seasons"][1]["open"] is False and v["seasons"][1]["need"] == 1
    assert do(action="pick", chart=charts.SEASONS[1]["charts"][0]["id"])["ok"] is False
    v = solve(first[7])                                                     # the biggest chart of the season counts as one of the five
    assert v["seasons"][1]["open"] is True and v["just"]["opened"] == ["Spring Sky"]
    assert "A new page opens" in v["message"]
    assert do(action="pick", chart=charts.SEASONS[1]["charts"][0]["id"])["ok"] is True


def test_seasons_done_and_stats_move_only_up():
    ids = [c["id"] for c in charts.SEASONS[0]["charts"]]
    seen = []
    for cid in ids:
        v = solve(cid)
        seen.append((v["totals"]["done"], v["totals"]["stars"], v["totals"]["pages_open"], v["totals"]["seasons_done"], v["totals"]["lines"]))
    for before, after in zip(seen, seen[1:]):
        assert all(b <= a for b, a in zip(before, after))
    assert seen[-1][0] == 8 and seen[-1][3] == 1 and seen[-1][2] == 2
    assert seen[-1][1] == sum(len(c["stars"]) for c in charts.SEASONS[0]["charts"])
    v = do(action="open")
    assert v["seasons"][0]["done"] == 8 and len(v["cards"]) == 8


def test_next_goes_to_the_next_open_unfinished_chart_and_wraps():
    first = charts.ORDER[0]
    v = do(action="next")
    assert v["chart"]["id"] == charts.ORDER[1]
    solve(charts.ORDER[1])
    v = do(action="pick", chart=charts.ORDER[0])
    v = do(action="next")
    assert v["chart"]["id"] == charts.ORDER[2], "a finished chart is skipped"
    assert do(action="pick", chart="nonsense")["ok"] is False and do(action="pick", chart=3)["ok"] is False


def test_the_atlas_places_every_chart_and_shows_only_finished_figures():
    solve(charts.ORDER[0])
    v = do(action="open")
    items = {i["id"]: i for i in v["atlas"]["items"]}
    assert len(items) == 40
    done = items[charts.ORDER[0]]
    assert done["solved"] and len(done["pts"]) == len(charts.BY_ID[done["id"]]["stars"]) and done["lines"]
    for i in items.values():
        assert 0 <= i["x"] <= v["atlas"]["w"] and 0 <= i["y"] <= v["atlas"]["h"]
    # Orion stands near right ascension 5.6 h, declination about +1: right-hand side of the atlas (right ascension runs right to left), near the equator
    o = items["orion"]
    assert o["x"] > 0.7 * v["atlas"]["w"] and abs(o["y"] - v["atlas"]["h"] / 2) < 0.1 * v["atlas"]["h"]
    s = items["scorpius"]
    assert s["y"] > v["atlas"]["h"] / 2, "Scorpius is south of the equator"


def test_cards_carry_the_note_brightest_star_best_time_and_sources():
    solve(charts.ORDER[0])
    card = do(action="open")["cards"][0]
    c = charts.BY_ID[charts.ORDER[0]]
    assert card["name"] == c["name"] and card["note"] == c["note"] and card["brightest"] == c["brightest"] and card["best"] == c["best"]
    assert any("HYG" in s for s in card["sources"]) and any("Stellarium" in s for s in card["sources"]) and any("2026-10-12" in s for s in card["sources"])


def test_the_whole_game_can_be_played_through_to_the_end_of_season_five():
    for cid in charts.ORDER:
        if not charts.chart_open(game_module.game.solved, cid):
            continue
        solve(cid)
    # keep going until every season is open
    for _ in range(5):
        for cid in charts.ORDER:
            if charts.chart_open(game_module.game.solved, cid) and cid not in game_module.game.solved:
                solve(cid)
    v = do(action="open")
    assert v["totals"]["done"] == 40 and v["totals"]["seasons_done"] == 5 and v["totals"]["pages_open"] == 5
    assert do(action="next")["ok"] is False


def test_reset_starts_over():
    solve(charts.ORDER[0])
    v = do(action="reset")
    assert v["totals"]["done"] == 0 and v["tally"] == {"draws": 0, "erases": 0, "hints": 0} and v["chart"]["id"] == charts.ORDER[0]


def test_bad_requests_are_answered_not_raised():
    assert "error" in json.loads(game_module.handle("not json"))
    assert "error" in do(action="no-such-action")
    assert "error" in json.loads(game_module.handle("[]"))


def test_the_engine_is_deterministic_and_reads_no_clock_or_random_source():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if path.name.startswith("charts_s"):
            continue
        for banned in ("import random", "from random", "import time", "from time", "datetime", "os.urandom", "secrets", "Date.now"):
            assert banned not in text, "%s uses %s" % (path.name, banned)
    a = [do(action="toggle", a=x, b=y)["problems"] for x, y in charts.BY_ID[charts.ORDER[0]]["figure"]]
    do(action="reset")
    b = [do(action="toggle", a=x, b=y)["problems"] for x, y in charts.BY_ID[charts.ORDER[0]]["figure"]]
    assert a == b


def test_engine_modules_run_under_the_python_pyodide_ships():
    """No syntax newer than 3.9 that the local interpreter would not parse either (the tests run under 3.9; Pyodide has 3.12)."""
    import ast
    for path in GAME_DIR.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"))
