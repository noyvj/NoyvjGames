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
