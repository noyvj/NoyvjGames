import json
from pathlib import Path

from .pagefiles import page_text


def test_page_contains_electrification_display():
    text = page_text()
    assert 'id="electrification-display"' in text


def test_pc_config_has_electrification_display_in_side():
    config_path = Path(__file__).resolve().parents[1] / "pc-config.json"
    with open(config_path) as f:
        config = json.load(f)
    assert "#electrification-display" in config["zones"]["side"]
