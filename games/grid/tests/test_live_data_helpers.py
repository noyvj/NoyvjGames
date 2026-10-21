import sys


# read_data_json / read_data_text (grid_realgrid) hand the page's data files to Python: the boot script sets a
# window global, the pytest fake page has none, so the file in games/grid/data/ is read instead.

def test_read_data_json_reads_the_data_folder_when_there_is_no_window_global(game_env):
    result = game_env.module.read_data_json("NO_SUCH_GLOBAL", "capacity_factors.json")
    assert isinstance(result, dict)
    assert "tables" in result


def test_read_data_json_gives_none_for_a_missing_file(game_env):
    assert game_env.module.read_data_json("X", "missing.json") is None


def test_read_data_json_gives_none_for_text_that_is_not_json(game_env, monkeypatch):
    monkeypatch.setattr(sys.modules["grid_realgrid"], "read_data_text", lambda *args: "not json")
    assert game_env.module.read_data_json("X", "any.json") is None


def test_read_data_text_prefers_the_window_global(game_env):
    sys.modules["js"].DEMO_GLOBAL = '{"a": 1}'
    assert game_env.module.read_data_json("DEMO_GLOBAL", "missing.json") == {"a": 1}
