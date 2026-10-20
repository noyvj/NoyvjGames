"""Edge-case tests for state.py save contract."""

import state


def test_clean_record_clamps_and_rejects_values():
    """Test clean_record handles out-of-bounds, booleans, and invalid types correctly."""
    # Empty or non-dict input returns fresh record
    assert state.clean_record(None) == state.new_record()
    assert state.clean_record("not a dict") == state.new_record()

    # Clamping best_error_nm to [0.0, 1000.0]
    rec = state.clean_record({"best_error_nm": -10.0})
    assert rec["best_error_nm"] == 0.0
    rec = state.clean_record({"best_error_nm": 2000.0})
    assert rec["best_error_nm"] == 1000.0

    # Clamping stars to [0, 3]
    rec = state.clean_record({"stars": -5})
    assert rec["stars"] == 0
    rec = state.clean_record({"stars": 10})
    assert rec["stars"] == 3

    # Clamping attempts to [0, 100000]
    rec = state.clean_record({"attempts": -1})
    assert rec["attempts"] == 0
    rec = state.clean_record({"attempts": 200000})
    assert rec["attempts"] == 100000

    # Boolean values for numeric fields are rejected (default used)
    rec = state.clean_record({"best_error_nm": True, "stars": False, "attempts": True})
    assert rec["best_error_nm"] is None
    assert rec["stars"] == 0
    assert rec["attempts"] == 0

    # discovered list limits and filtering
    hazard_ids = {"rock1", "rock2"}
    data = {"discovered": ["rock1", "rock2", "unknown_rock", "rock1"]}
    rec = state.clean_record(data, hazard_ids=hazard_ids)
    assert len(rec["discovered"]) == 2
    assert "unknown_rock" not in rec["discovered"]

    # Truncating discovered to 50 items
    data = {"discovered": [f"h{i}" for i in range(60)]}
    rec = state.clean_record(data)
    assert len(rec["discovered"]) == 50


def test_clean_meta_drops_unknown_charts_and_filters_flags():
    """Test clean_meta handles unknown charts, flag filtering, and best bounds."""
    known_charts = {"chart1": {"h1"}, "chart2": set()}

    # Unknown chart dropped
    data = {"charts": {"unknown_chart": {"stars": 3}, "chart1": {"stars": 2}}}
    meta = state.clean_meta(data, known_charts)
    assert "unknown_chart" not in meta["charts"]
    assert "chart1" in meta["charts"]

    # Flags filtered to FLAGS list
    data = {"flags": ["landfall", "fake_flag", "aground"]}
    meta = state.clean_meta(data, known_charts)
    assert set(meta["flags"]) == {"landfall", "aground"}

    # Best bounds clamping
    data = {"best": {"smallest_final_error_nm": -10.0, "longest_route_nm": 200000.0}}
    meta = state.clean_meta(data, known_charts)
    assert meta["best"]["smallest_final_error_nm"] == 0.0
    assert meta["best"]["longest_route_nm"] == 100000.0

    # practice_seeds_played clamping
    data = {"practice_seeds_played": -5}
    meta = state.clean_meta(data, known_charts)
    assert meta["practice_seeds_played"] == 0


def test_merge_record_commutes_and_merges_correctly():
    """Test merge_record is commutative and correctly merges fields."""
    a = {"best_error_nm": 5.0, "stars": 2, "attempts": 10, "discovered": ["h1", "h2"], "par_seen": False, "trusted": True}
    b = {"best_error_nm": 3.0, "stars": 1, "attempts": 20, "discovered": ["h2", "h3"], "par_seen": True, "trusted": False}

    merged_ab = state.merge_record(a, b)
    merged_ba = state.merge_record(b, a)

    assert merged_ab == merged_ba
    assert merged_ab["best_error_nm"] == 3.0
    assert merged_ab["stars"] == 2
    assert merged_ab["attempts"] == 20
    assert merged_ab["discovered"] == ["h1", "h2", "h3"]
    assert merged_ab["par_seen"] is True
    assert merged_ab["trusted"] is True


def test_clean_fixes_bounds_and_landmark_filtering():
    """Test clean_fixes handles out-of-bounds coordinates, invalid after_leg, and landmark filtering."""
    sailed = 2
    landmark_ids = {"cape", "lighthouse"}

    # Invalid after_leg (out of range or boolean)
    data = [{"after_leg": -1, "x": 10.0, "y": 10.0, "landmark": "cape"},
            {"after_leg": 2, "x": 10.0, "y": 10.0, "landmark": "cape"},
            {"after_leg": True, "x": 10.0, "y": 10.0, "landmark": "cape"}]
    fixes = state.clean_fixes(data, sailed, landmark_ids)
    assert len(fixes) == 0

    # Coordinate bounds clamping (default size=40 -> [-5.0, 45.0])
    data = [{"after_leg": 0, "x": -10.0, "y": 50.0, "landmark": "cape"}]
    fixes = state.clean_fixes(data, sailed, landmark_ids)
    assert len(fixes) == 1
    assert fixes[0]["x"] == -5.0
    assert fixes[0]["y"] == 45.0

    # Landmark filtering
    data = [{"after_leg": 0, "x": 10.0, "y": 10.0, "landmark": "unknown_landmark"}]
    fixes = state.clean_fixes(data, sailed, landmark_ids)
    assert len(fixes) == 0

    # Custom size parameter
    data = [{"after_leg": 0, "x": -5.0, "y": 45.0, "landmark": "cape"}]
    fixes = state.clean_fixes(data, sailed, landmark_ids, size=20)
    assert len(fixes) == 1
    assert fixes[0]["x"] == -5.0
    assert fixes[0]["y"] == 25.0  # size + 5.0 = 25.0

    # Returns sorted by after_leg key
    data = [{"after_leg": 1, "x": 10.0, "y": 10.0, "landmark": "cape"},
            {"after_leg": 0, "x": 10.0, "y": 10.0, "landmark": "cape"}]
    fixes = state.clean_fixes(data, sailed, landmark_ids)
    assert fixes[0]["after_leg"] == 0
    assert fixes[1]["after_leg"] == 1
