"""R-10: the fastest full playthrough, kept per run and for life."""


def _finish_all(m):
    for planet in m.PLANETS:
        m.planet_state[planet]["terraform_progress"] = m.TERRAFORM_MAX


def test_not_set_until_a_run_finishes(game_env):
    m = game_env.module
    assert m.best_run_ticks is None
    assert "not yet" in m.best_run_text()
    m._note_full_completion()
    assert m.best_run_ticks is None and m.run_completed is False


def test_first_finish_records_the_run_length(game_env):
    m = game_env.module
    _finish_all(m)
    m.total_ticks = 6000
    m._note_full_completion()
    assert m.run_completed is True and m.best_run_ticks == 6000
    assert m.best_run_text() == m._format_duration(6000 * (m.TICK_INTERVAL_MS / 1000))
    m.total_ticks = 9000
    m._note_full_completion()
    assert m.best_run_ticks == 6000  # recorded once per run


def test_a_later_run_is_measured_from_its_own_start_and_only_a_faster_one_wins(game_env):
    m = game_env.module
    _finish_all(m)
    m.total_ticks = 6000
    m._note_full_completion()
    m.run_start_tick, m.run_completed = 6000, False  # what a prestige does
    m.total_ticks = 8000
    m._note_full_completion()
    assert m.best_run_ticks == 2000
    m.run_start_tick, m.run_completed = 8000, False
    m.total_ticks = 20000
    m._note_full_completion()
    assert m.best_run_ticks == 2000  # a slower run never replaces it


def test_shows_in_the_stats_panel(game_env):
    m = game_env.module
    m.best_run_ticks = 600
    game_env.toggle_stats()
    texts = []

    def walk(node):
        texts.append(node.innerText)
        for child in node.children:
            walk(child)

    walk(game_env.elements["stats-panel-content"])
    assert any(t.startswith("Fastest full playthrough:") and "not yet" not in t for t in texts)


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    state = m.get_state()
    assert not [k for k in state if k in ("run_start_tick", "run_completed", "best_run_ticks")]
    m.run_start_tick, m.run_completed, m.best_run_ticks = 500, True, 1200
    saved = m.get_state()
    m.run_start_tick, m.run_completed, m.best_run_ticks = 0, False, None
    m.load_state(saved)
    assert (m.run_start_tick, m.run_completed, m.best_run_ticks) == (500, True, 1200)
    for bad in (True, -1, 2.5, "9", None, 10 ** 15):
        m.load_state({**saved, "run_start_tick": bad, "best_run_ticks": bad, "run_completed": "yes"})
        assert (m.run_start_tick, m.run_completed, m.best_run_ticks) == (0, False, None)
