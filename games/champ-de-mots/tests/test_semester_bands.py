"""LM-1: the farm shows FREN151 and FREN152 as two visibly separate semester bands over ONE continuous
sequence. The bands are only a wrapper: rows, review order, unlock chain and the save do not change, and a
collapsed band is a per-browser preference, never part of the save."""

import sys
import types
from pathlib import Path

HTML = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def _rows_in(env, element_id):
    return [c.id for c in env.elements[element_id].children]


def _display_rows(env):
    return [e.id for e in env.elements["farm"].descendants() if e.id and e.id.startswith("row-") and e.id[4:].isdigit()]


def _fake_window(store):
    window = types.SimpleNamespace(
        champPrefGet=lambda key: store.get(key),
        champPrefSet=lambda key, value: store.__setitem__(key, value),
    )
    sys.modules["js"].window = window
    return window


def test_two_bands_read_from_the_rows_own_course(game_env):
    bands = game_env.module.semester_bands()
    assert [b["course"] for b in bands] == ["FREN151", "FREN152"]
    assert [b["name"] for b in bands] == ["Semester 1", "Semester 2"]
    assert bands[0]["sequences"] == list(range(1, 12))
    assert bands[1]["sequences"] == list(range(12, 24))
    assert bands[0]["heading"] == "Semester 1 · FREN151"
    assert game_env.elements["semester-title-2"].innerText == "Semester 2 · FREN152"
    assert "12 weeks" in game_env.elements["semester-sub-2"].innerText


def test_every_week_sits_in_its_own_band_in_one_continuous_order(game_env):
    assert _rows_in(game_env, "semester-rows-1") == [f"row-{n}" for n in range(1, 12)]
    assert _rows_in(game_env, "semester-rows-2") == [f"row-{n}" for n in range(12, 24)]
    assert _display_rows(game_env) == [f"row-{n}" for n in range(1, 24)]
    assert [r.sequence for r in game_env.state.rows] == list(range(1, 24))


def test_each_band_has_a_heading_a_progress_line_a_meter_and_a_toggle(game_env):
    for i in (1, 2):
        for part in ("title", "sub", "progress", "meter", "bar", "toggle", "rows"):
            assert f"semester-{part}-{i}" in game_env.elements
        toggle = game_env.elements[f"semester-toggle-{i}"]
        assert toggle.innerText == "Hide weeks"
        assert toggle.getAttribute("aria-expanded") == "true"
        assert toggle.getAttribute("aria-controls") == f"semester-rows-{i}"
    assert game_env.elements["semester-title-1"].tagName == "H2"


def test_progress_line_counts_only_its_own_semester(game_env):
    module, state = game_env.module, game_env.state
    first = game_env.elements["semester-progress-1"].innerText
    assert "weeks open" in first and "plots growing" in first
    plot = state.row_plots(1)[0]
    state.review(plot.plot_id, True)
    module.render()
    assert game_env.elements["semester-progress-1"].innerText != first
    assert "0 of" in game_env.elements["semester-progress-2"].innerText.split("plots growing")[0].split("·")[-1]
    stats1 = module.semester_stats(module.semester_bands()[0])
    stats2 = module.semester_stats(module.semester_bands()[1])
    assert stats1["growing"] == 1 and stats2["growing"] == 0
    assert stats1["total"] + stats2["total"] == len(state.plots)
    assert game_env.elements["semester-bar-1"].style.width != "0.0%"
    assert game_env.elements["semester-bar-2"].style.width == "0.0%"


def test_summary_lists_both_semesters(game_env):
    chips = [c.innerText for c in game_env.elements["semester-summary"].children]
    assert len(chips) == 2
    assert chips[0].startswith("Semester 1 · FREN151") and chips[1].startswith("Semester 2 · FREN152")


def test_collapse_hides_only_that_bands_weeks_and_expand_restores_them(game_env):
    module = game_env.module
    game_env.elements["semester-toggle-1"].dispatch("click", None)
    assert game_env.elements["semester-rows-1"].hidden is True
    assert game_env.elements["semester-rows-2"].hidden is False
    toggle = game_env.elements["semester-toggle-1"]
    assert toggle.innerText == "Show weeks" and toggle.getAttribute("aria-expanded") == "false"
    assert "semester--collapsed" in game_env.elements["semester-1"].className
    toggle.dispatch("click", None)
    assert game_env.elements["semester-rows-1"].hidden is False
    assert toggle.innerText == "Hide weeks"
    assert module.semester_collapsed == set()


def test_collapsed_state_is_a_browser_preference_not_part_of_the_save(game_env):
    module = game_env.module
    store = {}
    _fake_window(store)
    before = module.get_state()
    module.toggle_semester("FREN151")
    assert store["champ-semesters-collapsed"] == "FREN151"
    assert module.get_state() == before
    assert "semester" not in repr(module.get_state()).lower()
    # a later visit reads it back
    module.semester_collapsed.clear()
    module._load_semester_prefs()
    assert module.semester_collapsed == {"FREN151"}
    store["champ-semesters-collapsed"] = "FREN151,NOPE,FREN152"
    module._load_semester_prefs()
    assert module.semester_collapsed == {"FREN151", "FREN152"}
    store["champ-semesters-collapsed"] = "garbage"
    module._load_semester_prefs()
    assert module.semester_collapsed == set()


def test_an_unknown_course_cannot_be_toggled(game_env):
    assert game_env.module.toggle_semester("FREN999") is False
    assert game_env.module.semester_collapsed == set()


def test_old_saves_load_unchanged(game_env):
    module, state = game_env.module, game_env.state
    plot = state.row_plots(3)[0]
    state.review(plot.plot_id, True)
    saved = module.get_state()
    module.load_state(saved)
    assert module.get_state() == saved
    assert [r.sequence for r in state.rows] == list(range(1, 24))
    old_style = {"version": 1, "current_day": 2, "plots": {}}
    assert module.load_state(old_style) is True
    assert module.state.current_day == 2


def test_other_sorts_mix_the_semesters_so_the_bands_step_aside(game_env):
    module = game_env.module
    module.set_farm_sort("weakest")
    assert game_env.elements["semester-1"].hidden and game_env.elements["semester-2"].hidden
    farm_children = [c.id for c in game_env.elements["farm"].children]
    assert all(f"row-{n}" in farm_children for n in range(1, 24))
    note = [c.innerText for c in game_env.elements["semester-summary"].children]
    assert any("Sorted view" in text for text in note)
    module.set_farm_sort("syllabus")
    assert not game_env.elements["semester-1"].hidden and not game_env.elements["semester-2"].hidden
    assert _rows_in(game_env, "semester-rows-2") == [f"row-{n}" for n in range(12, 24)]
    assert not any("Sorted view" in c.innerText for c in game_env.elements["semester-summary"].children)


def test_a_filter_that_empties_a_band_hides_the_whole_band(game_env):
    module, state = game_env.module, game_env.state
    plot = state.row_plots(1)[0]
    state.review(plot.plot_id, False)
    state.plots_by_id[plot.plot_id].in_weeds = True
    module.set_farm_filter("weeds")
    assert not game_env.elements["semester-1"].hidden
    assert game_env.elements["semester-2"].hidden
    module.set_farm_filter("all")
    assert not game_env.elements["semester-2"].hidden


def test_collapsing_does_not_change_scheduling(game_env):
    module, state = game_env.module, game_env.state
    due_before = [p.plot_id for p in state.due_plots()]
    module.toggle_semester("FREN152")
    module.set_farm_sort("weakest")
    module.set_farm_sort("syllabus")
    assert [p.plot_id for p in state.due_plots()] == due_before


def test_markup_has_the_summary_and_css_has_the_band_rules_without_motion():
    assert 'id="semester-summary"' in HTML
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    block = css[css.index("LM-1: semester bands"):]
    for needle in (".semester-head", ".semester-rows", ".semester + .semester"):
        assert needle in block
    assert "transition" not in block and "animation" not in block
    pc = (Path(__file__).resolve().parent.parent / "pc.css").read_text(encoding="utf-8")
    assert "grid-column: 1 / -1" in pc[pc.index("LM-1"):]


def test_slides_topics_land_in_the_semester_two_band_and_the_band_counts_them(game_env):
    """LM-3: the topics added from the FREN152 slides (ids containing -fs) sit in rows 12 to 23, so they fall in
    the FREN152 band without any band-specific code, and the band's totals include their plots."""
    m = game_env.module
    fs_plots = [p for p in game_env.state.plots if "-fs" in p.plot_id]
    assert fs_plots, "the slides content should be in the farm"
    assert all(p.sequence >= 12 for p in fs_plots)
    bands = {b["course"]: b for b in m.semester_bands()}
    assert set(p.sequence for p in fs_plots) <= set(bands["FREN152"]["sequences"])
    in_band = [p for p in game_env.state.plots if p.sequence in bands["FREN152"]["sequences"]]
    assert set(fs_plots) <= set(in_band)
    assert not (set(p.sequence for p in fs_plots) & set(bands["FREN151"]["sequences"]))
