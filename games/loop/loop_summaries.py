"""Rival, shock and rewind texts, the copyable summary, the Career panel, the material passport panel."""

import json

from js import document

import loop_runstate as runstate
from loop_bridge import _copy_to_clipboard
from loop_career import (
    career_best, career_closed_categories, career_plates, plate_for_mix, secret_progress, secret_unlocked,
)
from loop_rules import (
    ALL_GOODS, CIRCULARITY_INVESTMENTS, DEFAULT_GOODS_CATEGORY, GOODS_CATEGORIES, PASSPORT_PRODUCT_NAME,
    PASSPORT_STORY, PLATES, RIVAL_NAME, SECRET_GOODS, SHOCK_DEMAND_AT, SHOCK_PERIOD, SHOCK_PRICE_AT,
    SHOCK_STRIKE_AT, SHOCK_STRIKE_CYCLES, shock_effect, shock_name,
)
from loop_runstate import current_goods_label
from loop_sparklines import spend_history_text
from loop_visual_maps import trade_partner_flows


def rival_status_text():
    if runstate.chain.rival_on:
        return f"{RIVAL_NAME} is racing you. It is a fixed script, the same every time, and changes nothing for you."
    return (
        f"{RIVAL_NAME} is a straight-line competitor: it makes the same goods every cycle but digs up all of "
        "the material new and never invests in repair, reuse or recycling. Switch it on to race it. It is "
        "only a comparison: nothing you do depends on it."
    )


def shock_banner_text():
    """GH-3: the one-line notice shown in the status block ('' when there is nothing to say)."""
    if not runstate.chain.market_shocks:
        return ""
    active = runstate.chain.active_shock()
    coming = runstate.chain.next_shock()
    parts = []
    if active is not None:
        label = f"Market shock now: {shock_name(active)}, {shock_effect(active)}"
        if active["length"] > 1:
            label += f" (day {active['step']} of {active['length']})"
        parts.append(label + ".")
    if coming is not None:
        parts.append(f"Heads-up for next cycle: {shock_name(coming)}, {shock_effect(coming)}.")
    return " ".join(parts)


def shock_status_text():
    """GH-3: the always-visible explanation under the Market shocks switch."""
    if not runstate.chain.market_shocks:
        return (
            "Off. Turn it on for a fixed, announced schedule of price spikes, port strikes and demand surges. "
            "There is nothing random in it, every shock is shown one cycle early, and a chain that recovers "
            "its own material barely notices them."
        )
    text = (
        f"On. Every {SHOCK_PERIOD} cycles: a price spike on cycle {SHOCK_PRICE_AT}, a {SHOCK_STRIKE_CYCLES}-cycle "
        f"port strike from cycle {SHOCK_STRIKE_AT} (a different trade partner each round) and a demand surge on "
        f"cycle {SHOCK_DEMAND_AT}. Nothing is ever lost for good."
    )
    if runstate.chain.shocks_shrugged:
        text += f" Closed cycles that landed on a shock so far: {runstate.chain.shocks_shrugged}."
    return text


def rewind_token_text():
    return "Rewind: spent" if runstate.chain.rewind_used else "Rewind: 1 left"


def rewind_text():
    """GH-18: what the rewind token can do right now."""
    reason = runstate.chain.rewind_block_reason()
    if reason == "used":
        return "The rewind token on this chain is spent. A new chain gets a new one."
    if reason == "no_point":
        return "One rewind per chain. The undo point is set each time you advance a cycle, so advance one to use it."
    if reason == "donated":
        return "That cycle gave surplus to the regional pool, which cannot be taken back, so it cannot be rewound."
    return (
        f"One rewind per chain: go back to the start of cycle {runstate.chain.rewind_snapshot['cycle_number']}, "
        "undoing the last Advance Cycle and anything you bought since."
    )


def summary_blocks(fractions, width=40):
    """H-23: a block-character row, one block per cycle (the last `width`)."""
    blocks = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
    return "".join(blocks[max(0, min(7, round(f * 7)))] for f in fractions[-width:])


def summary_text():
    """H-23: plain text a player can paste anywhere."""
    spec = ALL_GOODS.get(runstate.chain.goods_category, GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY])
    name = spec.get("name") or spec["label"].capitalize()
    if runstate.chain.first_loop_closed_cycle is not None:
        head = f"Loop {name} - closed cycle {runstate.chain.first_loop_closed_cycle} - score {runstate.chain.score():.0f}"
    else:
        head = (
            f"Loop {name} - cycle {runstate.chain.cycle_number} - "
            f"{runstate.chain.circular_fraction_this_cycle() * 100:.0f}% circular - score {runstate.chain.score():.0f}"
        )
    row = summary_blocks(runstate.chain.circular_fraction_log)
    return head + ("\n" + row if row else "")


def plate_rows():
    """GH-15: (key, name, how, earned) in catalog order."""
    return [(key, spec["name"], spec["how"], key in career_plates) for key, spec in PLATES.items()]


def live_plate_text():
    shares = runstate.chain.supply_mix()
    key = plate_for_mix(shares)
    if key is None:
        return "Your supply mix right now would earn no plate: buy some circular supply first."
    top, share = max(shares.items(), key=lambda kv: kv[1])
    return (
        f"Your mix right now ({top} {share * 100:.0f}% of supply) would earn {PLATES[key]['name']} "
        "if you close the loop with it."
    )


def career_record_lines():
    """H-9: one line per goods category with any record."""
    lines = []
    for category in ALL_GOODS:
        record = career_best.get(category)
        if not record:
            continue
        name = ALL_GOODS[category].get("name") or ALL_GOODS[category]["label"].capitalize()
        parts = []
        if "fastest_close" in record:
            parts.append(f"first close on cycle {record['fastest_close']}")
        if "lowest_extraction" in record:
            parts.append(f"{record['lowest_extraction']:.0f} units extracted by then")
        if "best_score" in record:
            parts.append(f"best score {record['best_score']:.0f}")
        if record.get("best_streak"):
            parts.append(f"longest perfect run {record['best_streak']}")
        lines.append(f"{name}: " + ", ".join(parts))
    return lines


def secret_text():
    done, total = secret_progress()
    if secret_unlocked():
        return f"Secret category unlocked: {SECRET_GOODS['icon']} {SECRET_GOODS['name']}, shown with the goods choices at the start of a chain."
    missing = [GOODS_CATEGORIES[c]["label"] for c in GOODS_CATEGORIES if c not in career_closed_categories]
    return (
        f"\U0001F512 A fourth goods category is hidden. Run one fully closed cycle on each of the "
        f"{total} ordinary categories to reveal it ({done} of {total} done; still to close: {', '.join(missing)})."
    )


def accessible_chain_lines():
    """H-4: the ring, the trade partners and the meters as plain list lines, in reading order."""
    lines = [
        f"Cycle {runstate.chain.cycle_number}. Funds {runstate.chain.funds:.0f}.",
        f"New extraction this cycle: {runstate.chain.new_extraction_needed():.0f} of {runstate.chain.material_need():.0f} units needed.",
    ]
    for measure, spec in CIRCULARITY_INVESTMENTS.items():
        lines.append(
            f"{spec['label']}: {runstate.chain.circularity_investment[measure]} bought, supplying "
            f"{runstate.chain.measure_supply(measure):.0f} units per cycle."
        )
    for key, label, _icon, owned, units, _cost in trade_partner_flows():
        lines.append(f"{label}: {owned} bought, importing {units:.0f} units per cycle.")
    lines.append(f"Surplus sold or donated: {runstate.chain.exportable_surplus():.0f} units per cycle.")
    for measure in CIRCULARITY_INVESTMENTS:  # H-26: the ring-node sparklines, as text
        lines.append(spend_history_text(measure))
    lines.append(
        f"Environmental damage {runstate.chain.damage_fraction() * 100:.0f}%, extraction cost x{runstate.chain.extraction_cost_multiplier():.2f}."
    )
    lines.append(
        f"Circular this cycle {runstate.chain.circular_fraction_this_cycle() * 100:.0f}%, lifetime "
        f"{runstate.chain.lifetime_circular_fraction() * 100:.0f}%. Score {runstate.chain.score():.0f}."
    )
    return lines


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (it calls this by name through window.pyodide). Score, cycles run, lifetime circular
    share and, once it has happened, the cycle the loop first closed."""
    stats = [
        {"n": max(0, runstate.chain.cycle_number - 1), "one": "cycle", "many": "cycles"},
        f"{runstate.chain.lifetime_circular_fraction() * 100:.0f}% circular",
    ]
    if runstate.chain.first_loop_closed_cycle is not None:
        stats.append(f"loop closed in cycle {runstate.chain.first_loop_closed_cycle}")
    return json.dumps({"game": "Loop", "score": round(runstate.chain.score()), "unit": "points", "stats": stats})


def on_copy_summary(event=None):
    text = summary_text()
    status = document.getElementById("copy-summary-status")
    status.innerText = "Copied to the clipboard." if _copy_to_clipboard(text) else "Select the text above to copy it."


def render_career():
    """GH-14/15, H-9/23: the Career panel (plates, secret category, records, summary)."""
    plates = document.getElementById("plates-list")
    plates.innerHTML = ""
    for _key, name, how, earned in plate_rows():
        row = document.createElement("li")
        row.className = "plate-row plate-row--earned" if earned else "plate-row"
        mark = "\u2713" if earned else "\u25cb"
        row.innerText = f"{mark} {name}: {how}"
        plates.appendChild(row)
    document.getElementById("plates-count").innerText = f"{len(career_plates)} of {len(PLATES)} plates earned"
    document.getElementById("plate-live").innerText = live_plate_text()
    document.getElementById("secret-progress").innerText = secret_text()
    records = document.getElementById("career-records")
    records.innerHTML = ""
    lines = career_record_lines()
    if not lines:
        lines = ["No records yet: advance a cycle and they start filling in."]
    for line in lines:
        row = document.createElement("li")
        row.innerText = line
        records.appendChild(row)
    document.getElementById("summary-text").innerText = summary_text()


def passport_story_lines(entries, goods_category):
    """H7: (cycle, sentence) for each recorded step, oldest first. A step that
    keeps the product in the loop is its next 'life'; a fresh mining resets the
    count. Falls back to the default category for an unknown one."""
    category = goods_category if goods_category in PASSPORT_PRODUCT_NAME else DEFAULT_GOODS_CATEGORY
    product = PASSPORT_PRODUCT_NAME[category].split(",")[0]  # "Nova", not "Nova, a phone"
    lives = 1
    lines = []
    for entry in entries:
        source = entry["source"]
        if source == "extraction":
            lives = 1
            text = PASSPORT_STORY["extraction"][category].format(product=product)
        else:
            lives += 1
            text = PASSPORT_STORY[source][category].format(product=product, life=f"life {lives}")
        lines.append((entry["cycle"], text))
    return lines


def render_passport():
    """H21: the traced unit's journey, newest first, plus a one-line tally."""
    container = document.getElementById("passport-list")
    container.innerHTML = ""
    summary = document.getElementById("passport-summary")
    if not runstate.chain.passport:
        summary.innerText = f"Unit #1 of {current_goods_label()} hasn't started its journey yet: advance a cycle."
        return
    mined, recovered, longest = runstate.chain.passport_summary()
    summary.innerText = (
        f"{PASSPORT_PRODUCT_NAME.get(runstate.chain.goods_category, PASSPORT_PRODUCT_NAME[DEFAULT_GOODS_CATEGORY])}: "
        f"newly mined {mined} time(s), kept in the loop {recovered} time(s), "
        f"longest unbroken run in the loop {longest} cycle(s)."
    )
    for cycle, sentence in reversed(passport_story_lines(runstate.chain.passport, runstate.chain.goods_category)[-8:]):
        row = document.createElement("li")
        row.className = "passport-entry"
        row.innerText = f"Cycle {cycle}: {sentence}"
        container.appendChild(row)
