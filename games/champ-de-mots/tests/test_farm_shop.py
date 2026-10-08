"""Farm shop (TODO L-1, the part the owner said yes to on 2026-10-08): coins earned from
watering that unlock cosmetic plot skins. One coin source (a FULL watering), no effect on
scheduling, skins only frame the plot cells."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
STYLE = (GAME_DIR / "style.css").read_text(encoding="utf-8")


def _answer_on_the_farm(module, plot_id):
    module.open_practice(plot_id)
    return module.submit_answer(module.current_question["answer"])


def _open_shop(game_env):
    game_env.elements["shop-toggle-button"].dispatch("click", None)


def _earn(module, count):
    for plot in module.state.plots[:count]:
        module.water_plot(plot)


# --- where coins come from --------------------------------------------------------------


def test_a_full_watering_earns_one_coin_and_nothing_else_does(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[3]
    assert module.coin_balance() == 0
    assert _answer_on_the_farm(module, plot.plot_id) is True
    assert module.coins_state["earned"] == 1
    _answer_on_the_farm(module, plot.plot_id)  # same day: a nudge, no coin
    _answer_on_the_farm(module, plot.plot_id)  # nothing more to add
    assert module.coins_state["earned"] == 1
    other = state.plots[9]
    module.open_practice(other.plot_id)
    module.submit_answer("definitely wrong " + module.current_question["answer"])
    assert module.coins_state["earned"] == 1   # a wrong answer earns nothing
    state.advance_day(plot.interval_days)
    _answer_on_the_farm(module, plot.plot_id)  # a new day waters again
    assert module.coins_state["earned"] == 2


def test_every_plot_linked_activity_pays_the_same_single_coin(game_env):
    module = game_env.module
    plot = module.state.plots[0]
    assert module.water_plot(plot) == module.WATER_FULL
    assert module.coins_state["earned"] == 1
    assert module.water_plot(plot) == module.WATER_NUDGE
    assert module.water_plot(plot) is None
    assert module.coins_state["earned"] == 1
    # a minigame answer goes through the same one function
    module.credit_game_plot_id(module.state.plots[1].plot_id, "blitz")
    assert module.coins_state["earned"] == 2


def test_coins_never_change_how_a_plot_is_scheduled(game_env):
    module = game_env.module
    plot = module.state.plots[2]
    before = (plot.ease_factor, plot.interval_days, plot.next_due)
    module.earn_coins(40)
    assert (plot.ease_factor, plot.interval_days, plot.next_due) == before


def test_the_correct_answer_note_says_a_coin_was_earned(game_env):
    module = game_env.module
    text = module.water_result_text(module.WATER_FULL, module.state.plots[0])
    assert "+1 coin" in text
    assert "coin" not in module.water_result_text(module.WATER_NUDGE)


# --- buying and using skins -------------------------------------------------------------


def test_buying_needs_enough_coins_spends_them_and_equips_the_skin(game_env):
    module = game_env.module
    assert module.buy_skin("clay") == "poor"
    assert module.buy_skin("nope") == "unknown"
    module.earn_coins(20)
    assert module.buy_skin("clay") == "bought"
    assert module.coin_balance() == 5
    assert module.coins_state["owned"] == ["clay"] and module.coins_state["equipped"] == "clay"
    assert module.buy_skin("clay") == "owned"
    assert module.coin_balance() == 5
    assert module.buy_skin("stone") == "poor"


def test_equip_only_owned_skins_and_none_returns_to_plain_plots(game_env):
    module = game_env.module
    assert module.equip_skin("clay") is False
    module.earn_coins(100)
    module.buy_skin("clay")
    module.buy_skin("stone")
    assert module.coins_state["equipped"] == "stone"
    assert module.equip_skin("clay") is True and module.coins_state["equipped"] == "clay"
    assert module.equip_skin("") is True and module.coins_state["equipped"] == ""
    module.render()
    assert game_env.elements["farm"].getAttribute("data-skin") == "none"
    module.equip_skin("clay")
    module.render()
    assert game_env.elements["farm"].getAttribute("data-skin") == "clay"


def test_the_price_list_is_a_climb_the_player_can_finish(game_env):
    module = game_env.module
    prices = [skin[2] for skin in module.PLOT_SKINS]
    assert prices == sorted(prices) and len(set(prices)) == len(prices)
    assert sum(prices) <= 400     # a few days of watering buys the lot
    assert len(module.PLOT_SKINS) == 6


# --- the panel and the readout ---------------------------------------------------------


def test_the_coin_readout_and_shop_panel_say_where_coins_come_from(game_env):
    module = game_env.module
    elements = game_env.elements
    module.render()
    assert elements["coins-display"].innerText == "🪙 0 coins"
    assert elements["shop-panel"].hidden is True
    _open_shop(game_env)
    assert elements["shop-panel"].hidden is False
    assert elements["shop-toggle-button"].innerText == "Close farm shop"
    source = elements["shop-source-line"].innerText
    assert "full watering" in source and "cosmetic only" in source and "Nudges" in source
    assert "0 coins" in elements["shop-coins-line"].innerText.replace("have 0 coin", "0 coins") or "0 coin" in elements["shop-coins-line"].innerText
    assert elements["shop-progress-line"].innerText == "Skins collected: 0 of 6."
    _open_shop(game_env)
    assert elements["shop-panel"].hidden is True


def test_shop_rows_buy_and_use_through_their_buttons(game_env):
    module = game_env.module
    elements = game_env.elements
    module.earn_coins(70)
    _open_shop(game_env)
    rows = elements["shop-list"].children
    assert len(rows) == 1 + len(module.PLOT_SKINS)
    buttons = {}
    for row in rows:
        button = row.children[1]
        buttons[button.id] = button
    assert buttons["shop-use-none-button"].disabled is True        # plain plots are in use
    assert buttons["shop-buy-clay-button"].disabled is False
    assert buttons["shop-buy-lantern-button"].disabled is False     # 60 of 70
    assert buttons["shop-buy-hedge-button"].disabled is True        # 80 needed
    buttons["shop-buy-lantern-button"].dispatch("click", None)
    assert module.coins_state["owned"] == ["lantern"] and module.coin_balance() == 10
    assert game_env.elements["farm"].getAttribute("data-skin") == "lantern"
    buttons = {row.children[1].id: row.children[1] for row in elements["shop-list"].children}
    assert buttons["shop-use-lantern-button"].disabled is True      # in use now
    assert buttons["shop-use-none-button"].disabled is False
    buttons["shop-use-none-button"].dispatch("click", None)
    assert module.coins_state["equipped"] == ""
    assert elements["coins-display"].innerText == "🪙 10 coins"
    assert elements["shop-progress-line"].innerText == "Skins collected: 1 of 6."


# --- saving ----------------------------------------------------------------------------


def test_coins_are_saved_only_once_something_is_earned_and_round_trip(game_env):
    module = game_env.module
    assert "coins" not in module.get_state()
    module.earn_coins(50)
    module.buy_skin("clay")
    module.buy_skin("stone")
    saved = json.loads(json.dumps(module.get_state()))
    assert saved["coins"] == {"earned": 50, "spent": 45, "owned": ["clay", "stone"], "equipped": "stone"}
    module.coins_state.update({"earned": 0, "spent": 0, "owned": [], "equipped": ""})
    module.load_state(saved)
    assert module.coins_state == saved["coins"]
    assert module.coin_balance() == 5


def test_a_hand_edited_coins_record_is_made_safe(game_env):
    module = game_env.module
    blank = {"earned": 0, "spent": 0, "owned": [], "equipped": ""}
    for junk in (None, [], "x", 5, {"earned": "9"}, {"earned": -4, "spent": 2}):
        assert module._validated_coins(junk) == blank or module._validated_coins(junk)["earned"] == 0
    odd = module._validated_coins({
        "earned": 30, "spent": 99, "owned": ["clay", "clay", "dragon", 7, None], "equipped": "stone",
    })
    assert odd == {"earned": 30, "spent": 30, "owned": ["clay"], "equipped": ""}
    assert module._validated_coins({"earned": True, "spent": 1})["earned"] == 0
    assert module._validated_coins({"earned": 12, "owned": ["gilt"], "equipped": "gilt"})["equipped"] == "gilt"


# --- skins are cosmetic only ------------------------------------------------------------


def _skin_css():
    return [line for line in STYLE.splitlines() if "[data-skin" in line]


def test_every_skin_has_its_own_css_and_only_frames_the_cells(game_env):
    module = game_env.module
    css = "\n".join(_skin_css())
    for skin_id, *_ in module.PLOT_SKINS:
        assert f'#farm[data-skin="{skin_id}"] .plot ' in css, skin_id
    for line in _skin_css():
        body = line.split("{", 1)[1] if "{" in line else ""
        # nothing that carries state: not the cell's background, sprite colour or border style
        assert not re.search(r"(^|[; ])background", body), line
        assert "border-style" not in body and "border:" not in body and "border-color" not in body, line
        assert "animation" not in line and "transition" not in line, line
    # the due cue keeps its own inset line when a skin is on
    assert "inset 0 0 0 1px #b9a77f" in "\n".join(_skin_css())


def test_the_shop_is_reachable_on_the_desktop_page():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert ["shop-panel", "shop-toggle-button", "Farm shop"] in cfg["windows"]
    assert any(r[0] == "#coins-display" for r in cfg["readouts"])
    html = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
    for element_id in ("shop-panel", "shop-toggle-button", "shop-close-button", "coins-display", "shop-list"):
        assert f'id="{element_id}"' in html, element_id
