from grid_rules import INCIDENT_FILES, PLANT_TYPES, incident_ids


def test_incident_files_ids():
    expected = [
        "brownout_coal", "brownout_gas", "brownout_lingering",
        "damage_coal", "damage_gas",
    ] + [f"aging_{t}" for t in PLANT_TYPES]
    assert list(INCIDENT_FILES.keys()) == expected


def test_incident_files_non_empty():
    for id_, data in INCIDENT_FILES.items():
        assert data["title"]
        assert data["cause"]
        assert data["stops"]


def test_incident_files_aging_gas_title():
    assert INCIDENT_FILES["aging_gas"]["title"] == "Aging breakdown: Gas"


def test_incident_ids():
    assert incident_ids({"type": "brownout", "cause_plant": "gas"}, None) == ["brownout_gas"]
    assert incident_ids({"type": "brownout", "cause_plant": None}, None) == ["brownout_lingering"]
    assert incident_ids({"type": "damage", "damaged_plant": "coal"}, {"plant": "hydro"}) == ["damage_coal", "aging_hydro"]
    assert incident_ids(None, None) == []
    assert incident_ids(None, {"plant": "wind"}) == ["aging_wind"]


def test_incident_files_seen_brownout():
    from grid_state import GridState
    state = GridState()
    state.plant_counts["coal"] = 1
    state.emissions = 1000.0
    state.advance_round(rng=lambda: 0.0, age_rng=lambda: 1.0)
    assert state.incident_files_seen == {"brownout_coal": 1}

    # Second identical round should not overwrite the first occurrence
    state.advance_round(rng=lambda: 0.0, age_rng=lambda: 1.0)
    assert state.incident_files_seen == {"brownout_coal": 1}


def test_incident_files_seen_damage():
    from grid_state import GridState
    state = GridState()
    state.plant_counts["coal"] = 2
    state.emissions = 2000.0
    state.advance_round(rng=lambda: 0.0, age_rng=lambda: 1.0)
    assert "damage_coal" in state.incident_files_seen


def test_incident_files_seen_aging():
    from grid_state import GridState
    state = GridState()
    state.plant_counts["gas"] = 1
    state.plant_age["gas"] = 30.0
    state.emissions = 0.0
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 0.0)
    assert "aging_gas" in state.incident_files_seen
