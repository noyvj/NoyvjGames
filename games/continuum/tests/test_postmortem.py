"""K-14 -- the post-mortem report (postmortem.py) and its panel.

Built from the livability-vs-population record, the per-season stat history and
the Council Minutes. The engine tests drive a bare Campaign through real seasons
(no DOM); the panel tests drive the game module through the fake DOM."""

import copy
import json

import minutes
import postmortem
import save
import sim
import statlog
import sustainability
import trajectory


def _season(c):
    effects = c.tree.effects()
    report = c.state.advance_season(effects)
    c.state.record_score(sustainability.score(c.state, effects))
    trajectory.record(c.state, report, sustainability.livability(c.state, effects) * 100.0)
    statlog.record(c.ui, c.state, effects, report, len(c.tree.researched))
    return report


def _starving_run(minute_entries=True):
    """A settlement that is fed, then has everyone moved off food work."""
    c = save.Campaign()
    s = c.state
    for _ in range(6):
        _season(c)
    if minute_entries:
        minutes.record(c.ui, "build", "a Shelter", s.era, s.season)
    s.resources["food"] = 0.0
    s.allocation["foragers"] = 0
    for _ in range(4):
        _season(c)
    return c


def test_a_fresh_settlement_is_not_ready():
    c = save.Campaign()
    report = postmortem.build(c)
    assert report["ready"] is False
    assert report["notes"] and "Play at least" in report["notes"][0]
    assert postmortem.lines(report)[0] == "Post-mortem"


def test_two_seasons_is_still_not_ready():
    c = save.Campaign()
    _season(c)
    _season(c)
    assert postmortem.build(c)["ready"] is False


def test_the_biggest_drop_is_found_and_its_cause_named():
    c = _starving_run()
    report = postmortem.build(c)
    assert report["ready"] is True
    block = report["root_cause"]
    assert "Livability fell" in block["headline"]
    assert block["cause"] == "fed_pct"
    text = " ".join(block["lines"])
    assert "food security" in text.lower()
    assert "gathered" in text and "needed" in text


def test_the_decisions_before_the_drop_come_back_with_a_prompt():
    c = _starving_run()
    report = postmortem.build(c)
    assert report["redo"], "the minuted build before the drop should be offered"
    item = report["redo"][0]
    assert "a Shelter" in item["decision"]
    assert "food for everyone" in item["hint"]
    assert len(report["redo"]) <= postmortem.REDO_COUNT


def test_only_the_last_three_decisions_before_the_pivot_are_offered():
    c = save.Campaign()
    for i in range(6):
        _season(c)
        minutes.record(c.ui, "research", f"Discovery {i}", c.state.era, c.state.season - 1)
    c.state.allocation["foragers"] = 0
    c.state.resources["food"] = 0.0
    for _ in range(3):
        _season(c)
    redo = postmortem.build(c)["redo"]
    assert len(redo) == 3
    assert all("Discovery" in r["decision"] for r in redo)
    assert "Discovery 5" in redo[0]["decision"]  # newest first


def test_decisions_made_after_the_drop_are_not_blamed():
    c = _starving_run(minute_entries=False)
    minutes.record(c.ui, "build", "a Granary", c.state.era, c.state.season + 50)
    redo = postmortem.build(c)["redo"]
    assert all("Granary" not in r["decision"] for r in redo)


def test_with_no_minutes_the_report_says_so_instead_of_inventing_decisions():
    c = _starving_run(minute_entries=False)
    report = postmortem.build(c)
    assert report["redo"] == []
    assert any("No decisions were minuted" in n for n in report["notes"])


def test_a_calm_run_reports_no_major_drop():
    c = save.Campaign()
    for _ in range(6):
        _season(c)
    report = postmortem.build(c)
    assert report["ready"] is True
    assert "No major livability drop" in report["root_cause"]["headline"]
    assert report["root_cause"]["cause"] is None


def test_what_went_wrong_names_the_hunger_and_what_went_well_stays_honest():
    c = _starving_run()
    report = postmortem.build(c)
    assert any("were lost" in line for line in report["went_wrong"]) or any(
        "dropped as low as" in line for line in report["went_wrong"]
    )
    for line in report["went_well"] + report["went_wrong"]:
        assert isinstance(line, str) and line
    assert len(report["went_well"]) <= postmortem.MAX_LINES
    assert len(report["went_wrong"]) <= postmortem.MAX_LINES


def test_without_stat_history_an_old_save_still_gets_a_report():
    c = _starving_run()
    c.ui.pop(statlog.KEY)
    report = postmortem.build(c)
    assert report["ready"] is True
    assert report["root_cause"]["cause"] is None
    assert any("no per-season stat history" in n for n in report["notes"])


def test_hostile_ui_values_never_raise():
    c = _starving_run()
    for junk in (None, 5, "x", [1, 2], {"a": 1}, True):
        c.ui[statlog.KEY] = junk
        c.ui[minutes.KEY] = junk
        postmortem.build(c)
        postmortem.lines(postmortem.build(c))
    c.state.trajectory = [[float("nan")] * 4, "x", None]
    assert postmortem.build(c)["ready"] is False


def test_the_report_changes_nothing():
    c = _starving_run()
    before = copy.deepcopy(c.to_dict())
    postmortem.build(c)
    assert c.to_dict() == before


def test_a_look_back_reports_on_the_real_forward_progress():
    c = _starving_run()
    live = postmortem.build(c)
    c.state.era = "tribal"
    c.era_snapshots["tribal"] = save.snapshot_of(save.Campaign().state, c.tree)
    # park the real progress, as enter_revisit does, then look at a blank early snapshot
    c.parked_state = save.snapshot_of(c.state, c.tree)
    c.revisiting = "tribal"
    fresh = save.Campaign()
    save.restore_city(c.state, fresh.to_dict()["current_state"]["city"])
    during = postmortem.build(c)
    assert during["ready"] is True
    assert during["root_cause"]["headline"] == live["root_cause"]["headline"]


def test_when_formats_a_season_as_year_and_season():
    assert postmortem.when(1) == "Year 1, Spring"
    assert postmortem.when(6) == "Year 2, Summer"
    assert postmortem.when(0) == "Year 1, Spring"


def test_biggest_drop_handles_short_series():
    assert postmortem.biggest_drop([]) is None
    assert postmortem.biggest_drop([(1, 90.0, 6)]) is None
    drop = postmortem.biggest_drop([(1, 90.0, 6), (2, 80.0, 6), (3, 40.0, 6)])
    assert drop == (40.0, 2)


def test_every_line_of_the_text_form_is_a_nonempty_string():
    c = _starving_run()
    for line in postmortem.lines(postmortem.build(c)):
        assert isinstance(line, str) and line.strip()
    assert postmortem.lines(None) == []


# --- the panel ------------------------------------------------------------
def test_the_panel_starts_closed_and_opens_from_the_summary(game_env):
    m = game_env.module
    assert game_env.elements["postmortem-panel"].hidden is True
    game_env.elements["summary-toggle-button"].dispatch("click", None)
    button = game_env.elements["postmortem-open-button"]
    assert button.innerText == "Open a post-mortem report"
    button.dispatch("click", None)
    assert m.postmortem_open is True
    assert game_env.elements["postmortem-panel"].hidden is False
    assert game_env.elements["postmortem-open-button"].innerText == "Close the post-mortem report"


def test_the_panel_explains_when_there_is_nothing_to_look_back_on(game_env):
    game_env.elements["summary-toggle-button"].dispatch("click", None)
    game_env.elements["postmortem-open-button"].dispatch("click", None)
    panel = game_env.elements["postmortem-panel"]
    texts = [c.innerText for c in panel.children]
    assert any("Play at least" in t for t in texts)


def test_the_panel_shows_all_four_sections_after_a_run(game_env):
    m = game_env.module
    game_env.advance_season(5)
    m.state.allocation["foragers"] = 0
    m.state.resources["food"] = 0.0
    game_env.advance_season(4)
    game_env.elements["summary-toggle-button"].dispatch("click", None)
    game_env.elements["postmortem-open-button"].dispatch("click", None)
    panel = game_env.elements["postmortem-panel"]
    headings = [c.innerText for c in panel.children if c.className == "summary-eras-heading"]
    assert headings == [
        "What went well",
        "What went wrong",
        "Root cause of the biggest livability drop",
        "Three decisions to redo",
    ]


def test_the_close_button_and_the_hidden_toggle_both_close_it(game_env):
    m = game_env.module
    game_env.elements["postmortem-toggle-button"].dispatch("click", None)
    assert m.postmortem_open is True
    game_env.elements["postmortem-close-button"].dispatch("click", None)
    assert m.postmortem_open is False
    assert game_env.elements["postmortem-panel"].hidden is True


def test_the_panel_survives_a_render_and_a_season(game_env):
    m = game_env.module
    game_env.elements["postmortem-toggle-button"].dispatch("click", None)
    game_env.advance_season(4)
    assert m.postmortem_open is True
    assert game_env.elements["postmortem-panel"].hidden is False


def test_the_open_flag_is_never_saved(game_env):
    game_env.elements["postmortem-toggle-button"].dispatch("click", None)
    data = json.loads(json.dumps(game_env.module.get_state()))
    assert "postmortem" not in json.dumps(data["ui"]).lower()
    game_env.module.load_state(data)
    assert game_env.elements["postmortem-panel"].hidden is False  # a display flag, not game state: stays as the session had it


def test_every_catalogued_cause_has_a_label_and_a_need():
    for key, (name, need) in postmortem.CAUSES.items():
        assert key in statlog.COLUMN_KEYS and name and need
    assert sim.FOOD_PER_PERSON > 0
