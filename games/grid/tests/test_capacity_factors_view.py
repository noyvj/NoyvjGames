import json
from pathlib import Path

import pytest

from grid_rules import GENERATION_TYPES, PLANT_CAPACITY, PLANT_LABEL


@pytest.fixture(scope="module")
def capacity_data():
    """Load the actual capacity_factors.json from the game's data directory."""
    here = Path(__file__).resolve().parents[1] / "data" / "capacity_factors.json"
    with open(here, encoding="utf-8") as f:
        return json.load(f)


def test_capacity_factor_rows_structure_and_values(capacity_data, game_env):
    rows = game_env.module.capacity_factor_rows(capacity_data)
    assert len(rows) == 6

    for i, plant_type in enumerate(GENERATION_TYPES):
        row = rows[i]
        assert row["plant_type"] == plant_type
        assert row["label"] == PLANT_LABEL[plant_type]
        assert row["nameplate"] == PLANT_CAPACITY[plant_type]
        assert isinstance(row["year"], int)

        # average == round(nameplate * pct / 100, 1)
        expected_avg = round(row["nameplate"] * row["pct"] / 100, 1)
        assert row["average"] == expected_avg

        # 0 < pct <= 100
        assert 0 < row["pct"] <= 100

    # solar pct below nuclear pct
    solar_pct = next(r["pct"] for r in rows if r["plant_type"] == "solar")
    nuclear_pct = next(r["pct"] for r in rows if r["plant_type"] == "nuclear")
    assert solar_pct < nuclear_pct


def test_capacity_factor_note_content(capacity_data, game_env):
    note = game_env.module.capacity_factor_note(capacity_data)
    assert "Electric Power Monthly" in note
    assert f"data for {capacity_data['tables'][1]['data_for']}" in note
    assert f"read on {capacity_data['read']}" in note


def test_load_capacity_factors_falls_back_to_the_local_file(game_env, capacity_data):
    """With no CAPACITY_FACTORS_JSON window global the loader reads data/capacity_factors.json."""
    assert game_env.module.load_capacity_factors() == capacity_data
