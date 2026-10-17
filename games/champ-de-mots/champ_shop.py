"""The Farm shop panel (skins bought with coins). The coin rules live in champ_watering.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_util import _element
from champ_watering import (
    COIN_SOURCE_TEXT, PLOT_SKINS, apply_skin, buy_skin, coin_balance, coins_earned_today, coins_state,
    coins_text, equip_skin, shop_proxies,
)


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


def _destroy_shop_proxies():
    for proxy in shop_proxies:
        proxy.destroy()
    shop_proxies.clear()


def on_toggle_shop(event=None):
    runstate.shop_open = not runstate.shop_open
    render()


def _make_shop_handler(action, skin_id):
    def handler(event=None):
        if action == "buy":
            buy_skin(skin_id)
        else:
            equip_skin(skin_id)
        apply_skin()
        render()
    return handler


def _shop_row(name, note, button_text, disabled, action, skin_id, button_id):
    line = document.createElement("div")
    line.className = "water-option"
    text = document.createElement("div")
    text.className = "water-option-text dashboard-practice-row"
    title = document.createElement("strong")
    title.innerText = name
    detail = document.createElement("span")
    detail.className = "water-option-count dashboard-practice-row"
    detail.innerText = note
    text.appendChild(title)
    text.appendChild(detail)
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.innerText = button_text
    button.disabled = disabled
    proxy = create_proxy(_make_shop_handler(action, skin_id))
    button.addEventListener("click", proxy)
    shop_proxies.append(proxy)
    line.appendChild(text)
    line.appendChild(button)
    return line


def render_shop():
    toggle = _element("shop-toggle-button")
    panel = _element("shop-panel")
    toggle.innerText = "Close farm shop" if runstate.shop_open else "🪙 Farm shop"
    _element("coins-display").innerText = coins_text()
    _destroy_shop_proxies()
    apply_skin()
    if not runstate.shop_open:
        panel.hidden = True
        return
    panel.hidden = False
    today = coins_earned_today()
    _element("shop-coins-line").innerText = (
        f"You have {coin_balance()} coin{'s' if coin_balance() != 1 else ''} "
        f"({coins_state['earned']} earned in all, {coins_state['spent']} spent). "
        f"Earned today: {today}."
    )
    _element("shop-source-line").innerText = COIN_SOURCE_TEXT
    box = _element("shop-list")
    box.innerHTML = ""
    plain_in_use = not coins_state["equipped"]
    box.appendChild(_shop_row(
        "Plain plots", "The farm's own look.",
        "In use" if plain_in_use else "Use", plain_in_use, "equip", "", "shop-use-none-button",
    ))
    for skin_id, name, price, note in PLOT_SKINS:
        if skin_id in coins_state["owned"]:
            in_use = coins_state["equipped"] == skin_id
            box.appendChild(_shop_row(
                name, f"{note} Owned.", "In use" if in_use else "Use", in_use, "equip", skin_id,
                f"shop-use-{skin_id}-button",
            ))
        else:
            affordable = coin_balance() >= price
            need = "" if affordable else f" {price - coin_balance()} more coins needed."
            box.appendChild(_shop_row(
                name, f"{note} {price} coins.{need}", f"Buy for {price}", not affordable, "buy", skin_id,
                f"shop-buy-{skin_id}-button",
            ))
    owned = len(coins_state["owned"])
    _element("shop-progress-line").innerText = f"Skins collected: {owned} of {len(PLOT_SKINS)}."
