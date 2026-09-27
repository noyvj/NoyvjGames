"""GB-14: name your forest and give the adopted plot a nickname; the log narrates both."""

from .gb_helpers import FakeChangeEvent, decline_requests


def _name_forest(env, text):
    env.elements["forest-name-input"].dispatch("change", FakeChangeEvent(text))


def _nickname(env, text):
    env.elements["plot-nickname-input"].dispatch("change", FakeChangeEvent(text))


def _adopt(env, index):
    env.select(index)
    env.elements["adopt-plot-button"].dispatch("click", None)


def test_naming_the_forest_sets_logs_and_shows_it(game_env):
    m = game_env.module
    _name_forest(game_env, "Wren Hollow")
    assert m.forest_name == "Wren Hollow"
    assert any("Wren Hollow" in e["text"] and e["kind"] == "name" for e in m.forest_log)
    assert "Wren Hollow" in game_env.elements["forest-title-display"].innerText
    assert game_env.elements["forest-title-display"].hidden is False


def test_names_are_cleaned_and_capped(game_env):
    m = game_env.module
    _name_forest(game_env, "  A\tvery\n   long   forest name that keeps going and going  ")
    assert "\t" not in m.forest_name and "\n" not in m.forest_name and "  " not in m.forest_name
    assert len(m.forest_name) <= m.FOREST_NAME_MAX
    _name_forest(game_env, "x" * 200)
    assert len(m.forest_name) == m.FOREST_NAME_MAX
    _name_forest(game_env, "")
    assert m.forest_name == ""
    assert game_env.elements["forest-title-display"].hidden is True


def test_non_text_values_are_ignored(game_env):
    m = game_env.module
    assert m.set_forest_name(None) is False
    assert m.set_forest_name(42) is False
    assert m.forest_name == ""


def test_nickname_needs_an_adopted_plot(game_env):
    m = game_env.module
    assert game_env.elements["plot-nickname-input"].disabled is True
    _nickname(game_env, "Old Bramble")
    assert m.adopted_plot_nickname == ""
    _adopt(game_env, 7)
    assert game_env.elements["plot-nickname-input"].disabled is False
    _nickname(game_env, "Old Bramble")
    assert m.adopted_plot_nickname == "Old Bramble"


def test_nickname_shows_in_tooltip_and_adopted_panel(game_env):
    m = game_env.module
    _adopt(game_env, 7)
    _nickname(game_env, "Old Bramble")
    assert "Old Bramble" in game_env.elements["adopted-plot-panel"].innerText
    assert "as Old Bramble" in m._plot_tooltip_text(m.plots[7])


def test_releasing_or_switching_the_adoption_drops_the_nickname(game_env):
    m = game_env.module
    _adopt(game_env, 7)
    _nickname(game_env, "Old Bramble")
    _adopt(game_env, 7)  # release
    assert m.adopted_plot_index is None and m.adopted_plot_nickname == ""
    assert game_env.elements["plot-nickname-input"].value == ""


def test_the_log_narrates_the_nicknamed_plot_surviving_requests(game_env):
    m = game_env.module
    game_env.tick(3)
    _adopt(game_env, 7)
    _nickname(game_env, "Old Bramble")
    decline_requests(game_env, 7, 3)
    lines = [e["text"] for e in m.forest_log if e["kind"] == "preserve"]
    assert "Old Bramble survived a first clearing request" in lines[0]
    assert "Old Bramble survived a third clearing request" in lines[-1]


def test_unnamed_plots_keep_the_original_log_text(game_env):
    m = game_env.module
    game_env.tick(3)
    decline_requests(game_env, 7, 1)
    assert m.forest_log[-1]["text"] == "Declined a request to clear B2: kept it standing"


def test_other_events_use_the_nickname(game_env):
    m = game_env.module
    _adopt(game_env, 7)
    _nickname(game_env, "Old Bramble")
    game_env.clear()
    assert "Old Bramble (B2)" in m.forest_log[-1]["text"]


def test_forest_name_appears_in_history_summary_and_almanac(game_env):
    m = game_env.module
    _name_forest(game_env, "Wren Hollow")
    game_env.toggle_session_summary()
    assert "The story of Wren Hollow" in game_env.elements["forest-history-list"].innerText
    assert "Wren Hollow" in m.share_snippet()
    game_env.toggle_almanac()
    assert "Wren Hollow" in game_env.elements["almanac-panel"].children[0].innerText


def test_names_save_and_load(game_env):
    m = game_env.module
    assert "forest_name" not in m.get_state() and "adopted_plot_nickname" not in m.get_state()
    _name_forest(game_env, "Wren Hollow")
    _adopt(game_env, 7)
    _nickname(game_env, "Old Bramble")
    state = m.get_state()
    assert state["forest_name"] == "Wren Hollow" and state["adopted_plot_nickname"] == "Old Bramble"
    game_env.reset_session()
    assert m.forest_name == "" and game_env.elements["forest-name-input"].value == ""
    m.load_state(state)
    assert m.forest_name == "Wren Hollow" and m.adopted_plot_nickname == "Old Bramble"
    assert game_env.elements["forest-name-input"].value == "Wren Hollow"
    assert game_env.elements["plot-nickname-input"].value == "Old Bramble"


def test_a_save_without_names_clears_live_names(game_env):
    m = game_env.module
    plain = m.get_state()
    _name_forest(game_env, "Wren Hollow")
    m.load_state(plain)
    assert m.forest_name == ""


def test_load_validates_name_types(game_env):
    m = game_env.module
    base = m.get_state()
    for bad in (5, ["a"], {"a": 1}, True, None, "x" * 500):
        m.load_state(dict(base, forest_name=bad, adopted_plot_nickname=bad))
        assert isinstance(m.forest_name, str) and len(m.forest_name) <= m.FOREST_NAME_MAX
        assert m.adopted_plot_nickname == ""  # nothing adopted in this save


def test_nickname_only_loads_with_an_adopted_plot(game_env):
    m = game_env.module
    _adopt(game_env, 7)
    _nickname(game_env, "Old Bramble")
    state = m.get_state()
    state["adopted_plot_index"] = None
    m.load_state(state)
    assert m.adopted_plot_nickname == ""


def test_inputs_are_wired_by_setup(game_env):
    assert len(game_env.elements["forest-name-input"]._listeners["change"]) == 1
    assert len(game_env.elements["plot-nickname-input"]._listeners["change"]) == 1
