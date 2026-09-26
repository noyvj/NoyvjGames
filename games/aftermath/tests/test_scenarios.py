"""E17a: the climate scenario pack (coastal / inland / urban event schedules)."""


def test_four_scenarios_with_classic_as_default(game_env):
    m = game_env.module
    assert set(m.SCENARIOS) == {"classic", "coastal", "inland", "urban"}
    assert m.DEFAULT_SCENARIO == "classic"
    assert m.run.scenario == "classic" and m.run.schedule is m.EVENT_SCHEDULE


def test_every_schedule_is_seven_known_events(game_env):
    m = game_env.module
    for name, spec in m.SCENARIOS.items():
        assert len(spec["schedule"]) == len(m.EVENT_SCHEDULE) == 7, name
        assert all(e in m.EVENT_LABEL for e in spec["schedule"]), name


def test_total_damage_stays_within_about_ten_percent_of_classic(game_env):
    m = game_env.module
    classic = sum(m.EVENT_BASE_DAMAGE[e] for e in m.SCENARIOS["classic"]["schedule"])
    for name, spec in m.SCENARIOS.items():
        total = sum(m.EVENT_BASE_DAMAGE[e] for e in spec["schedule"])
        assert abs(total - classic) / classic <= 0.12, (name, total, classic)


def test_scenarios_differ_in_their_hazard_mix(game_env):
    m = game_env.module

    def count(name, event):
        return m.SCENARIOS[name]["schedule"].count(event)

    assert count("coastal", "storm") > count("classic", "storm")
    assert count("coastal", "flood") >= 2
    assert count("inland", "heatwave") > count("classic", "heatwave")
    assert count("urban", "infrastructure_failure") > count("classic", "infrastructure_failure")
    assert count("urban", "civil_unrest") > count("classic", "civil_unrest")
    assert len({tuple(s["schedule"]) for s in m.SCENARIOS.values()}) == 4


def test_a_run_follows_its_scenarios_schedule(game_env):
    m = game_env.module
    r = m.RunState(scenario="coastal")
    assert r.schedule == m.SCENARIOS["coastal"]["schedule"]
    assert r.scenario == "coastal"
    assert r.schedule[0] == "flood"


def test_unknown_scenario_falls_back_to_classic(game_env):
    m = game_env.module
    for bad in ("bogus", None, 3, ["coastal"], ""):
        assert m.RunState(scenario=bad).scenario == "classic"


def test_extended_doubles_the_chosen_scenario(game_env):
    m = game_env.module
    r = m.RunState(scenario="urban", extended=True)
    assert r.schedule == m.SCENARIOS["urban"]["schedule"] * 2


def test_selector_before_the_first_event_swaps_the_current_run(game_env):
    m = game_env.module
    game_env.elements["scenario-select"].value = "inland"
    game_env.elements["scenario-select"].dispatch("change", None)
    assert m.run.scenario == "inland" and m.run.event_index == 0
    assert m.run.schedule == m.SCENARIOS["inland"]["schedule"]


def test_selector_is_ignored_once_a_run_is_underway(game_env):
    m = game_env.module
    game_env.elements["resolve-event-button"].dispatch("click", None)
    assert m.run.event_index == 1
    before = m.run.schedule
    game_env.elements["scenario-select"].value = "urban"
    game_env.elements["scenario-select"].dispatch("change", None)
    assert m.run.scenario == "classic" and m.run.schedule is before


def test_selector_visibility_follows_the_run_state(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["scenario-wrapper"].hidden is False  # before the first event
    game_env.elements["resolve-event-button"].dispatch("click", None)
    assert game_env.elements["scenario-wrapper"].hidden is True  # mid-run
    for _ in range(len(m.run.schedule)):
        if not m.run.is_complete():
            game_env.elements["resolve-event-button"].dispatch("click", None)
    assert game_env.elements["scenario-wrapper"].hidden is False  # run complete


def test_new_run_reads_the_selected_scenario(game_env):
    m = game_env.module
    for _ in range(len(m.run.schedule)):
        game_env.elements["resolve-event-button"].dispatch("click", None)
    assert m.run.is_complete()
    game_env.elements["scenario-select"].value = "coastal"
    game_env.elements["new-run-button"].dispatch("click", None)
    assert m.run.scenario == "coastal" and m.run.event_index == 0


def test_blurb_tracks_the_selection(game_env):
    game_env.elements["scenario-select"].value = "coastal"
    game_env.elements["scenario-select"].dispatch("change", None)
    assert "Storm surge" in game_env.elements["scenario-blurb"].innerText


def test_save_round_trip_and_default_omits_key(game_env):
    m = game_env.module
    assert "scenario" not in m.get_state()
    game_env.elements["scenario-select"].value = "urban"
    game_env.elements["scenario-select"].dispatch("change", None)
    data = m.get_state()
    assert data["scenario"] == "urban"
    m.run = m.RunState()
    m.load_state(data)
    assert m.run.scenario == "urban" and m.run.schedule == m.SCENARIOS["urban"]["schedule"]


def test_load_rejects_bad_scenario_values(game_env):
    m = game_env.module
    for bad in ("bogus", 7, None, ["urban"], {"a": 1}):
        data = m.get_state()
        data["scenario"] = bad
        m.load_state(data)
        assert m.run.scenario == "classic"
