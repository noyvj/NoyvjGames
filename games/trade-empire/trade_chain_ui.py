"""Chain Builder page: signature, panel render, level select."""

from fractions import Fraction
from js import document
from pyodide.ffi import create_proxy

import trade_runstate as runstate
from trade_chain_logic import (
    _chain_esc, _chain_real_best, _chain_signature, chain_adjust_ships, chain_can_add_ship,
    chain_clear_board, chain_distance, chain_distances_text, chain_draft_result, chain_fits,
    chain_goal_lines, chain_good_name, chain_goods_line, chain_hint_label, chain_hint_press,
    chain_hint_text, chain_lock_in, chain_map_svg, chain_medal_counts, chain_medal_for, chain_path,
    chain_pick_site, chain_result_lines, chain_score_text, chain_set_site, chain_ships_on_board,
    chain_site_line, chain_solved_in_chapter, chain_stage_label, chain_status_text, chain_trips,
)
from trade_chain_rules import (
    CHAIN_BY_ID, CHAIN_CHAPTERS, CHAIN_CYCLE, CHAIN_MAX_PRODUCTS, CHAIN_MAX_STAGES, CHAIN_PUZZLES,
)
from trade_crises import CRISIS_MEDAL_MARK


def on_toggle_chain(event=None):
    runstate.chain_open = not runstate.chain_open
    render_chain()


def on_chain_lock(event=None):
    chain_lock_in()
    render_chain()


def on_chain_clear(event=None):
    chain_clear_board()
    render_chain()


def on_chain_hint(event=None):
    chain_hint_press()
    render_chain()


def _make_chain_tab_handler(index):
    def handler(event=None):
        runstate.chain_tab = index
        render_chain()
    return handler


def _make_chain_select_handler(index, stage):
    def handler(event=None):
        chain_set_site(index, stage, document.getElementById(f"chain-p{index}-s{stage}-select").value)
        render_chain()
    return handler


def _make_chain_ship_handler(index, stage, delta):
    def handler(event=None):
        chain_adjust_ships(index, stage, delta)
        render_chain()
    return handler


def on_chain_map_click(event=None):
    node = None
    try:
        node = event.target.closest("[data-site]")
    except Exception:  # noqa: BLE001 -- a click on empty map, or no event
        node = None
    if node is not None:
        chain_pick_site(node.getAttribute("data-site"))
        render_chain()


def render_chain():
    toggle = document.getElementById("chain-toggle-button")
    panel = document.getElementById("chain-panel")
    if toggle is None or panel is None:
        return
    signature = _chain_signature()
    if signature == runstate._chain_rendered_sig:
        return
    runstate._chain_rendered_sig = signature
    toggle.innerText = "Hide Chain Builder" if runstate.chain_open else "\U0001F517 Chain Builder"
    toggle.setAttribute("aria-expanded", "true" if runstate.chain_open else "false")
    panel.hidden = not runstate.chain_open
    document.getElementById("chain-board").hidden = runstate.chain_active is None
    if not runstate.chain_open:
        return
    solved, golds = chain_medal_counts()
    document.getElementById("chain-progress").innerText = (
        f"Solved {solved} of {len(CHAIN_PUZZLES)} puzzles, gold on {golds}. "
        + " ".join(f"{CHAIN_CHAPTERS[c][0]}: {chain_solved_in_chapter(c)}/{sum(1 for p in CHAIN_PUZZLES if p['chapter'] == c)}." for c in CHAIN_CHAPTERS)
    )
    document.getElementById("chain-status").innerText = chain_status_text()
    document.getElementById("chain-leave-button").hidden = runstate.chain_active is None
    if runstate.chain_active is None:
        runstate._chain_options_for = None
        return
    puzzle = CHAIN_BY_ID[runstate.chain_active]
    result = chain_draft_result()
    chapter = CHAIN_CHAPTERS[puzzle["chapter"]][0]
    document.getElementById("chain-title").innerText = f"Chapter {puzzle['chapter']}, {chapter}: {puzzle['title']}"
    document.getElementById("chain-blurb").innerText = puzzle["blurb"]
    document.getElementById("chain-rules").innerText = (
        f"Each ship holds {puzzle['cargo']} units. The fleet has {puzzle['fleet']} ships ({chain_ships_on_board()} on the board). "
        f"A cycle is {CHAIN_CYCLE} ticks. Sources and refineries can only do so much each cycle; ports take up to a limit."
    )
    for number, (done, text) in enumerate(chain_goal_lines(puzzle, result)):
        document.getElementById(f"chain-goal-{number}").innerText = ("✓ Done: " if done else "○ Not yet: ") + text
    document.getElementById("chain-map").innerHTML = chain_map_svg(puzzle)
    document.getElementById("chain-map").setAttribute(
        "aria-label", "Map of the sites. " + " ".join(chain_site_line(puzzle, sid) for sid in puzzle["sites"])
    )
    document.getElementById("chain-sites-text").innerText = " ".join(chain_site_line(puzzle, sid) for sid in puzzle["sites"])
    document.getElementById("chain-distances-text").innerText = chain_distances_text(puzzle)
    two = len(puzzle["products"]) > 1
    new_puzzle = runstate._chain_options_for != runstate.chain_active
    runstate._chain_options_for = runstate.chain_active
    for index in range(CHAIN_MAX_PRODUCTS):
        tab = document.getElementById(f"chain-product-{index}-tab")
        block = document.getElementById(f"chain-p{index}-block")
        present = index < len(puzzle["products"])
        tab.hidden = not (present and two)
        block.hidden = not present
        if not present:
            continue
        product = puzzle["products"][index]
        tab.innerText = f"Order {index + 1}: {chain_good_name(product['good'])}"
        tab.setAttribute("aria-pressed", "true" if runstate.chain_tab == index else "false")
        document.getElementById(f"chain-p{index}-title").innerText = (
            f"Order {index + 1}: {chain_goods_line(puzzle, index)} for {puzzle['sites'][product['port']]['name']}. "
            f"Needs {product['need']} a cycle, takes up to {product['want']}."
        )
        path = chain_path(product["good"])
        entry = runstate.chain_plan[index]
        full = entry["sites"] + [product["port"]]
        for stage in range(CHAIN_MAX_STAGES):
            row = document.getElementById(f"chain-p{index}-s{stage}-row")
            row.hidden = stage >= len(path)
            if stage >= len(path):
                continue
            select = document.getElementById(f"chain-p{index}-s{stage}-select")
            label = chain_stage_label(puzzle, index, stage)
            document.getElementById(f"chain-p{index}-s{stage}-label").innerText = label
            select.setAttribute("aria-label", f"Order {index + 1}: {label}")
            if new_puzzle:
                options = ['<option value="">Choose a site</option>']
                for sid, site in puzzle["sites"].items():
                    if chain_fits(site, path, stage):
                        detail = f"supplies {site['cap']} a cycle" if site["kind"] == "source" else f"takes in {site['cap']} a cycle"
                        options.append(f'<option value="{_chain_esc(sid)}">{_chain_esc(site["name"])} ({detail})</option>')
                select.innerHTML = "".join(options)
            select.value = entry["sites"][stage] or ""
            leg = result["legs"][index][stage] if result is not None and result["ok"] else None
            if full[stage] is not None and full[stage + 1] is not None:
                a, b = full[stage], full[stage + 1]
                text = (f"{puzzle['sites'][a]['name']} to {puzzle['sites'][b]['name']}: {chain_distance(puzzle, a, b)} steps, "
                        f"{chain_trips(puzzle, a, b)} round trips a cycle, {puzzle['cargo'] * chain_trips(puzzle, a, b)} units per ship.")
            else:
                text = "Choose this step's site and the next to see the leg."
            if leg is not None:
                text += f" Moves {leg['moved']} of a possible {leg['capacity']}."
            ships = entry["ships"][stage]
            document.getElementById(f"chain-p{index}-l{stage}-text").innerText = f"{text} Ships on this leg: {ships}."
            document.getElementById(f"chain-p{index}-l{stage}-down-button").disabled = ships <= 1
            document.getElementById(f"chain-p{index}-l{stage}-up-button").disabled = not chain_can_add_ship(index, stage)
    lines = chain_result_lines(puzzle, result)
    document.getElementById("chain-result").innerHTML = "".join(f"<p>{_chain_esc(line)}</p>" for line in lines)
    document.getElementById("chain-lock-button").disabled = not (result is not None and result["ok"] and result["met"])
    document.getElementById("chain-hint-button").innerText = chain_hint_label()
    for rung in range(1, 4):
        hint = document.getElementById(f"chain-hint-{rung - 1}-text")
        hint.hidden = rung > runstate.chain_hint_rung
        hint.innerText = chain_hint_text(puzzle, rung) if rung <= runstate.chain_hint_rung else ""
    _chain_sync_levels()


# --- Chain Builder: puzzle picker on the shared level select (shared/level-select.js) ------------------------------
_level_select_proxies = []


def _chain_js_window():
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return window


def _chain_to_js(value):
    try:
        from js import Object  # noqa: PLC0415
        from pyodide.ffi import to_js  # noqa: PLC0415
    except ImportError:
        return None
    return to_js(value, dict_converter=Object.fromEntries)


def chain_levels_list():
    """The puzzles as level-select entries; the first puzzle of each later chapter is flagged as a new mechanic."""
    levels = []
    for index, puzzle in enumerate(CHAIN_PUZZLES):
        opens_chapter = index == 0 or CHAIN_PUZZLES[index - 1]["chapter"] != puzzle["chapter"]
        levels.append({
            "id": puzzle["id"], "title": puzzle["title"],
            "kind": "mechanic" if opens_chapter and puzzle["chapter"] > 1 else "level",
            "blurb": f"Chapter {puzzle['chapter']}, {CHAIN_CHAPTERS[puzzle['chapter']][0]}. {puzzle['blurb']}",
            "better": "higher", "unit": "per ship",
        })
    return levels


def chain_levels_state():
    done, best = [], {}
    for puzzle in CHAIN_PUZZLES:
        entry = _chain_real_best().get(puzzle["id"])
        if entry is not None:
            score = Fraction(entry["units"], entry["ships"])
            done.append(puzzle["id"])
            best[puzzle["id"]] = {"value": float(score),
                                  "text": f"{CRISIS_MEDAL_MARK[chain_medal_for(puzzle, entry['units'], entry['ships'])]} {chain_score_text(score)} per ship"}
    return {"done": done, "best": best}


def _make_level_start_proxy(handler):
    proxy = create_proxy(lambda level_id, level=None: handler(str(level_id)))
    _level_select_proxies.append(proxy)
    return proxy


def _level_select_create(dom_id, title, levels, state, on_start):
    """A shared level-select screen, or None when the page has none (a test, or the script failed to load)."""
    window = _chain_js_window()
    factory = getattr(getattr(window, "NoyvjLevels", None), "create", None) if window is not None else None
    if factory is None:
        return None
    options = _chain_to_js({
        "domId": dom_id, "title": title, "levels": levels, "state": state,
        "onStart": _make_level_start_proxy(on_start),
        "onChange": create_proxy(lambda *args: None),  # progress is Python's: the screen stores nothing itself
    })
    if options is None:
        return None
    try:
        return factory(options)
    except Exception:  # noqa: BLE001 -- a JS-side failure must never break the game
        return None


def _chain_sync_levels():
    if runstate._chain_levels is None:
        return
    payload = _chain_to_js(chain_levels_state())
    try:
        if payload is not None:
            runstate._chain_levels.setState(payload)
    except Exception:  # noqa: BLE001
        pass
