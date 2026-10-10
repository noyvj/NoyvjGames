"""Z-18: Continuum's practice sandbox. The rules under test: entering and leaving never changes the real
settlement (get_state() is byte-identical and the very same objects come back), a save made while the
sandbox is on is the real game, nothing in the sandbox earns an achievement, writes browser storage or posts
a score, and the sandbox settlement cannot collapse whatever (or however little) the player does."""
import json
import sys
import types
from pathlib import Path

import pytest

import dynasty
import sandbox
import sim
import sustainability

from . import test_challengerun as challenge_tests

GAME_DIR = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "pc.html"]


def dump(data):
    return json.dumps(data, sort_keys=True)


def play_real_game(env, seasons=6):
    """A real settlement with some history: work, builds, a discovery, a name, a few seasons."""
    m = env.module
    env.assign("foragers", 1)
    env.assign("gatherers", 1)
    env.build("shelter")
    m.state.resources["knowledge"] = 500.0
    first = m.tree.available_nodes()[0]
    assert m.tree.research(first.node_id, m.state.resources)
    m.campaign.ui["settlement_name"] = "Ashford"
    env.advance_season(seasons)
    return m


def choose_era(env, value):
    env.elements["sandbox-era-select"].value = value


def test_it_starts_off(game_env):
    m = game_env.module
    assert m.sandbox_is_active() is False
    assert m.sandbox_leave() is True


def test_enter_then_leave_leaves_get_state_byte_identical_and_the_same_objects(game_env):
    m = play_real_game(game_env)
    before = dump(m.get_state())
    real = (m.campaign, m.state, m.tree, m.chronicle)
    assert m.sandbox_enter() is True
    assert m.sandbox_is_active() is True
    assert m.campaign is not real[0] and m.state is not real[1] and m.tree is not real[2]
    assert m.sandbox_leave() is True
    assert (m.campaign, m.state, m.tree, m.chronicle) == real
    assert all(a is b for a, b in zip((m.campaign, m.state, m.tree, m.chronicle), real))
    assert dump(m.get_state()) == before


def test_playing_hard_in_the_sandbox_never_reaches_the_real_settlement(game_env):
    m = play_real_game(game_env)
    before = dump(m.get_state())
    ui_before = json.dumps(m.campaign.ui, sort_keys=True)
    choose_era(game_env, "industrial")
    m.sandbox_enter()
    for building in sim.buildings_for_era("industrial"):
        game_env.build(building)
    for role in sim.roles_for_era("industrial"):
        game_env.assign(role, 1)
    game_env.advance_season(30)
    m.campaign.ui["settlement_name"] = "Throwaway"
    m.info_page_open = not m.info_page_open
    m.set_speed(4)
    m.sandbox_leave()
    assert dump(m.get_state()) == before
    assert json.dumps(m.campaign.ui, sort_keys=True) == ui_before
    assert m.sim_speed == 0, "the real game comes back paused"


def test_get_state_while_in_the_sandbox_is_the_real_game(game_env):
    m = play_real_game(game_env)
    before = dump(m.get_state())
    m.sandbox_enter()
    game_env.advance_season(5)
    assert dump(m.get_state()) == before
    assert m.get_state()["current_state"]["city"]["season"] != m.state.season


def test_a_save_made_in_the_sandbox_restores_the_real_game_not_the_sandbox(game_env):
    m = play_real_game(game_env)
    real_season = m.state.season
    m.sandbox_enter()
    game_env.advance_season(9)
    saved = json.loads(json.dumps(m.get_state()))
    m.sandbox_leave()
    game_env.advance_season(3)
    assert m.state.season == real_season + 3
    assert m.load_state(saved) is True
    assert m.state.season == real_season
    assert m.campaign.ui.get("settlement_name") == "Ashford"
    assert len(m.tree.researched) == 1, "the real game's own research, not the sandbox's all-known tree"


def test_loading_a_save_while_in_the_sandbox_leaves_it_and_lands_in_the_real_game(game_env):
    m = play_real_game(game_env)
    saved = json.loads(json.dumps(m.get_state()))
    syncs = []
    sys.modules["js"].window = types.SimpleNamespace(
        NoyvjSandbox=types.SimpleNamespace(sync=lambda: syncs.append(m.sandbox_active)))
    try:
        m.sandbox_enter()
        game_env.advance_season(2)
        assert m.load_state(saved) is True
        assert m.sandbox_is_active() is False
        assert dump(m.get_state()) == dump(saved)
        assert syncs == [False], "the page script is told so the banner goes away"
    finally:
        del sys.modules["js"].window


def test_every_discovery_is_known_in_the_sandbox_only(game_env):
    m = game_env.module
    m.sandbox_enter()
    assert sorted(m.tree.researched) == sorted(m.tree.nodes)
    m.sandbox_leave()
    assert len(m.tree.researched) == 0


def test_the_era_is_chosen_in_settings_or_defaults_to_the_current_one(game_env):
    m = game_env.module
    choose_era(game_env, "current")
    m.sandbox_enter()
    assert m.state.era == "tribal"
    m.sandbox_leave()
    for era in sim.ERA_ORDER:
        choose_era(game_env, era)
        m.sandbox_enter()
        assert m.state.era == era and m.campaign.furthest_era == era and m.tree.current_era == era
        assert m.state.population >= sandbox.MIN_PEOPLE
        m.sandbox_leave()
    choose_era(game_env, "nonsense")
    m.sandbox_enter()
    assert m.state.era == "tribal"


@pytest.mark.parametrize("era", sim.ERA_ORDER)
def test_an_idle_sandbox_settlement_never_collapses(game_env, era):
    m = game_env.module
    choose_era(game_env, era)
    m.sandbox_enter()
    low_scores = 0
    for _ in range(90):
        game_env.advance_season()
        assert m.state.population >= sandbox.MIN_PEOPLE
        assert m.state.resources["food"] >= 0
        assert not dynasty.is_collapsed(m.state)
        score = m.state.score_history[-1]
        low_scores = low_scores + 1 if score < sim.SCORE_COLLAPSE_THRESHOLD else 0
        assert low_scores < 3
    assert sustainability.score_label(m.state.score_history[-1]) != "Collapsing"


@pytest.mark.parametrize("era", ["tribal", "industrial", "relay"])
def test_reckless_play_cannot_collapse_it_either(game_env, era):
    m = game_env.module
    choose_era(game_env, era)
    m.sandbox_enter()
    for _ in range(60):
        # everyone to the dirtiest job, no sanitation, no planning, no shelter beyond the floor
        worst = "factory_workers" if era != "tribal" else "foragers"
        m.state.allocation[worst] = m.state.population
        m.state.clamp_allocation()
        game_env.advance_season()
        assert not dynasty.is_collapsed(m.state)
        assert m.state.population >= sandbox.MIN_PEOPLE


def test_resources_are_not_binding(game_env):
    m = game_env.module
    choose_era(game_env, "space")
    m.sandbox_enter()
    for building in sim.buildings_for_era("space"):
        for _ in range(8):
            before = m.state.buildings[building]
            game_env.build(building)
            assert m.state.buildings[building] == before + 1, f"could not afford {building}"
    game_env.advance_season(5)
    assert m.state.resources["materials"] >= sandbox.MATERIALS_FLOOR
    assert m.state.resources["tools"] >= sandbox.TOOLS_FLOOR
    assert m.state.resources["knowledge"] >= sandbox.KNOWLEDGE_FLOOR


def test_the_same_neglect_does_collapse_a_real_settlement(game_env):
    """The control: the sandbox, not the setup, is what removes the failure."""
    m = game_env.module
    m.state.land_health = 0.05
    m.state.resources["food"] = 0.0
    for key in m.state.allocation:
        m.state.allocation[key] = 0
    game_env.advance_season(60)
    assert m.state.population < sandbox.MIN_PEOPLE or dynasty.is_collapsed(m.state)


def test_nothing_in_the_sandbox_earns_an_achievement(game_env):
    m = game_env.module
    real_earned = m.achievement_ids_earned()
    choose_era(game_env, "relay")
    m.sandbox_enter()
    assert any(check() for key, check in m.ACHIEVEMENT_CHECKS.items() if key.startswith("reached_")), \
        "the sandbox settlement would satisfy checks"
    game_env.advance_season(10)
    assert m.achievement_ids_earned() == real_earned
    assert m.get_state()["achievements_earned"] == real_earned
    assert game_env.elements["achievement-toast"].hidden is True
    m.sandbox_leave()
    assert m.achievement_ids_earned() == real_earned


def test_the_real_games_earned_list_is_still_shown_inside_the_sandbox(game_env):
    m = game_env.module
    earned = m.achievement_ids_earned()
    assert earned
    m.sandbox_enter()
    game_env.elements["achievements-toggle-button"].dispatch("click", None)
    assert f"({len(earned)}/" in game_env.elements["achievements-toggle-button"].innerText


class Store:
    def __init__(self):
        self.data = {}
        self.writes = []

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        self.writes.append(key)
        self.data[key] = value


def test_the_sandbox_writes_no_browser_storage(game_env):
    m = play_real_game(game_env)
    store = Store()
    sys.modules["js"].window = types.SimpleNamespace(localStorage=store)
    try:
        assert m.archive_store([]) is True and store.writes, "control: outside the sandbox the archive is stored"
        store.writes.clear()
        choose_era(game_env, "digital")
        m.sandbox_enter()
        game_env.advance_season(12)
        assert m.archive_store([]) is False
        m._dynasty_local_store()
        assert m.challenge_ledger_store([]) is False
        assert m.beyond_ladder_store([]) is False
        game_env.elements["found-settlement-button"].dispatch("click", None)
        m.found_new_settlement()
        game_env.elements["dynasty-bank-button"].dispatch("click", None)
        m._bank_if_collapsed()
        assert store.writes == []
        assert "switched off in the sandbox" in game_env.elements["found-settlement-status"].innerText
        assert m.campaign.ui.get("settlement_name") is None, "nothing was founded or reset"
    finally:
        del sys.modules["js"].window


def _daily_record():
    """A started daily's saved record, made the way the game makes it (on a throwaway fresh campaign)."""
    import save

    fresh = save.Campaign()
    cr = challenge_tests.cr
    assert cr.start(fresh, None, "daily", cr.daily("2026-10-08")["config"], "SEED", "2026-10-08")
    return json.loads(json.dumps(fresh.ui[cr.KEY]))


def test_challenge_runs_cannot_be_started_in_the_sandbox(game_env):
    m = game_env.module
    cr = challenge_tests.cr
    m.sandbox_enter()
    assert cr.can_start(m.campaign) is False, "every discovery is known, so this is not a fresh start"
    game_env.elements["challenge-toggle-button"].dispatch("click", None)
    game_env.elements["challenge-daily-start-button"].dispatch("click", None)
    assert cr.get(m.campaign.ui) is None


def test_finishing_a_daily_posts_and_stores_nothing_from_the_sandbox(game_env):
    """Belt and braces: even a forged run record in the sandbox reports to nothing."""
    m = game_env.module
    cr = challenge_tests.cr
    record = _daily_record()
    result = {"points": 500, "seasons": 40}

    def finish():
        reports, marks, store = [], [], Store()
        window = challenge_tests._daily_window({"today": "2026-10-08"}, reports)
        window.NoyvjSeed.daily.markCompleted = lambda game, info: marks.append(game)
        window.localStorage = store
        sys.modules["js"].window = window
        try:
            m.campaign.ui[cr.KEY] = dict(record)
            m._finish_challenge_run(result)
        finally:
            del sys.modules["js"].window
        return reports, marks, store.writes

    reports, marks, writes = finish()
    assert reports and marks and writes, "control: a real daily is posted, marked and stored"
    m.sandbox_enter()
    assert finish() == ([], [], [])


def test_the_clock_is_paused_on_entering_and_again_on_return(game_env):
    m = game_env.module
    m.set_speed(2)
    m.season_progress = 3.5
    m.sandbox_enter()
    assert m.sim_speed == 0 and m.season_progress == 0.0
    m.set_speed(4)
    m.sandbox_leave()
    assert m.sim_speed == 0
    assert m.season_progress == 3.5


def test_the_sandbox_can_move_through_eras(game_env):
    m = game_env.module
    choose_era(game_env, "tribal")
    m.sandbox_enter()
    assert m.state.era == "tribal"
    m.state.population = 400
    m.state.buildings["shelter"] = 80
    game_env.advance_season(3)
    game_env.elements["advance-era-button"].dispatch("click", None)
    assert m.state.era == "agrarian"
    assert m.achievement_ids_earned() == m._sandbox_real["earned"], "reaching an era in the sandbox earns nothing"
    m.sandbox_leave()
    assert m.state.era == "tribal"


@pytest.mark.parametrize("name", PAGES)
def test_both_pages_carry_the_toggle_the_era_select_the_stylesheet_and_the_script(name):
    html = (GAME_DIR / name).read_text(encoding="utf-8")
    assert html.count('id="sandbox-toggle-button"') == 1 and "data-sandbox-toggle" in html
    assert html.count('id="sandbox-era-select"') == 1
    assert html.count('<link rel="stylesheet" href="../../shared/sandbox-mode.css">') == 1
    assert html.count('<script src="../../shared/sandbox-mode.js" data-game-id="continuum"></script>') == 1
    head = html[: html.index("</head>")]
    assert head.index("sandbox-mode.css") < head.index("shared/a11y.css")
    assert html.index("shared/save-widget.js") < html.index("shared/sandbox-mode.js")
    assert '"sandbox.py"' in html


def test_the_settings_window_holds_the_toggle_on_the_desktop_boot():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert ["settings-panel", "settings-toggle-button", "Settings"] in [list(w) for w in cfg["windows"]]
    html = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
    assert 'id="sandbox-toggle-button"' in html[html.index('id="settings-panel"'):html.index('id="achievement-toast"')]


def test_the_python_functions_the_shared_script_calls_exist(game_env):
    m = game_env.module
    for name in ("sandbox_enter", "sandbox_leave", "sandbox_is_active"):
        assert callable(getattr(m, name))
