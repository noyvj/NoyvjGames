import json
import os


def test_readings_sheet_in_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "pc-config.json")
    with open(config_path) as f:
        config = json.load(f)
    side_zones = config.get("zones", {}).get("side", [])
    assert "#readings-sheet" in side_zones, "Readings sheet must be in the side zone"


def test_readings_sheet_in_pc_js():
    js_path = os.path.join(os.path.dirname(__file__), "..", "pc.js")
    with open(js_path) as f:
        content = f.read()
    assert '"readings-sheet"' in content, "pc.js must create the readings sheet"
    assert "data-sort" in content, "pc.js must support sorting"
    assert "highlightTile" in content or "highlighted-ping" in content, "pc.js must highlight tiles on click"


def test_readings_sheet_in_pc_css():
    css_path = os.path.join(os.path.dirname(__file__), "..", "pc.css")
    with open(css_path) as f:
        content = f.read()
    assert "#readings-sheet" in content, "pc.css must style the readings sheet"
    assert ".highlighted-ping" in content, "pc.css must style the highlight class"
