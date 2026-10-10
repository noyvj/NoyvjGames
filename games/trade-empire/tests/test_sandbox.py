"""Z-18: Trade Empire's practice sandbox. The rules under test: entering and leaving never changes the real
corporation (get_state() is byte-identical, including every running table), a save made while the sandbox is
on is the real game, nothing in the sandbox earns an achievement or opens a story chapter, the balance cannot
run out, every system and route is open, and nothing can be lost to hazards or renewal."""
import json
import sys
import types
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "pc.html"]


def dump(data):
    return json.dumps(data, sort_keys=True)


def play_real_game(env, ticks=150):
    """A real corporation with plenty of history: research, a bought ship, automation, trade, tables full."""
    m = env.module
    m.total_profit = 6000
    m.research_points = 400.0
    for node in ("automation_slot", "galaxy_expansion", "fast_ships"):
        env.unlock_research(node)
    env.purchase_ship("5")
    env.rename_ship("1", "Wanderer")
    env.load()
    env.depart("verdant")
    env.tick(8)
    env.load()
    env.depart("ferrum")
    env.tick(8)
    env.automate("2")
    m.buy_stockpile("ore")
    m.build_trade_post()
    env.tick(ticks)
    return m


def test_it_starts_off(game_env):
    m = game_env.module
    assert m.sandbox_is_active() is False
    assert m.sandbox_leave() is True


def test_enter_then_leave_leaves_get_state_byte_identical(game_env):
    m = play_real_game(game_env)
    before = dump(m.get_state())
    assert m.get_state()["market_multiplier"] and m.get_state()["unlocked_research"], "the real game has history"
    assert m.sandbox_enter() is True
    assert m.sandbox_is_active() is True
    assert m.sandbox_leave() is True
    assert m.sandbox_is_active() is False
    assert dump(m.get_state()) == before


def test_playing_hard_in_the_sandbox_never_reaches_the_real_corporation(game_env):
    m = play_real_game(game_env)
    before = dump(m.get_state())
    m.sandbox_enter()
    for _ in range(4):
        game_env.load("1")
        game_env.depart("kepler_a", "1") if "kepler_a" in m.active_colony_ids() else game_env.depart("verdant", "1")
        game_env.tick(10)
    m.buy_stockpile("grain")
    m.build_trade_post()
    game_env.tick(250)
    m.seasonal_demand_enabled = True
    m.sandbox_leave()
    assert dump(m.get_state()) == before


def test_leaving_a_second_time_after_another_visit_is_still_identical(game_env):
    m = play_real_game(game_env, ticks=40)
    before = dump(m.get_state())
    for _ in range(3):
        m.sandbox_enter()
        game_env.tick(60)
        m.sandbox_leave()
        assert dump(m.get_state()) == before


def test_the_real_corporation_does_not_run_while_the_sandbox_is_on(game_env):
    m = play_real_game(game_env, ticks=20)
    before = dump(m.get_state())
    m.sandbox_enter()
    game_env.tick(100)
    assert dump(m.get_state()) == before
    m.sandbox_leave()
    assert dump(m.get_state()) == before


def test_a_save_made_in_the_sandbox_restores_the_real_game_not_the_sandbox(game_env):
    m = play_real_game(game_env)
    real_sales = m.total_sales_count
    real_research = sorted(m.unlocked_research)
    m.sandbox_enter()
    game_env.tick(80)
    saved = json.loads(json.dumps(m.get_state()))
    m.sandbox_leave()
    game_env.tick(60)
    assert m.load_state(saved) is True
    assert m.total_sales_count == real_sales
    assert sorted(m.unlocked_research) == real_research
    assert len(m.unlocked_research) < len(m.RESEARCH_NODES)


def test_loading_a_save_while_in_the_sandbox_leaves_it_and_lands_in_the_real_game(game_env):
    m = play_real_game(game_env, ticks=30)
    saved = json.loads(json.dumps(m.get_state()))
    syncs = []
    sys.modules["js"].window = types.SimpleNamespace(
        NoyvjSandbox=types.SimpleNamespace(sync=lambda: syncs.append(m.sandbox_active)))
    try:
        m.sandbox_enter()
        game_env.tick(5)
        assert m.load_state(saved) is True
        assert m.sandbox_is_active() is False
        assert dump(m.get_state()) == dump(saved)
        assert syncs == [False], "the page script is told so the banner goes away"
    finally:
        del sys.modules["js"].window


def test_every_system_and_route_is_open(game_env):
    m = game_env.module
    assert len(m.unlocked_research) == 0
    m.sandbox_enter()
    assert set(m.unlocked_research) == set(m.RESEARCH_NODES)
    assert set(m.active_colony_ids()) == set(m.ALL_COLONIES)
    assert all(ship.purchased for ship in m.ships.values())
    assert m.max_automated_ships() >= 3


def test_the_balance_cannot_run_out(game_env):
    m = game_env.module
    m.sandbox_enter()
    assert m.total_profit == m.SANDBOX_CREDITS
    assert game_env.elements["profit-display-text"].innerText == "Credits: unlimited (sandbox)"
    for ship_id in ("1", "2", "3", "4"):
        game_env.automate(ship_id)
    for _ in range(4):
        m.build_trade_post()
    m.total_profit = 0           # even a balance forced to zero is topped back up on the next render
    m.render()
    assert m.total_profit >= m.SANDBOX_CREDITS
    game_env.tick(30)
    assert m.total_profit >= m.SANDBOX_CREDITS
    m.sandbox_leave()
    assert game_env.elements["profit-display-text"].innerText.startswith("Total profit")


def test_purchases_that_a_real_new_game_cannot_afford_work_in_the_sandbox(game_env):
    m = game_env.module
    game_env.purchase_ship("6")
    assert m.ships["6"].purchased is False, "control: a fresh real game cannot afford it"
    m.sandbox_enter()
    assert m.ships["6"].purchased is True
    assert m.can_invest_in_colony("aurum")


def test_route_hazards_cannot_be_switched_on(game_env):
    m = game_env.module
    m.sandbox_enter()
    game_env.elements["route-hazards-toggle-button"].dispatch("click", None)
    assert m.route_hazards_enabled is False
    game_env.automate("1")
    game_env.tick(300)
    assert m.disruptions_suffered == 0


def test_a_corporation_cannot_be_renewed_from_the_sandbox(game_env):
    m = game_env.module
    m.sandbox_enter()
    m.endgame_reached = True
    assert m.can_found_new_corporation() is False
    assert m.found_new_corporation() is False
    assert game_env.elements["found-new-corporation-button"].hidden is True
    m.sandbox_leave()
    assert m.endgame_reached is False


def test_nothing_in_the_sandbox_earns_an_achievement_or_a_story_chapter(game_env):
    m = game_env.module
    chapters = []
    sys.modules["js"].window = types.SimpleNamespace(
        NoyvjStory=types.SimpleNamespace(reach=lambda chapter: chapters.append(chapter)))
    try:
        m._story_reach_all({"first_sale"})
        assert chapters, "control: outside the sandbox chapters are reached"
        chapters.clear()
        real_earned = m.achievement_ids_earned()
        m.sandbox_enter()
        game_env.load("1")
        game_env.depart("verdant", "1")
        game_env.tick(60)
        for ship_id in ("1", "2", "3"):
            game_env.automate(ship_id)
        game_env.tick(300)
        assert any(check() for check in m.ACHIEVEMENT_CHECKS.values()), "the sandbox would satisfy checks"
        assert m.achievement_ids_earned() == real_earned
        assert m.get_state()["achievements_earned"] == real_earned
        assert game_env.elements["achievement-toast"].hidden is True
        assert chapters == []
        m.sandbox_leave()
        assert m.achievement_ids_earned() == real_earned
    finally:
        del sys.modules["js"].window


def test_the_real_games_earned_list_is_still_shown_inside_the_sandbox(game_env):
    m = play_real_game(game_env)
    earned = m.achievement_ids_earned()
    assert earned
    m.sandbox_enter()
    game_env.toggle_achievements()
    shown = sorted(entry["id"] for entry in m.achievements_summary() if entry["earned"])
    assert shown == sorted(earned)
    assert m.achievement_ids_earned() == earned


def test_the_running_tables_do_not_leak_between_the_two_games(game_env):
    m = play_real_game(game_env)
    real_recent = {g: list(v) for g, v in m.good_profit_recent.items()}
    assert real_recent
    m.sandbox_enter()
    assert m.good_profit_recent == {} and m.need_history == {}
    assert m.sale_log == [] and m.total_sales_count == 0
    m.sandbox_leave()
    assert m.good_profit_recent == real_recent


@pytest.mark.parametrize("name", PAGES)
def test_both_pages_carry_the_toggle_the_stylesheet_and_the_script(name):
    html = (GAME_DIR / name).read_text(encoding="utf-8")
    assert html.count('id="sandbox-toggle-button"') == 1 and "data-sandbox-toggle" in html
    assert html.count('<link rel="stylesheet" href="../../shared/sandbox-mode.css">') == 1
    assert html.count('<script src="../../shared/sandbox-mode.js" data-game-id="trade-empire"></script>') == 1
    head = html[: html.index("</head>")]
    assert head.index("sandbox-mode.css") < head.index("shared/a11y.css")
    assert html.index("shared/save-widget.js") < html.index("shared/sandbox-mode.js")


def test_the_desktop_menu_lists_the_toggle_under_empire():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    group = [g for g in cfg["toolbar"]["menu"] if g["heading"] == "Empire"][0]
    assert "sandbox-toggle-button" in group["ids"]


def test_the_python_functions_the_shared_script_calls_exist(game_env):
    m = game_env.module
    for name in ("sandbox_enter", "sandbox_leave", "sandbox_is_active"):
        assert callable(getattr(m, name))
