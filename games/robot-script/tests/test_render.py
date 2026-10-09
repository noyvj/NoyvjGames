import re

import render
import rooms


def test_every_room_draws_with_its_ids_and_no_inline_colours():
    for r in rooms.ALL_ROOMS:
        svg = render.room_svg(r.layout, r.name)
        assert svg.startswith("<svg") and svg.endswith("</svg>")
        assert 'id="rs-robot"' in svg and 'id="rs-carry"' in svg
        for i in range(len(r.layout.parts)):
            assert 'id="rs-part-%d"' % i in svg
        for i in range(len(r.layout.sockets)):
            assert 'id="rs-fill-%d"' % i in svg
        for sid in r.layout.switch_ids:
            assert 'id="rs-lamp-%d"' % sid in svg
        assert svg.count('class="rs-door"') == len(r.layout.door_at)
        assert not re.search(r'(fill|stroke)="#', svg)


def test_robot_starts_on_its_tile_facing_its_way():
    layout = rooms.BY_ID["stop-short"].layout
    svg = render.room_svg(layout)
    assert "translate(72px,24px) rotate(180deg)" in svg


def test_room_in_words_names_everything():
    lines, rows = render.describe(rooms.BY_ID["the-shaft"].layout)
    text = " ".join(lines)
    assert "Door A" in text and "Switch 2" in text and "socket" in text and "exit pad" in text
    assert len(rows) == 10 and rows[0].startswith("Row 1:")


def test_each_kind_of_tile_has_its_own_shape_not_just_a_colour():
    svg = render.room_svg(rooms.BY_ID["the-shaft"].layout)
    for cls in ("rs-part-body", "rs-socket-frame", "rs-switch-plate", "rs-door-bar", "rs-wall-x", "rs-exit-ring"):
        assert cls in svg
