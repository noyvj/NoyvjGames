import json
from pathlib import Path

import pytest

from grid_realgrid import capacity_factor_rows, capacity_factor_note, load_capacity_factors
from grid_rules import GENERATION_TYPES


@pytest.fixture(scope="module")
def capacity_data():
    """Load the actual capacity_factors.json from the game's data directory."""
    here = Path(__file__).resolve().parents[1] / "data" / "capacity_factors.json"
    with open(here, encoding="utf-8") as f:
        return json.load(f)


def test_capacity_factor_rows_structure_and_values(capacity_data):
    rows = capacity_factor_rows(capacity_data)
    assert len(rows) == 6

    for i, plant_type in enumerate(GENERATION_TYPES):
        row = rows[i]
        assert row["plant_type"] == plant_type
        assert row["label"] is not None
        assert row["nameplate"] is not None
        assert row["pct"] is not None
        assert row["year"] is not None

        # average == round(nameplate * pct / 100, 1)
        expected_avg = round(row["nameplate"] * row["pct"] / 100, 1)
        assert row["average"] == expected_avg

        # 0 < pct <= 100
        assert 0 < row["pct"] <= 100

    # solar pct below nuclear pct
    solar_pct = next(r["pct"] for r in rows if r["plant_type"] == "solar")
    nuclear_pct = next(r["pct"] for r in rows if r["plant_type"] == "nuclear")
    assert solar_pct < nuclear_pct


def test_capacity_factor_note_content(capacity_data):
    note = capacity_factor_note(capacity_data)
    assert "Electric Power Monthly" in note
    assert f"data for {capacity_data['tables'][1]['data_for']}" in note
    assert f"read on {capacity_data['read']}" in note


def test_load_capacity_factors_fallback():
    """Ensure load_capacity_factors falls back to the local file when js is unavailable."""
    data = load_capacity_factors()
    assert data is not None
    assert "tables" in data
    assert "read" in data


def test_capacity_factor_markup_in_index_and_pc_config():
    from .pagefiles import page_text

    html = page_text("index.html")
    assert "capacity-factor-panel" in html
    assert "capacity-factor-table" in html
    assert "capacity-factor-source" in html

    pc_config_path = Path(__file__).resolve().parents[1] / "pc-config.json"
    with open(pc_config_path, encoding="utf-8") as f:
        config = json.load(f)

    compare_panel = next(c for c in config["composites"] if c["id"] == "pc-compare-panel")
    assert "#capacity-factor-panel" in compare_panel["members"]
