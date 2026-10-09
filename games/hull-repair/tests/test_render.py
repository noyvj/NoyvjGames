import boards
import render
import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_every_line_gets_its_own_shape_letter_and_a_solid_source_and_ringed_sink():
    b = boards.ALL_BOARDS[3]
    svg = render.board_svg(b)
    for c in b.lines:
        assert svg.count('hr-port hr-src hr-c-%s' % c) == 1 and svg.count('hr-port hr-dst hr-c-%s' % c) == 1
        assert ">%s<" % c in svg
    assert len(set(rules.LINE_SHAPES.values())) == len(rules.LINE_SHAPES) == 8


def test_all_eight_shapes_draw_something():
    rows = ["ABCDEFGH."] + ["........."] * 3 + ["abcdefgh."]
    b = mk([r + "" for r in rows])
    svg = render.board_svg(b)
    assert "<circle" in svg and "<rect" in svg and svg.count("<polygon") > 30


def test_holes_bridges_valves_and_mixers_have_their_own_markup():
    b = mk(["C.#=c", "A.1.B", ".>...", ".....", "....."], {"1": "AB"})
    svg = render.board_svg(b)
    for cls in ("hr-hole-body", "hr-crack", "hr-bridge-plate", "hr-bridge-over", "hr-valve-arrow", "hr-mixer-body", "hr-mix-m"):
        assert cls in svg, cls
    assert ">M<" in svg and "Mixer:" in svg


def test_the_lines_layer_shows_dots_ghosts_pipes_and_heads():
    b = boards.ALL_BOARDS[0]
    assert render.lines_svg(b, {}).count("hr-dot") == len(b.need)
    assert "hr-dot" not in render.lines_svg(b, {}, dots=False)
    part = {b.lines[0]: b.solution[b.lines[0]][:3]}
    svg = render.lines_svg(b, part, ghosts={"B": b.solution["B"]})
    assert "hr-head" in svg and "hr-ghost" in svg and "hr-joined" not in svg
    assert "hr-joined" in render.lines_svg(b, b.solution) and "hr-head" not in render.lines_svg(b, b.solution)
    assert render.lines_svg(b, b.solution).count("hr-dot") == 0


def test_a_line_over_a_bridge_is_drawn_again_on_top():
    b = mk(["..B..", "A.=.a", "..b..", ".....", "....."])
    svg = render.lines_svg(b, {"A": [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)], "B": [(2, 0), (2, 1), (2, 2)]})
    assert svg.count("hr-over-pipe") == 1


def test_the_board_in_words_names_everything():
    b = mk(["C.#=c", "A.1.B", ".>...", ".....", "....."], {"1": "AB"})
    words = " ".join(render.describe(b))
    for needle in ("Power line", "Air line", "Hole (no hull)", "Bridge at", "Valve at", "right only", "Mixer at"):
        assert needle in words, needle


def test_cell_words_say_what_is_there():
    b = boards.ALL_BOARDS[0]
    assert "Power source port" in render.cell_words(b, {}, b.src["A"])
    assert "empty" in render.cell_words(b, {}, (0, 0))
    assert "Coolant line" in render.cell_words(b, b.solution, (0, 0))
    hole = mk(["A.#.a", ".....", ".....", ".....", "....."])
    assert "hole" in render.cell_words(hole, {}, (2, 0))


def test_every_board_renders_without_markup_slips():
    for b in boards.ALL_BOARDS:
        svg = render.board_svg(b)
        assert svg.count("<svg") == 1 and svg.endswith("</svg>") and 'id="hr-lines"' in svg and 'id="hr-cursor"' in svg
        assert svg.count("<g") == svg.count("</g>")
