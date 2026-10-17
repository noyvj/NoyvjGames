"""Page renders for run seed, trade posts, route hazards, diplomacy, seasonal demand, market, research, fleet priority and the endgame (with its galaxy canvas)."""

import math

from js import document
from pyodide.ffi import create_proxy

import trade_runstate as runstate
from trade_blackout import blackout_bar_percent, blackout_has, blackout_price_range
from trade_charter import (
    background_revenue_this_tick, background_world_count, charter_points_for_next_renewal,
    hard_charter_unlocked, trade_post_cost, trade_post_income_each,
)
from trade_colony import galaxy_expansion_unlocked
from trade_effects import weather_active_event, weather_multiplier
from trade_founding import can_found_new_corporation, legacy_summary_text
from trade_mapdraw import FLEET_PRIORITY_TARGET_COLOR
from trade_market import (
    DIPLOMACY_THRESHOLDS, INSURANCE_COVERAGE, INSURANCE_PREMIUM_PER_TICK, MARKET_PRICE_RECOVERY_PER_TICK,
    MAX_PRICE_MULTIPLIER, ROUTE_HAZARD_CHANCE, SEASONAL_DEMAND_BONUS, SEASON_LENGTH_TICKS, STOCKPILE_LOT,
    STOCKPILE_SELL_FEE, can_stockpile_buy, current_run_seed, current_sell_price, diplomacy_level,
    diplomacy_multiplier, diplomacy_units_to_next_level, market_multiplier, price_history, price_memory,
    run_seed_changeable, seasonal_multiplier, seasonal_status, set_run_seed, stockpile, stockpile_capacity,
    stockpile_sale_value,
)
from trade_panels_fleet import _trend_sparkline_svg, price_memory_text, render_almanac
from trade_research import RESEARCH_NODES, can_unlock_research, research_node_blocked_by
from trade_rules import GOOD_LABEL
from trade_ships import (
    automation_is_maxed, build_trade_post, can_build_trade_post, next_trade_post_system,
    trade_post_income_per_tick, trade_posts,
)


def on_toggle_seasonal_demand(event=None):
    runstate.seasonal_demand_enabled = not runstate.seasonal_demand_enabled
    render_market()


def on_toggle_route_hazards(event=None):
    if runstate.sandbox_active:  # Z-18: no lost cargo in the sandbox
        runstate.route_hazards_enabled = False
        render_market()
        return
    runstate.route_hazards_enabled = not runstate.route_hazards_enabled
    render_market()


def on_toggle_route_insurance(event=None):
    runstate.route_insurance_enabled = not runstate.route_insurance_enabled
    render_market()


def _copy_text(text):
    """Best effort clipboard write (a browser may refuse; the note then shows the text to copy by hand)."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy

        clipboard = getattr(getattr(js, "navigator", None), "clipboard", None)
        if clipboard is None:
            return False
        clipboard.writeText(text)
        return True
    except Exception:  # noqa: BLE001
        return False


def on_apply_run_seed(event=None):
    field = document.getElementById("run-seed-input")
    ok, runstate.run_seed_message = set_run_seed(field.value or "")
    if ok:
        field.value = ""
    render_market()


def on_copy_run_seed(event=None):
    seed_text = current_run_seed()
    if _copy_text(seed_text):
        runstate.run_seed_message = f"Copied {seed_text}."
    else:
        runstate.run_seed_message = f"Your browser would not copy it. The seed is {seed_text}: select it above and copy it."
    render_market()


def render_run_seed():
    """Z-1b: the run seed, a Copy seed button and a start-from-seed field."""
    display = document.getElementById("run-seed-display")
    if display is None:
        return
    seed_text = current_run_seed()
    display.innerText = f"Run seed: {seed_text}"
    changeable = run_seed_changeable()
    document.getElementById("run-seed-input").disabled = not changeable
    document.getElementById("run-seed-apply-button").disabled = not changeable
    note = document.getElementById("run-seed-note")
    locked = "This seed has been used, so it is fixed for the run."
    if changeable:
        note.innerText = runstate.run_seed_message or (
            "Optional: type a shared seed to get the same route hazards, guild contracts and "
            "founding conditions. It can be changed until one of them has used it."
        )
    else:
        note.innerText = f"{runstate.run_seed_message} {locked}" if runstate.run_seed_message else locked
    try:
        import js  # noqa: PLC0415 -- Pyodide-only: lets the shared info footer show the seed

        window = getattr(js, "window", None)
        if window is not None:
            window.NOYVJ_SEED = seed_text
    except Exception:  # noqa: BLE001
        pass


def on_build_trade_post(event=None):
    build_trade_post()
    render_market()


def render_trade_post():
    button = document.getElementById("trade-post-button")
    status = document.getElementById("trade-post-status")
    if button is None or status is None:
        return
    show = automation_is_maxed() or bool(trade_posts)
    button.hidden = not show
    status.hidden = not show
    if not show:
        return
    target = next_trade_post_system()
    button.innerText = f"Establish trade post ({trade_post_cost()})" if target else "All trade posts established"
    button.disabled = not can_build_trade_post()
    button.title = (
        f"Build a post in the {target}: +{trade_post_income_each()} credits per tick, no ship needed."
        if target else "Every reachable system already has a trade post."
    )
    posts = ", ".join(trade_posts) if trade_posts else "none yet"
    status.innerText = (
        f"Trade posts: {posts} (+{trade_post_income_per_tick()} credits per tick). "
        f"Available once every automation slot is in use; one per system."
    )


def render_route_hazards():
    hazards_button = document.getElementById("route-hazards-toggle-button")
    insurance_button = document.getElementById("route-insurance-toggle-button")
    status = document.getElementById("route-hazards-status")
    if hazards_button is None or insurance_button is None or status is None:
        return
    hazards_button.innerText = f"Route hazards: {'on' if runstate.route_hazards_enabled else 'off'}"
    insurance_button.innerText = f"Route insurance: {'on' if runstate.route_insurance_enabled else 'off'}"
    insurance_button.disabled = not runstate.route_hazards_enabled
    if not runstate.route_hazards_enabled:
        status.innerText = (
            f"Optional: with hazards on, {int(ROUTE_HAZARD_CHANCE * 100)}% of loaded arrivals are disrupted "
            "and the cargo is lost. Insurance is then available."
        )
        return
    line = (
        f"Hazards on: {int(ROUTE_HAZARD_CHANCE * 100)}% of loaded arrivals are disrupted. "
        f"Insurance costs {INSURANCE_PREMIUM_PER_TICK} credit per ship in transit per tick and refunds "
        f"{int(INSURANCE_COVERAGE * 100)}% of a lost trip. "
    )
    line += f"So far: {runstate.disruptions_suffered} disrupted, {runstate.insurance_payouts} paid out, {runstate.premiums_paid} in premiums."
    status.innerText = line


def render_diplomacy():
    status = document.getElementById("diplomacy-status")
    if status is None:
        return
    if not galaxy_expansion_unlocked():
        status.hidden = True
        return
    status.hidden = False
    level = diplomacy_level()
    to_next = diplomacy_units_to_next_level()
    bonus = int(round((diplomacy_multiplier() - 1.0) * 100))
    line = f"Diplomatic relations: level {level} of {len(DIPLOMACY_THRESHOLDS)} (+{bonus}% on every sale)."
    line += f" Deliver {to_next} more unit(s) between systems for the next level." if to_next else " Fully established."
    status.innerText = line


def render_seasonal_demand():
    button = document.getElementById("seasonal-demand-toggle-button")
    status = document.getElementById("seasonal-demand-status")
    if button is None or status is None:
        return
    button.innerText = f"Seasonal demand: {'on' if runstate.seasonal_demand_enabled else 'off'}"
    if not runstate.seasonal_demand_enabled:
        status.innerText = (
            f"Optional: every {SEASON_LENGTH_TICKS} ticks two goods are in demand and sell for "
            f"{int(SEASONAL_DEMAND_BONUS * 100)}% more. Nothing is ever marked down."
        )
        return
    number, left, hot, upcoming = seasonal_status()
    names = lambda goods: " and ".join(GOOD_LABEL[g] for g in goods)  # noqa: E731
    status.innerText = (
        f"Season {number}: {names(hot)} in demand (+{int(SEASONAL_DEMAND_BONUS * 100)}%) for "
        f"{left} more tick(s). Next: {names(upcoming)}."
    )


def render_market():
    render_trade_post()
    render_route_hazards()
    render_run_seed()
    render_diplomacy()
    render_seasonal_demand()
    render_almanac()
    for good in market_multiplier:
        price = current_sell_price(good)
        pct = market_multiplier[good] * 100
        display = document.getElementById(f"market-{good}-display")
        if blackout_has("feed"):
            line = f"{GOOD_LABEL[good]}: {price} credits/unit ({pct:.0f}% of baseline)"
        else:  # J-29: Blackout, the price feed is dark -- a range and a coarse bar, no exact number
            low, high = blackout_price_range(price)
            line = f"{GOOD_LABEL[good]}: about {low}-{high} credits/unit (price feed dark)"
        if seasonal_multiplier(good) > 1.0:
            line += f" · in demand (+{int(SEASONAL_DEMAND_BONUS * 100)}%)"
        if weather_multiplier(good) != 1.0:
            ev = weather_active_event()
            line += f" · {'boom' if weather_multiplier(good) > 1.0 else 'slump'} ({(weather_multiplier(good) - 1.0) * 100:+.0f}%, {ev['left']} tick(s) left)"
        display.innerText = line
        display.className = "market-price"
        display.title = ""
        if market_multiplier[good] < 0.7 and blackout_has("feed"):
            display.className += " market-price--crashed"
            # J20 — recovery ETA back to baseline at the flat per-tick rate
            # (further sales of this good would push it back down).
            eta = math.ceil(round((MAX_PRICE_MULTIPLIER - market_multiplier[good])
                                  / MARKET_PRICE_RECOVERY_PER_TICK, 6))
            display.title = (
                f"Crashed: about {eta} tick(s) to recover to baseline if nothing "
                f"more of it is sold."
            )
        buy_button = document.getElementById(f"stockpile-{good}-buy-button")
        if buy_button is not None:
            sell_button = document.getElementById(f"stockpile-{good}-sell-button")
            status = document.getElementById(f"stockpile-{good}-status")
            buy_button.disabled = not can_stockpile_buy(good)
            buy_button.innerText = f"Buy {STOCKPILE_LOT}"
            sell_button.disabled = stockpile[good] <= 0
            status.innerText = (
                f"Stockpile {stockpile[good]}/{stockpile_capacity(good)}"
                + (f" (sells for {stockpile_sale_value(good)} after the {int(STOCKPILE_SELL_FEE * 100)}% fee)" if stockpile[good] else "")
            )
        document.getElementById(f"market-{good}-bar").style.width = (
            f"{pct:.0f}%" if blackout_has("feed") else f"{blackout_bar_percent(pct)}%"
        )
        # J12 — a small price-history sparkline alongside the bar.
        memory_note = price_memory_text(good)
        sparkline_html = _trend_sparkline_svg(
            price_history.get(good, []), "price-sparkline", f"Now: {price} credits",
            ghost=price_memory.get(good), ghost_label=memory_note or None,
        ) if blackout_has("feed") else ""
        if memory_note and sparkline_html:
            sparkline_html += f'<span class="sparkline-pct price-memory-note">{memory_note}</span>'
        document.getElementById(f"market-{good}-sparkline").innerHTML = sparkline_html


def render_research():
    document.getElementById("research-points-display").innerText = (
        f"Research points: {runstate.research_points:.0f}"
    )
    for node_id, node in RESEARCH_NODES.items():
        status_el = document.getElementById(f"research-{node_id}-status")
        unlock_button = document.getElementById(f"research-{node_id}-unlock-button")
        if node_id in runstate.unlocked_research:
            status_el.innerText = f"{node['label']} — unlocked ({node['description']})"
            unlock_button.hidden = True
        else:
            status_text = f"{node['label']} — {node['description']}"
            requires = node.get("requires")
            # Onboarding-tooltip audit (planning/TODO.md, origin A14): the
            # static index.html placeholder text used to state a node's
            # prerequisite ("requires Automation Expansion"/"requires Galaxy
            # Expansion") before Pyodide finished loading, but render()
            # replaced it with RESEARCH_NODES["description"], which never
            # mentioned the prereq at all -- so a returning player with
            # plenty of research points but a missing prerequisite saw the
            # unlock button disabled with no stated reason anywhere
            # permanent. Restate it here, matching Aftermath's own
            # missing-prereq status-text pattern, so it survives every
            # render rather than only the pre-Python placeholder.
            # Build the text in a local and assign once: reading innerText
            # back from an element inside a collapsed <details> returns ""
            # in a real browser, so `innerText += ...` would wipe the label.
            if requires is not None and requires not in runstate.unlocked_research:
                status_text += f" (requires {RESEARCH_NODES[requires]['label']})"
            closed_by = research_node_blocked_by(node_id)
            if closed_by is not None:
                status_text += f" (closed: you chose {RESEARCH_NODES[closed_by]['label']})"
            status_el.innerText = status_text
            unlock_button.hidden = False
            unlock_button.innerText = f"Research ({node['cost']})"
            unlock_button.disabled = not can_unlock_research(node_id)
            # J26 — say exactly what a locked node still needs.
            needs = []
            if requires is not None and requires not in runstate.unlocked_research:
                needs.append(f"unlock {RESEARCH_NODES[requires]['label']} first")
            if runstate.research_points < node["cost"]:
                needs.append(f"{node['cost'] - runstate.research_points:.0f} more research points")
            if closed_by is not None:
                unlock_button.title = f"Closed by your choice of {RESEARCH_NODES[closed_by]['label']}."
            else:
                unlock_button.title = ("Still needed: " + " and ".join(needs)) if needs else "Ready to unlock."


def render_fleet_priority():
    button = document.getElementById("fleet-priority-button")
    button.innerText = f"Fleet Priority: {'ON' if runstate.fleet_priority_enabled else 'OFF'}"
    button.disabled = False
    status = document.getElementById("fleet-priority-status")
    if runstate.fleet_priority_enabled:
        status.innerText = (
            "Idle automated ships abandon their home shuttle and reposition empty "
            "toward whichever producer feeds the fleet's most under-served colony."
        )
    else:
        status.innerText = "Automated ships stick to their fixed shuttle route."


def render_endgame():
    panel = document.getElementById("endgame-panel")
    panel.hidden = not runstate.endgame_reached
    if not runstate.endgame_reached:
        document.getElementById("found-new-corporation-button").hidden = True
        document.getElementById("hard-charter-toggle-button").hidden = True
        return
    worlds = background_world_count()
    document.getElementById("endgame-message-display").innerText = (
        "A fully automated fleet, running on Fleet Priority, spanning two systems — "
        "the pattern you built is spreading. This is a soft finish line, not a stop: "
        "the sandbox keeps running for as long as you want to keep watching it."
    )
    document.getElementById("endgame-worlds-display").innerText = (
        f"{worlds:,} worlds beyond your own fleet have adopted the pattern, trading "
        f"quietly among themselves — {background_revenue_this_tick()} credits/tick "
        f"in background revenue."
    )
    document.getElementById("legacy-display").innerText = legacy_summary_text()
    document.getElementById("found-new-corporation-button").hidden = not can_found_new_corporation()
    _render_renewal_options()
    render_endgame_galaxy(worlds)


# J20 — a visual flourish on the background galaxy: a small canvas that
# actually grows a scattering of dots as background_world_count() climbs,
# rather than the number alone standing in for "a growing galaxy." A
# fixed golden-angle spiral keeps the scatter stable frame to frame
# (no jitter) without needing to store per-dot state anywhere.
ENDGAME_GALAXY_CANVAS_SIZE = 140
ENDGAME_GALAXY_DOT_CAP = 200
GOLDEN_ANGLE_RADIANS = 2.399963


def endgame_galaxy_dot_position(i):
    """Canvas position of dot `i`, or None when the spiral has drifted
    off the canvas (those dots are simply not drawn)."""
    center = ENDGAME_GALAXY_CANVAS_SIZE / 2
    angle = i * GOLDEN_ANGLE_RADIANS
    radius = 3 + 4.6 * math.sqrt(i)
    cx = center + radius * math.cos(angle)
    cy = center + radius * math.sin(angle)
    if 0 <= cx <= ENDGAME_GALAXY_CANVAS_SIZE and 0 <= cy <= ENDGAME_GALAXY_CANVAS_SIZE:
        return cx, cy
    return None


# J16 — hovering the galaxy canvas names the nearest drawn dot. The dots
# are decoration standing in for the abstracted background worlds, so the
# tooltip says so honestly rather than inventing per-world data.
ENDGAME_GALAXY_HOVER_RADIUS = 5
ENDGAME_GALAXY_DEFAULT_TITLE = "The background galaxy: each dot is one of the worlds that trickle in passive revenue."


def endgame_galaxy_hover_text(x, y, worlds):
    best_index = None
    best_distance = ENDGAME_GALAXY_HOVER_RADIUS
    for i in range(min(ENDGAME_GALAXY_DOT_CAP, worlds)):
        position = endgame_galaxy_dot_position(i)
        if position is None:
            continue
        distance = math.hypot(position[0] - x, position[1] - y)
        if distance <= best_distance:
            best_index, best_distance = i, distance
    if best_index is None:
        return ENDGAME_GALAXY_DEFAULT_TITLE
    return (
        f"Background world #{best_index + 1} of {worlds:,}: part of the growing galaxy "
        "that trickles in passive revenue (decorative dot; the galaxy is abstracted)."
    )


def _wire_endgame_galaxy_hover(canvas):
    if runstate._galaxy_hover_wired:
        return
    runstate._galaxy_hover_wired = True

    def on_move(event):
        scale = ENDGAME_GALAXY_CANVAS_SIZE / (getattr(canvas, "clientWidth", 0) or ENDGAME_GALAXY_CANVAS_SIZE)
        x = float(getattr(event, "offsetX", -100)) * scale
        y = float(getattr(event, "offsetY", -100)) * scale
        canvas.title = endgame_galaxy_hover_text(x, y, background_world_count())

    canvas.addEventListener("mousemove", create_proxy(on_move))


def render_endgame_galaxy(worlds):
    canvas = document.getElementById("endgame-galaxy-canvas")
    if canvas is None:
        return
    _wire_endgame_galaxy_hover(canvas)
    canvas.title = ENDGAME_GALAXY_DEFAULT_TITLE
    ctx = canvas.getContext("2d")
    ctx.clearRect(0, 0, ENDGAME_GALAXY_CANVAS_SIZE, ENDGAME_GALAXY_CANVAS_SIZE)
    ctx.fillStyle = FLEET_PRIORITY_TARGET_COLOR
    dot_count = min(ENDGAME_GALAXY_DOT_CAP, worlds)
    for i in range(dot_count):
        position = endgame_galaxy_dot_position(i)
        if position is not None:
            ctx.beginPath()
            ctx.arc(position[0], position[1], 1.6, 0, 2 * math.pi)
            ctx.fill()


def _render_renewal_options():
    """The renewal preview and the harder-charter toggle, in the endgame panel."""
    gain = charter_points_for_next_renewal()
    preview = document.getElementById("charter-renew-preview-display")
    toggle = document.getElementById("hard-charter-toggle-button")
    if preview is not None:
        text = f"Renewing earns {gain} charter points."
        if runstate.hard_charter_next:
            text += " The next charter will be a harder one."
        preview.innerText = text
    if toggle is not None:
        toggle.hidden = not (hard_charter_unlocked() and can_found_new_corporation())
        toggle.innerText = f"Harder charter: {'on' if runstate.hard_charter_next else 'off'}"
        toggle.setAttribute("aria-pressed", "true" if runstate.hard_charter_next else "false")
