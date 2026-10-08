import re
from pathlib import Path
from xml.dom import minidom

from render import chart_notes, plan_marks, render_chart, tide_table, visible_hazards
from sim import clean_legs, estimate, sail
from tests import golden_charts
from tests.golden_charts import GOLDEN_A, GOLDEN_B

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def test_the_two_golden_charts_render_exactly_as_pinned():
    built = golden_charts.build()
    for name, svg in built.items():
        assert svg + "\n" == (GOLDEN_DIR / (name + ".svg")).read_text(encoding="utf-8"), name


def test_the_markup_is_well_formed_xml():
    for svg in golden_charts.build().values():
        minidom.parseString(svg)


def test_the_chart_has_an_accessible_name_and_a_text_description():
    svg = golden_charts.build()["golden_a"]
    assert 'role="img"' in svg and "aria-labelledby=" in svg
    assert "<title" in svg and "Chart of Golden Water" in svg and "<desc" in svg and "Little Rock" in svg


def test_every_chart_always_shows_a_scale_bar_and_a_compass_rose_and_the_flag():
    for svg in golden_charts.build().values():
        assert "dr-scale" in svg and "dr-rose" in svg and "dr-flag" in svg and "dr-arrival-ring" in svg


def test_hazards_differ_by_shape_hatch_and_label_not_colour():
    svg = golden_charts.build()["golden_b"]
    assert 'fill="url(#dr-pat-reef)"' in svg and 'fill="url(#dr-pat-shoal)"' in svg and 'fill="url(#dr-pat-land)"' in svg
    assert "dr-hazard-cross" in golden_charts.build()["golden_a"]           # rocks carry a cross
    assert ">Reef<" in svg and ">Shoal<" in svg and ">Isle<" in svg
    assert 'style=' not in svg and 'stroke="#' not in svg and 'fill="#' not in svg   # colour only via CSS classes


def test_a_current_is_an_outlined_zone_with_an_arrow_and_a_number_range():
    svg = golden_charts.build()["golden_b"]
    assert "dr-current-zone" in svg and "dr-current-arrow" in svg and ">1 to 2 kn<" in svg


def test_wind_is_drawn_only_when_the_chart_has_wind():
    built = golden_charts.build()
    assert "dr-wind-arrow" in built["golden_b"] and "Wind from 270, 10 to 15 kn" in built["golden_b"]
    assert "dr-wind-arrow" not in built["golden_a"]


def test_the_estimated_track_is_a_polyline_with_numbered_leg_markers():
    svg = golden_charts.build()["golden_a"]
    assert svg.count('class="dr-leg-mark"') == 2 and ">1<" in svg and ">2<" in svg
    assert svg.count("dr-est-track") == 1 and "dr-true-track" not in svg


def test_plan_marks_find_each_leg_end():
    legs = clean_legs(GOLDEN_A, golden_charts.GOLDEN_A_LEGS)
    est = estimate(GOLDEN_A, legs)
    marks = plan_marks(legs, est)
    assert len(marks) == 2 and marks[-1] == [est[-1][1], est[-1][2]]


def test_unmarked_hazards_are_not_on_the_chart_until_found_or_revealed():
    assert [h["id"] for h in visible_hazards(GOLDEN_B)] == ["reef", "shoal"]
    assert [h["id"] for h in visible_hazards(GOLDEN_B, discovered=["hidden"])] == ["reef", "shoal", "hidden"]
    assert len(visible_hazards(GOLDEN_B, reveal=True)) == 3
    plain = render_chart(GOLDEN_B)
    assert "Hidden" not in plain and "Hidden" not in "".join(chart_notes(GOLDEN_B))
    found = render_chart(GOLDEN_B, discovered=["hidden"])
    assert "Hidden (found)" in found and "dr-hazard-unmarked" in found
    assert "Hidden (unmarked)" in render_chart(GOLDEN_B, reveal=True)


def test_the_true_track_appears_only_when_the_caller_hands_it_over():
    legs = clean_legs(GOLDEN_A, golden_charts.GOLDEN_A_LEGS)
    est = estimate(GOLDEN_A, legs)
    res = sail(GOLDEN_A, legs)
    before = render_chart(GOLDEN_A, est=est, marks=plan_marks(legs, est))
    after = render_chart(GOLDEN_A, est=est, marks=plan_marks(legs, est), true_track=res["track"], reveal=True)
    assert "dr-true-track" not in before and "dr-ribbon" not in before and "dr-ship" not in before
    assert 'id="dr-true-track"' in after and 'class="dr-ribbon"' in after and 'id="dr-ship"' in after
    ts = [float(t) for t in re.findall(r'class="dr-ribbon" data-t="([\d.]+)"', after)]
    assert ts == [float(h) for h in range(1, int(res["hours"]) + 1)] and ts   # one ribbon per whole hour sailed


def test_the_ruler_point_and_believed_position_and_fixes_are_drawn_on_request():
    svg = render_chart(GOLDEN_A, point=(3, 4), believed=(2, 2), fixes=[(2.5, 2.5)])
    assert "dr-point-cross" in svg and "dr-believed-shape" in svg and 'class="dr-fix"' in svg
    assert "dr-point" not in render_chart(GOLDEN_A)


def test_notes_say_everything_the_picture_says():
    notes = " ".join(chart_notes(GOLDEN_B))
    for needle in ("Start at 1 east, 5 north", "arrive within 1 nm", "Isle", "Reef: a reef", "Shoal", "1 to 2 kn", "Wind from 270",
                   "The Light: a lighthouse"):
        assert needle in notes, needle


def test_tide_table_lists_peaks_and_slack_in_words():
    zone = {"id": "t", "rect": [0, 0, 5, 5], "set": 90, "drift_range": [1.0, 2.0], "tide": {"period": 12.0, "phase": 3.0}}
    table = tide_table(zone)
    assert table[0].startswith("Hour 0: the stream is slack") or table[0].startswith("Hour 0")
    assert any("Hour 3: the stream peaks toward 090" in line for line in table)
    assert any("Hour 9: the stream peaks toward 270" in line for line in table)
    assert any("slack" in line for line in table)


def test_notes_mention_fog_and_compass_error_when_present():
    chart = dict(GOLDEN_A, fog=True, compass={"range": [3, 5], "true": 4}, landmarks=[{"id": "l", "name": "L", "kind": "buoy", "x": 1, "y": 1, "visible": 5}])
    notes = " ".join(chart_notes(chart))
    assert "Fog" in notes and "Compass error: 3 to 5 degrees east" in notes and "not in fog" in notes
