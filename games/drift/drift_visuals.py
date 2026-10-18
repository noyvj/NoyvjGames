"""The region picture (building counts and heights, building pop animation, strain heartbeat), the pending pipeline and small DOM helpers (_pulse, _set_pressed)."""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import drift_runstate as runstate
from drift_model_region import region
from drift_rules import pending_age_bands, pending_pipeline_text


def render_pending_pipeline():
    bands = pending_age_bands(region)
    total = sum(bands.values())
    pipeline = document.getElementById("pending-pipeline")
    text = document.getElementById("pending-pipeline-text")
    pipeline.hidden = total < 0.5
    text.hidden = False
    text.innerText = pending_pipeline_text(bands)
    for key in ("new", "recent", "old"):
        share = bands[key] / total * 100 if total >= 0.5 else 0
        segment = document.getElementById(f"pending-band-{key}")
        segment.style.width = f"{share:.1f}%"
        segment.title = f"{bands[key]:.0f} people"


# I2: scale the region skyline's building count/height with real capacity,
# so the ambient visual reflects institutional growth instead of always
# rendering the same fixed six buildings regardless of state. Six buildings
# are authored in the markup (each with its own distinct height, see
# style.css); they're revealed one at a time as capacity grows, and every
# revealed building is scaled toward its own authored height by one shared
# vertical scale factor -- via a CSS transform, not a duplicated pixel
# height, so this file never needs to know the authored heights themselves.
REGION_VISUAL_BUILDING_IDS = ["a", "b", "c", "d", "e", "f"]
REGION_VISUAL_CAPACITY_PER_BUILDING = 20.0
REGION_VISUAL_MIN_HEIGHT_SCALE = 0.35
REGION_VISUAL_FULL_HEIGHT_CAPACITY = 150.0


def region_visual_building_count(total_capacity):
    """How many of the six authored buildings are currently revealed --
    always at least one (a region exists from round 1), one more per
    REGION_VISUAL_CAPACITY_PER_BUILDING of total capacity built, capped at
    the six actually authored in the markup."""
    unlocked = 1 + int(total_capacity // REGION_VISUAL_CAPACITY_PER_BUILDING)
    return min(unlocked, len(REGION_VISUAL_BUILDING_IDS))


def region_visual_height_scale(total_capacity):
    """A shared vertical scale (never below a visible floor, so a fresh
    region reads as "just starting out" rather than invisible) applied to
    every revealed building's own authored height -- grows smoothly toward
    REGION_VISUAL_FULL_HEIGHT_CAPACITY rather than only jumping in discrete
    steps when a new building is revealed."""
    fraction = total_capacity / REGION_VISUAL_FULL_HEIGHT_CAPACITY
    return max(REGION_VISUAL_MIN_HEIGHT_SCALE, min(1.0, fraction))


# GI-14: each capacity investment makes one building on the skyline rise and settle with a tiny dust
# puff (pure CSS, drawn in style.css; Reduce Motion and the Animation speed "Off" setting stop it).
# A building that has just been revealed pops first; otherwise the pops take turns along the skyline.
BUILDING_POP_MS = 1100


def building_to_pop(count_before, count_after, pops_so_far):
    """Index (0-based) of the skyline building that pops for an investment that took the visible
    building count from count_before to count_after."""
    count_after = max(1, min(count_after, len(REGION_VISUAL_BUILDING_IDS)))
    if count_after > count_before:
        return count_after - 1
    return pops_so_far % count_after


def _pop_building(count_before):
    count_after = region_visual_building_count(region.total_capacity())
    index = building_to_pop(count_before, count_after, runstate.building_pop_count)
    runstate.building_pop_count += 1
    element_id = f"region-visual-building-{REGION_VISUAL_BUILDING_IDS[index]}"
    element = document.getElementById(element_id)
    # Two identical animations under two class names: swapping to the other one restarts the pop
    # when the player buys again before the last pop has finished.
    css_class = "building-pop-b" if element.classList.contains("building-pop-a") else "building-pop-a"
    _pulse(element_id, css_class, BUILDING_POP_MS)


# GI-19: a soft pulse on the strain readout whose beat quickens with the strain level and calms
# as it falls. Seconds per beat; style.css multiplies it by the Animation speed setting.
STRAIN_HEARTBEAT_SECONDS = {"stable": 6.0, "strained": 2.6, "critical": 1.2}


def strain_heartbeat_seconds(level):
    return STRAIN_HEARTBEAT_SECONDS.get(level, STRAIN_HEARTBEAT_SECONDS["stable"])


def scaled_seconds(seconds):
    """A CSS duration that follows the player's Animation speed setting (settings.js sets
    --drift-anim-scale on the page: 2 slow, 1 normal, 0.5 fast)."""
    return f"calc({seconds:.2f}s * var(--drift-anim-scale, 1))"


# I6: a one-line plain-language consequence description per strain level,
# not just the existing colour/label change on the strain bar -- so a
# player who hasn't opened the pressure section's info-toggle still knows
# what "critical" actually costs them.
STRAIN_LEVEL_CONSEQUENCE = {
    "stable": "Services are keeping pace with arrivals — no meaningful drag on income.",
    "strained": "Shortfalls are starting to bite: strain is cutting into this region's income each round.",
    "critical": "Services are badly outpaced: strain is cutting deep into income, and it will stay elevated even after you catch up.",
}


def strain_consequence_message(region_state):
    return STRAIN_LEVEL_CONSEQUENCE[region_state.strain_level()]


# I15 -- lightweight, reusable pulse feedback: adds a CSS animation class
# to an element for a fixed short duration, then removes it. Same
# setTimeout+create_proxy technique as Herd's F19 _pulse()/this file's
# own achievement toast above.
def _pulse(element_id, css_class, duration_ms=1600):
    element = document.getElementById(element_id)
    element.classList.add(css_class)

    def _unpulse(*args):
        element.classList.remove(css_class)
        proxy.destroy()

    proxy = create_proxy(_unpulse)
    setTimeout(proxy, duration_ms)


def _set_pressed(button, on):
    button.setAttribute("aria-pressed", "true" if on else "false")
    if on:
        button.classList.add("active")
    else:
        button.classList.remove("active")
