"""Batch A #5: the "recently completed" strip."""

from .helpers import all_text, click, find_all, known_state


def _part_row(game_env, name):
    return next(r for r in game_env.elements["components-body"].children if r.attributes.get("data-part") == name)


def test_finishing_a_part_by_typing_is_recorded_with_the_date(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}})
    m._now_stamp = lambda: "2026-09-27 10:00"
    row = _part_row(game_env, "Rahn Prism")
    owned = find_all(row, tag="input", class_name="owned-input")[0]
    owned.value = "1"
    owned.dispatch("change", None)
    assert m.state["completed"] == [{"n": "Rahn Prism", "d": "2026-09-27"}]
    strip = game_env.elements["recent-completed"]
    assert strip.hidden is False and "Rahn Prism (2026-09-27)" in all_text(strip)


def test_the_build_button_records_completion_only_when_it_finishes(game_env):
    m = game_env.module
    inv = {n: {"built": q} for n, q in m.MANUFACTURING_RECIPES["Rahn Prism"].items()}
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 2}}, inventory={k: {"built": v["built"] * 2} for k, v in inv.items()})
    m._now_stamp = lambda: "2026-09-27 10:00"
    row = _part_row(game_env, "Rahn Prism")
    click(find_all(row, tag="button", class_name="build-btn")[0])
    assert m.state["completed"] == []  # 1 of 2: not finished
    click(find_all(_part_row(game_env, "Rahn Prism"), tag="button", class_name="build-btn")[0])
    assert m.state["completed"] == [{"n": "Rahn Prism", "d": "2026-09-27"}]


def test_only_the_last_five_are_kept_and_repeats_move_to_the_end(game_env):
    m = game_env.module
    known_state(m)
    m._now_stamp = lambda: "2026-09-27 10:00"
    for name in ("Raplak Prism", "Shwaak Prism", "Granmu Prism", "Rahn Prism", "Cantic Prism", "Lega Prism"):
        m.state["parts"][name]["owned"] = 0
        before = m.completion_snapshot()
        m.state["parts"][name]["owned"] = 1
        m.record_completions(before)
    assert [e["n"] for e in m.state["completed"]] == ["Shwaak Prism", "Granmu Prism", "Rahn Prism", "Cantic Prism", "Lega Prism"]
    before = m.completion_snapshot()
    m.state["parts"]["Rahn Prism"]["owned"] = 0
    m.state["parts"]["Rahn Prism"]["owned"] = 1
    assert m.record_completions(before) == []  # nothing newly finished


def test_a_finished_combo_is_recorded(game_env):
    m = game_env.module
    known_state(m)
    m.add_combo("Duo", ["Rahn Prism", "Lega Prism"])
    m.state["parts"]["Rahn Prism"]["owned"] = 0
    before = m.completion_snapshot()
    assert "Duo" not in before
    m.state["parts"]["Rahn Prism"]["owned"] = 1
    m._now_stamp = lambda: "2026-09-27 10:00"
    assert m.record_completions(before) == ["Duo", "Rahn Prism"]


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "completed" not in m.get_state()
    m.state["completed"] = [{"n": "Rahn Prism", "d": "2026-09-27"}]
    saved = m.get_state()
    m.state["completed"] = []
    m.load_state(saved)
    assert m.state["completed"] == [{"n": "Rahn Prism", "d": "2026-09-27"}]
    m.load_state({"completed": [
        {"n": "Nope", "d": "2026-09-27"}, {"n": "Rahn Prism", "d": "2026-13-40"}, {"n": "Rahn Prism", "d": "x"},
        {"n": ["l"], "d": "2026-09-27"}, "junk", {"n": "177", "d": "2026-01-02"},
    ]})
    assert m.state["completed"] == [{"n": "177", "d": "2026-01-02"}]
    m.load_state({"completed": 3})
    assert m.state["completed"] == []
