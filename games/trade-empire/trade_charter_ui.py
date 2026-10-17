"""The charter panel, the crest, the ribbon, the captains panel."""

from js import document

import trade_runstate as runstate
from trade_achievements import ACHIEVEMENTS, achievement_ids_earned
from trade_captains import CAPTAINS, captain_of
from trade_charter import (
    CHARTER_PERKS, can_buy_charter_perk, charter_crest, charter_crest_text,
    charter_perk_missing_requirements, charter_points_available, charter_points_for_next_renewal, crest_for,
    founding_summary_text,
)
from trade_crew import (
    can_assign_captain, can_release_captain, captain_is_earned, captain_status_text, captains_summary_text,
    is_captain_swap,
)
from trade_ships import ships
from trade_uikit import _html_escape


# ===========================================================================
# O-1/O-3/O-4 -- the Charter panel: the perk tree, the lifetime ledger and the
# renewal options. Static markup in index.html (the buy buttons keep keyboard
# focus across the once-a-second render); filled in here.
# ===========================================================================


def on_toggle_charter(event=None):
    runstate.charter_open = not runstate.charter_open
    update_charter_display()


def charter_perk_status_text(perk_id):
    perk = CHARTER_PERKS[perk_id]
    text = f"{perk['label']} ({perk['cost']} pt) — {perk['description']}"
    if perk_id in runstate.charter_perks:
        return text + " Owned."
    missing = charter_perk_missing_requirements(perk_id)
    if missing:
        return text + " (requires " + " and ".join(CHARTER_PERKS[m]["label"] for m in missing) + ")"
    return text


def career_entry_text(entry):
    """J-14 -- one line of the career log."""
    kind = "Harder charter" if entry["hard"] else "Charter"
    label, glyph = crest_for(entry["n"])
    return (
        f"{glyph} {kind} {entry['n']} ({label} crest): {entry['units']:,} units moved, {entry['routes']} route(s), "
        f"peak profit {entry['peak']:,}, {entry['perks']} perk(s) owned."
        + (" \u25d0 Dark run." if entry.get("dark") else "")
    )


def update_charter_display():
    toggle = document.getElementById("charter-toggle-button")
    panel = document.getElementById("charter-panel")
    if toggle is None or panel is None:
        return
    suffix = " (harder)" if runstate.hard_charter_active else ""
    toggle.innerText = ("Hide Charter" if runstate.charter_open else "\U0001F4DC Charter") + suffix
    toggle.setAttribute("aria-expanded", "true" if runstate.charter_open else "false")
    panel.hidden = not runstate.charter_open
    if not runstate.charter_open:
        return

    def put(element_id, text):
        element = document.getElementById(element_id)
        if element is not None:
            element.innerText = text

    hard_note = " This is a harder charter: markets saturate faster and colony needs fade sooner." if runstate.hard_charter_active else ""
    put(
        "charter-points-display",
        f"Charter points: {charter_points_available()} to spend ({runstate.charter_points_earned} earned). "
        f"Renewing the charter earns {charter_points_for_next_renewal()} more." + hard_note,
    )
    put("charter-founding-display", founding_summary_text())
    for perk_id, perk in CHARTER_PERKS.items():
        put(f"charter-perk-{perk_id}-status", charter_perk_status_text(perk_id))
        button = document.getElementById(f"charter-perk-{perk_id}-buy-button")
        if button is None:
            continue
        owned = perk_id in runstate.charter_perks
        button.innerText = "Owned" if owned else f"Buy ({perk['cost']})"
        button.disabled = owned or not can_buy_charter_perk(perk_id)
        button.setAttribute("aria-label", f"Buy charter perk {perk['label']} for {perk['cost']} charter points")
        if owned:
            button.title = "Already owned."
        else:
            missing = charter_perk_missing_requirements(perk_id)
            if missing:
                button.title = "Still needed: " + " and ".join(CHARTER_PERKS[m]["label"] for m in missing)
            elif charter_points_available() < perk["cost"]:
                button.title = f"Needs {perk['cost'] - charter_points_available()} more charter point(s)."
            else:
                button.title = "Ready to buy."
    put("ledger-units-display", f"Goods moved: {runstate.ledger_units_moved:,} units delivered across every charter.")
    put(
        "ledger-routes-display",
        f"Routes established: {runstate.ledger_routes_established:,} in total ({len(runstate.ledger_routes_seen)} in this charter).",
    )
    put("ledger-charters-display", f"Charters completed: {runstate.charters_completed:,}.")
    put("ledger-hard-display", f"Harder charters completed: {runstate.ledger_hard_completed:,}.")
    put(
        "charter-crest-display",
        f"Active crest: {charter_crest_text()}. Crests change at 1, 3, 5 and 10 completed charters "
        "(Founder, Renewed, Veteran, Master, Sovereign), each with its own shape and word.",
    )
    career_list = document.getElementById("charter-career-list")
    if career_list is not None:
        career_list.innerHTML = ""
        if not runstate.charter_career:
            item = document.createElement("li")
            item.className = "charter-career-empty"
            item.innerText = (
                "No completed charters logged yet. Each renewal adds a line here: goods moved, routes, "
                "peak profit and perks owned."
            )
            career_list.appendChild(item)
        for entry in reversed(runstate.charter_career):
            item = document.createElement("li")
            item.className = "charter-career-entry"
            item.innerText = career_entry_text(entry)
            career_list.appendChild(item)


# ===========================================================================
# J-14 (crest) / J-31 (ledger ribbon) / J-7, J-8 (captains panel)
# ===========================================================================
RIBBON_SHAPES = ("\u25cf", "\u25b2", "\u25a0", "\u25c6")  # circle, triangle, square, diamond
RIBBON_MAX_BADGES = 8


def render_crest():
    crest = document.getElementById("charter-crest")
    if crest is None:
        return
    label, glyph = charter_crest()
    crest.innerText = charter_crest_text()
    crest.title = (
        f"Charter crest: {glyph} {label}. Charters completed: {runstate.charters_completed}. "
        "The shape and the word both change as you renew the charter."
    )


def ribbon_badges():
    """Up to RIBBON_MAX_BADGES of the earned achievements, latest in the
    catalog first, each with a shape (cycling through four) and its label."""
    earned = achievement_ids_earned()
    labels = {entry["id"]: entry["label"] for entry in ACHIEVEMENTS}
    badges = []
    for index, achievement_id in enumerate(earned):
        badges.append((RIBBON_SHAPES[index % len(RIBBON_SHAPES)], labels.get(achievement_id, achievement_id)))
    return list(reversed(badges[-RIBBON_MAX_BADGES:])), len(earned)


def render_ribbon():
    ribbon = document.getElementById("ledger-ribbon")
    if ribbon is None:
        return
    badges, earned_count = ribbon_badges()
    parts = [
        f'<span class="ribbon-count">Ledger ribbon: {earned_count} of {len(ACHIEVEMENTS)} badges</span>'
    ]
    for shape, label in badges:
        parts.append(
            f'<span class="ribbon-badge"><span class="ribbon-shape" aria-hidden="true">{shape}</span> {_html_escape(label)}</span>'
        )
    hidden = earned_count - len(badges)
    if hidden > 0:
        parts.append(f'<span class="ribbon-more">+{hidden} more in Achievements</span>')
    if not badges:
        parts.append('<span class="ribbon-more">Earn an achievement to pin its badge here.</span>')
    ribbon.innerHTML = "".join(parts)


def on_toggle_captains(event=None):
    runstate.captains_open = not runstate.captains_open
    render_captains()


def render_captains():
    toggle = document.getElementById("captains-toggle-button")
    panel = document.getElementById("captains-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Captains" if runstate.captains_open else "\U0001F396\ufe0f Captains"
    toggle.setAttribute("aria-expanded", "true" if runstate.captains_open else "false")
    panel.hidden = not runstate.captains_open
    # The per-ship captain line is always kept current, panel open or not.
    for ship in ships.values():
        line = document.getElementById(f"ship-{ship.id}-captain")
        if line is None:
            continue
        perk_id = captain_of(ship)
        line.hidden = not ship.purchased or (perk_id is None and not captain_is_earned(ship.id))
        text_el = document.getElementById(f"ship-{ship.id}-captain-text")
        quote_el = document.getElementById(f"ship-{ship.id}-captain-quote")
        if perk_id is not None:
            captain = CAPTAINS[perk_id]
            if text_el is not None:
                text_el.innerText = f"Captain: {captain['name']}, {captain['label']}."
            if quote_el is not None:
                quote_el.innerText = f"\u201c{captain['quote']}\u201d"
        else:
            if text_el is not None:
                text_el.innerText = "Captain's seat earned: pick a captain in the Captains panel."
            if quote_el is not None:
                quote_el.innerText = ""
    if not runstate.captains_open:
        return
    summary = document.getElementById("captains-summary-display")
    if summary is not None:
        summary.innerText = captains_summary_text()
    for perk_id in CAPTAINS:
        status = document.getElementById(f"captain-{perk_id}-status")
        if status is not None:
            status.innerText = captain_status_text(perk_id)
        quote = document.getElementById(f"captain-{perk_id}-quote")
        if quote is not None:
            quote.innerText = f"\u201c{CAPTAINS[perk_id]['quote']}\u201d"
        release = document.getElementById(f"captain-{perk_id}-release-button")
        if release is not None:
            release.hidden = not can_release_captain(perk_id)
        for ship_id in ships:
            button = document.getElementById(f"captain-{perk_id}-ship-{ship_id}-button")
            if button is None:
                continue
            applicable = can_assign_captain(perk_id, ship_id)
            button.hidden = not applicable
            button.disabled = not applicable
            ship = ships[ship_id]
            verb = "Move to" if is_captain_swap(perk_id) else "Post to"
            button.innerText = f"{verb} {ship.name}"
            button.setAttribute(
                "aria-label", f"{verb} {ship.name}: {CAPTAINS[perk_id]['name']}, {CAPTAINS[perk_id]['label']}"
            )
