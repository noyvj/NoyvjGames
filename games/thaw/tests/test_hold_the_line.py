"""Oct 8 batch: GG-2 Hold the Line (the run mode), GG-24 title ladder, GG-21 AI stewards,
G-1 Field Notes, G-2 two-run overlay, G-13 temperature units, G-14 graph patterns."""

import json
import sys

import pytest


class FakeStorage:
    def __init__(self, initial=None):
        self.data = dict(initial or {})

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        self.data[key] = value


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def _hold(env):
    assert env.module.set_hold_the_line(True)
    return env.module


def _play_until_over(env, limit=200):
    for _ in range(limit):
        if env.module.run_over:
            return
        env.advance_round()
    raise AssertionError("the run never ended")


# --------------------------------------------------------------------------- escalation
def test_nothing_changes_outside_the_mode(game_env):
    m = game_env.module
    assert m.hold_the_line is False
    for rn in (1, 6, 40):
        assert m.escalation_level(rn) == 0
        assert m.base_rise_per_round(rn) == m.BASE_TEMP_RISE_PER_ROUND
        assert m.max_dampening(rn) == m.MAX_FEEDBACK_DAMPENING


def test_escalation_steps_every_five_rounds(game_env):
    m = _hold(game_env)
    assert [m.escalation_level(r) for r in (1, 5, 6, 10, 11, 16)] == [0, 0, 1, 1, 2, 3]
    assert m.base_rise_per_round(1) == pytest.approx(1.0)
    assert m.base_rise_per_round(6) == pytest.approx(1.0 + m.HOLD_LINE_ESCALATION_STEP)
    assert m.max_dampening(11) == pytest.approx(m.MAX_FEEDBACK_DAMPENING - 2 * m.HOLD_LINE_CAP_EROSION)
    assert m.max_dampening(10000) == m.HOLD_LINE_MIN_CAP


def test_escalation_raises_the_rise_and_caps_dampening_for_a_region(game_env):
    m = _hold(game_env)
    r = m.region
    r.capacity["preserve"] = 11  # 88% uncapped, over the 85% ceiling
    assert r.feedback_dampening_fraction() == pytest.approx(0.85)
    r.round_number = 21  # level 4
    assert r.base_rise() == pytest.approx(1.0 + 4 * m.HOLD_LINE_ESCALATION_STEP)
    assert r.feedback_dampening_fraction() == pytest.approx(0.85 - 4 * m.HOLD_LINE_CAP_EROSION)


def test_counterfactual_faces_the_same_escalation(game_env):
    m = _hold(game_env)
    for _ in range(12):
        game_env.advance_round()
    # With nothing invested the real region and its counterfactual are identical.
    assert m.region.temperature == pytest.approx(m.region.counterfactual_temperature)
    assert m.region.temperature > 12.0  # harsher than the steady +1.0 a round


def test_region_d_tracks_the_counterfactual_in_the_mode(game_env):
    m = _hold(game_env)
    for _ in range(8):
        game_env.advance_round()
    assert m.region_d.temperature == pytest.approx(m.region.counterfactual_temperature)


def test_escalation_is_announced_once_and_logged(game_env):
    m = _hold(game_env)
    for _ in range(4):
        game_env.advance_round()
    assert game_env.elements["escalation-callout"].hidden is True
    game_env.advance_round()  # round 5 -> 6: the first event lands
    callout = game_env.elements["escalation-callout"]
    assert callout.hidden is False and "Heat dome" in callout.innerText
    assert any(e["region"] == "ALL" and "Heat dome" in e["text"] for e in m.science_log)
    game_env.advance_round()
    assert callout.hidden is True
    assert "Escalation: Heat dome" not in game_env.elements["sr-announcer"].innerText


def test_status_shows_what_is_coming(game_env):
    m = _hold(game_env)
    m.render()
    text = game_env.elements["hold-line-display"].innerText
    assert "Hold the Line, round 1" in text and "3 of 3" in text
    assert "Next: Heat dome in 5 rounds" in text


# --------------------------------------------------------------------------- choosing the mode
def test_toggle_only_before_round_one(game_env):
    m = game_env.module
    game_env.elements["hold-line-toggle-button"].dispatch("click", None)
    assert m.hold_the_line is True
    assert game_env.elements["hold-line-toggle-button"].innerText == "Hold the Line: on"
    game_env.elements["hold-line-toggle-button"].dispatch("click", None)
    assert m.hold_the_line is False
    game_env.advance_round()
    assert m.set_hold_the_line(True) is False
    assert game_env.elements["hold-line-toggle-button"].disabled is True


def test_long_game_and_hold_the_line_exclude_each_other(game_env):
    m = game_env.module
    assert m.set_long_game(True)
    assert m.set_hold_the_line(True) is False
    assert m.set_long_game(False) and m.set_hold_the_line(True)
    assert m.set_long_game(True) is False
    m.render()
    assert game_env.elements["long-game-toggle-button"].disabled is True


# --------------------------------------------------------------------------- the run
def test_run_ends_when_two_regions_go_critical(game_env):
    m = _hold(game_env)
    _play_until_over(game_env)
    assert m.run_over is True
    assert m.run_result["reason"] == "tipped"
    assert len(m.tipped_labels()) >= 2
    played = m.region.round_number - 1
    assert m.run_result["survived"] == played - 1
    assert 5 <= m.run_result["survived"] <= 30  # doing nothing breaks the line early


def test_unmanaged_run_is_shorter_than_a_protected_one(game_env):
    m = _hold(game_env)
    _play_until_over(game_env)
    unmanaged = m.run_result["survived"]
    protected = m.simulate_steward("kai")["survived"]
    assert protected > unmanaged + 5


def test_advance_is_refused_and_disabled_after_the_run(game_env):
    m = _hold(game_env)
    _play_until_over(game_env)
    rounds = m.region.round_number
    game_env.advance_round()
    assert m.region.round_number == rounds
    button = game_env.elements["advance-round-button"]
    assert button.disabled is True and button.innerText == "Run over"


def test_nothing_is_a_run_without_the_mode(game_env):
    m = game_env.module
    for _ in range(40):
        game_env.advance_round()
    assert m.run_over is False and m.run_result is None
    assert game_env.elements["advance-round-button"].disabled is False


def test_rescue_keeps_a_region_out_of_the_critical_tier(game_env):
    m = _hold(game_env)
    for r in (m.region, m.region_b, m.region_c):
        r.funds = 5000.0
    for _ in range(40):
        if m.run_over or any(r.is_critical() for r in (m.region, m.region_b, m.region_c)):
            break
        game_env.advance_round()
    critical = [r for r in (m.region, m.region_b, m.region_c) if r.is_critical()]
    assert critical
    assert critical[0].rescue()
    assert not critical[0].is_critical()
    assert m.untipped_count() >= 1


def test_limit_ends_a_standing_run(game_env, monkeypatch):
    m = _hold(game_env)
    monkeypatch.setattr(m, "HOLD_LINE_MAX_ROUNDS", 3)
    for _ in range(3):
        game_env.advance_round()
    assert m.run_over and m.run_result["reason"] == "limit"
    assert m.run_result["survived"] == 3
    assert "all 3 rounds" in "".join(game_env.elements["hold-line-result"].innerHTML)


def test_result_panel_lists_title_goal_and_stewards(game_env):
    _hold(game_env)
    _play_until_over(game_env)
    html = game_env.elements["hold-line-result"].innerHTML
    assert game_env.elements["hold-line-result"].hidden is False
    assert "Your title:" in html and "Next title:" in html
    for name in ("Cautious Kai", "Rash Rasmus", "Balanced Bea"):
        assert name in html
    assert "You beat 0 of 3 stewards" in html


def test_run_end_is_logged_and_announced(game_env):
    m = _hold(game_env)
    _play_until_over(game_env)
    assert any("the run is over" in e["text"] for e in m.science_log)
    assert "The run is over after" in game_env.elements["sr-announcer"].innerText
    assert len(m.science_log) <= m.SCIENCE_LOG_MAX


# --------------------------------------------------------------------------- GG-24 titles
def test_title_ladder_bands(game_env):
    m = game_env.module
    assert m.run_title(0.0) == ("Ice Cube", "Snowflake Counter", 10.0)
    assert m.run_title(9.99)[0] == "Ice Cube"
    assert m.run_title(10.0)[0] == "Snowflake Counter"
    assert m.run_title(150.0)[0] == "Glacier Steward"
    assert m.run_title(10000.0) == ("Cryosphere Guardian", None, None)


def test_titles_ascend_and_start_at_zero(game_env):
    m = game_env.module
    minimums = [minimum for minimum, _name in m.RUN_TITLES]
    assert minimums[0] == 0.0 and minimums == sorted(minimums)
    assert m.RUN_TITLES[0][1] == "Ice Cube" and m.RUN_TITLES[-1][1] == "Cryosphere Guardian"


# --------------------------------------------------------------------------- GG-21 stewards
def test_stewards_are_deterministic_and_ordered(game_env):
    m = game_env.module
    first = m.steward_scores()
    m._steward_cache.clear()
    assert m.steward_scores() == first
    assert first["kai"]["survived"] > first["rasmus"]["survived"] > first["bea"]["survived"]
    assert first["bea"]["survived"] > 14  # more than doing nothing


def test_simulating_stewards_leaves_the_game_alone(game_env):
    m = game_env.module
    m.simulate_steward("kai")
    assert m.hold_the_line is False and m.long_game is False
    assert m.region.round_number == 1 and m.region.funds == m.STARTING_FUNDS
    assert m.base_rise_per_round(40) == m.BASE_TEMP_RISE_PER_ROUND


def test_stewards_beaten_counts_strictly_better_runs(game_env):
    m = game_env.module
    scores = m.steward_scores()
    assert m.stewards_beaten(0) == 0
    assert m.stewards_beaten(scores["bea"]["survived"]) == 0
    assert m.stewards_beaten(scores["bea"]["survived"] + 1) == 1
    assert m.stewards_beaten(scores["kai"]["survived"] + 1) == 3


# --------------------------------------------------------------------------- save / load
def test_state_round_trip_mid_run_and_after(game_env):
    m = _hold(game_env)
    for _ in range(7):
        game_env.advance_round()
    state = json.loads(json.dumps(m.get_state()))
    assert state["hold_the_line"] is True and "run" not in state
    _play_until_over(game_env)
    done = json.loads(json.dumps(m.get_state()))
    assert done["run"]["reason"] == "tipped"
    m.hold_the_line, m.run_over, m.run_result = False, False, None
    assert m.load_state(done)
    assert m.hold_the_line and m.run_over and m.run_result == done["run"]
    assert m.load_state(state)
    assert m.hold_the_line and not m.run_over and m.run_result is None


def test_old_saves_have_no_new_keys(game_env):
    state = game_env.module.get_state()
    assert "hold_the_line" not in state and "run" not in state


@pytest.mark.parametrize("bad", [
    {"survived": -1, "saved": 1.0, "reason": "tipped"},
    {"survived": 3.5, "saved": 1.0, "reason": "tipped"},
    {"survived": True, "saved": 1.0, "reason": "tipped"},
    {"survived": 3, "saved": float("nan"), "reason": "tipped"},
    {"survived": 3, "saved": 1.0, "reason": "nope"},
    "garbage",
    None,
])
def test_a_bad_saved_run_loads_as_not_over(game_env, bad):
    m = game_env.module
    assert m.load_state({"hold_the_line": True, "run": bad})
    assert m.hold_the_line is True and m.run_over is False and m.run_result is None


def test_mode_flag_must_be_a_real_true_and_not_with_long_game(game_env):
    m = game_env.module
    m.load_state({"hold_the_line": 1})
    assert m.hold_the_line is False
    m.load_state({"hold_the_line": True, "long_game": True})
    assert m.hold_the_line is False and m.long_game is True


# --------------------------------------------------------------------------- G-1 Field Notes
def test_finishing_a_run_records_a_note_and_stores_it(game_env):
    storage = _storage()
    m = _hold(game_env)
    _play_until_over(game_env)
    assert len(m.field_notes) == 1
    stored = json.loads(storage.data[m.FIELD_NOTES_KEY])
    assert stored == m.field_notes
    note = m.field_notes[0]
    assert note["survived"] == m.run_result["survived"]
    assert set(note["mix"]) == {"output", "preserve", "monitor"}
    assert len(note["curve"]) == min(len(m.region.temperature_history), 60)
    assert len(game_env.elements["field-notes-list"].innerHTML) > 0
    assert game_env.elements["field-notes-count"].innerText == "1"


def test_nothing_is_recorded_without_a_finished_run(game_env):
    storage = _storage()
    for _ in range(5):
        game_env.advance_round()
    assert game_env.module.field_notes == []
    assert game_env.module.FIELD_NOTES_KEY not in storage.data


def test_notes_are_cleaned_on_load(game_env):
    m = game_env.module
    good = {"survived": 7, "saved": 12.5, "tipped": 2, "avg_accel": 1.4,
            "mix": {"output": 3, "preserve": 4, "monitor": 1},
            "region_saved": {"A": 5.0, "B": 3.0, "C": 4.5}, "best_region": "B",
            "curve": [0.0, 1.0, 2.0], "baseline": [0.0, 1.2, 2.5]}
    junk = [good, "x", {"survived": "7"}, {"survived": -3}, {"survived": 5, "saved": float("inf"),
            "mix": {"output": -1, "preserve": "a"}, "best_region": "Z", "curve": [1, "a", None, True, 2]}]
    _storage({m.FIELD_NOTES_KEY: json.dumps(junk)})
    notes = m.load_field_notes()
    assert len(notes) == 2
    assert notes[0] == good
    assert notes[1]["saved"] == 0.0 and notes[1]["mix"] == {"output": 0, "preserve": 0, "monitor": 0}
    assert notes[1]["best_region"] == "A" and notes[1]["curve"] == [1.0, 2.0]


@pytest.mark.parametrize("raw", ["not json", "{}", "42", "null", ""])
def test_unreadable_notes_load_as_empty(game_env, raw):
    m = game_env.module
    _storage({m.FIELD_NOTES_KEY: raw})
    assert m.load_field_notes() == []


def test_notes_keep_only_the_newest_thirty(game_env):
    m = _hold(game_env)
    _storage()
    m.field_notes[:] = [m._clean_note({"survived": i}) for i in range(m.FIELD_NOTES_MAX)]
    _play_until_over(game_env)
    assert len(m.field_notes) == m.FIELD_NOTES_MAX
    assert m.field_notes[0]["survived"] == 1 and m.field_notes[-1]["survived"] == m.run_result["survived"]


def test_decimation_keeps_the_ends_and_the_limit(game_env):
    m = game_env.module
    values = [float(i) for i in range(300)]
    out = m._decimate(values)
    assert len(out) == 60 and out[0] == 0.0 and out[-1] == 299.0
    assert out == sorted(out)
    assert m._decimate([1.0, 2.0]) == [1.0, 2.0]


def test_bests_and_rows(game_env):
    m = game_env.module
    m.field_notes[:] = [
        m._clean_note({"survived": 5, "region_saved": {"A": 2.0, "B": 9.0, "C": 1.0}}),
        m._clean_note({"survived": 8, "region_saved": {"A": 4.0, "B": 3.0, "C": 1.5}}),
    ]
    assert m.field_note_bests() == {"A": 4.0, "B": 9.0, "C": 1.5}
    rows = m.field_note_rows()
    assert rows[0].startswith("Run 1: held 5 rounds") and rows[1].startswith("Run 2: held 8 rounds")
    m.render()
    assert "Region B 9.0" in game_env.elements["field-notes-bests"].innerText
    assert "<svg" in game_env.elements["field-notes-chart"].innerHTML


def test_empty_notes_say_so(game_env):
    game_env.module.render()
    assert "No finished runs yet" in game_env.elements["field-notes-list"].innerHTML
    assert game_env.elements["field-notes-chart"].innerHTML == ""


# --------------------------------------------------------------------------- G-2 overlay
def _two_runs(m):
    m.field_notes[:] = [
        m._clean_note({"survived": 5, "curve": [0, 1, 2, 3, 4], "baseline": [0, 1, 3, 6, 10]}),
        m._clean_note({"survived": 9, "curve": [0, 1, 2, 3, 4, 5], "baseline": [0, 1, 4, 9, 16, 25]}),
    ]


def test_choices_name_every_run_and_baseline(game_env):
    m = game_env.module
    _two_runs(m)
    values = [v for v, _l in m.compare_choices()]
    assert values == ["run:1", "run:2", "base:1", "base:2"]
    assert m.compare_curve("run:2") == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    assert m.compare_curve("base:1") == [0.0, 1.0, 3.0, 6.0, 10.0]
    for bad in ("run:0", "run:3", "x:1", "run:", "run:-1", None, 5, "run"):
        assert m.compare_curve(bad) is None


def test_divergence_and_readout(game_env):
    m = game_env.module
    assert m.compare_divergence([0, 1, 2], [0, 2, 5, 9]) == [0, 1, 3]
    text = m.compare_readout([0, 1, 2, 3, 4], [0, 1, 3, 6, 10])
    assert "peaks at 6.0" in text and "round 5" in text and "round 3" in text
    assert "never differ" in m.compare_readout([0, 1], [0, 1.5])
    assert "Pick two runs" in m.compare_readout([], [1, 2])


def test_chart_has_two_distinct_lines_and_the_melt_line(game_env):
    m = game_env.module
    svg = m.compare_chart_svg([0, 5, 12], [0, 3, 6])
    assert "compare-line--first" in svg and "compare-line--second" in svg
    assert "mini-temp-threshold-line" in svg and 'role="img"' in svg
    assert m.compare_chart_svg([], [1]) == ""


def test_selects_default_to_the_newest_run_against_its_baseline(game_env):
    m = _hold(game_env)
    _storage()
    _play_until_over(game_env)
    assert game_env.elements["compare-run-a"].value == "run:1"
    assert game_env.elements["compare-run-b"].value == "base:1"
    assert "<polyline" in game_env.elements["compare-chart"].innerHTML
    assert "Over the" in game_env.elements["compare-readout"].innerText
    # The run's own curve ended no hotter than the no-action baseline.
    a, b = m.compare_curve("run:1"), m.compare_curve("base:1")
    assert a[-1] <= b[-1] + 1e-6


def test_changing_a_select_redraws(game_env):
    m = game_env.module
    _two_runs(m)
    m.render()
    game_env.elements["compare-run-a"].value = "run:1"
    game_env.elements["compare-run-b"].value = "run:2"
    game_env.elements["compare-run-b"].dispatch("change", None)
    assert "Over the 5 rounds" in game_env.elements["compare-readout"].innerText


def test_no_runs_prompts_instead_of_charting(game_env):
    game_env.module.render()
    assert game_env.elements["compare-chart"].innerHTML == ""
    assert "Finish a run" in game_env.elements["compare-readout"].innerText


# --------------------------------------------------------------------------- G-13 units
def test_celsius_text_is_unchanged(game_env):
    m = game_env.module
    assert m.deg(3.14159) == "3.1°"
    assert m.deg(3.14159, 2, plus=True) == "+3.14°"
    m.render()
    assert game_env.elements["temperature-display"].innerText == "Global temperature: +0.0°"


def test_fahrenheit_and_kelvin_convert_the_rise(game_env):
    m = game_env.module
    m.set_temp_unit("f")
    assert m.deg(10.0, 1, plus=True) == "+18.0°F"
    assert m.deg(0.0) == "0.0°F"  # a rise: no 32 degree offset
    m.set_temp_unit("k")
    assert m.deg(10.0, 1, plus=True) == "+10.0 K"


def test_unit_select_changes_every_readout_and_persists(game_env):
    storage = _storage()
    m = game_env.module
    for _ in range(3):
        game_env.advance_round()
    select = game_env.elements["temp-unit-select"]
    select.value = "f"
    select.dispatch("change", None)
    assert m.temp_unit == "f" and storage.data[m.TEMP_UNIT_STORAGE_KEY] == "f"
    assert game_env.elements["temperature-display"].innerText == "Global temperature: +5.4°F"
    assert "°F" in game_env.elements["b-temperature-display"].innerText
    assert "°F" in game_env.elements["rise-rate-display"].innerText
    assert "°F" in game_env.elements["advance-round-button"].title
    select.value = "k"
    select.dispatch("change", None)
    assert game_env.elements["temperature-display"].innerText == "Global temperature: +3.0 K"


def test_bad_unit_is_ignored_and_stored_unit_is_validated(game_env):
    m = game_env.module
    assert m.set_temp_unit("x") is False and m.temp_unit == "c"
    _storage({m.TEMP_UNIT_STORAGE_KEY: "f"})
    assert m.load_temp_unit() == "f"
    _storage({m.TEMP_UNIT_STORAGE_KEY: "rankine"})
    assert m.load_temp_unit() == "c"
    _storage()
    assert m.load_temp_unit() == "c"


def test_unit_is_not_part_of_the_save(game_env):
    m = game_env.module
    m.set_temp_unit("f")
    assert "temp_unit" not in json.dumps(m.get_state())


def test_forecast_box_is_read_in_the_chosen_unit(game_env):
    m = game_env.module
    m.set_temp_unit("f")
    game_env.elements["forecast-input"].value = "5.4"
    game_env.elements["forecast-lock-button"].dispatch("click", None)
    assert m.forecast_guess == pytest.approx(3.0)
    m.set_temp_unit("c")
    game_env.elements["forecast-input"].value = "4.0"
    game_env.elements["forecast-lock-button"].dispatch("click", None)
    assert m.forecast_guess == pytest.approx(4.0)


def test_graph_threshold_label_follows_the_unit(game_env):
    m = game_env.module
    assert "+10°</text>" in m.mini_temp_graph_svg([2.0, 8.0, 14.0])
    m.set_temp_unit("f")
    assert "+18°F</text>" in m.mini_temp_graph_svg([2.0, 8.0, 14.0])


# --------------------------------------------------------------------------- G-14 graph patterns
def test_each_region_graph_has_its_own_class_and_marker(game_env):
    m = game_env.module
    shapes = {}
    for name, key in (("Region A", "a"), ("Region B", "b"), ("Region C", "c"), ("Region D", "d")):
        svg = m.mini_temp_graph_svg([1.0, 4.0, 9.0], name)
        assert f"graph-region-{key}" in svg and f"mini-temp-end--{key}" in svg
        shapes[key] = svg.split("mini-temp-end--" + key)[1].split(">")[1]
    assert len({s.split(" ")[0] for s in shapes.values()}) >= 3  # circle, rect, polygon shapes differ
    assert "mini-temp-end" not in m.mini_temp_graph_svg([1.0, 4.0, 9.0])
    assert "mini-temp-end" not in m.mini_temp_graph_svg([1.0, 4.0, 9.0], "Somewhere")


def test_marker_stays_inside_the_graph(game_env):
    m = game_env.module
    svg = m.mini_temp_graph_svg([0.0, 5.0, 10.0], "Region A")
    assert 'cx="116.8"' in svg  # clamped off the right edge (120 - radius 3.2)


# --------------------------------------------------------------------------- settings and wiring
def test_settings_panel_has_the_new_controls_and_settings_js_drives_them():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "settings.js").read_text(encoding="utf-8")
    css = (root / "style.css").read_text(encoding="utf-8")
    for box, attr in (("blindfold-checkbox", "data-blindfold"), ("graph-patterns-checkbox", "data-graph-patterns"),
                      ("high-contrast-checkbox", "data-high-contrast")):
        assert f'id="{box}"' in html
        assert box in js and attr in js
        assert f'html[{attr}="true"]' in css
    assert 'id="temp-unit-select"' in html
    for key in ("thaw-blindfold", "thaw-graph-patterns", "thaw-high-contrast"):
        assert key in js
    assert "resetFlags()" in js  # Reset to Default clears them


def test_pc_boot_carries_the_new_panels():
    from pathlib import Path
    pc = (Path(__file__).resolve().parent.parent / "pc.html").read_text(encoding="utf-8")
    for element_id in ("hold-line-toggle-button", "field-notes-details", "compare-chart", "temp-unit-select",
                       "blindfold-checkbox", "hold-line-result"):
        assert f'id="{element_id}"' in pc


def test_graph_summary_speaks_the_chosen_unit(game_env):
    m = game_env.module
    assert "+5.0 degrees," in m.graph_summary_text("Region B", [1.0, 5.0])
    m.set_temp_unit("f")
    text = m.graph_summary_text("Region B", [1.0, 5.0, 11.0])
    assert "+1.8 degrees Fahrenheit" in text and "+19.8 degrees Fahrenheit" in text
    assert "+18 degree Fahrenheit melt threshold" in text
    m.set_temp_unit("k")
    assert "+11.0 kelvin" in m.graph_summary_text("Region B", [1.0, 5.0, 11.0])


def test_field_notes_chart_bars_never_get_fat(game_env):
    m = game_env.module
    m.field_notes[:] = [m._clean_note({"survived": 5, "saved": 10.0})]
    assert 'width="12.0"' in m.field_notes_chart_svg()
