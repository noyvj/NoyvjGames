"""GE-21: the closing line on the run summary."""


def _texts(el):
    out = [el.innerText]
    for child in el.children:
        out.extend(_texts(child))
    return out


def _finish(game_env, resilience=0, growth=0):
    m = game_env.module
    m.run.resilience_capacity += resilience
    m.run.growth_capacity += growth
    for _ in range(len(m.run.schedule)):
        game_env.resolve_event()
    return m.run


def _epitaphs(game_env):
    panel = game_env.elements["run-summary-panel"]
    return [c.innerText for c in panel.children if c.className == "run-epitaph"]


def test_every_bucket_has_a_real_bank(game_env):
    m = game_env.module
    assert set(m.EPITAPHS) == {"ruin", "flawless", "rich", "resilience", "growth", "steady"}
    assert sum(len(v) for v in m.EPITAPHS.values()) >= 36
    for lines in m.EPITAPHS.values():
        assert len(set(lines)) == len(lines) and all(line.strip() for line in lines)


def test_hard_run_lines_stay_gentle(game_env):
    m = game_env.module
    harsh = ("fail", "lose", "loser", "dead", "died", "death", "worst", "pathetic", "terrible", "ruined", "deserve")
    for line in m.EPITAPHS["ruin"]:
        assert not any(word in line.lower() for word in harsh), line


def test_the_bucket_follows_the_outcome(game_env):
    m = game_env.module
    r = m.RunState()
    r.resources = 0.0
    assert m.epitaph_kind(r) == "ruin"
    r.resources = 5.0
    assert m.epitaph_kind(r) == "ruin"  # at or below the very-bad score
    r.resources = 300.0
    assert m.epitaph_kind(r) == "rich"
    r.resources = 150.0
    r.resilience_capacity = 4
    assert m.epitaph_kind(r) == "resilience"
    r.resilience_capacity, r.growth_capacity = 0, 4
    assert m.epitaph_kind(r) == "growth"
    r.growth_capacity = 0
    assert m.epitaph_kind(r) == "steady"
    r.event_log = [{"type": "flood", "damage": 1.0, "severity": 1.0}]
    assert m.epitaph_kind(r) == "flawless"


def test_the_line_is_deterministic_and_comes_from_the_right_bank(game_env):
    m = game_env.module
    r = m.RunState(run_number=4)
    r.resources = 0.0
    first = m.epitaph_text(r)
    assert first == m.epitaph_text(r) and first in m.EPITAPHS["ruin"]


def test_a_scenario_line_replaces_every_third_non_ruinous_run(game_env):
    m = game_env.module
    r = m.RunState(run_number=3, scenario="heat_season")
    r.resources = 150.0
    assert m.epitaph_text(r) == m.SCENARIO_EPITAPHS["heat_season"]
    r.resources = 0.0
    assert m.epitaph_text(r) in m.EPITAPHS["ruin"]
    r2 = m.RunState(run_number=4, scenario="heat_season")
    r2.resources = 150.0
    assert m.epitaph_text(r2) in sum(m.EPITAPHS.values(), [])


def test_the_summary_shows_one_line_after_a_finished_run(game_env):
    _finish(game_env)
    lines = _epitaphs(game_env)
    assert len(lines) == 1 and lines[0]
    game_env.module.render()
    assert _epitaphs(game_env) == lines  # stable across renders


def test_no_line_mid_run_and_none_when_hidden(game_env):
    m = game_env.module
    game_env.resolve_event()
    assert game_env.elements["run-summary-panel"].hidden is True
    m.localStorage.setItem(m.HIDE_EPITAPH_STORAGE_KEY, "true")
    _finish(game_env)
    assert _epitaphs(game_env) == []
    m.localStorage.setItem(m.HIDE_EPITAPH_STORAGE_KEY, "false")
    m.render()
    assert len(_epitaphs(game_env)) == 1


def test_the_line_changes_no_number(game_env):
    m = game_env.module
    run = _finish(game_env)
    assert run.run_score() == m.run.resources and m.run_history[-1] == run.run_score()
