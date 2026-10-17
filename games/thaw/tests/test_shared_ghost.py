"""Z-3e3: Thaw's best-run pace line (G-21) now runs through the shared ghost (shared/ghost.py). One number per round
(Region A's temperature, lower is ahead) recorded by ghost.Recorder when a new best is stored; the old stored record
shape still loads; the dashed line is labelled in text; the shared sentence is in the graph's accessible name and in a
visually hidden status; a long run is thinned, not cut; hostile data is dropped; the save is untouched."""

import json
import sys

import ghost

from .fakes import FakeStorage
from .pagefiles import game_css


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def _best(temps, saved=5.0, **extra):
    return {"saved": saved, "temps": temps, **extra}


def test_an_old_stored_record_loads_unchanged_and_gives_a_shared_trace(game_env):
    m = game_env.module
    old = {"saved": 5.0, "temps": [1.0, 2.0, 3.0]}              # the exact G-21 storage shape from before the shared ghost
    _storage({m.PACE_KEY: json.dumps(old)})
    assert m.load_best_pace() == old
    trace = m.pace_trace(m.load_best_pace())
    assert trace["values"] == [1, 2, 3] and trace["turns"] == 3 and trace["label"] == "best run"
    assert ghost.load(trace) == trace


def test_one_number_per_round_is_recorded_when_a_new_best_is_stored(game_env):
    m = game_env.module
    storage = _storage()
    m.pace_best = m.pace_baseline = None
    for _ in range(4):
        game_env.invest("preserve")
        game_env.advance_round()
    m.region.counterfactual_temperature = m.region.temperature + 3.0
    m.render()
    stored = json.loads(storage.data[m.PACE_KEY])
    assert "rounds" not in stored and len(stored["temps"]) == len(m.region.temperature_history) == 4
    assert stored["temps"] == [round(t, 2) for t in m.region.temperature_history]
    assert ghost.load({"turns": 4, "values": stored["temps"]})["values"] == stored["temps"]   # already clean shared numbers


def test_a_long_best_run_is_thinned_evenly_and_remembers_its_length(game_env):
    m = game_env.module
    storage = _storage()
    m.pace_best = m.pace_baseline = None
    m.region.temperature_history = [float(i) / 2 for i in range(400)]
    m.region.temperature = 199.5
    m.region.counterfactual_temperature = 300.0
    m._maybe_update_pace()
    stored = json.loads(storage.data[m.PACE_KEY])
    assert stored["rounds"] == 400 and len(stored["temps"]) <= m.PACE_MAX_ROUNDS
    assert stored["temps"][0] == 0 and stored["temps"][-1] == 199.5
    reloaded = m.load_best_pace()
    assert reloaded["rounds"] == 400
    trace = m.pace_trace(reloaded)
    assert trace["turns"] == 400 and ghost.value_at(trace, 400) == 199.5 and ghost.value_at(trace, 1) == 0
    m.pace_baseline = reloaded
    assert len(m.pace_values(250)) == 250 and len(m.pace_values(9999)) == 400    # the line now covers the whole run, not 120 rounds
    m.region.temperature_history = [0.0] * 401
    assert "past the 400 rounds" in m.pace_text()


def test_the_sentence_is_the_shared_wording_in_rounds_and_degrees(game_env):
    m = game_env.module
    m.pace_baseline = _best([1.0, 2.0, 3.0], saved=6.0)
    m.region.temperature_history = [1.0, 1.5]
    assert m.ghost_sentence() == "Ghost: you are 0.5° ahead of your best run at round 2."
    m.region.temperature_history = [1.0, 2.0]
    assert m.ghost_sentence() == "Ghost: level with your best run at round 2."
    m.region.temperature_history = [1.0, 2.6]
    assert m.ghost_sentence() == "Ghost: your best run was 0.6° ahead at round 2."
    m.region.temperature_history = [1.0, 2.0, 3.0, 4.0]
    assert m.ghost_sentence() == "Ghost: your best run ended before round 4."
    m.region.temperature_history = []
    assert m.ghost_sentence() == ""
    m.pace_baseline = None
    m.region.temperature_history = [1.0, 2.0]
    assert m.ghost_sentence() == ""
    assert "turn" not in m.ghost_sentence()


def test_the_sentence_follows_the_temperature_unit(game_env):
    m = game_env.module
    m.pace_baseline = _best([1.0, 2.0, 3.0], saved=6.0)
    m.region.temperature_history = [1.0, 1.5]
    m.temp_unit = "f"
    assert m.ghost_sentence() == "Ghost: you are 0.9°F ahead of your best run at round 2."
    m.temp_unit = "k"
    assert m.ghost_sentence() == "Ghost: you are 0.5 K ahead of your best run at round 2."
    m.temp_unit = "c"
    assert m.ghost_sentence().endswith("0.5° ahead of your best run at round 2.")


def test_the_dashed_line_is_labelled_in_text_and_names_itself_for_screen_readers(game_env):
    m = game_env.module
    note = "Ghost: you are 0.5° ahead of your best run at round 2."
    svg = m.mini_temp_graph_svg([1.0, 1.5], "Region A", pace=[1.0, 2.0, 3.0], ghost_note=note)
    assert 'data-testid="ghost-line"' in svg and "mini-pace-line" in svg
    assert "Ghost: best run (dashed)" in svg and f"<title>{note}</title>" in svg
    assert svg.count(note) == 2                                          # the line's title and the graph's accessible name
    plain = m.mini_temp_graph_svg([1.0, 1.5], "Region A", pace=[1.0, 2.0, 3.0])
    assert "<title>" not in plain.split("mini-pace-line")[1].split("</g>")[0]
    assert "Ghost" not in m.mini_temp_graph_svg([1.0, 1.5], "Region A")
    assert "Ghost: you are" not in m.mini_temp_graph_svg([1.0, 1.5], "Region A", ghost_note=note)  # no line, no claim


def test_render_fills_the_hidden_status_and_the_graph(game_env):
    m = game_env.module
    m.pace_baseline = _best([1.0, 2.0, 3.0, 4.0])
    game_env.advance_round()
    game_env.advance_round()
    box = game_env.elements["ghost-sentence"]
    assert box.hidden is False and box.innerText.startswith("Ghost: ")
    assert box.innerText in game_env.elements["graph"].innerHTML
    m.pace_baseline = None
    m.render()
    assert box.hidden is True and box.innerText == ""
    assert "ghost-line" not in game_env.elements["graph"].innerHTML


def test_the_sentence_is_not_recomputed_while_nothing_changes(game_env):
    m = game_env.module
    m.pace_baseline = _best([1.0, 2.0, 3.0])
    m.region.temperature_history = [1.0, 1.5]
    first = m.ghost_sentence()
    key = m._ghost_sentence_cache["key"]
    assert m.ghost_sentence() == first and m._ghost_sentence_cache["key"] == key
    m.region.temperature_history = [1.0, 1.5, 2.5]
    assert m.ghost_sentence() != first


def test_hostile_stored_records_give_no_ghost(game_env):
    m = game_env.module
    bad = (
        {"saved": 1, "temps": [1, 2], "rounds": "x"}, {"saved": 1, "temps": [1.0] * 500},
        {"saved": 1, "temps": [1, float("nan")]}, {"saved": 1, "temps": [True, 2]},
        {"saved": 1, "temps": [1, 2], "rounds": 10 ** 12}, [1, 2], "x", None, 7,
    )
    for record in bad:
        _storage({m.PACE_KEY: json.dumps(record)})
        loaded = m.load_best_pace()
        if loaded is not None:              # a bad "rounds" alone only loses the length, never the whole record
            assert "rounds" not in loaded and loaded["temps"] == [1.0, 2.0], record
    for rounds in (True, 2, 1, -5, 1.5, 10 ** 12, "400", None, [400]):
        _storage({m.PACE_KEY: json.dumps({"saved": 1, "temps": [1, 2], "rounds": rounds})})
        assert m.load_best_pace() == {"saved": 1.0, "temps": [1.0, 2.0]}, rounds
    _storage({m.PACE_KEY: json.dumps({"saved": 1, "temps": [1, 2], "rounds": 50})})
    assert m.load_best_pace()["rounds"] == 50
    m.pace_baseline = {"saved": 1.0, "temps": [1.0]}                    # an unusable record that bypassed loading
    assert m.pace_trace() is None and m.ghost_sentence() == "" and m.pace_text() == ""
    m.region.temperature_history = [1.0] * (ghost.HARD_INPUT_LIMIT + 1)
    m.pace_baseline = _best([1.0, 2.0])
    assert m.ghost_sentence() == ""                                      # over the shared cap: says nothing, never fails


def test_the_setting_that_hides_the_pace_line_hides_label_and_sentence_too():
    from pathlib import Path
    css = game_css()
    block = css.split('html[data-hide-pace="true"] .mini-pace-line')[1].split("}")[0]
    assert ".mini-pace-label" in block and ".ghost-sentence" in block and ".pace-display" in block


def test_nothing_new_enters_the_save_or_other_storage(game_env):
    m = game_env.module
    storage = _storage()
    m.pace_best = m.pace_baseline = None
    for _ in range(3):
        game_env.advance_round()
    m.region.counterfactual_temperature = m.region.temperature + 2.0
    m.render()
    assert m.PACE_KEY in storage.data and not [key for key in storage.data if "ghost" in key]   # no new storage key
    assert "ghost" not in json.dumps(m.get_state()).lower() and "pace" not in json.dumps(m.get_state()).lower()
