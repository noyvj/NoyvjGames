"""Round-7 pass: Gridley, the dry one-line commentator (GC-19)."""
from .test_career import _play
from .test_round7_trend import _tick


def test_gridley_welcomes_before_the_first_round(game_env):
    game_env.module.render()
    line = game_env.elements["gridley-line"]
    assert line.hidden is False and line.innerText.startswith("Gridley: ")
    assert line.innerText[len("Gridley: "):] in game_env.module.GRIDLEY_LINES["welcome"]


def test_checkbox_turns_gridley_off_and_on(game_env):
    _tick(game_env, "pref-gridley", False)
    assert game_env.elements["gridley-line"].hidden is True and game_env.elements["gridley-line"].innerText == ""
    assert game_env.module.prefs["gridley"] is False
    _tick(game_env, "pref-gridley", True)
    assert game_env.elements["gridley-line"].innerText.startswith("Gridley: ")


def test_every_category_has_lines_and_none_carry_digits_or_emoji(game_env):
    g = game_env.module
    assert set(g.GRIDLEY_LINES) == {"welcome", "brownout", "damage", "aging", "perfect", "short", "clean", "quiet"}
    for category, pool in g.GRIDLEY_LINES.items():
        assert len(pool) >= 3 and len(set(pool)) == len(pool), category
        for line in pool:
            assert not any(ch.isdigit() for ch in line), line
            assert line.isascii() and len(line) < 100, line


def test_categories_follow_the_last_round(game_env):
    g = game_env.module
    s = game_env.state
    assert g.gridley_category() == "welcome"
    s.plant_counts["nuclear"] = 3
    _play(game_env, 1)
    assert g.gridley_category() in ("perfect", "quiet")
    s.last_event = {"type": "brownout", "severity": 0.1, "revenue_loss": 1}
    assert g.gridley_category() == "brownout"
    s.last_event = {"type": "damage", "severity": 0.7, "revenue_loss": 1, "damaged_plant": "coal"}
    assert g.gridley_category() == "damage"
    s.last_event = None
    s.last_aging_event = {"type": "aging_breakdown", "plant": "coal", "repair_cost": 10}
    assert g.gridley_category() == "aging"
    s.last_aging_event = None
    s.last_round_recap["perfect"] = False
    s.plant_counts["nuclear"] = 0
    assert g.gridley_category() == "short"
    s.plant_counts["hydro"] = 5
    s.plant_counts["solar"] = 5
    assert g.gridley_category() == "clean"


def test_the_same_run_gets_the_same_line(game_env):
    g = game_env.module
    game_env.state.plant_counts["nuclear"] = 3
    _play(game_env, 3)
    first = g.gridley_line()
    assert g.gridley_line() == first
    game_env.state.seed = "GRID-BCDFG"
    assert g.gridley_line() in g.GRIDLEY_LINES[g.gridley_category()]


def test_lines_vary_across_rounds(game_env):
    g = game_env.module
    game_env.state.plant_counts["nuclear"] = 5
    seen = set()
    for _ in range(12):
        _play(game_env, 1)
        seen.add(g.gridley_line())
    assert len(seen) >= 2


def test_gridley_never_changes_state_or_the_save(game_env):
    g = game_env.module
    before = g.get_state()
    g.render()
    g.gridley_line()
    assert g.get_state() == before
    assert not any("gridley" in key for key in before)
