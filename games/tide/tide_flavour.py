"""Harbor quips, critters and sightings, scene themes, the delta popover, the market panel and crew."""

from js import document

import tide_runstate as runstate
from tide_achievements import achievement_ids_earned, achievements_summary
from tide_bridge import _read_local_storage_item
from tide_chrome import announce
from tide_rules import CREW, CREW_HIRE_COST, CREW_MAX, CREW_WAGE


# render() is defined in tide_renderer, which comes later in the module list; that module puts it here when it
# loads (see the end of tide_renderer.py). Calls below find it at run time.
render = None


# GD-17 harbour-master quips and GD-18 secret critters ---------------------------------------------------------------
QUIPS_MUTED_KEY = "tide-quips-muted"
_quip = {"text": "", "last": ""}


def quips_muted():
    return _read_local_storage_item(QUIPS_MUTED_KEY) == "true"


def _storm_next_season():
    wait = runstate.state.seasons_until_storm()
    return wait is not None and wait <= 1


# (id, condition, line). The first match that is not the line just spoken wins, so the voice varies without any dice.
QUIPS = (
    ("rescue", lambda ctx: ctx["rescued"], "That was close, boss. The lamp stays lit."),
    ("flooded", lambda ctx: ctx["new_rows"] > 0, "Water's in the lower yard again. We'll pump and carry on."),
    ("storm", lambda ctx: _storm_next_season(), "Storm's brewing. Batten the shutters."),
    ("fish", lambda ctx: runstate.state.fish_warning_active(), "Nets came up light this week. The fish are thin."),
    ("quiet", lambda ctx: runstate.state.quiet_seasons() >= 5, "Quiet water. Too quiet. I like it."),
    ("wall", lambda ctx: runstate.state.current_tier_index() >= 2, "Wall's holding, boss. Ask me again in five seasons."),
    ("broke", lambda ctx: runstate.state.funds < 30, "Purse is nearly empty, boss. We make do."),
)


def pick_quip(ctx, last=""):
    for quip_id, condition, line in QUIPS:
        if line != last and condition(ctx):
            return line
    return ""


def speak_quip(new_rows=0, rescued=False):
    """Called after a real Advance click. Sets the one-line quip (empty when muted or nothing applies)."""
    if quips_muted():
        _quip["text"] = ""
        return ""
    line = pick_quip({"new_rows": new_rows, "rescued": rescued}, _quip["last"])
    _quip["text"] = line
    if line:
        _quip["last"] = line
    return line


CRITTERS = {
    "seal": {
        "icon": "\U0001F9AD", "name": "Grey seal", "hint": "keep the acidity low for five seasons",
        "available": lambda: len(runstate.state.acidity_history) >= 5 and all(a < CRITTER_LOW_ACIDITY for a in runstate.state.acidity_history[-5:]),
    },
    "whale": {
        "icon": "\U0001F433", "name": "Whale fin", "hint": "save a heritage site through a storm",
        "available": lambda: runstate.state.protected_heritage_count() > 0 and len(runstate.state.storm_log) > 0,
    },
}
CRITTER_LOW_ACIDITY = 2.0


def critter_available(critter_id):
    entry = CRITTERS.get(critter_id)
    return bool(entry) and critter_id not in runstate.state.sightings and entry["available"]()


def log_sighting(critter_id):
    """Clicking a surfaced critter writes it into the Sightings list (once)."""
    if critter_id not in CRITTERS or critter_id in runstate.state.sightings or not critter_available(critter_id):
        return False
    runstate.state.sightings.append(critter_id)
    name = CRITTERS[critter_id]["name"].lower()
    runstate.state._log_ticker(f"{CRITTERS[critter_id]['icon']} A {name} was logged in the Sightings list.")
    runstate.state._chronicle_event(f"A {name} was sighted off the harbour.")
    announce(f"Sighting logged: {CRITTERS[critter_id]['name']}.")
    return True


def _make_critter_handler(critter_id):
    def handler(event=None):
        log_sighting(critter_id)
        render()
    return handler


def sightings_text():
    parts = []
    for critter_id, entry in CRITTERS.items():
        parts.append(f"{entry['icon']} {entry['name']}: seen" if critter_id in runstate.state.sightings
                     else f"? Unseen ({entry['hint']})")
    return " | ".join(parts)


def render_critters_and_quip():
    for critter_id, entry in CRITTERS.items():
        button = document.getElementById(f"critter-{critter_id}")
        if button is not None:
            button.hidden = not critter_available(critter_id)
            button.innerText = f"{entry['icon']} A {entry['name'].lower()} surfaced: log it"
    box = document.getElementById("sightings-list")
    if box is not None:
        box.innerText = sightings_text()
    quip = document.getElementById("harbor-quip")
    if quip is not None:
        quip.hidden = not _quip["text"]
        quip.innerText = f"\u2693 Harbour master: {_quip['text']}" if _quip["text"] else ""


# GD-22 scene themes unlocked by achievements ---------------------------------------------------------------------
SCENE_THEME_KEY = "tide-scene-theme"
SCENE_THEMES = {
    "default": {"label": "Daylight (default)", "achievement": None},
    "dusk": {"label": "Dusk sky", "achievement": "fortified_in_time"},
    "storm_glass": {"label": "Storm-glass", "achievement": "tier_storm_surge"},
    "coral_sand": {"label": "Coral-pink sand", "achievement": "stocks_rebound"},
}


def theme_unlocked(theme_id):
    entry = SCENE_THEMES.get(theme_id)
    return bool(entry) and (entry["achievement"] is None or entry["achievement"] in achievement_ids_earned())


def chosen_scene_theme():
    value = _read_local_storage_item(SCENE_THEME_KEY)
    return value if value in SCENE_THEMES and theme_unlocked(value) else "default"


def _achievement_label(achievement_id):
    entry = next((a for a in achievements_summary() if a["id"] == achievement_id), None)
    return entry["label"] if entry else achievement_id


def render_scene_theme():
    theme = chosen_scene_theme()
    root = getattr(document, "documentElement", None)
    if root is not None and hasattr(root, "setAttribute"):
        root.setAttribute("data-scene-theme", theme)
    select = document.getElementById("scene-theme-select")
    if select is None:
        return
    select.innerHTML = ""
    for theme_id, entry in SCENE_THEMES.items():
        option = document.createElement("option")
        option.value = theme_id
        unlocked = theme_unlocked(theme_id)
        option.disabled = not unlocked
        option.innerText = entry["label"] if unlocked else f"{entry['label']} (unlock: {_achievement_label(entry['achievement'])})"
        select.appendChild(option)
    select.value = theme


# D-28 delta breakdown ------------------------------------------------------------------------------------------
def delta_breakdown_text(kind):
    """Plain lines explaining last season's change in acidity or funds ('' before the first season)."""
    data = (runstate.state.last_breakdown or {}).get(kind)
    if not data:
        return "No season has been resolved yet."
    delta = data["to"] - data["from"]
    lines = [f"{'Funds' if kind == 'funds' else 'Acidity'} last season: {data['from']:.1f} to {data['to']:.1f} ({delta:+.1f})."]
    for label, value in data["parts"]:
        if abs(value) >= 0.05:
            lines.append(f"{value:+.1f} {label}")
    if len(lines) == 1:
        lines.append("Nothing moved it.")
    shown = sum(v for _l, v in data["parts"])
    gap = delta - shown
    if abs(gap) >= 0.05 and kind == "acidity":
        lines.append(f"{gap:+.1f} held at zero (acidity cannot go below 0)")
    elif abs(gap) >= 0.05:
        lines.append(f"{gap:+.1f} other")
    return "\n".join(lines)


_delta_open = {"kind": ""}


def render_delta_popover():
    box = document.getElementById("delta-popover")
    kind = _delta_open["kind"]
    if box is not None:
        box.hidden = not kind
        box.innerText = delta_breakdown_text(kind) if kind else ""
    for name in ("acidity", "funds"):
        button = document.getElementById(f"why-{name}-button")
        if button is not None:
            button.setAttribute("aria-expanded", "true" if kind == name else "false")


def render_market():
    panel, text = document.getElementById("market-panel"), document.getElementById("market-text")
    offer = runstate.state.market_offer_text()
    hint = runstate.state.market_telegraph_text()
    if panel is not None:
        panel.hidden = not (offer or hint)
    if text is not None:
        text.innerText = offer or hint
    for button_id in ("market-accept-button", "market-decline-button"):
        button = document.getElementById(button_id)
        if button is not None:
            button.hidden = not offer


def crew_text():
    if not runstate.state.crew:
        return f"No crew hired. Each specialist costs {CREW_HIRE_COST} to hire and {CREW_WAGE} a season."
    names = ", ".join(f"{CREW[c]['name']} ({CREW[c]['effect']})" for c in runstate.state.crew)
    return f"Crew: {names}. Wages: {CREW_WAGE * len(runstate.state.crew)} a season."


def render_crew():
    box = document.getElementById("crew-text")
    if box is not None:
        box.innerText = crew_text()
    for crew_id, entry in CREW.items():
        button = document.getElementById(f"crew-{crew_id}-button")
        if button is None:
            continue
        hired = crew_id in runstate.state.crew
        button.innerText = f"Dismiss the {entry['name']}" if hired else f"Hire a {entry['name']} ({CREW_HIRE_COST})"
        button.disabled = (not hired) and (len(runstate.state.crew) >= CREW_MAX or runstate.state.funds < CREW_HIRE_COST)
        button.title = f"{entry['name']}: {entry['effect']}; wage {CREW_WAGE} a season"
