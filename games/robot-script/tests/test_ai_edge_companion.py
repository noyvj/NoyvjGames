import companion
import rooms


def test_part_for_known_room():
    """part_for returns the correct zone and name for a room in PARTS."""
    assert companion.part_for("wake-up") == ("treads", "Left drive roller")


def test_part_for_new_room():
    """part_for returns the correct zone and name for rooms added in AN-4."""
    assert companion.part_for("face-the-pad") == ("treads", "Idler wheel")
    assert companion.part_for("left-at-the-corner") == ("treads", "Drive sprocket")


def test_line_for_valid_medals():
    """line_for returns a line for medals 1, 2, and 3."""
    rid = "wake-up"
    for medal in (1, 2, 3):
        line = companion.line_for(rid, medal)
        assert isinstance(line, str) and len(line) > 0


def test_line_for_invalid_medal_fallback():
    """line_for falls back to medal 1 when given an invalid or out-of-range medal type."""
    rid = "wake-up"
    line_default = companion.line_for(rid, 1)
    assert companion.line_for(rid, 99) == line_default
    assert companion.line_for(rid, 0) == line_default
    assert companion.line_for(rid, -5) == line_default


def test_parts_view_empty_best():
    """parts_view returns all parts with found=False and empty finish when best is empty."""
    parts = companion.parts_view({})
    expected_count = len(companion.PARTS) + len(companion.NEW_PARTS)
    assert len(parts) == expected_count
    assert all(not p["found"] for p in parts)
    assert all(p["finish"] == "" for p in parts)


def test_parts_view_partial_best():
    """parts_view correctly marks found parts and finish when best contains some rooms."""
    best = {"wake-up": {"n": 3, "t": "main: F F F"}}
    parts = companion.parts_view(best)
    wake_up_part = next(p for p in parts if p["room"] == "wake-up")
    assert wake_up_part["found"] is True
    assert wake_up_part["finish"] in companion.FINISH.values()


def test_zones_view_empty_parts():
    """zones_view handles an empty parts list without error."""
    zones = companion.zones_view([])
    assert len(zones) == len(companion.ZONES)
    assert all(z["have"] == 0 and z["finish"] == "" for z in zones)


def test_zones_view_populated_parts():
    """zones_view aggregates parts correctly by zone."""
    parts = [
        {"zone": "treads", "found": True, "finish": "polished"},
        {"zone": "treads", "found": False, "finish": ""},
        {"zone": "chassis", "found": True, "finish": "clean"},
    ]
    zones = companion.zones_view(parts)
    treads_zone = next(z for z in zones if z["id"] == "treads")
    assert treads_zone["have"] == 1 and treads_zone["need"] == 2
    assert treads_zone["finish"] == "polished"
    chassis_zone = next(z for z in zones if z["id"] == "chassis")
    assert chassis_zone["have"] == 1 and chassis_zone["finish"] == "clean"


def test_svg_empty_best():
    """svg returns a valid SVG string when best is empty."""
    svg_str = companion.svg({})
    assert svg_str.startswith("<svg") and svg_str.endswith("</svg>")
    assert 'class="scrap"' in svg_str


def test_label_empty_zones():
    """label returns the correct count string for an empty zones list."""
    assert companion.label([]) == "Scrap, the salvage drone, with 0 of 0 parts back on."


def test_label_populated_zones():
    """label returns the correct count string for a populated zones list."""
    zones = [{"id": "treads", "have": 6, "need": 6}, {"id": "chassis", "have": 0, "need": 6}]
    assert companion.label(zones) == "Scrap, the salvage drone, with 6 of 12 parts back on."


def test_view_empty_best():
    """view returns correct structure and counts when best is empty."""
    v = companion.view({})
    assert v["found"] == 0
    assert v["total"] == len(companion.PARTS) + len(companion.NEW_PARTS)
    assert v["polished"] == 0
    assert "svg" in v and "parts" in v and "zones" in v


def test_view_all_polished():
    """view correctly counts polished parts when all rooms are cleared with gold."""
    best = {rid: {"n": 1, "t": "main: F"} for rid in rooms.ORDER}
    v = companion.view(best)
    assert v["found"] == len(rooms.ORDER)
    assert v["polished"] == len(rooms.ORDER)
