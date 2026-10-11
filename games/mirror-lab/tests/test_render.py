"""The bench and map SVG strings: every state is drawn by shape and letter as well as colour."""

import re
import xml.dom.minidom

import benches
import logbook
import optics
import progress
import render


def svg_for(bench_id, layout=None):
    b = benches.BY_ID[bench_id]
    layout = b.solution_layout() if layout is None else layout
    tr = optics.trace(b.board, layout)
    return render.bench_svg(b.board, layout, tr, "label"), b, tr


def test_every_bench_svg_is_well_formed_xml_with_one_hit_target_per_cell():
    for b in benches.ALL_BENCHES:
        for layout in ({}, b.solution_layout()):
            tr = optics.trace(b.board, layout)
            svg = render.bench_svg(b.board, layout, tr, "x")
            xml.dom.minidom.parseString(svg)
            assert svg.count('class="ml-hit"') == b.board.w * b.board.h
            assert svg.count('class="ml-slot"') == len(b.board.slots)
            assert svg.count('class="ml-wall"') == len(b.board.walls)
            assert svg.count("ml-piece ") == len(layout)
            assert svg.count('class="ml-emitter"') == 1


def test_beam_kinds_have_their_own_dash_style_and_letter_in_the_markup():
    svg, b, tr = svg_for("c3-3")
    assert "ml-beam-W" in svg and "ml-beam-S" in svg and "ml-beam-L" in svg
    assert re.search(r'class="ml-letter ml-letter-S"[^>]*>S<', svg) and re.search(r'class="ml-letter ml-letter-L"[^>]*>L<', svg)
    css = open(render.__file__.replace("render.py", "style.css")).read()
    assert re.search(r"\.ml-beam-S \{[^}]*stroke-dasharray: 6 5", css) and re.search(r"\.ml-beam-L \{[^}]*stroke-dasharray: 17 7", css)
    assert "stroke-dasharray" not in re.search(r"\.ml-beam-W \{[^}]*\}", css).group(0)
    svg_white, _b, _t = svg_for("c1-1")
    assert "ml-letter" not in svg_white                                       # a white beam needs no letter


def test_a_lit_sensor_is_filled_and_ticked_and_an_unlit_one_is_hollow_with_no_tick():
    svg, b, tr = svg_for("c1-1")
    assert 'class="ml-sensor lit"' in svg and "s-tick" in svg
    dark, _b, _t = svg_for("c1-1", {})
    assert 'class="ml-sensor"' in dark and "s-tick" not in dark and 'class="ml-sensor lit"' not in dark


def test_s_and_l_sensors_carry_their_letter():
    svg, b, tr = svg_for("c3-1")
    assert svg.count('class="s-letter"') == 2 and ">S</text>" in svg and ">L</text>" in svg


def test_each_piece_has_its_own_shape_and_a_flipped_piece_is_a_mirror_image():
    shapes = {p: render.glyph(p) for p in optics.PIECES}
    assert len(set(shapes.values())) == len(optics.PIECES)
    assert render.glyph("mirror", 1) != render.glyph("mirror", 0) and "scale(-1 1)" in render.glyph("mirror", 1)
    assert render.glyph("prism", 1) != render.glyph("prism", 0)
    assert "&#189;" in render.glyph("splitter") and ">P<" in render.glyph("prism")
    assert render.glyph("filter_s") != render.glyph("filter_l") and ">S<" in render.glyph("filter_s") and ">L<" in render.glyph("filter_l")


def test_decoys_show_a_cross_and_an_exclamation_when_hit():
    b = optics.Board([">AX"])
    tr = optics.trace(b, {})
    svg = render.bench_svg(b, {}, tr, "x")
    assert "ml-sensor decoy hit" in svg and "s-cross" in svg and ">!<" in svg
    blocked = optics.Board([">#X"])
    dark = render.bench_svg(blocked, {}, optics.trace(blocked, {}), "x")
    assert 'class="ml-sensor decoy"' in dark and "decoy hit" not in dark and ">!<" not in dark


def test_the_relay_map_marks_cleared_fewest_current_and_locked_by_shape_and_word():
    fresh_cleared = {}
    chapters = []
    for ch in benches.CHAPTERS:
        items = []
        for b in ch["benches"]:
            layout = fresh_cleared.get(b.id)
            items.append({"id": b.id, "name": b.name, "number": b.number, "cleared": layout is not None, "fewest": False, "current": b.id == "c1-1"})
        chapters.append({"number": ch["number"], "name": ch["name"], "open": ch["number"] == 1, "cleared": 0, "benches": items})
    chapters[0]["benches"][1].update(cleared=True, fewest=True)
    svg = render.map_svg(chapters)
    xml.dom.minidom.parseString(svg)
    assert svg.count("map-node ") == 40 and "Locked" in svg and "node-tick" in svg and "node-ring" in svg and "node-num" in svg
    assert svg.count('aria-disabled="true"') == 32


def test_the_shelf_fills_on_first_use_and_the_cards_fill_on_clear():
    shelf = logbook.shelf(set())
    assert [p["id"] for p in shelf] == ["mirror", "splitter", "prism", "filter", "absorber"] and not any(p["filled"] for p in shelf)
    shelf = logbook.shelf({"mirror", "prism"})
    assert [p["filled"] for p in shelf] == [True, False, True, False, False]
    assert shelf[1]["text"].startswith("An empty page") and "quarter turn" in shelf[0]["text"]
    cleared = {"c1-1": benches.BY_ID["c1-1"].solution_layout()}
    cards = logbook.cards(cleared)
    assert len(cards) == 40 and cards[0]["filled"] and cards[0]["fewest"] and cards[0]["pieces"] == 1 and "1 mirror" in cards[0]["used"]
    assert not cards[1]["filled"] and not cards[1]["locked"] and cards[8]["locked"] and cards[16]["locked"]
    assert logbook.families_used(["filter_s", "filter_l", "absorber", "lens"]) == {"filter", "absorber"}
    assert logbook.summary({"mirror"}, cleared) == {"pages": 1, "pages_total": 5, "cards": 1, "cards_total": 40}


def test_totals_and_tags():
    cleared = {"c1-1": benches.BY_ID["c1-1"].solution_layout(), "c1-2": {(0, 3): ("mirror", 1), (4, 3): ("mirror", 1), (1, 1): ("mirror", 0)}}
    assert progress.fewest_tags(cleared) == 1 and progress.sensors_lit(cleared) == 2 and progress.totals(cleared)["cleared"] == 2
