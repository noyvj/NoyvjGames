"""G-21: a faint pace line from the best earlier Region A run, and a sentence on where you stand."""

import json
import sys

from .fakes import FakeStorage


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def _best(temps, saved=5.0):
    return {"saved": saved, "temps": temps}


def test_no_stored_run_means_no_line_and_no_sentence(game_env):
    m = game_env.module
    assert m.pace_baseline is None
    for _ in range(3):
        game_env.advance_round()
    assert "mini-pace-line" not in game_env.elements["graph"].innerHTML
    assert game_env.elements["pace-display"].hidden is True
    assert game_env.elements["pace-display"].innerText == ""


def test_loads_a_stored_best_run_and_cleans_bad_ones(game_env):
    m = game_env.module
    good = _best([1.0, 2.0, 3.0])
    _storage({m.PACE_KEY: json.dumps(good)})
    assert m.load_best_pace() == {"saved": 5.0, "temps": [1.0, 2.0, 3.0]}
    for bad in (
        {"saved": -1, "temps": [1, 2]},
        {"saved": 1, "temps": [1]},
        {"saved": 1, "temps": "x"},
        {"saved": 1, "temps": [1, "a"]},
        {"saved": 1, "temps": [1.0] * 500},
        {"saved": True, "temps": [1, 2]},
        {"temps": [1, 2]},
        [1, 2],
    ):
        _storage({m.PACE_KEY: json.dumps(bad)})
        assert m.load_best_pace() is None, bad
    _storage({m.PACE_KEY: "{not json"})
    assert m.load_best_pace() is None


def test_graph_draws_the_pace_line_and_scales_to_include_it(game_env):
    m = game_env.module
    history = [1.0, 2.0, 3.0]
    plain = m.mini_temp_graph_svg(history, "Region A")
    paced = m.mini_temp_graph_svg(history, "Region A", pace=[5.0, 6.0, 7.0])
    assert "mini-pace-line" in paced and "mini-pace-line" not in plain
    # the pace values are higher, so the real line now sits at the bottom of the shared scale
    assert plain != paced


def test_pace_longer_than_the_run_is_cut_to_the_rounds_played(game_env):
    m = game_env.module
    svg = m.mini_temp_graph_svg([1.0, 2.0], "Region A", pace=[1.0, 2.0, 3.0, 4.0])
    line = svg.split('class="mini-pace-line"')[0].rsplit("<polyline", 1)[1]
    assert line.count(",") == 2  # two points only


def test_one_point_of_pace_draws_nothing(game_env):
    m = game_env.module
    assert "mini-pace-line" not in m.mini_temp_graph_svg([1.0, 2.0], "Region A", pace=[3.0])


def test_sentence_says_ahead_level_behind_and_past_the_end(game_env):
    m = game_env.module
    m.pace_baseline = _best([1.0, 2.0, 3.0], saved=6.0)
    m.region.temperature_history = [1.0, 1.5]
    assert "0.5" in m.pace_text() and "cooler" in m.pace_text() and "ahead of your best pace" in m.pace_text()
    m.region.temperature_history = [1.0, 2.0]
    assert "Level with your best earlier run" in m.pace_text()
    m.region.temperature_history = [1.0, 2.6]
    assert "0.6" in m.pace_text() and "warmer" in m.pace_text() and "dashed line" in m.pace_text()
    m.region.temperature_history = [1.0, 2.0, 3.0, 4.0]
    assert "past the 3 rounds" in m.pace_text()
    m.region.temperature_history = []
    assert "faint dashed line" in m.pace_text()


def test_pace_sentence_is_never_scolding(game_env):
    m = game_env.module
    m.pace_baseline = _best([1.0, 2.0, 3.0], saved=6.0)
    for hist in ([1.0, 1.0], [1.0, 9.0], [1, 2, 3, 4]):
        m.region.temperature_history = hist
        text = m.pace_text().lower()
        for word in ("fail", "lose", "lost", "worse", "behind"):
            assert word not in text


def test_render_shows_the_sentence_and_the_line(game_env):
    m = game_env.module
    m.pace_baseline = _best([1.0, 2.0, 3.0, 4.0])
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.elements["pace-display"].hidden is False
    assert game_env.elements["pace-display"].innerText
    assert "mini-pace-line" in game_env.elements["graph"].innerHTML


def test_a_better_run_is_stored_but_does_not_change_this_sessions_line(game_env):
    m = game_env.module
    storage = _storage()
    m.pace_best = None
    m.pace_baseline = None
    for _ in range(3):
        game_env.invest("preserve")
        game_env.advance_round()
    m.region.counterfactual_temperature = m.region.temperature + 4.0  # 4 degrees saved
    m.render()
    stored = json.loads(storage.data[m.PACE_KEY])
    assert stored["saved"] == m.region.temperature_saved()
    assert stored["temps"] == [round(t, 3) for t in m.region.temperature_history]
    assert m.pace_baseline is None  # the line shown this session is still the one from page load


def test_a_worse_run_does_not_replace_the_stored_best(game_env):
    m = game_env.module
    storage = _storage()
    m.pace_best = _best([1.0, 2.0], saved=50.0)
    m.pace_baseline = m.pace_best
    for _ in range(3):
        game_env.advance_round()
    m.region.counterfactual_temperature = m.region.temperature + 2.0
    m.render()
    assert m.PACE_KEY not in storage.data
    assert m.pace_best["saved"] == 50.0


def test_nothing_is_stored_before_anything_is_saved(game_env):
    m = game_env.module
    storage = _storage()
    m.pace_best = None
    game_env.advance_round()
    game_env.advance_round()
    m.render()
    assert m.PACE_KEY not in storage.data  # no degrees saved yet


def test_stored_path_is_capped(game_env):
    m = game_env.module
    storage = _storage()
    m.pace_best = None
    m.region.temperature_history = [float(i) for i in range(300)]
    m.region.temperature = 299.0
    m.region.counterfactual_temperature = 400.0
    m._maybe_update_pace()
    stored = json.loads(storage.data[m.PACE_KEY])
    # Z-3e3: a long run is thinned evenly by the shared recorder (not cut off), and says how long it really was
    assert 2 <= len(stored["temps"]) <= m.PACE_MAX_ROUNDS and stored["rounds"] == 300
    assert stored["temps"][0] == 0 and stored["temps"][-1] == 299


def test_pace_does_not_enter_the_save(game_env):
    m = game_env.module
    m.pace_baseline = _best([1.0, 2.0])
    assert "pace" not in json.dumps(m.get_state())
