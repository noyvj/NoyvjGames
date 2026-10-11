"""R-33 (the parked K30): the "another settlement" ghost (peers.py, game.py's peer_* functions, peers.js
wiring in both pages). The backend half is app/ghosts.py (tested in app/tests/test_ghosts.py).

The browser half (the Settings switch and the two network buttons) is covered by test_peers_browser.py."""

import json
import re
import sys
import types
from pathlib import Path

import pytest

import peers
import sim
import statlog

GAME_DIR = Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parent.parent


def history_rows(n=8, era="agrarian", people=10, score=60.0, start=1):
    rows = []
    for i in range(n):
        values = {key: 0.0 for key in statlog.COLUMN_KEYS}
        values.update(season=float(start + i), era=float(sim.era_index(era)), population=float(people + i), score=score + i)
        rows.append(statlog._row_from(values))
    return rows


def ghost_series(n=10, era=2, people=20, score=50.0, start=1):
    return [[start + i, era, people + i, score + i] for i in range(n)]


def make_ghost(series=None, ghost_id="0b1c2d3e-aaaa-bbbb-cccc-1234567890ab"):
    return {"id": ghost_id, "scenario": "standard", "hard": False, "era": 2, "seasons": 10,
            "series": series if series is not None else ghost_series()}


# ---------------------------------------------------------------- the publish payload

def test_payload_has_exactly_the_documented_keys_and_only_numbers_in_the_series():
    payload = peers.publish_payload(history_rows(), "standard", False)
    assert set(payload) == {"game", "scenario", "hard", "series", "opt_in"}
    assert payload["game"] == "continuum" and payload["opt_in"] is True and payload["hard"] is False
    assert len(payload["series"]) == 8
    for row in payload["series"]:
        assert len(row) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in row)
        assert isinstance(row[0], int) and isinstance(row[1], int) and isinstance(row[2], int)


def test_payload_is_none_until_enough_seasons_exist():
    assert peers.publish_payload(history_rows(peers.MIN_SEASONS - 1), "standard", False) is None
    assert peers.publish_payload([], "standard", False) is None
    assert peers.publish_payload(history_rows(peers.MIN_SEASONS), "standard", False) is not None
    assert peers.publish_json(history_rows(2), "standard", False) == ""


def test_payload_is_capped_at_the_servers_maximum():
    rows = history_rows(120)
    assert len(peers.my_series(rows)) == 120 <= peers.MAX_SEASONS


def test_the_series_matches_the_stat_history_values():
    payload = peers.publish_payload(history_rows(6, era="medieval", people=30, score=71.26), "frontier", True)
    first = payload["series"][0]
    assert first == [1, sim.era_index("medieval"), 30, 71.3]
    assert payload["scenario"] == "frontier" and payload["hard"] is True


def test_peers_bounds_match_the_backend_registration():
    source = (ROOT / "app" / "ghosts.py").read_text(encoding="utf-8")
    match = re.search(r'register_ghost_game\("continuum", min_seasons=(\d+), max_seasons=(\d+), max_era=(\d+)\)', source)
    assert match, "app/ghosts.py no longer registers continuum"
    assert (peers.MIN_SEASONS, peers.MAX_SEASONS, peers.ERA_TOP) == tuple(int(x) for x in match.groups())
    assert peers.ERA_TOP == len(sim.ERA_ORDER) - 1


def test_publish_schedule_first_time_then_every_few_seasons_or_on_an_era_change():
    short, enough = history_rows(3), history_rows(6)
    assert peers.due_to_publish(short, None, -1) is False
    assert peers.due_to_publish(enough, None, -1) is True                      # first time past the minimum
    era = sim.era_index("agrarian")
    assert peers.due_to_publish(enough, 6, era) is False                       # just sent this one
    assert peers.due_to_publish(history_rows(10), 6, era) is False             # 4 seasons on: not yet
    assert peers.due_to_publish(history_rows(11), 6, era) is True              # 5 seasons on
    assert peers.due_to_publish(enough, 6, era - 1) is True                    # the era changed
    assert peers.due_to_publish(history_rows(3, start=1) + history_rows(6, start=4), 90, era) is True  # a fresh settlement


def test_peer_query_asks_for_the_players_own_band_and_clamps_the_era():
    assert peers.peer_query(3, "standard", False) == {"scenario": "standard", "era": 3, "hard": False}
    assert peers.peer_query(99, "frontier", True, "abc")["era"] == peers.ERA_TOP
    assert peers.peer_query(-4, "standard", False)["era"] == 0
    assert peers.peer_query("x", "standard", False)["era"] == 0
    assert "exclude" not in peers.peer_query(1, "standard", False, "")
    assert peers.peer_query(1, "standard", False, "id-1")["exclude"] == "id-1"


# ---------------------------------------------------------------- reading a ghost

def test_clean_ghost_accepts_a_real_one_as_a_dict_or_a_json_string():
    ghost = make_ghost()
    for raw in (ghost, json.dumps(ghost)):
        cleaned = peers.clean_ghost(raw)
        assert cleaned["id"] == ghost["id"] and len(cleaned["series"]) == 10
        assert set(cleaned) == {"id", "series"}      # nothing else from the server is kept


@pytest.mark.parametrize("mutate", [
    lambda g: g.update(series="nope"),
    lambda g: g.update(series=[]),
    lambda g: g.update(series=[[1, 2, 3]]),
    lambda g: g.update(series=[[1, 2, 3, "x"]]),
    lambda g: g.update(series=[[1, 2, 3, True]]),
    lambda g: g.update(series=[[1, 2, 3, float("nan")]]),
    lambda g: g.update(series=[[2, 1, 5, 50.0], [1, 1, 5, 50.0]]),     # seasons not increasing
    lambda g: g.update(series=[[1, 9, 5, 50.0]]),                       # era out of range
    lambda g: g.update(series=[[1, 1, -5, 50.0]]),
    lambda g: g.update(series=[[1, 1, 5, 150.0]]),
    lambda g: g.update(series=[[1.5, 1, 5, 50.0]]),
    lambda g: g.update(series=ghost_series(peers.MAX_SEASONS + 1)),
    lambda g: g.update(id=7),
    lambda g: g.update(id="x"),
    lambda g: g.pop("id"),
])
def test_clean_ghost_refuses_anything_malformed(mutate):
    ghost = make_ghost()
    mutate(ghost)
    assert peers.clean_ghost(ghost) is None


def test_clean_ghost_refuses_garbage_input():
    for raw in (None, 5, [], "not json", "[1, 2]", "{}", '{"series": 4}'):
        assert peers.clean_ghost(raw) is None


# ---------------------------------------------------------------- the maths and the words

def test_row_at_finds_the_latest_row_at_or_before_a_season():
    series = ghost_series(5, start=3)       # seasons 3 to 7
    assert peers.row_at(series, 2) is None
    assert peers.row_at(series, 3)[0] == 3
    assert peers.row_at(series, 5)[0] == 5
    assert peers.row_at(series, 99)[0] == 7


def test_comparison_line_for_the_same_season_names_both_sides():
    mine = [[s, 2, 20 + s, 40.0 + s] for s in range(1, 31)]
    mine[-1] = [30, 2, 38, 57.0]
    theirs = [[s, 2, 20 + s, 40.0 + s] for s in range(1, 41)]
    theirs[29] = [30, 2, 41, 62.0]
    assert peers.comparison_line(mine, theirs) == (
        "At season 30 they had 41 people and a score of 62; you have 38 people and a score of 57."
    )


def test_comparison_line_when_the_other_record_is_shorter_reads_yours_at_the_same_season():
    mine = [[s, 2, 30, 50.0] for s in range(1, 41)]
    theirs = ghost_series(24)
    line = peers.comparison_line(mine, theirs)
    assert line.startswith("Their record ends at season 24, when they had")
    assert "at that season you had 30 people and a score of 50" in line


def test_comparison_line_handles_one_person_empty_and_no_overlap():
    mine = [[1, 0, 1, 50.0]]
    assert "1 person and a score of 50" in peers.comparison_line(mine, [[1, 0, 1, 50.0]])
    assert peers.comparison_line([], ghost_series()) == "Advance a season to compare your settlement with this one."
    assert peers.comparison_line(mine, None) == ""
    assert "do not overlap" in peers.comparison_line([[1, 0, 5, 50.0]], ghost_series(5, start=40))


def test_comparison_line_never_ranks_or_judges():
    text = peers.comparison_line([[10, 2, 38, 57.0]], ghost_series(30))
    for word in ("better", "worse", "ahead", "behind", "winning", "losing", "rank", "beat"):
        assert word not in text.lower()


def test_text_equivalent_states_the_numbers_for_both_lines():
    mine = [[s, 2, 20, 40.0 + s] for s in range(1, 11)]
    text = peers.text_equivalent(mine, ghost_series(12), "score")
    assert "dashed" in text and "solid" in text
    assert "12 seasons" in text and "10 seasons" in text
    assert "peaking at 61" in text and "peaking at 50" in text
    assert "people" in peers.text_equivalent(mine, ghost_series(12), "people").lower()
    assert peers.text_equivalent(mine, None, "score") == ""


def test_compare_svg_draws_both_lines_with_a_dashed_ghost_and_a_text_label():
    mine = [[s, 2, 20 + s, 40.0 + s] for s in range(1, 11)]
    svg = peers.compare_svg(mine, ghost_series(15), "score")
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "peer-line--ghost" in svg and "peer-line--mine" in svg
    assert 'role="img"' in svg and "another settlement, anonymous (dashed line)" in svg
    assert svg.count("<polyline") == 2 and svg.count("<circle") == 2
    # every plotted coordinate stays inside the drawing
    for x, y in re.findall(r"(\d+\.\d),(\d+\.\d)", svg):
        assert 0 <= float(x) <= peers.CHART_W and 0 <= float(y) <= peers.CHART_H


def test_compare_svg_people_metric_scales_to_the_data_and_handles_edge_cases():
    big = [[s, 3, 5000 + s, 50.0] for s in range(1, 8)]
    svg = peers.compare_svg(big, big, "people")
    assert "5" in svg and svg.count("<polyline") == 2
    assert peers.compare_svg([], [[1, 0, 5, 50.0]], "score").count("<polyline") == 0     # one point: a dot, no line
    assert peers.compare_svg([], [[1, 0, 5, 50.0]], "score").count("<circle") == 1
    assert peers.compare_svg([[1, 0, 5, 50.0]], None, "score") == ""
    assert peers.compare_svg([[1, 0, 5, 50.0]], ghost_series(), "bogus") == ""


def test_messages_are_plain_and_never_blame_the_player():
    assert "Not enough players" in peers.message("too_few")
    assert "No shared settlement is close" in peers.message("no_match")
    assert "not available right now" in peers.message("unavailable")
    assert peers.message("whatever") == peers.UNAVAILABLE_TEXT
    assert "not saved" in peers.message("shown")


# ---------------------------------------------------------------- inside the game

def _play(game_env, seasons):
    game_env.advance_season(seasons)


def test_a_real_state_produces_a_payload_that_only_holds_numbers(game_env):
    module = game_env.module
    module.campaign.ui["settlement_name"] = "Secret Hollow"
    module.campaign.ui["founders_log"] = [{"season": 1, "text": "my private note"}]
    _play(game_env, 6)
    plan = module.peer_publish_plan()
    assert plan, "six played seasons should be shareable"
    payload = json.loads(plan)
    assert set(payload) == {"game", "scenario", "hard", "series", "opt_in"}
    assert payload["scenario"] == module.state.scenario and payload["hard"] == module.state.hard_mode
    assert len(payload["series"]) == 6
    assert "Secret Hollow" not in plan and "private note" not in plan
    assert [row[0] for row in payload["series"]] == [1, 2, 3, 4, 5, 6]


def test_nothing_is_offered_before_enough_seasons(game_env):
    _play(game_env, peers.MIN_SEASONS - 1)
    assert game_env.module.peer_publish_plan() == ""


def test_the_schedule_follows_the_last_sent_season(game_env):
    module = game_env.module
    _play(game_env, 6)
    assert module.peer_publish_plan(-1, -1)
    era = sim.era_index(module.state.era)
    assert module.peer_publish_plan(6, era) == ""
    _play(game_env, 5)
    assert module.peer_publish_plan(6, era)


def test_the_sandbox_a_look_back_and_challenge_runs_are_never_shared(game_env):
    module = game_env.module
    _play(game_env, 6)
    assert module.peer_publish_plan()
    module.campaign.revisiting = "tribal"
    assert module.peer_publish_plan() == ""
    module.campaign.revisiting = None
    module.campaign.ui["challenge_run"] = {"anything": 1}
    # a (valid or not) challenge entry may be cleaned away; what matters is that _resting decides it
    module._resting = lambda: True
    assert module.peer_publish_plan() == ""
    module._resting = lambda: False
    module.sandbox_active = True
    assert module.peer_publish_plan() == ""


def test_peer_query_json_names_the_players_band_and_the_ghost_on_screen(game_env):
    module = game_env.module
    query = json.loads(module.peer_query_json())
    assert query == {"scenario": "standard", "era": 0, "hard": False}
    module.peer_show(json.dumps(make_ghost()))
    assert json.loads(module.peer_query_json(module.peer_ghost_id()))["exclude"] == make_ghost()["id"]


def test_showing_a_ghost_draws_the_chart_the_sentence_and_the_text(game_env):
    module, elements = game_env.module, game_env.elements
    _play(game_env, 8)
    assert elements["peer-graph"].innerHTML == "" and elements["peer-legend"].hidden is True
    assert module.peer_show(json.dumps(make_ghost())) is True
    assert "peer-line--ghost" in elements["peer-graph"].innerHTML
    assert elements["peer-summary"].innerText.startswith("At season 8 they had")
    assert "dashed" in elements["peer-text"].innerText
    for element_id in ("peer-legend", "peer-hide-button", "peer-report-button", "peer-metric-button"):
        assert elements[element_id].hidden is False, element_id
    assert module.peer_ghost_id() == make_ghost()["id"]


def test_the_chart_follows_the_players_progress_season_by_season(game_env):
    module, elements = game_env.module, game_env.elements
    _play(game_env, 6)
    module.peer_show(json.dumps(make_ghost()))
    first = elements["peer-summary"].innerText
    _play(game_env, 2)
    assert elements["peer-summary"].innerText != first
    assert "season 8" in elements["peer-summary"].innerText


def test_an_invalid_ghost_is_refused_and_nothing_is_shown(game_env):
    module, elements = game_env.module, game_env.elements
    assert module.peer_show("not json") is False
    assert module.peer_show(json.dumps({"id": "abcdefgh12", "series": [[1, 99, 5, 5]]})) is False
    assert module.peer_ghost_id() == ""
    assert elements["peer-legend"].hidden is True and elements["peer-graph"].innerHTML == ""


def test_hide_clears_it_and_the_metric_button_switches_the_chart(game_env):
    module, elements = game_env.module, game_env.elements
    _play(game_env, 6)
    module.peer_show(json.dumps(make_ghost()))
    before = elements["peer-graph"].innerHTML
    elements["peer-metric-button"].dispatch("click", None)
    assert elements["peer-graph"].innerHTML != before
    assert "people" in elements["peer-text"].innerText.lower()
    assert elements["peer-metric-button"].innerText.startswith("Chart: people")
    elements["peer-metric-button"].dispatch("click", None)
    assert elements["peer-metric-button"].innerText.startswith("Chart: sustainability score")
    elements["peer-hide-button"].dispatch("click", None)
    assert module.peer_ghost_id() == ""
    assert elements["peer-graph"].innerHTML == "" and elements["peer-legend"].hidden is True
    assert elements["peer-summary"].innerText == ""


def test_showing_a_ghost_changes_nothing_in_the_save(game_env):
    module = game_env.module
    _play(game_env, 6)
    before = json.dumps(module.get_state(), sort_keys=True)
    module.peer_show(json.dumps(make_ghost()))
    module.on_peer_metric()
    after = json.dumps(module.get_state(), sort_keys=True)
    assert before == after
    assert "peer" not in after and make_ghost()["id"] not in after
    module.load_state(json.loads(after))
    assert json.dumps(module.get_state(), sort_keys=True) == after


def test_the_ghost_is_not_shown_for_a_settlement_with_no_history_it_just_waits(game_env):
    module, elements = game_env.module, game_env.elements
    module.peer_show(json.dumps(make_ghost()))
    assert elements["peer-summary"].innerText == "Advance a season to compare your settlement with this one."
    assert "peer-line--ghost" in elements["peer-graph"].innerHTML


def test_a_failing_or_missing_peers_hook_never_breaks_a_season(game_env):
    module = game_env.module
    calls = []

    def boom():
        calls.append(1)
        raise RuntimeError("peers.js blew up")

    window = types.SimpleNamespace(ContinuumPeers=types.SimpleNamespace(seasonDone=boom))
    sys.modules["js"].window = window
    try:
        _play(game_env, 3)
    finally:
        del sys.modules["js"].window
    assert calls == [1, 1, 1]
    assert module.state.season == 4


def test_the_hook_is_called_once_per_completed_season(game_env):
    module = game_env.module
    calls = []
    sys.modules["js"].window = types.SimpleNamespace(ContinuumPeers=types.SimpleNamespace(seasonDone=lambda: calls.append(1)))
    try:
        _play(game_env, 4)
        assert len(calls) == 4
    finally:
        del sys.modules["js"].window


# ---------------------------------------------------------------- the pages (Classic and Desktop boot)

PEER_IDS = ["peer-section", "peer-show-button", "peer-metric-button", "peer-hide-button", "peer-report-button",
            "peer-status", "peer-graph", "peer-legend", "peer-summary", "peer-text", "peer-publish-checkbox",
            "peer-publish-note"]


@pytest.mark.parametrize("page", ["index.html", "pc.html"])
def test_both_pages_carry_every_peer_element_and_load_the_script(page):
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    assert set(PEER_IDS) <= ids
    assert '<script src="peers.js"></script>' in html
    assert '"peers.py"' in html


@pytest.mark.parametrize("page", ["index.html", "pc.html"])
def test_sharing_is_off_and_locked_in_the_markup_by_default(page):
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    tag = re.search(r'<input type="checkbox" id="peer-publish-checkbox"[^>]*>', html).group(0)
    assert "checked" not in tag and "disabled" in tag


def test_the_desktop_boot_shows_the_section_as_a_menu_window():
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    composites = {c["id"]: c for c in config["composites"]}
    assert composites["pc-peer-panel"]["members"] == ["#peer-section"]
    assert composites["pc-peer-panel"]["group"] == "Records"


def test_settings_reset_does_not_touch_the_sharing_switch():
    settings = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert "peer" not in settings.lower()


def test_peers_js_never_reads_the_save_or_sends_anything_but_python_built_numbers():
    js = (GAME_DIR / "peers.js").read_text(encoding="utf-8")
    assert "get_state" not in js and "settlement_name" not in js and "founders" not in js
    # the publish body is the string Python built, and a report carries only an id and a fixed reason
    assert "body: plan" in js
    assert 'reason: "implausible"' in js
