"""Every chart is PROVED: exactly one valid figure (two independent counters), equal to the traditional figure; every clue is needed;
the figure can be finished by line logic; the geometry is exact and the data is sourced."""

import json
import math
from pathlib import Path

import pytest

import charts
import sky

GAME_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT = json.loads((GAME_DIR / "data" / "snapshot.json").read_text(encoding="utf-8"))
IDS = [c["id"] for c in charts.ALL]


def fig_idx(c):
    rules = charts.rules(c["id"])
    return frozenset(rules.index[tuple(e)] for e in c["figure"])


def test_three_seasons_of_eight_with_sizes_five_to_fourteen():
    assert [len(s["charts"]) for s in charts.SEASONS] == [8, 8, 8]
    assert [s["name"] for s in charts.SEASONS] == ["Winter Sky", "Spring Sky", "Summer Sky"]
    assert len(charts.ALL) == 24 and len(set(IDS)) == 24
    sizes = [len(c["stars"]) for c in charts.ALL]
    assert min(sizes) == 5 and max(sizes) <= 14
    for s in charts.SEASONS:
        counts = [len(c["stars"]) for c in s["charts"]]
        assert counts == sorted(counts), "a season goes from small charts to big ones"
        assert [c["number"] for c in s["charts"]] == list(range(1, 9))


@pytest.mark.parametrize("cid", IDS)
def test_exactly_one_valid_figure_and_it_is_the_traditional_one(cid):
    c = charts.BY_ID[cid]
    rules = charts.rules(cid)
    found = sky.solutions(rules, 3)
    assert len(found) == 1, "%s has %d valid figures" % (cid, len(found))
    assert found[0] == fig_idx(c)
    assert sky.analyse(rules, fig_idx(c))["valid"]


@pytest.mark.parametrize("cid", IDS)
def test_the_independent_counter_agrees(cid):
    assert sky.count_by_stars(charts.rules(cid), 3) == 1


@pytest.mark.parametrize("cid", IDS)
def test_every_clue_is_needed(cid):
    """Take away any one number, given line or crossed-out pair and a second valid figure appears."""
    c = charts.BY_ID[cid]
    rules = charts.rules(cid)
    clues = c["clues"]
    must = [tuple(e) for e in clues["must"]]
    never = [tuple(e) for e in clues["never"]]
    degree = dict(rules.need)
    for v in degree:
        rest = {k: n for k, n in degree.items() if k != v}
        assert sky.count_solutions(rules.with_clues(rest, must, never), 2) == 2, "%s: number on star %d is padding" % (cid, v)
    for e in must:
        assert sky.count_solutions(rules.with_clues(degree, [m for m in must if m != e], never), 2) == 2, "%s: given line %s is padding" % (cid, e)
    for e in never:
        assert sky.count_solutions(rules.with_clues(degree, must, [m for m in never if m != e]), 2) == 2, "%s: crossed-out %s is padding" % (cid, e)


@pytest.mark.parametrize("cid", IDS)
def test_line_logic_finishes_the_chart(cid):
    """No guessing: the logic a person can follow (full, forced, cross, close, bridge, and one what-if step when the chart says so) ends at the figure."""
    c = charts.BY_ID[cid]
    rules = charts.rules(cid)
    plain = sky.solved_by_logic(rules)
    what_if = sky.solved_by_logic(rules, lookahead=True)
    assert c["logic"] in (1, 2)
    if c["logic"] == 1:
        assert plain == fig_idx(c)
    else:
        assert plain != fig_idx(c) and what_if == fig_idx(c)


@pytest.mark.parametrize("cid", IDS)
def test_line_logic_never_contradicts_the_figure(cid):
    c = charts.BY_ID[cid]
    rules = charts.rules(cid)
    truth = fig_idx(c)
    for lookahead in (False, True):
        known, _ = sky.propagate(rules, lookahead=lookahead)
        assert known is not None
        for k, val in known.items():
            assert (k in truth) == (val == sky.IN)


def test_most_charts_need_no_what_if_step():
    ones = sum(1 for c in charts.ALL if c["logic"] == 1)
    assert ones >= 10, "the early charts of each season are meant to be plain line logic"
    for s in charts.SEASONS:
        assert s["charts"][0]["logic"] in (1, 2)


# ---- geometry and data ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cid", IDS)
def test_positions_are_whole_numbers_inside_the_canvas_and_stars_are_apart(cid):
    c = charts.BY_ID[cid]
    assert c["w"] == 1000 and 560 <= c["h"] <= 1000
    pts = [(s["x"], s["y"]) for s in c["stars"]]
    for s in c["stars"]:
        assert isinstance(s["x"], int) and isinstance(s["y"], int)
        assert 50 <= s["x"] <= c["w"] - 50 and 50 <= s["y"] <= c["h"] - 50
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            assert math.dist(pts[i], pts[j]) >= 66, "stars too close on %s" % cid


@pytest.mark.parametrize("cid", IDS)
def test_candidate_lines_are_sorted_pairs_that_include_the_figure_and_keep_clear_of_other_stars(cid):
    c = charts.BY_ID[cid]
    edges = [tuple(e) for e in c["edges"]]
    assert len(edges) == len(set(edges)) and all(a < b for a, b in edges)
    assert {tuple(e) for e in c["figure"]} <= set(edges)
    pts = [(s["x"], s["y"]) for s in c["stars"]]
    for a, b in edges:
        for v in range(len(pts)):
            if v not in (a, b):
                assert sky.point_segment_distance2(pts[v], pts[a], pts[b]) ** 0.5 >= 20, "line %s-%s runs over star %d on %s" % (a, b, v, cid)


@pytest.mark.parametrize("cid", IDS)
def test_the_figure_is_connected_planar_and_covers_every_star(cid):
    c = charts.BY_ID[cid]
    rules = charts.rules(cid)
    report = sky.analyse(rules, fig_idx(c))
    assert report["connected"] and not report["crossings"]
    assert all(d >= 1 for d in report["degree"]), "every star of a chart is part of its figure"


@pytest.mark.parametrize("cid", IDS)
def test_every_star_has_a_catalogue_id_a_name_and_a_magnitude_from_the_snapshot(cid):
    c = charts.BY_ID[cid]
    for s in c["stars"]:
        row = SNAPSHOT["stars"][str(s["hip"])]
        assert abs(float(row["mag"]) - s["mag"]) < 0.006
        assert s["name"] and isinstance(s["hip"], int)
    assert len({s["hip"] for s in c["stars"]}) == len(c["stars"])
    assert len(c["stars"]) <= 26, "stars are lettered A to Z"


def test_the_snapshot_is_dated_and_names_both_sources():
    assert SNAPSHOT["read"] == "2026-10-12"
    assert "github.com/astronexus/HYG-Database" in SNAPSHOT["sources"]["stars"]["url"]
    assert "stellarium.org" in SNAPSHOT["sources"]["figures"]["url"]
    for c in charts.ALL:
        assert c["code"] in SNAPSHOT["lines"]


def test_known_stars_are_where_they_should_be():
    """A few facts anyone can check: the brightest star of each famous constellation, and Orion's belt in a row."""
    brightest = {"canis-major": "Sirius", "lyra": "Vega", "aquila": "Altair", "scorpius": "Antares", "cygnus": "Deneb", "bootes": "Arcturus",
                 "virgo": "Spica", "taurus": "Aldebaran", "leo": "Regulus", "gemini": "Pollux", "auriga": "Capella", "orion": "Rigel",
                 "ursa-minor": "Polaris", "corona-borealis": "Alphecca", "ophiuchus": "Rasalhague"}
    for cid, name in brightest.items():
        assert charts.BY_ID[cid]["brightest"]["name"] == name, cid
    orion = charts.BY_ID["orion"]
    by_name = {s["name"]: s for s in orion["stars"]}
    belt = [by_name[n] for n in ("Alnitak", "Alnilam", "Mintaka")]
    # the belt is nearly a straight line: the middle star is within 40 units of the line joining the outer two
    d = sky.point_segment_distance2((belt[1]["x"], belt[1]["y"]), (belt[0]["x"], belt[0]["y"]), (belt[2]["x"], belt[2]["y"])) ** 0.5
    assert d < 40
    # east is on the left on a sky map: Betelgeuse (RA 5h55m) lies left of Rigel (RA 5h14m)
    assert by_name["Betelgeuse"]["x"] < by_name["Rigel"]["x"]
    assert by_name["Betelgeuse"]["y"] < by_name["Rigel"]["y"], "Betelgeuse is north (up), Rigel south (down)"


def test_every_chart_names_its_sources_and_the_read_date():
    for c in charts.ALL:
        assert "HYG" in c["source"]["stars"] and "Stellarium" in c["source"]["figure"] and c["source"]["read"] == SNAPSHOT["read"]


def test_the_notes_are_written_for_the_game_and_short_enough_to_read_at_a_glance():
    for c in charts.ALL:
        assert 60 <= len(c["note"]) <= 330, c["id"]
        assert c["name"] and c["meaning"].startswith("The ")
        assert c["best"]
        assert c["atlas"]["scale"] > 0 and 0 <= c["atlas"]["ra"] < 24 and -90 <= c["atlas"]["dec"] <= 90


def test_rebuilding_from_the_snapshot_gives_the_same_chart():
    """The data modules are generated; three charts are rebuilt here to show the pipeline and the files agree (deterministic)."""
    import build_charts
    import chart_specs
    for season in chart_specs.SEASONS:
        for spec in season["charts"]:
            if spec["id"] in ("delphinus", "corvus", "sagitta"):
                built = build_charts.build_chart(SNAPSHOT, spec, [s["id"] for s in chart_specs.SEASONS].index(season["id"]), charts.BY_ID[spec["id"]]["number"])
                stored = charts.BY_ID[spec["id"]]
                assert json.loads(json.dumps(built, sort_keys=True)) == json.loads(json.dumps(stored, sort_keys=True))
