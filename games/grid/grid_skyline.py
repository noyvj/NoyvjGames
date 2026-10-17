"""The city skyline strip (GC-8): the SVG buildings, the smog haze and its caption.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import EMISSIONS_METER_MAX


# ---- GC-8 city skyline strip --------------------------------------------------------------------------------------
# A small picture of the city the grid serves, drawn from the numbers on screen: buildings light up (left to right) as
# capacity covers demand, flicker and dim after a brownout round, and a smoky haze thickens with the emissions meter.
# Lit buildings show windows and unlit ones are bare outlines, so the state never rests on colour alone, and a line of
# words repeats it. A reduced-motion player gets the same picture without the flicker (the dimming stays).
SKYLINE_WIDTH = 280
SKYLINE_HEIGHT = 56
# (x, width, height) of each building, left to right.
SKYLINE_BUILDINGS = (
    (4, 16, 30), (22, 12, 42), (36, 18, 24), (56, 14, 48), (72, 16, 34), (90, 12, 26), (104, 18, 50), (124, 14, 36),
    (140, 16, 28), (158, 12, 44), (172, 18, 32), (192, 14, 52), (208, 16, 30), (226, 12, 40), (240, 18, 26), (260, 14, 36),
)
SKYLINE_MAX_HAZE = 0.55


def skyline_status():
    """How lit the city is, from capacity against demand, how hazy from the emissions meter, and whether the last
    round was a brownout."""
    capacity = runstate.state.total_capacity()
    coverage = 0.0 if runstate.state.demand <= 0 else min(1.0, capacity / runstate.state.demand)
    total = len(SKYLINE_BUILDINGS)
    lit = int(round(total * coverage)) if capacity > 0 else 0
    haze = min(1.0, runstate.state.emissions / EMISSIONS_METER_MAX)
    event = runstate.state.last_event
    brownout = bool(event) and event.get("type") in ("brownout", "damage")
    return {"lit": lit, "total": total, "coverage": coverage, "haze": haze, "brownout": brownout}


def skyline_haze_word(haze):
    if haze < 0.05:
        return "clear air"
    if haze < 0.35:
        return "a light haze"
    if haze < 0.7:
        return "a thick haze"
    return "heavy smog"


def skyline_caption(status):
    text = (
        f"City: {status['lit']} of {status['total']} buildings lit "
        f"(capacity covers {status['coverage'] * 100:.0f}% of demand), {skyline_haze_word(status['haze'])}."
    )
    if status["brownout"]:
        text += " Lights dimmed by last round's disruption."
    return text


def skyline_svg(status):
    parts = []
    for index, (x, width, height) in enumerate(SKYLINE_BUILDINGS):
        y = SKYLINE_HEIGHT - height
        lit = index < status["lit"]
        css = "sky-building sky-building--lit" if lit else "sky-building sky-building--dark"
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" class="{css}" />')
        if lit:
            dim = " sky-window--dim" if status["brownout"] else ""
            for col in range(max(1, (width - 2) // 5)):
                for row in range(max(1, (height - 4) // 8)):
                    parts.append(
                        f'<rect x="{x + 2 + col * 5}" y="{y + 3 + row * 8}" width="3" height="4" '
                        f'class="sky-window{dim}" />'
                    )
    haze = status["haze"] * SKYLINE_MAX_HAZE
    parts.append(f'<rect x="0" y="0" width="{SKYLINE_WIDTH}" height="{SKYLINE_HEIGHT}" class="sky-haze" style="opacity:{haze:.2f}" />')
    flicker = " skyline-svg--flicker" if status["brownout"] else ""
    return (
        f'<svg viewBox="0 0 {SKYLINE_WIDTH} {SKYLINE_HEIGHT}" class="skyline-svg{flicker}" role="img" '
        f'aria-label="{skyline_caption(status)}">{"".join(parts)}</svg>'
    )


def render_skyline():
    strip = document.getElementById("skyline-strip")
    document.getElementById("pref-skyline").checked = runstate.prefs["skyline"]
    strip.hidden = not runstate.prefs["skyline"]
    if not runstate.prefs["skyline"]:
        return
    status = skyline_status()
    document.getElementById("skyline-graphic").innerHTML = skyline_svg(status)
    document.getElementById("skyline-caption").innerText = skyline_caption(status)
