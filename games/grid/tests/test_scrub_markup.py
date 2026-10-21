import json
from pathlib import Path

from .pagefiles import page_text


def test_scrub_markup_exists():
    html = page_text("index.html")
    assert 'id="scrub-panel"' in html
    assert 'id="scrub-slider"' in html
    assert 'id="scrub-readout"' in html


def test_scrub_in_pc_config():
    config_path = Path(__file__).resolve().parents[1] / "pc-config.json"
    with open(config_path) as f:
        config = json.load(f)
    side_zones = config.get("zones", {}).get("side", [])
    assert "#scrub-panel" in side_zones
