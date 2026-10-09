"""E-22 notes, E-21 sort / filter / archive, E-20 side-by-side compare on the Past Runs list."""

import types
from pathlib import Path

LOG = [{"type": "flood", "damage": 10.0, "severity": 1.0}] * 7


def _entry(m, number, score, scenario="classic", extended=False, damage=None):
    schedule = m.SCENARIOS[scenario]["schedule"] * (2 if extended else 1)
    log = [{"type": t, "damage": (damage if damage is not None else 10.0), "severity": 1.0} for t in schedule]
    return {
        "run_number": number, "score": float(score), "resilience_capacity": 1, "growth_capacity": 1,
        "damage_taken": sum(e["damage"] for e in log), "knowledge_earned": 2, "event_log": log,
    }


def _seed(game_env, *entries):
    m = game_env.module
    m.run_log_history[:] = list(entries)
    game_env.toggle_past_runs()
    return m


def _cards(game_env):
    return game_env.elements["past-runs-list"].children


def _find(card, action):
    stack = list(card.children)
    while stack:
        el = stack.pop()
        if el.getAttribute("data-action") == action:
            return el
        stack.extend(el.children)
    raise AssertionError(action)


def _event(target):
    return types.SimpleNamespace(target=target)


def _nums(game_env):
    import re
    return ["#" + re.search(r"Run #(\d+)", c.children[0].innerText).group(1) for c in _cards(game_env)]


def _titles(game_env):
    return [c.children[0].innerText for c in _cards(game_env)]


# ---- E-22 notes -------------------------------------------------------------
def test_every_card_has_a_note_box_and_a_saved_note_is_shown(game_env):
    m = game_env.module
    m = _seed(game_env, _entry(m, 1, 50))
    box = _find(_cards(game_env)[0], "note")
    assert box.value == "" and box.getAttribute("data-run") == "1"
    box.value = "  Built the sea wall first  "
    m.on_past_runs_event(_event(box))
    assert m.run_note(1) == "Built the sea wall first"
    m.render()
    assert _find(_cards(game_env)[0], "note").value == "Built the sea wall first"


def test_notes_are_trimmed_capped_cleared_and_persisted(game_env):
    m = game_env.module
    assert len(m.set_run_note(3, "x" * 400)) == m.RUN_NOTE_MAX_CHARS
    assert m.load_meta()["run_notes"]["3"] == "x" * m.RUN_NOTE_MAX_CHARS
    m.set_run_note(3, "   ")
    assert "3" not in m.meta["run_notes"]


def test_notes_and_archive_ride_the_progress_export(game_env):
    m = game_env.module
    m.set_run_note(2, "tough one")
    m.set_run_archived(2, True)
    code = m.export_progress_code()
    m.set_run_note(2, "")
    m.set_run_archived(2, False)
    assert m.import_progress_code(code) is True
    assert m.run_note(2) == "tough one" and m.meta["archived_runs"] == [2]


def test_old_meta_without_the_new_keys_gets_defaults(game_env):
    m = game_env.module
    meta = m._sanitize_meta({"settlement_name": "Old", "pinned_skills": []})
    assert meta["run_notes"] == {} and meta["archived_runs"] == []
    junk = m._sanitize_meta({"run_notes": {"x": "a", "4": 5, "5": "ok"}, "archived_runs": [1, "2", True, -3, 7]})
    assert junk["run_notes"] == {"5": "ok"} and junk["archived_runs"] == [1, 7]


# ---- E-21 sort / filter / archive ---------------------------------------------
def test_run_mode_is_inferred_from_the_log(game_env):
    m = game_env.module
    assert m.run_mode(_entry(m, 1, 1)) == {"scenario": "classic", "extended": False}
    assert m.run_mode(_entry(m, 1, 1, "coastal", True)) == {"scenario": "coastal", "extended": True}
    assert m.run_mode(_entry(m, 1, 1, "heat_season"))["scenario"] == "heat_season"
    assert m.run_mode({"event_log": [{"type": "flood"}]}) == {"scenario": None, "extended": False}
    assert m.run_mode_label({"event_log": []}) == "Custom schedule"
    assert m.run_mode_label(_entry(m, 1, 1, "urban", True)) == "Urban, extended"


def _set(game_env, sort=None, flt=None, archived=None):
    m = game_env.module
    if sort is not None:
        game_env.elements["past-runs-sort"].value = sort
    if flt is not None:
        game_env.elements["past-runs-filter"].value = flt
    if archived is not None:
        game_env.elements["past-runs-archived"].checked = archived
    m.on_past_runs_controls_change()


def test_default_view_is_newest_first_and_sorts_by_score_and_age(game_env):
    m = game_env.module
    _seed(game_env, _entry(m, 1, 30), _entry(m, 2, 90), _entry(m, 3, 60))
    assert _nums(game_env) == ["#3", "#2", "#1"]
    _set(game_env, sort="oldest")
    assert _nums(game_env) == ["#1", "#2", "#3"]
    _set(game_env, sort="score_high")
    assert _nums(game_env) == ["#2", "#3", "#1"]
    _set(game_env, sort="score_low")
    assert _nums(game_env) == ["#1", "#3", "#2"]


def test_filters_by_length_and_scenario(game_env):
    m = game_env.module
    _seed(game_env, _entry(m, 1, 30), _entry(m, 2, 90, "coastal"), _entry(m, 3, 60, extended=True))
    _set(game_env, flt="extended")
    assert len(_cards(game_env)) == 1 and "Run #3" in _titles(game_env)[0]
    _set(game_env, flt="standard")
    assert len(_cards(game_env)) == 2
    _set(game_env, flt="scenario:coastal")
    assert len(_cards(game_env)) == 1 and "Run #2" in _titles(game_env)[0]
    _set(game_env, flt="scenario:nowhere")  # an unknown value is ignored, the filter stays
    assert len(_cards(game_env)) == 1
    _set(game_env, flt="scenario:phoenix")
    assert "No runs match" in _cards(game_env)[0].innerText
    assert "Showing 0 of 3" in game_env.elements["past-runs-status"].innerText


def test_archiving_hides_but_keeps_score_knowledge_and_stats(game_env):
    m = game_env.module
    m.skill_tree.add_knowledge(5)
    m.run_history[:] = [30.0, 90.0]
    _seed(game_env, _entry(m, 1, 30), _entry(m, 2, 90))
    knowledge, history = m.skill_tree.knowledge_points, list(m.run_history)
    archive = _find(_cards(game_env)[1], "archive")  # run 1 (newest first)
    assert archive.innerText == "Archive"
    m.on_past_runs_event(_event(archive))
    assert m.meta["archived_runs"] == [1]
    assert len(_cards(game_env)) == 1 and "Run #2" in _titles(game_env)[0]
    assert m.skill_tree.knowledge_points == knowledge and m.run_history == history
    assert len(m.run_log_history) == 2 and m.lifetime_stats()["runs"] == 2
    assert "(2)" in game_env.elements["past-runs-toggle-button"].innerText or "Hide" in game_env.elements["past-runs-toggle-button"].innerText
    _set(game_env, archived=True)
    assert len(_cards(game_env)) == 2
    unarchive = _find(_cards(game_env)[1], "archive")
    assert unarchive.innerText == "Unarchive" and "archived" in _titles(game_env)[1]
    m.on_past_runs_event(_event(unarchive))
    assert m.meta["archived_runs"] == []


# ---- E-20 compare -----------------------------------------------------------------
def test_ticking_two_runs_shows_them_side_by_side_with_differences(game_env):
    m = game_env.module
    a, b = _entry(m, 1, 30, damage=10.0), _entry(m, 2, 90, damage=4.0)
    _seed(game_env, a, b)
    box_for_run = lambda n: _find(next(c for c in _cards(game_env) if f"Run #{n}" in c.children[0].innerText), "compare")  # noqa: E731
    first = box_for_run(1)
    first.checked = True
    m.on_past_runs_event(_event(first))
    assert game_env.elements["past-runs-compare"].hidden is True  # one pick is not a comparison
    second = box_for_run(2)
    second.checked = True
    m.on_past_runs_event(_event(second))
    panel = game_env.elements["past-runs-compare"]
    assert panel.hidden is False
    assert "Run #2 scored 60 more than Run #1" in panel.children[0].innerText
    cells = [c.innerText for c in panel.children[1].children]
    assert "Run #1 (Classic mix)" in cells[0] and "Run #2 (Classic mix)" in cells[1]
    assert any("Score: 30" == c for c in cells) and any(c.startswith("Score: 90 (+60)") for c in cells)
    assert any("(harsher)" in c for c in cells) and any("(gentler)" in c for c in cells)


def test_a_third_pick_replaces_the_oldest_and_unticking_removes(game_env):
    m = game_env.module
    _seed(game_env, _entry(m, 1, 1), _entry(m, 2, 2), _entry(m, 3, 3))
    for n in (1, 2, 3):
        box = _find(next(c for c in _cards(game_env) if f"Run #{n}" in c.children[0].innerText), "compare")
        box.checked = True
        m.on_past_runs_event(_event(box))
    assert m.past_runs_compare == [2, 3]
    box = _find(next(c for c in _cards(game_env) if "Run #3" in c.children[0].innerText), "compare")
    box.checked = False
    m.on_past_runs_event(_event(box))
    assert m.past_runs_compare == [2] and game_env.elements["past-runs-compare"].hidden is True


def test_compare_handles_runs_of_different_length_and_events(game_env):
    m = game_env.module
    rows = m.compare_runs_rows(_entry(m, 1, 10), _entry(m, 2, 10, "coastal", True))
    events = [r for r in rows if r["kind"] == "event"]
    assert len(events) == 14
    assert events[-1]["left"] == "(no event)" and events[-1]["different"]
    assert any("(different event)" in r["left"] or "(different event)" in r["right"] for r in events)


def test_a_malformed_event_is_ignored(game_env):
    m = game_env.module
    m.on_past_runs_event(None)
    m.on_past_runs_event(types.SimpleNamespace(target=None))
    m.on_past_runs_event(_event(game_env.elements["past-runs-list"]))  # no data-action
    m.on_past_runs_event(_event(types.SimpleNamespace(getAttribute=lambda n: "evil" if n == "data-run" else "note", value="x")))


def test_the_page_offers_every_scenario_as_a_filter_option():
    m_html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    import re
    options = set(re.findall(r'<option value="scenario:([a-z_]+)">', m_html))
    scenarios = set(re.findall(r'<option value="([a-z_]+)">', m_html.split('id="scenario-select"')[1].split("</select>")[0]))
    assert options == scenarios
