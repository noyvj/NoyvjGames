def test_read_data_json_from_disk():
    from grid_realgrid import read_data_json

    result = read_data_json("NO_SUCH_GLOBAL", "capacity_factors.json")
    assert isinstance(result, dict)
    assert "tables" in result


def test_read_data_json_missing_file():
    from grid_realgrid import read_data_json

    result = read_data_json("X", "missing.json")
    assert result is None


def test_read_data_json_invalid_json():
    import grid_realgrid

    original_text = grid_realgrid.read_data_text
    grid_realgrid.read_data_text = lambda *args, **kwargs: "not json"
    try:
        from grid_realgrid import read_data_json
        result = read_data_json("X", "any.json")
        assert result is None
    finally:
        grid_realgrid.read_data_text = original_text
