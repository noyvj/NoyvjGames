"""Difficulty presets (C-10): relaxed, standard, operator and custom, derived from the existing toggles.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate


# C-10 -- difficulty presets: one choice that sets the three existing
# difficulty controls together (steeper demand, weather variability and the
# starting scenario). The preset is derived from those controls, never stored,
# so it can never disagree with them; any other combination reads "Custom".
DIFFICULTY_PRESETS = {
    "relaxed": {
        "label": "Relaxed",
        "steeper": False,
        "weather": False,
        "scenario": "greenfield",
        "blurb": "Greenfield start with extra funds, steady demand, no weather swings.",
    },
    "standard": {
        "label": "Standard",
        "steeper": False,
        "weather": False,
        "scenario": "standard",
        "blurb": "The default: standard start, steady demand, no weather swings.",
    },
    "operator": {
        "label": "Operator",
        "steeper": True,
        "weather": True,
        "scenario": "standard",
        "blurb": "Standard start with steeper demand growth and weather variability on renewables.",
    },
}
DIFFICULTY_PRESET_ORDER = ("relaxed", "standard", "operator")


def difficulty_preset_key():
    for key in DIFFICULTY_PRESET_ORDER:
        preset = DIFFICULTY_PRESETS[key]
        if (
            runstate.state.steeper_demand_growth_enabled == preset["steeper"]
            and runstate.state.weather_variability_enabled == preset["weather"]
            and runstate.state.scenario == preset["scenario"]
        ):
            return key
    return "custom"


def apply_difficulty_preset(key):
    """Sets the two toggles, and the starting scenario while it is still
    allowed to change. Returns True if the whole preset applied, False if the
    scenario part was locked (the toggles still changed)."""
    if key not in DIFFICULTY_PRESETS:
        return False
    preset = DIFFICULTY_PRESETS[key]
    runstate.state.steeper_demand_growth_enabled = preset["steeper"]
    runstate.state.weather_variability_enabled = preset["weather"]
    if runstate.state.scenario == preset["scenario"]:
        return True
    return runstate.state.apply_scenario(preset["scenario"])


def render_difficulty_preset():
    key = difficulty_preset_key()
    select = document.getElementById("difficulty-preset-select")
    select.value = key
    label = DIFFICULTY_PRESETS[key]["label"] if key != "custom" else "Custom"
    header = document.getElementById("difficulty-header-display")
    header.innerText = f"Difficulty: {label}" + (" | Ironman" if runstate.state.ironman else "")
    header.title = DIFFICULTY_PRESETS[key]["blurb"] if key != "custom" else "A mix of the difficulty controls."
    document.getElementById("difficulty-preset-note").innerText = runstate.difficulty_note
