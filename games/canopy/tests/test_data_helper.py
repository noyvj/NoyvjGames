

def test_read_data_json_from_disk(game_env):
    m = game_env.module
    result = m.read_data_json("NO_SUCH_GLOBAL", "forest_carbon.json")
    assert isinstance(result, dict)
    assert "fao_fra2020" in result


def test_read_wildlife_status_species_is_list(game_env):
    m = game_env.module
    result = m.read_data_json("X", "wildlife_status.json")
    assert isinstance(result["species"], list)


def test_read_missing_file_returns_none(game_env):
    m = game_env.module
    assert m.read_data_json("X", "missing.json") is None


def test_read_data_json_handles_value_error(monkeypatch, game_env):
    m = game_env.module

    def raise_value_error(*args, **kwargs):
        raise ValueError("test")

    monkeypatch.setattr(m.json, "loads", raise_value_error)
    assert m.read_data_json("X", "forest_carbon.json") is None
