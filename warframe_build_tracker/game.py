"""Warframe Build Resource Tracker -- Pyodide port.

Rearchitected 2026-09-20 from a Flask app (render_template + data.json on
disk, single-machine only) into the same Python-via-Pyodide, no-build-step
stack every hub game already uses, so it can reuse the hub's existing
account/save-code system (shared/hub-auth.js + shared/save-widget.js,
unmodified) for real multi-user, account-based saves instead of a single
local JSON file. See planning/TODO2.md's "X. Warframe Build Tracker"
section and this repo's root CLAUDE.md for the save-widget contract this
file implements (get_state()/load_state()).

Recipes/locations/categories are static reference data, not player state --
they're rebuilt fresh from RECIPES every page load and never round-tripped
through get_state()/load_state(), unlike the old app.py's data.json which
persisted a copy of them (there's no longer a "sync/reload recipe data"
step needed at all: the data is just always current, since it's baked
into this file).
"""

import base64
import copy
import json
import math
import re
from datetime import date, datetime, timedelta, timezone

from js import confirm, document
from pyodide.ffi import create_proxy

WIKI_BASE = "https://wiki.warframe.com/w/"

# X: "days since last update" readout. The recipe/location data lives in this
# file now (there's no data.json to stat), so "last updated" honestly means
# "the day the maintainer last hand-edited MANUFACTURING_RECIPES /
# RESOURCE_LOCATIONS / DEFAULT_PARTS". Bump this ISO date whenever you do --
# see README.md "Updating the requested parts".
DATA_UPDATED = "2026-09-26"

# X: a resource whose total requirement across the whole build list is at
# least this many units gets a small "grindy" flag. One place to tune it.
GRINDY_THRESHOLD = 500

# Sort modes for the component table. "category" is the original fixed order.
SORT_MODES = ("category", "priority", "name", "remaining")
NOTE_MAX_LEN = 500

# Your requested parts and target quantities.
DEFAULT_PARTS = [
    ("Raplak Prism", 1), ("Shwaak Prism", 1), ("Granmu Prism", 1),
    ("Rahn Prism", 1), ("Cantic Prism", 1), ("Lega Prism", 1),
    ("Klamora Prism", 1), ("Shraksun Scaffold", 1), ("Phahd Scaffold", 3),
    ("Propa Scaffold", 3), ("Certus Brace", 6), ("Lohrin Brace", 1),
    ("Balla Strike", 1), ("Cyath Strike", 1), ("Dehtat Strike", 1),
    ("Dokrahm Strike", 1), ("Kronsh Strike", 1), ("Mewan Strike", 1),
    ("Ooltha Strike", 1), ("Rabvee Strike", 1), ("Sepfahn Strike", 1),
    ("Plague Keewar Strike", 1), ("Plague Kripath Strike", 1),
    ("Shtung Grip", 11), ("Vargeet Jai II Link", 11),
    ("Catchmoon Chamber", 1), ("Gaze Chamber", 1),
    ("Rattleguts Chamber", 1), ("Tombfinger Chamber", 1),
    ("Sporelacer Chamber", 1), ("Vermisplicer Chamber", 1),
    ("Haymaker Grip", 6), ("Splat Loader", 6),
]

# Manufacturing Requirements for every part above, read by hand off the real
# WARFRAME Wiki page for each (see README.md for why this is hand-curated
# rather than live-scraped). Credits are tracked here too since the Wiki
# lists them as part of the recipe, but the tracker's own resource
# checklist only makes sense for farmable materials -- see calculate()/
# RESOURCE_EXCLUDE below for where Credits gets dropped from that view.
#
# Several zaw/kitgun parts are NOT documented on the Wiki under their full
# display name -- e.g. "Balla Strike" has no such page; the real page is
# just "Balla". WIKI_PAGE_OVERRIDES (below) points the "Wiki ↗" link at the
# real page per part without changing the display name shown in the
# tracker, which still matches exactly what you asked for.
MANUFACTURING_RECIPES = {
    "Raplak Prism": {"Iradite": 40, "Murkray Liver": 2, "Tear Azurite": 10, "Esher Devar": 10},
    "Shwaak Prism": {"Iradite": 60, "Norg Brain": 2, "Marquise Veridos": 10, "Esher Devar": 15},
    "Granmu Prism": {"Cuthol Tendrils": 2, "Marquise Veridos": 10, "Star Crimzian": 6, "Breath Of The Eidolon": 3},
    "Rahn Prism": {"Iradite": 50, "Seram Beetle Shell": 2, "Tear Azurite": 20, "Esher Devar": 15},
    "Cantic Prism": {"Gyromag Systems": 3, "Longwinder Lathe Coagulant": 6, "Radiant Zodian": 3, "Vega Toroid": 3},
    "Lega Prism": {"Charamote Sagan Module": 6, "Gyromag Systems": 3, "Radiant Zodian": 3, "Vega Toroid": 3},
    "Klamora Prism": {"Gyromag Systems": 3, "Radiant Zodian": 3, "Tromyzon Entroplasma": 6, "Vega Toroid": 3},
    "Shraksun Scaffold": {"Cetus Wisp": 4, "Coprite Alloy": 60, "Grokdrul": 60, "Norg Brain": 2},
    "Phahd Scaffold": {"Grokdrul": 40, "Heart Nyth": 1, "Pyrotic Alloy": 60, "Seram Beetle Shell": 2},
    "Propa Scaffold": {"Atmo Systems": 2, "Calda Toroid": 3, "Hespazym Alloy": 30, "Tromyzon Entroplasma": 6},
    "Certus Brace": {"Marquise Thyst": 3, "Repeller Systems": 1, "Sola Toroid": 3, "Tromyzon Entroplasma": 6},
    "Lohrin Brace": {"Breath Of The Eidolon": 3, "Cetus Wisp": 5, "Cuthol Tendrils": 2, "Fish Oil": 20},
    "Balla Strike": {"Fish Scales": 15, "Nistlepod": 20, "Pyrotic Alloy": 60, "Tear Azurite": 10},
    "Cyath Strike": {"Breath Of The Eidolon": 1, "Fersteel Alloy": 20, "Fish Scales": 55, "Marquise Veridos": 6},
    "Dehtat Strike": {"Fersteel Alloy": 40, "Fish Scales": 45, "Maprico": 2, "Marquise Veridos": 8},
    "Dokrahm Strike": {"Fish Scales": 45, "Marquise Veridos": 7, "Nistlepod": 25, "Pyrotic Alloy": 60},
    "Kronsh Strike": {"Coprite Alloy": 60, "Esher Devar": 10, "Fish Scales": 45, "Grokdrul": 20},
    "Mewan Strike": {"Cetus Wisp": 1, "Fersteel Alloy": 20, "Fish Scales": 55, "Marquise Veridos": 6},
    "Ooltha Strike": {"Fish Scales": 25, "Iradite": 20, "Pyrotic Alloy": 60, "Tear Azurite": 10},
    "Rabvee Strike": {"Esher Devar": 10, "Fersteel Alloy": 20, "Fish Scales": 50, "Grokdrul": 35},
    "Sepfahn Strike": {"Condroc Wing": 15, "Coprite Alloy": 60, "Fish Scales": 55, "Tear Azurite": 10},
    "Plague Keewar Strike": {"Coprite Alloy": 60, "Esher Devar": 10, "Nano Spores": 1600, "Plastids": 700},
    "Plague Kripath Strike": {"Nano Spores": 1600, "Plastids": 700, "Pyrotic Alloy": 60, "Tear Azurite": 10},
    "Shtung Grip": {"Ferrite": 850, "Fish Scales": 55, "Grokdrul": 25, "Pyrotic Alloy": 60},
    "Vargeet Jai II Link": {"Condroc Wing": 2, "Khut-Khut Venom Sac": 5, "Nistlepod": 10, "Pyrotic Alloy": 20},
    "Catchmoon Chamber": {"Alloy Plate": 1700, "Mytocardia Spore": 15, "Scrubber Exa Brain": 10, "Travocyte Alloy": 20},
    "Gaze Chamber": {"Cryotic": 1200, "Kriller Thermal Laser": 40, "Tepa Nodule": 15, "Venerdo Alloy": 40},
    "Rattleguts Chamber": {"Eye-Eye Rotoblade": 10, "Gorgaricus Spore": 15, "Rubedo": 900, "Venerdo Alloy": 20},
    "Tombfinger Chamber": {"Axidrol Alloy": 20, "Circuits": 900, "Thermal Sludge": 15, "Tink Dissipator Coil": 10},
    "Sporelacer Chamber": {"Adramal Alloy": 20, "Benign Infested Tumor": 25, "Pustulite": 15, "Sporulate Sac": 10},
    "Vermisplicer Chamber": {"Benign Infested Tumor": 25, "Dendrite Blastoma": 10, "Ganglion": 15, "Tempered Bapholite": 20},
    "Haymaker Grip": {"Goblite Tears": 5, "Recaster Neural Relay": 10, "Scrap": 20, "Travocyte Alloy": 30},
    "Splat Loader": {"Auroxium Alloy": 40, "Scrap": 20, "Star Amarast": 10, "Synathid Ecosynth Analyzer": 5},
}

# Refinery / Foundry recipes for the resources that are refined from a raw
# material rather than picked up directly. Read from each resource's own
# Manufacturing Requirements on the Warframe Wiki (2026-09-26). "output" is
# how many you get per craft, "credits" the per-craft cost, and "primary" is
# the raw material that maps 1:1 onto the output (the "raw" bucket in this
# tracker is a count of that precursor). Ingredient quantities are per craft.
# Like every recipe here this is hand-copied data: check the in-game Foundry if
# a number ever looks off, and bump DATA_UPDATED when you edit it.
REFINERY_RECIPES = {
    "Adramal Alloy": {"output": 20, "credits": 1000, "primary": "Adramalium",
                      "ingredients": {"Adramalium": 20, "Travoride": 20, "Plastids": 600, "Lucent Teroglobe": 15}},
    "Auroxium Alloy": {"output": 20, "credits": 1000, "primary": "Auron",
                       "ingredients": {"Auron": 20, "Oxium": 600, "Morphics": 5}},
    "Axidrol Alloy": {"output": 20, "credits": 1000, "primary": "Axidite",
                      "ingredients": {"Axidite": 20, "Ferrite": 500, "Rubedo": 100}},
    "Coprite Alloy": {"output": 20, "credits": 1000, "primary": "Coprun",
                      "ingredients": {"Coprun": 20, "Ferrite": 400, "Rubedo": 50}},
    "Esher Devar": {"output": 10, "credits": 1000, "primary": "Devar", "ingredients": {"Devar": 10}},
    "Fersteel Alloy": {"output": 20, "credits": 1000, "primary": "Ferros",
                       "ingredients": {"Ferros": 20, "Plastids": 400, "Rubedo": 200}},
    "Goblite Tears": {"output": 10, "credits": 2500, "primary": "Goblite", "ingredients": {"Goblite": 10}},
    "Heart Nyth": {"output": 3, "credits": 10000, "primary": "Nyth", "ingredients": {"Nyth": 3}},
    "Hespazym Alloy": {"output": 20, "credits": 1000, "primary": "Hesperon",
                       "ingredients": {"Hesperon": 20, "Plastids": 300, "Morphics": 2}},
    "Marquise Thyst": {"output": 3, "credits": 10000, "primary": "Thyst", "ingredients": {"Thyst": 3}},
    "Marquise Veridos": {"output": 10, "credits": 2500, "primary": "Veridos", "ingredients": {"Veridos": 10}},
    "Pyrotic Alloy": {"output": 20, "credits": 1000, "primary": "Pyrol",
                      "ingredients": {"Pyrol": 20, "Cryotic": 200, "Rubedo": 50}},
    "Radiant Zodian": {"output": 3, "credits": 10000, "primary": "Zodian", "ingredients": {"Zodian": 3}},
    "Star Amarast": {"output": 6, "credits": 5000, "primary": "Amarast", "ingredients": {"Amarast": 6}},
    "Star Crimzian": {"output": 6, "credits": 5000, "primary": "Crimzian", "ingredients": {"Crimzian": 6}},
    "Tear Azurite": {"output": 10, "credits": 1000, "primary": "Azurite", "ingredients": {"Azurite": 10}},
    "Tempered Bapholite": {"output": 20, "credits": 1000, "primary": "Bapholite",
                           "ingredients": {"Bapholite": 20, "Pyrol": 20, "Nano Spores": 1600, "Lucent Teroglobe": 15}},
    "Travocyte Alloy": {"output": 20, "credits": 1000, "primary": "Travoride",
                        "ingredients": {"Travoride": 20, "Salvage": 500, "Plastids": 100}},
    "Venerdo Alloy": {"output": 20, "credits": 1000, "primary": "Venerol",
                      "ingredients": {"Venerol": 20, "Rubedo": 300, "Gallium": 2}},
}

# Syndicate layer: the refined resources cannot be made until you own the
# reusable Foundry blueprint, and every one of those blueprints is bought with
# Syndicate standing (the tracker's 65 resources have no Void Relic sources).
# Read from each resource's own Wiki page on 2026-09-26. "standing" is the cost,
# "rank" the rank needed with that faction. The Wiki page for Auroxium Alloy
# lists 7,500 in its text and 7,000 in its infobox; the higher figure is used.
SYNDICATE_SOURCES = {
    "Adramal Alloy": {"faction": "Entrati", "vendor": "Otak", "standing": 1000, "rank": "Neutral"},
    "Auroxium Alloy": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 7500, "rank": "Trusted"},
    "Axidrol Alloy": {"faction": "Solaris United", "vendor": "Smokefinger", "standing": 1000, "rank": "Neutral"},
    "Coprite Alloy": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 2500, "rank": "Offworlder"},
    "Esher Devar": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 2500, "rank": "Offworlder"},
    "Fersteel Alloy": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 5000, "rank": "Visitor"},
    "Goblite Tears": {"faction": "Solaris United", "vendor": "Smokefinger", "standing": 2000, "rank": "Outworlder"},
    "Heart Nyth": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 10000, "rank": "Surah"},
    "Hespazym Alloy": {"faction": "Solaris United", "vendor": "Smokefinger", "standing": 4000, "rank": "Rapscallion"},
    "Marquise Thyst": {"faction": "Solaris United", "vendor": "Smokefinger", "standing": 12000, "rank": "Cove"},
    "Marquise Veridos": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 5000, "rank": "Visitor"},
    "Pyrotic Alloy": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 500, "rank": "Neutral"},
    "Radiant Zodian": {"faction": "Solaris United", "vendor": "Smokefinger", "standing": 8000, "rank": "Doer"},
    "Star Amarast": {"faction": "Solaris United", "vendor": "Smokefinger", "standing": 4000, "rank": "Rapscallion"},
    "Star Crimzian": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 7500, "rank": "Trusted"},
    "Tear Azurite": {"faction": "Ostron", "vendor": "Old Man Suumbaat", "standing": 500, "rank": "Neutral"},
    "Tempered Bapholite": {"faction": "Entrati", "vendor": "Otak", "standing": 1000, "rank": "Neutral"},
    "Travocyte Alloy": {"faction": "Solaris United", "vendor": "Smokefinger", "standing": 1000, "rank": "Neutral"},
    "Venerdo Alloy": {"faction": "Solaris United", "vendor": "Smokefinger", "standing": 2000, "rank": "Outworlder"},
}

# Where each resource is actually found, hand-researched the same way as
# MANUFACTURING_RECIPES above. Most entries are a planet/location string
# straight off the resource's own infobox. A handful of resources aren't
# picked up in the field at all -- they're refined from a different raw
# resource (e.g. Tear Azurite is cut from a raw Azurite gem). For those,
# this points at the raw material by name rather than guessing at a
# planet, since the refining source's own Wiki page is the honest place
# to look up where *that* is found.
RESOURCE_LOCATIONS = {
    "Adramal Alloy": "Refined from Adramalium (see Adramalium's own Wiki page)",
    "Alloy Plate": "Venus, Phobos, Ceres, Jupiter, Pluto, and Sedna",
    "Atmo Systems": "Orb Vallis (Venus) -- Heist reward",
    "Auroxium Alloy": "Refined from Auron (see Auron's own Wiki page)",
    "Axidrol Alloy": "Refined from Axidite (see Axidite's own Wiki page)",
    "Benign Infested Tumor": "Cambion Drift (Deimos) -- cut from fish via Daughter",
    "Breath Of The Eidolon": "Plains of Eidolon (Earth) -- bounty reward",
    "Calda Toroid": "Orb Vallis (Venus) -- Enrichment Lab enemies and Scyto Raknoids",
    "Cetus Wisp": "Plains of Eidolon (Earth)",
    "Charamote Sagan Module": "Orb Vallis (Venus) -- fish part (Charamote)",
    "Circuits": "Venus, Ceres, and the Kuva Fortress",
    "Condroc Wing": "Plains of Eidolon (Earth)",
    "Coprite Alloy": "Refined from Coprun (see Coprun's own Wiki page)",
    "Cryotic": "Venus, Earth, Phobos, Europa, Neptune, Pluto -- Excavation missions",
    "Cuthol Tendrils": "Plains of Eidolon (Earth) -- fish part (Cuthol)",
    "Dendrite Blastoma": "Cambion Drift (Deimos) -- fish part (Vitreospina/Barbisteo)",
    "Esher Devar": "Refined from Devar (see Devar's own Wiki page)",
    "Eye-Eye Rotoblade": "Orb Vallis (Venus) -- fish part (Eye-Eye)",
    "Ferrite": "Mercury, Earth, Lua, Neptune, and the Void",
    "Fersteel Alloy": "Refined from Ferros (see Ferros's own Wiki page)",
    "Fish Oil": "Plains of Eidolon (Earth) -- fish part (any)",
    "Fish Scales": "Plains of Eidolon (Earth) -- fish part (any)",
    "Ganglion": "Cambion Drift (Deimos)",
    "Goblite Tears": "Refined from Goblite (see Goblite's own Wiki page)",
    "Gorgaricus Spore": "Orb Vallis (Venus)",
    "Grokdrul": "Plains of Eidolon (Earth)",
    "Gyromag Systems": "Orb Vallis (Venus) -- Heist reward",
    "Heart Nyth": "Refined from Nyth (see Nyth's own Wiki page)",
    "Hespazym Alloy": "Refined from Hesperon -- blueprint sold by Smokefinger in Fortuna (Venus)",
    "Iradite": "Plains of Eidolon (Earth)",
    "Khut-Khut Venom Sac": "Plains of Eidolon (Earth) -- fish part (Khut-Khut)",
    "Kriller Thermal Laser": "Orb Vallis (Venus) -- fish part (Kriller)",
    "Longwinder Lathe Coagulant": "Orb Vallis (Venus) -- fish part (Longwinder)",
    "Maprico": "Plains of Eidolon (Earth)",
    "Marquise Thyst": "Refined from Thyst (see Thyst's own Wiki page)",
    "Marquise Veridos": "Refined from Veridos (see Veridos's own Wiki page)",
    "Murkray Liver": "Plains of Eidolon (Earth) -- fish part (Murkray)",
    "Mytocardia Spore": "Orb Vallis (Venus)",
    "Nano Spores": "Saturn, Neptune, Eris, and Deimos",
    "Nistlepod": "Plains of Eidolon (Earth)",
    "Norg Brain": "Plains of Eidolon (Earth) -- fish part (Norg)",
    "Plastids": "Phobos, Saturn, Uranus, Pluto, and Eris",
    "Pustulite": "Cambion Drift (Deimos)",
    "Pyrotic Alloy": "Refined from Pyrol (see Pyrol's own Wiki page)",
    "Radiant Zodian": "Refined from Zodian (see Zodian's own Wiki page)",
    "Recaster Neural Relay": "Orb Vallis (Venus) -- fish part (Recaster)",
    "Repeller Systems": "Orb Vallis (Venus) -- Heist reward",
    "Rubedo": "Earth, Lua, Phobos, Europa, Pluto, Sedna, and the Void",
    "Scrap": "Orb Vallis (Venus) -- disassembled from any Servofish",
    "Scrubber Exa Brain": "Orb Vallis (Venus) -- fish part (Scrubber)",
    "Seram Beetle Shell": "Plains of Eidolon (Earth) -- fish part (Glappid)",
    "Sola Toroid": "Orb Vallis (Venus) -- Temple of Profit enemies and Kyta Raknoids",
    "Sporulate Sac": "Cambion Drift (Deimos) -- fish part (Glutinox)",
    "Star Amarast": "Refined from Amarast (see Amarast's own Wiki page)",
    "Star Crimzian": "Refined from Crimzian (see Crimzian's own Wiki page)",
    "Synathid Ecosynth Analyzer": "Orb Vallis (Venus) -- fish part (Synathid)",
    "Tear Azurite": "Refined from Azurite (see Azurite's own Wiki page)",
    "Tempered Bapholite": "Refined from Bapholite (see Bapholite's own Wiki page)",
    "Tepa Nodule": "Orb Vallis (Venus)",
    "Thermal Sludge": "Orb Vallis (Venus)",
    "Tink Dissipator Coil": "Orb Vallis (Venus) -- fish part (Tink)",
    "Travocyte Alloy": "Refined from Travoride (see Travoride's own Wiki page)",
    "Tromyzon Entroplasma": "Orb Vallis (Venus) -- fish part (Tromyzon)",
    "Vega Toroid": "Orb Vallis (Venus) -- Spaceport enemies and Mite Raknoids",
    "Venerdo Alloy": "Refined from Venerol (see Venerol's own Wiki page)",
}

# Round-2 idea (TODO.md, section X): "a small icon per planet/location on
# the resource location tooltip, for faster scanning" -- RESOURCE_LOCATIONS
# above is free-text (straight off each resource's Wiki infobox), not a
# structured field, so the icon is picked by matching a handful of
# substrings that actually occur in that text, checked in order (most
# specific first) with a generic fallback for an ordinary planet list.
_LOCATION_ICON_KEYWORDS = [
    ("Refined from", "\U0001F504"),  # 🔄 -- not farmed directly, refined from another resource
    ("Plains of Eidolon", "\U0001F33E"),  # 🌾 -- Cetus open world
    ("Orb Vallis", "❄️"),  # ❄️ -- Fortuna open world
    ("Cambion Drift", "\U0001F9EC"),  # 🧬 -- Deimos open world (Infested)
]
_LOCATION_ICON_DEFAULT = "\U0001FA90"  # 🪐 -- an ordinary planet/mission-node list


def location_icon(location_text):
    for keyword, icon in _LOCATION_ICON_KEYWORDS:
        if keyword in location_text:
            return icon
    return _LOCATION_ICON_DEFAULT


# Real Wiki page slugs that don't match the part's display name -- mostly
# zaw Strikes/Grips/Links/kitgun Chambers, which the Wiki documents under
# just the component's proper noun (e.g. "Balla", not "Balla Strike").
WIKI_PAGE_OVERRIDES = {
    "Balla Strike": "Balla",
    "Cyath Strike": "Cyath",
    "Dehtat Strike": "Dehtat",
    "Dokrahm Strike": "Dokrahm",
    "Kronsh Strike": "Kronsh",
    "Mewan Strike": "Mewan",
    "Ooltha Strike": "Ooltha",
    "Rabvee Strike": "Rabvee",
    "Sepfahn Strike": "Sepfahn",
    "Plague Keewar Strike": "Plague_Keewar",
    "Plague Kripath Strike": "Plague_Kripath",
    "Shtung Grip": "Shtung",
    "Vargeet Jai II Link": "Jai",
    "Catchmoon Chamber": "Catchmoon",
    "Gaze Chamber": "Gaze",
    "Rattleguts Chamber": "Rattleguts",
    "Tombfinger Chamber": "Tombfinger",
    "Sporelacer Chamber": "Sporelacer",
    "Vermisplicer Chamber": "Vermisplicer",
    "Haymaker Grip": "Haymaker",
    "Splat Loader": "Splat",
}

# Which build category each part belongs to. DEFAULT_PARTS above happens to
# already be grouped in this exact order (Amp parts, then Zaw parts, then
# Kitgun parts) -- built from that ordering rather than duplicating it, so
# there's one place to change if a part ever moves.
_AMP_PARTS = [
    "Raplak Prism", "Shwaak Prism", "Granmu Prism", "Rahn Prism", "Cantic Prism",
    "Lega Prism", "Klamora Prism", "Shraksun Scaffold", "Phahd Scaffold",
    "Propa Scaffold", "Certus Brace", "Lohrin Brace",
]
_ZAW_PARTS = [
    "Balla Strike", "Cyath Strike", "Dehtat Strike", "Dokrahm Strike",
    "Kronsh Strike", "Mewan Strike", "Ooltha Strike", "Rabvee Strike",
    "Sepfahn Strike", "Plague Keewar Strike", "Plague Kripath Strike",
    "Shtung Grip", "Vargeet Jai II Link",
]
_KITGUN_PARTS = [
    "Catchmoon Chamber", "Gaze Chamber", "Rattleguts Chamber", "Tombfinger Chamber",
    "Sporelacer Chamber", "Vermisplicer Chamber", "Haymaker Grip", "Splat Loader",
]

PART_CATEGORY = {}
PART_CATEGORY.update({name: "amp" for name in _AMP_PARTS})
PART_CATEGORY.update({name: "zaw" for name in _ZAW_PARTS})
PART_CATEGORY.update({name: "kitgun" for name in _KITGUN_PARTS})

# What each requested part actually does, one line each, read from the
# Warframe Wiki's Amp, Zaw and Kitgun pages on 2026-09-26. Stat lines are the
# Wiki's own figures; kitgun parts are described only in the Wiki's relative
# terms ("higher", "much lower"), so they are kept that way rather than given
# invented numbers.
PART_NOTES = {
    "Raplak Prism": "Semi-auto, long-range, precise hit-scan.",
    "Shwaak Prism": "Semi-auto, medium range, punch-through projectile.",
    "Granmu Prism": "Three-shot grenade burst.",
    "Rahn Prism": "Fully-auto, long range shots.",
    "Cantic Prism": "Quick and precise three-shot burst.",
    "Lega Prism": "Continuous, widespread jet of void fire with medium range.",
    "Klamora Prism": "Wide, short ranged beam.",
    "Shraksun Scaffold": "Alt-fire: short-range flak grenade.",
    "Phahd Scaffold": "Alt-fire: powerful shots bounce between targets.",
    "Propa Scaffold": "Alt-fire: timed explosive that also detonates on impact.",
    "Certus Brace": "+20% Amp critical chance.",
    "Lohrin Brace": "+12% Amp critical/status chance.",
    "Balla Strike": "Puncture. Base damage 224, speed +0.083, crit 18%/2.0x, status 18%, disposition 0.8.",
    "Cyath Strike": "Slash. Base damage 230, speed +0.000, crit 18%/2.0x, status 18%, disposition 0.95.",
    "Dehtat Strike": "Puncture. Base damage 224, speed +0.083, crit 18%/2.0x, status 18%, disposition 1.2.",
    "Dokrahm Strike": "Slash. Base damage 309, speed +0.083, crit 18%/2.0x, status 18%, disposition 0.75.",
    "Kronsh Strike": "Impact. Base damage 234, speed -0.067, crit 18%/2.0x, status 18%, disposition 1.3.",
    "Mewan Strike": "Slash. Base damage 224, speed -0.067, crit 18%/2.0x, status 18%, disposition 1.1.",
    "Ooltha Strike": "Slash. Base damage 224, speed +0.000, crit 18%/2.0x, status 18%, disposition 1.25.",
    "Rabvee Strike": "Impact. Base damage 234, speed -0.067, crit 18%/2.0x, status 18%, disposition 1.3.",
    "Sepfahn Strike": "Slash. Base damage 226, speed +0.000, crit 20%/2.0x, status 20%, disposition 0.7.",
    "Plague Keewar Strike": "Viral. Base damage 306, speed -0.033, crit 18%/2.0x, status 22%, disposition 0.85.",
    "Plague Kripath Strike": "Viral. Base damage 213, speed +0.033, crit 22%/2.2x, status 18%, disposition 0.6.",
    "Shtung Grip": "Two-handed: +28 damage bonus, base speed 0.783.",
    "Vargeet Jai II Link": "Speed +0.167, crit +7%, status -4%, damage -8.",
    "Catchmoon Chamber": "Impact and heat damage.",
    "Gaze Chamber": "Puncture and radiation damage (radiation only as a primary).",
    "Rattleguts Chamber": "Slash, puncture and radiation damage.",
    "Tombfinger Chamber": "Impact, puncture and radiation damage.",
    "Sporelacer Chamber": "Impact and toxin damage.",
    "Vermisplicer Chamber": "Impact, puncture, slash and toxin damage.",
    "Haymaker Grip": "Secondary grip: much higher damage, much lower fire rate and beam range, much higher recoil.",
    "Splat Loader": "Higher magazine, slower reload, much higher crit, much lower status.",
}

# Named builds worth tracking. Only combinations with a named source belong
# here: the Wiki's Amp page names "177" (Raplak, Propa, Certus). The Wiki's Zaw
# and Kitgun pages name no popular combination, so none is invented for them;
# add your own with the "My combos" box (state["combos"]).
KNOWN_COMBOS = [
    {"name": "177", "category": "amp", "parts": ["Raplak Prism", "Propa Scaffold", "Certus Brace"],
     "source": "the Warframe Wiki's Amp page"},
]
COMBO_MAX_PARTS = 5
COMBO_NAME_MAX = 30
COMBO_MAX_COUNT = 20

# One short, honest comment per build type -- assembly mechanics and what
# each component slot actually controls, not a "current meta" claim.
CATEGORY_INFO = {
    "amp": {
        "label": "Amp builds",
        "note": ("Prism sets damage type/crit stats, Scaffold sets fire mode "
                 "and multishot, Brace sets status/fire-rate/charge stats -- "
                 "any Prism+Scaffold+Brace combo below is a valid Amp, mix "
                 "freely rather than treating these as fixed sets."),
    },
    "zaw": {
        "label": "Zaw builds",
        "note": ("Strike is the blade (damage type/stance slot), Grip sets "
                 "the base stat priorities, Link is mostly a stat-balance "
                 "modifier -- this list pairs every Strike with the same "
                 "Shtung Grip + Vargeet Jai II Link, so building a specific "
                 "Zaw just needs 1 Strike + 1 Grip + 1 Link."),
    },
    "kitgun": {
        "label": "Kitgun builds",
        "note": ("Chamber sets damage type and crit/status stats, Grip sets "
                 "fire mode, Loader sets ammo/reload -- this list pairs "
                 "every Chamber with the same Haymaker Grip + Splat Loader, "
                 "so building a specific Kitgun just needs 1 Chamber + 1 "
                 "Grip + 1 Loader."),
    },
}


def slug(name):
    return name.replace(" ", "_")


def wiki_url(name):
    return WIKI_BASE + WIKI_PAGE_OVERRIDES.get(name, slug(name))


# Static reference data, built once at import time -- never persisted
# through get_state()/load_state(), since it's derived entirely from
# MANUFACTURING_RECIPES above and is always current the instant this file
# is loaded. This replaces the old app.py's load_recipes()/"Reload Recipe
# Data" button entirely: there's no more live-vs-stored distinction to
# sync, so that whole step is gone.
RECIPES = {
    name: {"ingredients": dict(ingredients), "wiki": wiki_url(name)}
    for name, ingredients in MANUFACTURING_RECIPES.items()
}


def _normalize_resource_key(name):
    """Strips spaces/punctuation and lowercases, so e.g. "Tear Azurite"
    matches an internal game path ending in ".../TearAzurite" regardless
    of exact casing/separator conventions -- see import_last_data()'s own
    docstring for why this is a deliberately fuzzy tail-match rather than
    a hardcoded exact-path lookup table."""
    return "".join(ch for ch in name if ch.isalnum()).lower()


_RESOURCE_MATCH_KEYS = {_normalize_resource_key(name): name for name in RESOURCE_LOCATIONS}


def flatten_recipe(item_name, multiplier, out=None, stack=None):
    """Recursively converts a component requirement into lowest-level
    resources. If a resource has its own crafting recipe in RECIPES, it is
    expanded; otherwise it remains a direct inventory resource. None of the
    resources in MANUFACTURING_RECIPES above currently have their own
    recipe entry here (the raw ores/gems/alloys they need would be a
    second research pass -- see README.md/TODO2.md's X section), so this
    stays ready for that without needing any change when it's added."""
    if out is None:
        out = {}
    if stack is None:
        stack = set()

    if item_name in stack:
        # Prevent circular data from breaking the tracker.
        out[item_name] = out.get(item_name, 0) + multiplier
        return out

    recipe = RECIPES.get(item_name)
    if not recipe or not recipe.get("ingredients"):
        out[item_name] = out.get(item_name, 0) + multiplier
        return out

    stack = set(stack)
    stack.add(item_name)

    for ingredient, qty in recipe["ingredients"].items():
        flatten_recipe(ingredient, multiplier * qty, out, stack)

    return out


def resource_usage(resource):
    """Every requested part whose own recipe needs `resource`, and how much
    each one needs per single craft -- a plain reverse lookup over
    MANUFACTURING_RECIPES. Deliberately NOT scaled by how many of that part
    you still need to build -- this is "where does this resource show up
    across my whole build list", a fixed reference fact, not a live need
    number (that's what the resource row's own "needed" column already
    is)."""
    usage = []
    for part_name, _ in DEFAULT_PARTS:
        ingredients = RECIPES.get(part_name, {}).get("ingredients", {})
        if resource in ingredients:
            usage.append({"name": part_name, "qty": ingredients[resource]})
    return usage


def refinery_plan(resource, short, raw_have=0):
    """What refining `short` units of a refined resource takes, or None when it
    is not a refined resource or nothing is short. The number of Foundry crafts
    is the shortfall rounded up to whole crafts (`output` per craft). Every
    other ingredient scales with the crafts; the raw precursor you already hold
    (`raw_have`) is subtracted from the primary material to gather (never below
    zero). Credits are reported separately, like everywhere else in the tracker."""
    recipe = REFINERY_RECIPES.get(resource)
    if recipe is None or short <= 0:
        return None
    crafts = -(-int(short) // recipe["output"])
    ingredients = {}
    for name, qty in recipe["ingredients"].items():
        needed = qty * crafts
        if name == recipe["primary"]:
            needed = max(0, needed - max(0, int(raw_have)))
        if needed:
            ingredients[name] = needed
    return {
        "crafts": crafts,
        "produces": crafts * recipe["output"],
        "credits": recipe["credits"] * crafts,
        "primary": recipe["primary"],
        "ingredients": ingredients,
    }


def refinery_totals(resources):
    """Everything to gather to refine every resource that is still short: a
    dict of material -> quantity (credits under "Credits"), summed over the
    rows' own refinery plans."""
    totals = {}
    credits = 0
    for row in resources:
        plan = row.get("refinery")
        if not plan:
            continue
        credits += plan["credits"]
        for name, qty in plan["ingredients"].items():
            totals[name] = totals.get(name, 0) + qty
    if credits:
        totals["Credits"] = credits
    return totals


def has_enough_for_one(ingredients, inventory):
    """Whether the inventory (built + raw, pooled the same way the resource
    checklist pools them) covers a single craft of `ingredients`. Credits
    are skipped -- they're not a farmable material this tracker tracks a
    "have" count for."""
    if not ingredients:
        return False
    for resource, qty in ingredients.items():
        if resource == "Credits":
            continue
        inv = inventory.get(resource, {})
        have = int(inv.get("built", 0)) + int(inv.get("raw", 0))
        if have < qty:
            return False
    return True


# One-time migration bootstrap: your real progress from the old Flask
# app's data.json (24/33 parts owned, 55 tracked resources), carried over
# so the rearchitect from Flask to Pyodide/save-widget doesn't lose any of
# it. This constant is only ever read once, below, to seed the fresh
# `state` a brand-new page load starts with -- the moment you click Save
# (or sign in, if you're already signed in elsewhere on this site), your
# real save code/account becomes the source of truth and this stops
# mattering. Safe to delete once you've confirmed your first save/load
# round-trips correctly.
_MIGRATED_FROM_DATA_JSON = {'parts': {'Raplak Prism': {'target': 1, 'owned': 1}, 'Shwaak Prism': {'target': 1, 'owned': 1}, 'Granmu Prism': {'target': 1, 'owned': 1}, 'Rahn Prism': {'target': 1, 'owned': 0}, 'Cantic Prism': {'target': 1, 'owned': 0}, 'Lega Prism': {'target': 1, 'owned': 0}, 'Klamora Prism': {'target': 1, 'owned': 0}, 'Shraksun Scaffold': {'target': 1, 'owned': 1}, 'Phahd Scaffold': {'target': 3, 'owned': 0}, 'Propa Scaffold': {'target': 3, 'owned': 1}, 'Certus Brace': {'target': 6, 'owned': 1}, 'Lohrin Brace': {'target': 1, 'owned': 1}, 'Balla Strike': {'target': 1, 'owned': 1}, 'Cyath Strike': {'target': 1, 'owned': 1}, 'Dehtat Strike': {'target': 1, 'owned': 1}, 'Dokrahm Strike': {'target': 1, 'owned': 1}, 'Kronsh Strike': {'target': 1, 'owned': 1}, 'Mewan Strike': {'target': 1, 'owned': 1}, 'Ooltha Strike': {'target': 1, 'owned': 0}, 'Rabvee Strike': {'target': 1, 'owned': 1}, 'Sepfahn Strike': {'target': 1, 'owned': 1}, 'Plague Keewar Strike': {'target': 1, 'owned': 1}, 'Plague Kripath Strike': {'target': 1, 'owned': 1}, 'Shtung Grip': {'target': 11, 'owned': 2}, 'Vargeet Jai II Link': {'target': 11, 'owned': 4}, 'Catchmoon Chamber': {'target': 1, 'owned': 1}, 'Gaze Chamber': {'target': 1, 'owned': 0}, 'Rattleguts Chamber': {'target': 1, 'owned': 1}, 'Tombfinger Chamber': {'target': 1, 'owned': 0}, 'Sporelacer Chamber': {'target': 1, 'owned': 1}, 'Vermisplicer Chamber': {'target': 1, 'owned': 1}, 'Haymaker Grip': {'target': 6, 'owned': 1}, 'Splat Loader': {'target': 6, 'owned': 0}}, 'inventory': {'Adramal Alloy': {'raw': 0, 'built': 20}, 'Alloy Plate': {'raw': 0, 'built': 1700}, 'Axidrol Alloy': {'raw': 0, 'built': 20}, 'Benign Infested Tumor': {'raw': 0, 'built': 50}, 'Breath Of The Eidolon': {'raw': 0, 'built': 3}, 'Calda Toroid': {'raw': 0, 'built': 2}, 'Cetus Wisp': {'raw': 0, 'built': 9}, 'Charamote Sagan Module': {'raw': 0, 'built': 6}, 'Circuits': {'raw': 0, 'built': 900}, 'Condroc Wing': {'raw': 0, 'built': 14}, 'Coprite Alloy': {'raw': 0, 'built': 0}, 'Cryotic': {'raw': 0, 'built': 1200}, 'Cuthol Tendrils': {'raw': 0, 'built': 2}, 'Dendrite Blastoma': {'raw': 0, 'built': 10}, 'Esher Devar': {'raw': 0, 'built': 15}, 'Eye-Eye Rotoblade': {'raw': 0, 'built': 10}, 'Ferrite': {'raw': 0, 'built': 8500}, 'Fish Oil': {'raw': 0, 'built': 20}, 'Fish Scales': {'raw': 0, 'built': 258}, 'Ganglion': {'raw': 0, 'built': 15}, 'Goblite Tears': {'raw': 0, 'built': 30}, 'Gorgaricus Spore': {'raw': 0, 'built': 15}, 'Grokdrul': {'raw': 0, 'built': 405}, 'Gyromag Systems': {'raw': 0, 'built': 2}, 'Heart Nyth': {'raw': 0, 'built': 3}, 'Hespazym Alloy': {'raw': 0, 'built': 60}, 'Iradite': {'raw': 0, 'built': 13}, 'Khut-Khut Venom Sac': {'raw': 0, 'built': 35}, 'Kriller Thermal Laser': {'raw': 0, 'built': 25}, 'Longwinder Lathe Coagulant': {'raw': 0, 'built': 6}, 'Marquise Thyst': {'raw': 0, 'built': 13}, 'Mytocardia Spore': {'raw': 0, 'built': 15}, 'Nano Spores': {'raw': 0, 'built': 3200}, 'Nistlepod': {'raw': 0, 'built': 70}, 'Norg Brain': {'raw': 0, 'built': 2}, 'Plastids': {'raw': 0, 'built': 1400}, 'Pustulite': {'raw': 0, 'built': 15}, 'Pyrotic Alloy': {'raw': 0, 'built': 50}, 'Radiant Zodian': {'raw': 0, 'built': 9}, 'Recaster Neural Relay': {'raw': 0, 'built': 27}, 'Rubedo': {'raw': 0, 'built': 900}, 'Scrap': {'raw': 0, 'built': 240}, 'Scrubber Exa Brain': {'raw': 0, 'built': 10}, 'Seram Beetle Shell': {'raw': 0, 'built': 8}, 'Sola Toroid': {'raw': 0, 'built': 4}, 'Sporulate Sac': {'raw': 0, 'built': 10}, 'Star Amarast': {'raw': 0, 'built': 48}, 'Tear Azurite': {'raw': 0, 'built': 40}, 'Tepa Nodule': {'raw': 0, 'built': 15}, 'Thermal Sludge': {'raw': 0, 'built': 15}, 'Tink Dissipator Coil': {'raw': 0, 'built': 4}, 'Travocyte Alloy': {'raw': 0, 'built': 25}, 'Vega Toroid': {'raw': 0, 'built': 5}, 'Venerdo Alloy': {'raw': 0, 'built': 60}, 'Tempered Bapholite': {'raw': 0, 'built': 20}}}

# Player state -- the only thing get_state()/load_state() actually
# round-trip. A fresh page load always starts here (seeded from the
# migration data above); save-widget.js then either autoloads the
# signed-in account's own save or restores whatever save code is
# remembered in this browser, same as every other game -- both of which
# overwrite this bootstrap the instant a real save exists.
state = {
    "parts": {
        name: dict(_MIGRATED_FROM_DATA_JSON["parts"].get(name, {"target": qty, "owned": 0}))
        for name, qty in DEFAULT_PARTS
    },
    "inventory": {k: dict(v) for k, v in _MIGRATED_FROM_DATA_JSON["inventory"].items()},
    # X: per-part free-text "note to self" (name -> str), and the two saved
    # view preferences. Both are optional in old saves -- load_state()
    # validates/defaults them.
    "notes": {},
    "prefs": {"sort": "category", "hide_complete": False},
    # Session farming log: every increase in a resource's total on hand
    # (typed in, or found by an import), newest last. See log_gain().
    "farm_log": [],
    # Refined-resource name -> True/False when the player ticked "blueprint
    # owned" themselves (see blueprint_owned()).
    "blueprints": {},
    # Player-defined combos for the build comparison: [{"name", "parts"}].
    "combos": [],
    # Batch A planner features (2026-09-27). Every key below is written by
    # get_state() only when non-default and fully validated by load_state();
    # see _extra_state()/_load_extra_state().
    "pins": [],
    "timers": [],
    "budget": {"credits": 0, "endo": 0},
    "mastery": {"base": 0, "items": []},
    "completed": [],
    "trader": {"last": "", "watch": []},
    "enough": [],
    "tag_labels": [],
    "tags": {},
    "goals": [],
    "history": [],
    "checklist": {"items": [], "ticks": {"daily": {"stamp": "", "done": []}, "weekly": {"stamp": "", "done": []}}},
    "loadouts": {},
    "inv_source": {},
    "edit_log": [],
}

FARM_LOG_MAX = 300
_LOG_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

# UI-only (not saved): current search text, and Wiki links already clicked
# this session.
_search = {"text": ""}
_visited_wiki = set()
# UI-only: the colour-tag filter, the open tools tab, and the last-rendered
# signature the minute tick compares against.
_filters = {"tag": ""}
_ui = {"tab": "timers", "sig": None}


def _now_stamp():
    """UTC "YYYY-MM-DD HH:MM" for a farming-log entry. One place, so tests can
    swap it for a fixed clock."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def log_gain(resource, before, after):
    """Records that the total on hand of `resource` (built + raw) rose from
    `before` to `after`. Decreases are not logged: spending on a build or
    correcting a typo down is not farming. Same-minute gains of the same
    resource merge into one entry. The log is capped at FARM_LOG_MAX."""
    gained = int(after) - int(before)
    if gained <= 0:
        return False
    stamp = _now_stamp()
    log = state["farm_log"]
    if log and log[-1]["r"] == resource and log[-1]["t"] == stamp:
        log[-1]["d"] += gained
    else:
        log.append({"t": stamp, "r": resource, "d": gained})
    del log[:-FARM_LOG_MAX]
    return True


def farm_log_summary(today=None):
    """Totals gained per resource: {"today": {...}, "all": {...}} for the
    logged history ("today" is the UTC date of `today`, default now)."""
    today_prefix = (today or _now_stamp())[:10]
    summary = {"today": {}, "all": {}}
    for entry in state["farm_log"]:
        summary["all"][entry["r"]] = summary["all"].get(entry["r"], 0) + entry["d"]
        if entry["t"].startswith(today_prefix):
            summary["today"][entry["r"]] = summary["today"].get(entry["r"], 0) + entry["d"]
    return summary


def farm_log_text(limit=10):
    if not state["farm_log"]:
        return "Nothing logged yet. Gains show up here when you raise a resource's count."
    summary = farm_log_summary()

    def top(totals):
        ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        return ", ".join(f"{name} +{qty}" for name, qty in ranked) or "nothing"

    lines = [f"Gained today: {top(summary['today'])}.", f"Gained overall: {top(summary['all'])}."]
    lines.append("Latest: " + "; ".join(
        f"{e['t']} {e['r']} +{e['d']}" for e in reversed(state["farm_log"][-limit:])
    ))
    return " ".join(lines)


def days_since(date_str, today=None):
    """Whole days between an ISO date string and `today` (default: the real
    today). None if the string isn't a valid ISO date; never negative."""
    try:
        then = date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None
    return max(0, ((today or date.today()) - then).days)


def missing_for_one(ingredients, inventory):
    """Resource -> units short for a single craft of `ingredients`, pooling
    built + raw the same way has_enough_for_one() does. Credits skipped."""
    missing = {}
    for resource, qty in ingredients.items():
        if resource == "Credits":
            continue
        inv = inventory.get(resource, {})
        have = int(inv.get("built", 0)) + int(inv.get("raw", 0))
        if have < qty:
            missing[resource] = qty - have
    return missing


def whats_blocking(components):
    """The single resource currently short for the most unfinished parts
    -> (resource, parts_blocked, [part names]) or None if nothing is
    blocked. Ties break on total units short, then name."""
    blocked = {}
    for part in components:
        if part["complete"]:
            continue
        for resource, short in part["missing"].items():
            entry = blocked.setdefault(resource, {"parts": [], "short": 0})
            entry["parts"].append(part["name"])
            entry["short"] += short
    if not blocked:
        return None
    best = min(blocked, key=lambda r: (-len(blocked[r]["parts"]), -blocked[r]["short"], r))
    return best, len(blocked[best]["parts"]), blocked[best]["parts"]


def category_progress(components):
    """category -> (done, total), in Amp/Zaw/Kitgun order."""
    out = {}
    for cat in ("amp", "zaw", "kitgun"):
        group = [p for p in components if p["category"] == cat]
        out[cat] = (sum(1 for p in group if p["complete"]), len(group))
    return out


def arrange_components(components, sort_mode="category", query="", hide_complete=False, tag=""):
    """Filters (search text, hide-completed) and orders the component list.
    "category" keeps the fixed DEFAULT_PARTS order; "priority" ranks by
    closest-to-buildable (fewest resources short for one craft, finished
    parts last). `tag` keeps only parts carrying that colour-tag label."""
    query = (query or "").strip().lower()
    rows = [
        p for p in components
        if (not hide_complete or not p["complete"])
        and (not query or query in p["name"].lower())
        and (not tag or state["tags"].get(p["name"]) == tag)
    ]
    if sort_mode == "priority":
        rows.sort(key=lambda p: (p["complete"], len(p["missing"]), sum(p["missing"].values())))
    elif sort_mode == "name":
        rows.sort(key=lambda p: p["name"].lower())
    elif sort_mode == "remaining":
        rows.sort(key=lambda p: (-p["remaining"], p["name"].lower()))
    return rows  # list.sort is stable, so ties keep the fixed order


# Route planner: the places a resource's location text can name. The text is
# free-form (straight from each Wiki infobox), so places are found by name after
# removing "(...)" asides, which only ever restate the open world's planet
# ("Plains of Eidolon (Earth)"). Resources refined from another material name no
# place and are left out of the planner (they are farmed at their precursor).
ROUTE_PLACES = [
    "Plains of Eidolon", "Orb Vallis", "Cambion Drift", "Kuva Fortress", "Mercury", "Venus", "Earth", "Lua",
    "Mars", "Phobos", "Ceres", "Jupiter", "Europa", "Saturn", "Uranus", "Neptune", "Pluto", "Sedna",
    "Eris", "Deimos", "Void",
]


def location_places(location_text):
    """The places a resource's location text names, in ROUTE_PLACES order."""
    if not location_text or location_text.startswith("Refined from"):
        return []
    text = re.sub(r"\([^)]*\)", "", location_text).split(" -- ")[0]
    return [place for place in ROUTE_PLACES if place in text]


def route_suggestions(resources, top=3):
    """Which single places would cover the most resources you are still short
    on, best first (most resources, then most units short, then name). Each item
    is {"place", "resources": [names], "units"}."""
    by_place = {}
    for row in resources:
        if row["built_short"] <= 0:
            continue
        for place in location_places(row["location"]):
            entry = by_place.setdefault(place, {"place": place, "resources": [], "units": 0})
            entry["resources"].append(row["name"])
            entry["units"] += row["built_short"]
    ranked = sorted(by_place.values(), key=lambda e: (-len(e["resources"]), -e["units"], e["place"]))
    return ranked[:top]


def route_text(resources):
    picks = route_suggestions(resources)
    if not picks:
        return ""
    best = picks[0]
    names = ", ".join(best["resources"][:6]) + (" and more" if len(best["resources"]) > 6 else "")
    text = f"Best single stop to farm next: {best['place']}, covering {len(best['resources'])} short resource(s) ({names})."
    if len(picks) > 1:
        text += " Then: " + "; ".join(f"{p['place']} ({len(p['resources'])})" for p in picks[1:]) + "."
    return text


# Resource value heuristic. There is no price or drop-rate data here, so rarity
# is judged from what the location text does say: how many places the resource
# drops (five or more is common), and phrases that mark a gated or one-off
# source (a heist reward, a bounty reward, a fish part, a specific enemy). It is
# a prioritising hint, not a market value: "rare" means hard to come by for this
# list, not that it sells for much.
COMMON_MIN_PLACES = 5
RARE_SOURCE_MARKERS = ("Heist reward", "bounty reward", "fish part", "Enrichment Lab", "Temple of Profit", "Spaceport enemies")


def resource_rarity(location_text):
    """"common", "uncommon" or "rare" for a resource's location text, or
    "refined" for one refined from another material (its rarity is its
    precursor's)."""
    if not location_text or location_text.startswith("Refined from"):
        return "refined"
    if any(marker in location_text for marker in RARE_SOURCE_MARKERS):
        return "rare"
    places = len(location_places(location_text))
    if places >= COMMON_MIN_PLACES:
        return "common"
    if places <= 1:
        return "rare"
    return "uncommon"


# Market prices (Warframe.market, via the site's own backend because that API
# sends no CORS headers). Only the refined gems are tradeable there; the plain
# resources, alloys and the zaw/kitgun/amp parts are not. UI-only, never saved.
_market = {"prices": {}}


def market_slug(resource):
    return "_".join(re.findall(r"[a-z0-9]+", resource.lower()))


def set_market_prices(json_text):
    """Called by index.html with the backend's /market/prices JSON text. Keeps
    only whole-number-or-decimal positive prices for known resources; anything
    else is ignored. Returns how many resources now have a price."""
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return 0
    prices = data.get("prices") if isinstance(data, dict) else None
    _market["prices"] = {}
    if isinstance(prices, dict):
        for resource in RESOURCE_LOCATIONS:
            entry = prices.get(market_slug(resource))
            value = entry.get("lowest_sell") if isinstance(entry, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                _market["prices"][resource] = value
    render()
    return len(_market["prices"])


def market_value_short(resources):
    """(total platinum, resources counted) for the tradeable resources you are
    still short on, at the lowest online sell price each."""
    total, counted = 0, 0
    for row in resources:
        price = _market["prices"].get(row["name"])
        if price and row["built_short"] > 0:
            total += price * row["built_short"]
            counted += 1
    return total, counted


def market_text(resources):
    total, counted = market_value_short(resources)
    if not counted:
        return ""
    return (
        f"Buying what you are short on for the {counted} tradeable resource(s) would cost about {total:,.0f} "
        "platinum at today's lowest online sell prices (Warframe.market; prices refresh every few minutes)."
    )


def blueprint_owned(resource, inventory=None):
    """Whether this refined resource's blueprint counts as bought. An explicit
    tick (state["blueprints"]) wins; otherwise holding any of the refined
    resource is taken as proof you can already make it."""
    explicit = state["blueprints"].get(resource)
    if isinstance(explicit, bool):
        return explicit
    inv = (inventory if inventory is not None else state["inventory"]).get(resource, {})
    return int(inv.get("built", 0)) > 0


def standing_needed(resources):
    """Standing still to earn per faction for the blueprints of refined
    resources you are short on and do not own yet: {faction: standing}."""
    totals = {}
    for row in resources:
        source = SYNDICATE_SOURCES.get(row["name"])
        if not source or row["built_short"] <= 0 or blueprint_owned(row["name"]):
            continue
        totals[source["faction"]] = totals.get(source["faction"], 0) + source["standing"]
    return totals


def syndicate_text(resources):
    totals = standing_needed(resources)
    if not totals:
        return ""
    return "Blueprint standing still to earn: " + " · ".join(
        f"{faction} {standing:,}" for faction, standing in sorted(totals.items())
    ) + "."


def all_combos():
    """The built-in named combos followed by the player's own."""
    return [dict(c, custom=False) for c in KNOWN_COMBOS] + [
        {"name": c["name"], "category": PART_CATEGORY.get(c["parts"][0], "other"), "parts": list(c["parts"]),
         "source": "your own list", "custom": True}
        for c in state["combos"]
    ]


def add_combo(name, part_names):
    """Saves a custom combo. Returns (ok, message)."""
    name = str(name or "").strip()[:COMBO_NAME_MAX]
    parts = [p.strip() for p in part_names if p and p.strip()] if isinstance(part_names, list) else []
    if not name:
        return False, "Give the combo a name."
    if not parts or len(parts) > COMBO_MAX_PARTS:
        return False, f"A combo needs 1 to {COMBO_MAX_PARTS} parts."
    unknown = [p for p in parts if p not in RECIPES]
    if unknown:
        return False, "Unknown part(s): " + ", ".join(unknown)
    if len(set(parts)) != len(parts):
        return False, "List each part once."
    if len(state["combos"]) >= COMBO_MAX_COUNT:
        return False, "That is the maximum number of saved combos."
    if any(c["name"].lower() == name.lower() for c in all_combos()):
        return False, "A combo with that name already exists."
    state["combos"].append({"name": name, "parts": parts})
    return True, f"Saved combo {name}."


def remove_combo(name):
    before = len(state["combos"])
    state["combos"] = [c for c in state["combos"] if c["name"] != name]
    _prune_build_refs()
    return len(state["combos"]) != before


def combo_progress(combo, components):
    """How close one combo is: which parts are built, which are not, and what
    the unbuilt ones are still short of for one craft each."""
    by_name = {c["name"]: c for c in components}
    built, missing_parts, short = [], [], {}
    for part in combo["parts"]:
        info = by_name.get(part)
        if info is not None and info["owned"] >= 1:
            built.append(part)
            continue
        missing_parts.append(part)
        for resource, qty in missing_for_one(RECIPES.get(part, {}).get("ingredients", {}), state["inventory"]).items():
            short[resource] = short.get(resource, 0) + qty
    return {
        "combo": combo, "built": built, "missing_parts": missing_parts, "short": short,
        "units_short": sum(short.values()), "complete": not missing_parts,
    }


def compare_combos(components):
    """Every combo ranked by how close it is: fewest parts still to build, then
    fewest resource units short, then name. Finished combos come last."""
    rows = [combo_progress(c, components) for c in all_combos()]
    rows.sort(key=lambda r: (r["complete"], len(r["missing_parts"]), r["units_short"], r["combo"]["name"].lower()))
    return rows


def combos_text(components):
    rows = compare_combos(components)
    if not rows:
        return "No combos to compare yet."
    lines = []
    for r in rows:
        head = f"{r['combo']['name']} ({r['combo']['category']}): {len(r['built'])}/{len(r['combo']['parts'])} parts built"
        if r["complete"]:
            lines.append(head + ", complete.")
        else:
            lines.append(
                head + "; still to build " + ", ".join(r["missing_parts"])
                + (f" (short {r['units_short']} resource units)" if r["units_short"] else " (all resources on hand)")
                + "."
            )
    return "\n".join(lines)


def shopping_list_text(resources):
    """Plain-text list of exactly what's still needed (built/refined stock
    is what satisfies a requirement, same as the resource checklist)."""
    short = [r for r in resources if r["built_short"] > 0]
    if not short:
        return "Nothing left to farm -- every requirement is covered."
    lines = [f"Warframe build shopping list ({len(short)} resources)"]
    for r in short:
        line = f"- {r['name']} x{r['built_short']}"
        if r["raw_have"]:
            line += f" ({r['raw_have']} raw on hand to refine)"
        line += f" -- {r['location']}"
        lines.append(line)
    return "\n".join(lines)


def calculate():
    parts = state["parts"]
    inventory = state["inventory"]
    notes = state["notes"]

    raw_need = {}
    component_status = []

    for name, default_target in DEFAULT_PARTS:
        info = parts.get(name, {})
        target = int(info.get("target", default_target))
        owned = min(int(info.get("owned", 0)), target)

        remaining_parts = max(0, target - owned)
        ingredients = RECIPES.get(name, {}).get("ingredients", {})
        component_status.append({
            "missing": missing_for_one(ingredients, inventory) if remaining_parts > 0 else {},
            "note": notes.get(name, ""),
            "name": name,
            "target": target,
            "owned": owned,
            "remaining": remaining_parts,
            "complete": remaining_parts == 0,
            "wiki": wiki_url(name),
            "can_build": remaining_parts > 0 and has_enough_for_one(ingredients, inventory),
            "category": PART_CATEGORY.get(name, "other"),
        })

        if remaining_parts and name in RECIPES:
            flattened = flatten_recipe(name, remaining_parts)
            for resource, qty in flattened.items():
                raw_need[resource] = raw_need.get(resource, 0) + qty

    # Credits are part of every recipe on the Wiki but aren't a farmable
    # material worth tracking a checklist row for.
    raw_need.pop("Credits", None)

    resource_rows = []
    for resource, needed in sorted(raw_need.items()):
        inv = inventory.get(resource, {})
        built_have = int(inv.get("built", 0))
        raw_have = int(inv.get("raw", 0))
        remaining_after_built = max(0, needed - built_have)

        resource_rows.append({
            "name": resource,
            "needed": needed,
            "built_have": built_have,
            "raw_have": raw_have,
            "built_short": remaining_after_built,
            "complete": built_have >= needed,
            "wiki": wiki_url(resource),
            "used_in": resource_usage(resource),
            "location": RESOURCE_LOCATIONS.get(resource, "Unknown -- not yet researched"),
            "grindy": needed >= GRINDY_THRESHOLD,
            "refinery": refinery_plan(resource, remaining_after_built, raw_have),
            "rarity": resource_rarity(RESOURCE_LOCATIONS.get(resource, "")),
            "market_price": _market["prices"].get(resource),
            "enough": resource in state["enough"],
        })

    return component_status, resource_rows


def get_state():
    return {
        "parts": copy.deepcopy(state["parts"]),
        "inventory": copy.deepcopy(state["inventory"]),
        "notes": dict(state["notes"]),
        "prefs": dict(state["prefs"]),
        **({"farm_log": [dict(e) for e in state["farm_log"]]} if state["farm_log"] else {}),
        **({"blueprints": dict(state["blueprints"])} if state["blueprints"] else {}),
        **({"combos": [{"name": c["name"], "parts": list(c["parts"])} for c in state["combos"]]} if state["combos"] else {}),
        **_extra_state(),
    }


def load_state(data):
    """Merges the loaded save onto the live state key-by-key (per part/
    resource), rather than a wholesale replace -- a save written before a
    part was added to DEFAULT_PARTS (or missing a resource entirely)
    shouldn't crash or silently drop the parts/resources it DOES know
    about. Same defensive-merge shape as every other game's load_state()
    in this hub (see e.g. games/canopy/game.py)."""
    saved_parts = data.get("parts", {})
    for name, default_target in DEFAULT_PARTS:
        part = state["parts"].setdefault(name, {"target": default_target, "owned": 0})
        saved = saved_parts.get(name, {})
        if "target" in saved:
            part["target"] = max(0, int(saved["target"]))
        if "owned" in saved:
            part["owned"] = max(0, int(saved["owned"]))

    saved_inventory = data.get("inventory", {})
    for resource, amounts in saved_inventory.items():
        inv = state["inventory"].setdefault(resource, {"raw": 0, "built": 0})
        if "raw" in amounts:
            inv["raw"] = max(0, int(amounts["raw"]))
        if "built" in amounts:
            inv["built"] = max(0, int(amounts["built"]))

    # Old saves have neither field -- default, and drop anything malformed.
    saved_notes = data.get("notes")
    if isinstance(saved_notes, dict):
        state["notes"] = {
            name: text[:NOTE_MAX_LEN] for name, text in saved_notes.items()
            if name in RECIPES and isinstance(text, str) and text.strip()
        }
    saved_log = data.get("farm_log")
    state["farm_log"] = []
    if isinstance(saved_log, list):
        for entry in saved_log:
            if (
                isinstance(entry, dict) and isinstance(entry.get("t"), str) and _LOG_TIME_RE.match(entry["t"])
                and entry.get("r") in RESOURCE_LOCATIONS
                and isinstance(entry.get("d"), int) and not isinstance(entry["d"], bool) and entry["d"] > 0
            ):
                state["farm_log"].append({"t": entry["t"], "r": entry["r"], "d": entry["d"]})
        del state["farm_log"][:-FARM_LOG_MAX]
    saved_combos = data.get("combos")
    state["combos"] = []
    if isinstance(saved_combos, list):
        for entry in saved_combos[:COMBO_MAX_COUNT]:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not isinstance(entry.get("parts"), list):
                continue
            name = entry["name"].strip()[:COMBO_NAME_MAX]
            parts = entry["parts"]
            if (
                name and 1 <= len(parts) <= COMBO_MAX_PARTS and all(isinstance(p, str) and p in RECIPES for p in parts)
                and len(set(parts)) == len(parts)
                and not any(c["name"].lower() == name.lower() for c in all_combos())
            ):
                state["combos"].append({"name": name, "parts": list(parts)})
    _load_extra_state(data)
    saved_blueprints = data.get("blueprints")
    state["blueprints"] = (
        {name: value for name, value in saved_blueprints.items() if name in SYNDICATE_SOURCES and isinstance(value, bool)}
        if isinstance(saved_blueprints, dict) else {}
    )
    saved_prefs = data.get("prefs")
    if isinstance(saved_prefs, dict):
        if saved_prefs.get("sort") in SORT_MODES:
            state["prefs"]["sort"] = saved_prefs["sort"]
        if isinstance(saved_prefs.get("hide_complete"), bool):
            state["prefs"]["hide_complete"] = saved_prefs["hide_complete"]

    render()


def import_last_data(json_text):
    """X-b (planning/TODO2.md): best-effort import of a real Warframe
    inventory snapshot -- either a plain inventory.json or a decrypted
    lastData.dat (index.html's own script handles the AES-CBC decryption
    before calling this; by the time json_text reaches here it's always
    plain JSON text).

    Deliberately narrow in scope: this only ever sets resource "built"
    counts, never part-owned counts or the "raw" bucket. Two real reasons,
    not just caution:
      - A built Zaw/Kitgun/Amp component isn't tracked as a standalone
        countable inventory item in Warframe's own data model -- once
        built, it becomes part of a specific equipped weapon, not a
        stackable count the way a resource is. There's nothing in this
        API response that means "how many spare Raplak Prisms do I have."
      - This tracker's own "raw" bucket is a convenience concept (an
        unrefined precursor you haven't cut/refined yet) that doesn't
        correspond to a single named inventory entry the way "built"
        does -- a resource's own MiscItems count IS its "built" total.

    Matching is a fuzzy tail-match on the internal item path (see
    _normalize_resource_key/_RESOURCE_MATCH_KEYS above), not a hardcoded
    exact-path table -- this project doesn't have a verified real sample
    file to test the exact schema against, so silently claiming a
    guaranteed-correct exhaustive mapping would be dishonest. Returns a
    plain summary string naming exactly what matched and what didn't,
    so a partial result is still useful and the gap is visible rather
    than hidden.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return "That file's contents weren't valid JSON once read -- nothing was imported."

    misc_items = data.get("MiscItems") or data.get("miscItems") or []
    if not isinstance(misc_items, list):
        return "No MiscItems inventory list found in that file -- nothing was imported."

    counts_by_key = {}
    for entry in misc_items:
        if not isinstance(entry, dict):
            continue
        item_type = entry.get("ItemType") or entry.get("itemType") or entry.get("Type") or ""
        count = entry.get("ItemCount", entry.get("itemCount", entry.get("Count", 0)))
        tail = item_type.rstrip("/").rsplit("/", 1)[-1]
        try:
            counts_by_key[_normalize_resource_key(tail)] = int(count)
        except (TypeError, ValueError):
            continue

    matched = []
    unmatched = []
    for match_key, resource_name in _RESOURCE_MATCH_KEYS.items():
        if match_key in counts_by_key:
            inv = state["inventory"].setdefault(resource_name, {"raw": 0, "built": 0})
            log_gain(resource_name, int(inv.get("raw", 0)) + int(inv.get("built", 0)),
                     int(inv.get("raw", 0)) + counts_by_key[match_key])
            inv["built"] = counts_by_key[match_key]
            set_source(resource_name, "import")
            matched.append(resource_name)
        else:
            unmatched.append(resource_name)

    note_edit("import")
    take_snapshot()
    render()

    total = len(matched) + len(unmatched)
    summary = f"Imported {len(matched)}/{total} resources' built counts from your file."
    if unmatched:
        summary += " Not found in the file (fill in manually): " + ", ".join(sorted(unmatched)) + "."
    return summary


# ---------------------------------------------------------------------------
# Batch A planner features (2026-09-27). All UI-additive: none of these change
# calculate()'s need numbers. Each keeps its own state key, written by
# get_state() only when non-default and validated key-by-key in load_state().
# ---------------------------------------------------------------------------

def _now_ms():
    """Current UTC time in epoch milliseconds. One place, so tests can swap it."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _now_utc():
    """Current UTC datetime. One place, so tests can swap it for a fixed clock."""
    return datetime.now(timezone.utc)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _str_in(value, container):
    """`value in container`, but False (not a TypeError) for unhashable junk from a bad save."""
    return isinstance(value, str) and value in container


def _clean(value, limit):
    return str(value if value is not None else "").strip()[:limit]


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(text):
    if not isinstance(text, str) or not _DATE_RE.match(text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def build_names():
    """Every name that counts as a "build" for pins/tags/notes: the requested
    parts followed by the named and custom combos."""
    return list(RECIPES) + [c["name"] for c in all_combos()]


def resolve_build(text):
    """The canonical build name for typed text (case-insensitive exact match),
    or None."""
    wanted = str(text or "").strip().lower()
    for name in build_names():
        if name.lower() == wanted and wanted:
            return name
    return None


def _prune_build_refs():
    """Drops pins/tags/notes/completions that point at a build that no longer
    exists (a removed custom combo)."""
    names = set(build_names())
    state["pins"] = [n for n in state["pins"] if n in names]
    state["tags"] = {n: v for n, v in state["tags"].items() if n in names}
    state["loadouts"] = {n: v for n, v in state["loadouts"].items() if n in names}
    state["completed"] = [e for e in state["completed"] if e["n"] in names]


# --- 12. Own-edits changelog + edited-vs-imported markers ----------------

EDIT_LOG_MAX = 200
EDIT_PHRASES = {
    "build": ("added", "build", "builds"),
    "resource": ("edited", "resource count", "resource counts"),
    "combo": ("added", "combo", "combos"),
    "goal": ("added", "goal", "goals"),
    "timer": ("added", "timer", "timers"),
    "import": ("ran", "import", "imports"),
}
SOURCE_MARKS = {"hand": "typed", "import": "import"}


def note_edit(kind, count=1):
    """Records one of the player's own edits ("added 3 builds today"). Same
    minute + same kind merge into one entry; the log is capped."""
    if kind not in EDIT_PHRASES or count <= 0:
        return False
    stamp = _now_stamp()
    log = state["edit_log"]
    if log and log[-1]["k"] == kind and log[-1]["t"] == stamp:
        log[-1]["d"] += count
    else:
        log.append({"t": stamp, "k": kind, "d": count})
    del log[:-EDIT_LOG_MAX]
    return True


def edit_phrase(kind, count):
    verb, one, many = EDIT_PHRASES[kind]
    return f"{verb} {count} {one if count == 1 else many}"


def edit_log_summary(today=None):
    today_prefix = (today or _now_stamp())[:10]
    summary = {"today": {}, "all": {}}
    for entry in state["edit_log"]:
        summary["all"][entry["k"]] = summary["all"].get(entry["k"], 0) + entry["d"]
        if entry["t"].startswith(today_prefix):
            summary["today"][entry["k"]] = summary["today"].get(entry["k"], 0) + entry["d"]
    return summary


def edit_log_text():
    if not state["edit_log"]:
        return "Nothing yet. Your own edits (builds, resource counts, combos, goals, timers, imports) are counted here."
    summary = edit_log_summary()

    def phrase(totals):
        return ", ".join(edit_phrase(k, totals[k]) for k in EDIT_PHRASES if k in totals) or "nothing"

    return f"Today: {phrase(summary['today'])}. In the whole log: {phrase(summary['all'])}."


def set_source(resource, source):
    """Remembers whether a resource's count was typed by hand or set by an import."""
    if resource in RESOURCE_LOCATIONS and source in SOURCE_MARKS:
        state["inv_source"][resource] = source


# --- 1. "This week" pins ---------------------------------------------------

PIN_MAX = 3


def toggle_pin(text):
    """Pins or unpins a build (part or combo). Returns (ok, message)."""
    name = resolve_build(text)
    if name is None:
        return False, "That is not a part or combo name."
    if name in state["pins"]:
        state["pins"].remove(name)
        return True, f"Unpinned {name}."
    if len(state["pins"]) >= PIN_MAX:
        return False, f"You can pin up to {PIN_MAX} builds. Unpin one first."
    state["pins"].append(name)
    return True, f"Pinned {name} to this week."


def pin_status(components):
    """One dict per pinned build: name, kind, and a one-line status."""
    by_name = {c["name"]: c for c in components}
    out = []
    for name in state["pins"]:
        part = by_name.get(name)
        if part is not None:
            if part["complete"]:
                status = f"done ({part['owned']}/{part['target']})"
            else:
                status = f"{part['owned']}/{part['target']} built"
                if part["can_build"]:
                    status += ", ready to build"
                elif part["missing"]:
                    status += f", short {len(part['missing'])} resource(s)"
            out.append({"name": name, "kind": "part", "status": status})
            continue
        combo = next((c for c in all_combos() if c["name"] == name), None)
        if combo is None:
            continue
        row = combo_progress(combo, components)
        if row["complete"]:
            status = "done (all parts built)"
        else:
            status = f"{len(row['built'])}/{len(combo['parts'])} parts built"
            if row["units_short"]:
                status += f", short {row['units_short']} resource units for the rest"
        out.append({"name": name, "kind": "combo", "status": status})
    return out


# --- 5. Recently completed -----------------------------------------------

COMPLETED_MAX = 5


def completion_snapshot():
    """Names of every build that is finished right now: complete parts and
    combos whose parts are all built."""
    comps, _ = calculate()
    done = {c["name"] for c in comps if c["complete"]}
    for row in compare_combos(comps):
        if row["complete"]:
            done.add(row["combo"]["name"])
    return done


def record_completions(before):
    """Adds every build that became finished since `before` (a
    completion_snapshot()) to the recently-completed strip, dated today (UTC)."""
    added = sorted(completion_snapshot() - set(before))
    for name in added:
        state["completed"] = [e for e in state["completed"] if e["n"] != name]
        state["completed"].append({"n": name, "d": _now_stamp()[:10]})
    del state["completed"][:-COMPLETED_MAX]
    return added


# --- 2. Foundry timers --------------------------------------------------

TIMER_MAX = 20
TIMER_NAME_MAX = 30
TIMER_MIN_MS = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
TIMER_MAX_MS = int(datetime(2100, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
TIMER_MAX_DURATION_MIN = 90 * 24 * 60
_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([dhm])")
_DURATION_FULL_RE = re.compile(r"(?:\d+(?:\.\d+)?\s*[dhm]\s*)+")
_BROWSER_TIMEOUT_MAX_MS = 2 ** 31 - 1


def parse_duration_minutes(text):
    """"12h", "1d 2h 30m", "90m" or a bare number of hours -> whole minutes, or
    None when it is not a duration between one minute and 90 days."""
    text = str(text or "").strip().lower()
    if not text:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        minutes = float(text) * 60
    elif _DURATION_FULL_RE.fullmatch(text):
        unit = {"d": 1440, "h": 60, "m": 1}
        minutes = sum(float(qty) * unit[u] for qty, u in _DURATION_RE.findall(text))
    else:
        return None
    minutes = round(minutes)
    return minutes if 1 <= minutes <= TIMER_MAX_DURATION_MIN else None


def parse_local_datetime(text):
    """A datetime-local value ("2026-09-27T18:30") in the browser's own time
    zone -> epoch ms, or None. Outside a browser (tests) it reads it as UTC."""
    text = str(text or "").strip()
    if not text:
        return None
    try:
        from js import Date  # noqa: PLC0415 -- Pyodide-only
    except ImportError:
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return int(parsed.replace(tzinfo=timezone.utc).timestamp() * 1000)
    ms = Date.new(text).getTime()
    if ms != ms:  # NaN
        return None
    return int(ms)


def format_local_time(ms):
    """A timestamp in the viewer's local time, or UTC text outside a browser."""
    try:
        from js import Date  # noqa: PLC0415 -- Pyodide-only
    except ImportError:
        return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return str(Date.new(ms).toLocaleString())


def format_remaining(diff_ms):
    """"ready now" or "in 2h 5m" / "in 3d 4h" for a millisecond difference."""
    if diff_ms <= 0:
        return "ready now"
    minutes = -(-diff_ms // 60000)
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    if days:
        return f"in {days}d {hours}h"
    if hours:
        return f"in {hours}h {mins}m"
    return f"in {mins}m"


def add_timer(name, start_ms=None, duration_min=None, ready_ms=None, notify=False):
    """Adds a foundry-timer note from either a start time + duration or a
    ready-at time. Times are epoch ms. Returns (ok, message)."""
    name = _clean(name, TIMER_NAME_MAX)
    if not name:
        return False, "Give the craft a name."
    if ready_ms is None:
        if start_ms is None or duration_min is None:
            return False, "Enter a start time and a duration (for example 12h), or a ready-at time."
        ready_ms = start_ms + duration_min * 60000
    if not _is_int(ready_ms) or not TIMER_MIN_MS <= ready_ms <= TIMER_MAX_MS:
        return False, "That time is not valid."
    if len(state["timers"]) >= TIMER_MAX:
        return False, f"You can keep up to {TIMER_MAX} timers. Remove one first."
    state["timers"].append({"n": name, "ms": int(ready_ms), "notify": bool(notify)})
    state["timers"].sort(key=lambda t: (t["ms"], t["n"].lower()))
    return True, f"Added {name}."


def remove_timer(index):
    if 0 <= index < len(state["timers"]):
        del state["timers"][index]
        return True
    return False


def timer_line(timer, now_ms=None):
    now_ms = _now_ms() if now_ms is None else now_ms
    return f"{timer['n']}: ready at {format_local_time(timer['ms'])} ({format_remaining(timer['ms'] - now_ms)})"


def notification_permission():
    """"granted"/"denied"/"default", or None when the browser has no Notification API."""
    try:
        from js import Notification  # noqa: PLC0415 -- Pyodide-only
        return str(Notification.permission)
    except Exception:  # noqa: BLE001 -- unsupported: degrade silently
        return None


def request_notification_permission():
    """Asks the browser for notification permission. Only ever called from an
    explicit button click. Returns False when the browser cannot do it."""
    try:
        from js import Notification  # noqa: PLC0415 -- Pyodide-only
        Notification.requestPermission()
        return True
    except Exception:  # noqa: BLE001 -- unsupported: degrade silently
        return False


_notify_state = {"handles": [], "proxies": []}


def schedule_notifications(now_ms=None):
    """(Re)schedules a browser notification for every future timer flagged
    "notify", but only when permission is already granted. It fires only
    while this page stays open. Silent no-op when unsupported. Returns how
    many were scheduled."""
    for handle in _notify_state["handles"]:
        try:
            from js import clearTimeout  # noqa: PLC0415 -- Pyodide-only
            clearTimeout(handle)
        except Exception:  # noqa: BLE001, S110
            pass
    for proxy in _notify_state["proxies"]:
        proxy.destroy()
    _notify_state["handles"], _notify_state["proxies"] = [], []
    if notification_permission() != "granted":
        return 0
    now_ms = _now_ms() if now_ms is None else now_ms
    count = 0
    for timer in state["timers"]:
        delay = timer["ms"] - now_ms
        if not timer["notify"] or not 0 < delay <= _BROWSER_TIMEOUT_MAX_MS:
            continue

        def fire(name=timer["n"]):
            try:
                from js import Notification, Object  # noqa: PLC0415 -- Pyodide-only
                from pyodide.ffi import to_js  # noqa: PLC0415 -- Pyodide-only
                Notification.new("Foundry craft ready", to_js({"body": f"{name} is ready."}, dict_converter=Object.fromEntries))
            except Exception:  # noqa: BLE001, S110 -- unsupported: degrade silently
                pass

        try:
            from js import setTimeout  # noqa: PLC0415 -- Pyodide-only
            proxy = create_proxy(fire)
            _notify_state["proxies"].append(proxy)
            _notify_state["handles"].append(setTimeout(proxy, delay))
            count += 1
        except Exception:  # noqa: BLE001, S110
            pass
    return count


# --- 3. Credits and endo budget -----------------------------------------

BUDGET_MAX = 10 ** 10


def budget_status(resources):
    """How the refinery plan sits against the credits on hand. `resources` are
    the resource rows still being planned. Credits on hand of 0 means "not
    entered". Endo is a manually entered figure only: no tracked recipe uses it."""
    totals = refinery_totals(resources)
    needed = totals.get("Credits", 0)
    materials = {k: v for k, v in totals.items() if k != "Credits"}
    have = state["budget"]["credits"]
    entered = have > 0
    short = max(0, needed - have) if entered else 0
    credit_limited = entered and short > 0
    farm_limited = bool(materials)
    if credit_limited and farm_limited:
        limit = "both"
    elif credit_limited:
        limit = "credits"
    elif farm_limited:
        limit = "farming"
    elif needed and not entered:
        limit = "unknown"
    else:
        limit = "none"
    return {"needed": needed, "have": have, "entered": entered, "short": short,
            "materials": materials, "limit": limit, "endo": state["budget"]["endo"]}


def budget_text(resources):
    status = budget_status(resources)
    if not status["needed"] and not status["materials"] and not status["endo"] and not status["entered"]:
        return ""
    parts = []
    if status["needed"]:
        line = f"Credits for the refinery plan: {status['needed']:,}"
        line += f" (you have {status['have']:,})." if status["entered"] else " (enter your credits on hand to compare)."
        parts.append(line)
    elif status["entered"]:
        parts.append(f"Credits on hand: {status['have']:,} (the refinery plan needs none right now).")
    parts.append({
        "credits": f"Credit-limited: short {status['short']:,} credits; the materials are not the bottleneck.",
        "farming": "Farm-limited: the credits cover it, the raw materials still have to be gathered.",
        "both": f"Credit-limited and farm-limited: short {status['short']:,} credits and materials still to gather.",
        "none": "Nothing is holding up refining right now.",
        "unknown": "Enter credits on hand to see whether credits or farming limits the plan.",
    }[status["limit"]])
    if status["endo"]:
        parts.append(f"Endo on hand: {status['endo']:,} (typed by you; no live data, and no tracked recipe uses it).")
    return " ".join(parts)


# --- 4. Mastery-rank checklist ------------------------------------------

# Read from the Warframe Wiki's Mastery Rank page on 2026-09-27
# (https://wiki.warframe.com/w/Mastery_Rank): weapons (incl. kitgun chambers,
# zaw strikes, amp prisms) give 100 mastery points per rank up to rank 30, so
# 3,000; Warframes, companions, archwings, K-Drives, Plexus and Necramechs give
# 200 per rank, so 6,000. The total mastery points needed for rank N is
# 2,500 x N squared (the page's own formula and table).
MASTERY_ITEM_XP = {"weapon": 3000, "frame": 6000}
MASTERY_ITEM_LABELS = {
    "weapon": "Weapon (3,000 points)",
    "frame": "Warframe, companion or archwing (6,000 points)",
}
MASTERY_MAX_RANK = 30
MASTERY_ITEM_MAX = 200
MASTERY_NAME_MAX = 40
MASTERY_BASE_MAX = 10 ** 7


def mastery_points_for_rank(rank):
    """Total mastery points needed to reach `rank` (rank 1 to 30)."""
    return 2500 * rank * rank


def mastery_rank_for_points(points):
    return min(MASTERY_MAX_RANK, math.isqrt(max(0, points) // 2500))


def mastery_total():
    m = state["mastery"]
    return m["base"] + sum(MASTERY_ITEM_XP[i["t"]] for i in m["items"] if i["done"])


def mastery_status():
    """Current rank, points to the next one, and how many items that is."""
    m = state["mastery"]
    total = mastery_total()
    rank = mastery_rank_for_points(total)
    status = {"total": total, "rank": rank, "next_rank": None, "needed": 0, "weapons": 0, "frames": 0, "from_list": None}
    if rank >= MASTERY_MAX_RANK:
        return status
    target = mastery_points_for_rank(rank + 1)
    needed = target - total
    status.update(next_rank=rank + 1, needed=needed, weapons=-(-needed // 3000), frames=-(-needed // 6000))
    gained, count = 0, 0
    for item in m["items"]:
        if item["done"]:
            continue
        gained += MASTERY_ITEM_XP[item["t"]]
        count += 1
        if gained >= needed:
            status["from_list"] = count
            break
    return status


def mastery_text():
    status = mastery_status()
    line = f"{status['total']:,} mastery points: Mastery Rank {status['rank']}."
    if status["next_rank"] is None:
        return line + " Rank 30 reached; the Wiki gives a separate formula for Legendary ranks."
    line += (f" {status['needed']:,} points to rank {status['next_rank']}: about {status['weapons']} weapon(s) "
             f"or {status['frames']} frame(s).")
    if status["from_list"] is not None:
        line += f" Ticking the next {status['from_list']} item(s) on your list gets you there."
    elif state["mastery"]["items"]:
        line += " Your list alone does not reach it yet: add more items."
    return line


def add_mastery_item(name, kind):
    name = _clean(name, MASTERY_NAME_MAX)
    if not name:
        return False, "Give the item a name."
    if kind not in MASTERY_ITEM_XP:
        return False, "Pick weapon or frame."
    items = state["mastery"]["items"]
    if len(items) >= MASTERY_ITEM_MAX:
        return False, f"That is the maximum of {MASTERY_ITEM_MAX} items."
    if any(i["n"].lower() == name.lower() for i in items):
        return False, "That item is already on the list."
    items.append({"n": name, "t": kind, "done": False})
    return True, f"Added {name}."


# --- 6. Trader schedule -------------------------------------------------

# Baro Ki'Teer: "he makes appearances every two weeks, and is only available
# for trading for up to 48 hours" (https://wiki.warframe.com/w/Baro_Ki'Teer,
# read 2026-09-27).
BARO_INTERVAL_DAYS = 14
BARO_STAY_DAYS = 2
WATCH_MAX = 30
WATCH_TEXT_MAX = 40


def baro_reminder(today=None):
    """Where Baro is in his two-week cycle, from an arrival date the player
    entered: {"state": "today"|"here"|"waiting"|"future", "days": N, "date": iso}
    or None when no date is entered."""
    last = state["trader"]["last"]
    if not _valid_date(last):
        return None
    today = today or _now_utc().date()
    arrival = date.fromisoformat(last)
    delta = (today - arrival).days
    if delta < 0:
        return {"state": "future", "days": -delta, "date": arrival.isoformat()}
    since = delta % BARO_INTERVAL_DAYS
    if since == 0:
        return {"state": "today", "days": 0, "date": today.isoformat()}
    if since < BARO_STAY_DAYS:
        return {"state": "here", "days": 0, "date": (today - timedelta(days=since)).isoformat()}
    days = BARO_INTERVAL_DAYS - since
    return {"state": "waiting", "days": days, "date": (today + timedelta(days=days)).isoformat()}


def baro_text(today=None):
    info = baro_reminder(today)
    if info is None:
        return "Enter a date Baro arrived (or is due) to see a countdown."
    days = info["days"]
    if info["state"] == "today":
        return "Baro is due today (he stays up to 48 hours)."
    if info["state"] == "here":
        return f"Baro arrived on {info['date']} and may still be here (he stays up to 48 hours)."
    unit = "day" if days == 1 else "days"
    return f"Baro is due back in {days} {unit} ({info['date']})."


def add_watch(text):
    text = _clean(text, WATCH_TEXT_MAX)
    if not text:
        return False, "Type what you are watching for."
    if len(state["trader"]["watch"]) >= WATCH_MAX:
        return False, f"That is the maximum of {WATCH_MAX} items."
    if any(w.lower() == text.lower() for w in state["trader"]["watch"]):
        return False, "You are already watching for that."
    state["trader"]["watch"].append(text)
    return True, f"Watching for {text}."


# --- 8. Per-resource "I have enough" ------------------------------------

def set_enough(resource, flag):
    if resource not in RESOURCE_LOCATIONS:
        return False
    if flag and resource not in state["enough"]:
        state["enough"].append(resource)
        state["enough"].sort()
    elif not flag and resource in state["enough"]:
        state["enough"].remove(resource)
    return True


def active_rows(resources):
    """The resource rows that still count as needs: those the player has not
    marked "I have enough"."""
    return [r for r in resources if not r.get("enough")]


def display_components(components):
    """Components with resources marked "have enough" dropped from their
    missing lists, for display only (calculate()'s numbers are untouched)."""
    enough = set(state["enough"])
    if not enough:
        return components
    return [dict(c, missing={k: v for k, v in c["missing"].items() if k not in enough}) for c in components]


# --- 9. Colour tags -----------------------------------------------------

PRESET_TAGS = ("daily driver", "fun", "sell")
TAG_LABEL_MAX = 16
TAG_CUSTOM_MAX = 8
TAG_COLORS = ["#4c8dff", "#e6a23c", "#4caf7d", "#c678dd", "#e06c75", "#2bb5c7", "#b8942d", "#8a94a6", "#d96ba0", "#7a9c3a", "#a0724a"]


def tag_labels():
    return list(PRESET_TAGS) + list(state["tag_labels"])


def tag_color(label):
    labels = tag_labels()
    return TAG_COLORS[labels.index(label) % len(TAG_COLORS)] if label in labels else "#8a94a6"


def resolve_tag(text):
    wanted = str(text or "").strip().lower()
    for label in tag_labels():
        if label.lower() == wanted and wanted:
            return label
    return None


def add_tag_label(text):
    text = _clean(text, TAG_LABEL_MAX)
    if not text:
        return False, "Type a short label."
    if resolve_tag(text) is not None:
        return False, "That label already exists."
    if len(state["tag_labels"]) >= TAG_CUSTOM_MAX:
        return False, f"You can add up to {TAG_CUSTOM_MAX} of your own labels."
    state["tag_labels"].append(text)
    return True, f"Added label {text}."


def remove_tag_label(text):
    label = resolve_tag(text)
    if label is None or label in PRESET_TAGS:
        return False, "Only labels you added yourself can be removed."
    state["tag_labels"].remove(label)
    state["tags"] = {n: v for n, v in state["tags"].items() if v != label}
    return True, f"Removed label {label}."


def assign_tag(build, label):
    """Tags a build (part or combo) with a label; an empty label clears it."""
    name = resolve_build(build)
    if name is None:
        return False, "That is not a part or combo name."
    if not str(label or "").strip():
        state["tags"].pop(name, None)
        return True, f"Cleared the tag on {name}."
    resolved = resolve_tag(label)
    if resolved is None:
        return False, "Unknown label. Add it first."
    state["tags"][name] = resolved
    return True, f"Tagged {name} as {resolved}."


# --- 10. Long-term goals ------------------------------------------------

GOAL_MAX = 30
GOAL_TEXT_MAX = 60


def add_goal(text):
    text = _clean(text, GOAL_TEXT_MAX)
    if not text:
        return False, "Type a goal."
    if len(state["goals"]) >= GOAL_MAX:
        return False, f"That is the maximum of {GOAL_MAX} goals."
    if any(g["text"].lower() == text.lower() for g in state["goals"]):
        return False, "That goal is already on the list."
    state["goals"].append({"text": text, "done": False})
    return True, f"Added goal: {text}."


# --- 14. Progress history -----------------------------------------------

HISTORY_MAX = 60


def completion_percent(components):
    total = len(components)
    return round(sum(1 for c in components if c["complete"]) / total * 100) if total else 0


def take_snapshot(components=None):
    """Records the current completion percentage (newest last, capped at 60).
    A second snapshot in the same minute replaces the first."""
    if components is None:
        components, _ = calculate()
    entry = {"t": _now_stamp(), "p": completion_percent(components)}
    history = state["history"]
    if history and history[-1]["t"] == entry["t"]:
        history[-1] = entry
    else:
        history.append(entry)
    del history[:-HISTORY_MAX]
    return entry


def history_summary(history=None):
    history = state["history"] if history is None else history
    if not history:
        return "No snapshots yet. One is taken each time you import, or press Snapshot now."
    first, last = history[0], history[-1]
    if len(history) == 1:
        return f"1 snapshot: {last['p']}% of parts complete on {last['t']}."
    delta = last["p"] - first["p"]
    trend = f"up {delta} points" if delta > 0 else (f"down {-delta} points" if delta < 0 else "unchanged")
    return (f"{len(history)} snapshots: from {first['p']}% on {first['t']} to {last['p']}% on {last['t']} ({trend}).")


def history_chart_svg(history=None):
    """A small inline SVG line chart of completion percentage, with an
    accessible label. Empty string when there is nothing to draw."""
    history = state["history"] if history is None else history
    if not history:
        return ""
    width, height, pad = 320, 120, 14
    n = len(history)
    points = []
    for i, entry in enumerate(history):
        x = pad + (width - 2 * pad) * (i / (n - 1) if n > 1 else 0.5)
        y = height - pad - (height - 2 * pad) * entry["p"] / 100
        points.append((round(x, 1), round(y, 1)))
    poly = " ".join(f"{x},{y}" for x, y in points)
    dots = "".join(f'<circle class="hist-dot" cx="{x}" cy="{y}" r="2.5"></circle>' for x, y in points)
    return (
        f'<svg class="hist-chart" viewBox="0 0 {width} {height}" role="img" aria-label="{history_summary(history)}">'
        f'<line class="hist-axis" x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}"></line>'
        f'<line class="hist-axis" x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}"></line>'
        f'<text class="hist-label" x="{pad + 3}" y="{pad + 8}">100%</text>'
        f'<text class="hist-label" x="{pad + 3}" y="{height - pad - 3}">0%</text>'
        f'<polyline class="hist-line" points="{poly}"></polyline>{dots}</svg>'
    )


# --- 13. Daily / weekly checklist ---------------------------------------

# Reset times from the Warframe Wiki's reset page (https://wiki.warframe.com/w/Daily_Reset,
# read 2026-09-27): the daily reset is at 0:00 UTC, the weekly reset every
# Monday at 0:00 UTC.
CHECK_KINDS = ("daily", "weekly")
CHECK_MAX = 30
CHECK_NAME_MAX = 40


def period_stamps(now=None):
    """The current daily and weekly period stamps (UTC): today's date, and the
    date of the Monday that started this week."""
    now = now or _now_utc()
    today = now.date()
    return {"daily": today.isoformat(), "weekly": (today - timedelta(days=today.weekday())).isoformat()}


def roll_checklist(now=None):
    """Clears the ticks of any period that has reset since they were saved.
    Returns True when something was cleared or restamped."""
    stamps = period_stamps(now)
    changed = False
    for kind in CHECK_KINDS:
        ticks = state["checklist"]["ticks"][kind]
        if ticks["stamp"] != stamps[kind]:
            ticks["stamp"] = stamps[kind]
            ticks["done"] = []
            changed = True
    return changed


def next_reset(kind, now=None):
    """The UTC datetime of the next daily or weekly reset."""
    now = now or _now_utc()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if kind == "daily":
        return midnight + timedelta(days=1)
    return midnight + timedelta(days=7 - now.weekday())


def add_check_item(name, kind):
    name = _clean(name, CHECK_NAME_MAX)
    if not name:
        return False, "Give the task a name."
    if kind not in CHECK_KINDS:
        return False, "Pick daily or weekly."
    items = state["checklist"]["items"]
    if len(items) >= CHECK_MAX:
        return False, f"That is the maximum of {CHECK_MAX} tasks."
    if any(i["n"].lower() == name.lower() and i["k"] == kind for i in items):
        return False, "That task is already on the list."
    items.append({"n": name, "k": kind})
    return True, f"Added {kind} task {name}."


def toggle_check(name, kind, now=None):
    roll_checklist(now)
    ticks = state["checklist"]["ticks"][kind]
    if not any(i["n"] == name and i["k"] == kind for i in state["checklist"]["items"]):
        return False
    if name in ticks["done"]:
        ticks["done"].remove(name)
    else:
        ticks["done"].append(name)
    return True


def remove_check_item(name, kind):
    cl = state["checklist"]
    before = len(cl["items"])
    cl["items"] = [i for i in cl["items"] if not (i["n"] == name and i["k"] == kind)]
    cl["ticks"][kind]["done"] = [n for n in cl["ticks"][kind]["done"] if n != name]
    return len(cl["items"]) != before


def check_reset_text(now=None):
    now = now or _now_utc()
    parts = []
    for kind, label in (("daily", "Daily reset"), ("weekly", "Weekly reset")):
        diff = int((next_reset(kind, now) - now).total_seconds() * 1000)
        parts.append(f"{label} {format_remaining(diff)}")
    return " · ".join(parts) + " (0:00 UTC daily; Monday 0:00 UTC weekly)."


# --- 16. Build-loadout notes --------------------------------------------

LOADOUT_MAX = 600


def set_loadout(build, mods, play):
    """Attaches the player's own mod list and playstyle notes to a finished
    build. Empty notes remove the entry. Returns (ok, message)."""
    name = resolve_build(build)
    if name is None:
        return False, "That is not a part or combo name."
    mods, play = _clean(mods, LOADOUT_MAX), _clean(play, LOADOUT_MAX)
    if not mods and not play:
        state["loadouts"].pop(name, None)
        return True, f"Cleared the notes on {name}."
    if name not in completion_snapshot() and name not in {e["n"] for e in state["completed"]}:
        return False, f"{name} is not finished yet. Notes attach to finished builds."
    state["loadouts"][name] = {"mods": mods, "play": play}
    return True, f"Saved notes for {name}."


# --- 7. Wishlist text and 15. Shared goals code -------------------------

GOALS_CODE_PREFIX = "WFG1."
GOALS_CODE_MAX_LEN = 8000
GOALS_MAX_BUILDS = 60
GOALS_MAX_NEEDS = 80
GOALS_MAX_QTY = 10 ** 7
_CODE_BODY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def wishlist_data(components, resources):
    """(builds, needs): parts still to build as (name, remaining) with pinned
    ones first, and resources still short (not marked "have enough") as
    (name, short)."""
    builds = [(c["name"], c["remaining"]) for c in components if c["remaining"] > 0]
    builds.sort(key=lambda b: 0 if b[0] in state["pins"] else 1)
    needs = [(r["name"], r["built_short"]) for r in active_rows(resources) if r["built_short"] > 0]
    return builds, needs


def wishlist_text(components, resources):
    builds, needs = wishlist_data(components, resources)
    if not builds and not needs:
        return "Nothing on my wishlist: every requirement is covered."
    lines = []
    if builds:
        lines.append("Building: " + ", ".join(f"{n} x{q}" for n, q in builds))
    if needs:
        lines.append("Need: " + ", ".join(f"{n} x{q}" for n, q in needs))
    return "\n".join(lines)


def export_goals_code(components, resources):
    """A short shareable code: base64 (URL-safe, unpadded) of a compact JSON
    holding only the wishlist's builds and needs. No notes, no usernames."""
    builds, needs = wishlist_data(components, resources)
    payload = {"v": 1, "b": [[n, q] for n, q in builds], "n": [[n, q] for n, q in needs]}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return GOALS_CODE_PREFIX + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _valid_pairs(value, known, limit):
    if not isinstance(value, list) or len(value) > limit:
        return None
    out, seen = [], set()
    for entry in value:
        if not isinstance(entry, list) or len(entry) != 2:
            return None
        name, qty = entry
        if not isinstance(name, str) or name not in known or name in seen:
            return None
        if not _is_int(qty) or not 1 <= qty <= GOALS_MAX_QTY:
            return None
        seen.add(name)
        out.append((name, qty))
    return out


def parse_goals_code(text):
    """Strictly validates a pasted goals code. Returns (data, error): data is
    {"builds": [(name, qty)], "needs": [(name, qty)]} or None with a message."""
    text = str(text or "").strip()
    if not text.startswith(GOALS_CODE_PREFIX):
        return None, "That is not a goals code (it should start with WFG1.)."
    body = text[len(GOALS_CODE_PREFIX):]
    if len(text) > GOALS_CODE_MAX_LEN or not body or not _CODE_BODY_RE.match(body):
        return None, "That code has invalid characters or is too long."
    try:
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, "That code could not be decoded."
    if not isinstance(data, dict) or set(data) != {"v", "b", "n"} or data["v"] != 1 or not _is_int(data["v"]):
        return None, "That code is not in the expected format."
    builds = _valid_pairs(data["b"], set(RECIPES), GOALS_MAX_BUILDS)
    needs = _valid_pairs(data["n"], set(RESOURCE_LOCATIONS), GOALS_MAX_NEEDS)
    if builds is None or needs is None:
        return None, "That code holds entries this tracker does not recognise."
    return {"builds": builds, "needs": needs}, ""


def goals_comparison_text(friend, resources):
    """Who can help farm what: the friend's needs you have spare of, and the
    needs you both still have. `resources` are this player's calculated rows."""
    mine = {r["name"]: r for r in resources}
    can_give, shared = [], []
    for name, qty in friend["needs"]:
        inv = state["inventory"].get(name, {})
        have = int(inv.get("built", 0)) + int(inv.get("raw", 0))
        row = mine.get(name)
        spare = max(0, have - (row["needed"] if row else 0))
        if spare > 0:
            can_give.append(f"{name} (they need {qty}, you have {spare} spare)")
        if row and row["built_short"] > 0 and not row.get("enough"):
            shared.append(f"{name} (they need {qty}, you are short {row['built_short']})")
    lines = [f"Their list: {len(friend['builds'])} build(s), {len(friend['needs'])} resource need(s)."]
    lines.append("You could cover: " + ("; ".join(can_give) if can_give else "nothing from your current stock") + ".")
    lines.append("You both still need: " + ("; ".join(shared) if shared else "no shared shortfalls") + " (farm these together).")
    return "\n".join(lines)


# --- Save/load for the batch A keys --------------------------------------

def _extra_state():
    """The batch A keys, each present only when non-default."""
    out = {}
    if state["pins"]:
        out["pins"] = list(state["pins"])
    if state["timers"]:
        out["timers"] = [dict(t) for t in state["timers"]]
    if state["budget"]["credits"] or state["budget"]["endo"]:
        out["budget"] = dict(state["budget"])
    m = state["mastery"]
    if m["base"] or m["items"]:
        out["mastery"] = {"base": m["base"], "items": [dict(i) for i in m["items"]]}
    if state["completed"]:
        out["completed"] = [dict(e) for e in state["completed"]]
    if state["trader"]["last"] or state["trader"]["watch"]:
        out["trader"] = {"last": state["trader"]["last"], "watch": list(state["trader"]["watch"])}
    if state["enough"]:
        out["enough"] = list(state["enough"])
    if state["tag_labels"]:
        out["tag_labels"] = list(state["tag_labels"])
    if state["tags"]:
        out["tags"] = dict(state["tags"])
    if state["goals"]:
        out["goals"] = [dict(g) for g in state["goals"]]
    if state["history"]:
        out["history"] = [dict(h) for h in state["history"]]
    cl = state["checklist"]
    if cl["items"]:
        out["checklist"] = {
            "items": [dict(i) for i in cl["items"]],
            "ticks": {k: {"stamp": cl["ticks"][k]["stamp"], "done": list(cl["ticks"][k]["done"])} for k in CHECK_KINDS},
        }
    if state["loadouts"]:
        out["loadouts"] = {n: dict(v) for n, v in state["loadouts"].items()}
    if state["inv_source"]:
        out["inv_source"] = dict(state["inv_source"])
    if state["edit_log"]:
        out["edit_log"] = [dict(e) for e in state["edit_log"]]
    return out


def _dict_entries(value):
    return [e for e in value if isinstance(e, dict)] if isinstance(value, list) else []


def _load_extra_state(data):
    """Validates and installs the batch A keys: wrong types, bad bounds and
    unknown ids are dropped, missing keys fall back to their defaults. Must run
    after the combos are loaded (pins/tags/notes may name a combo)."""
    names = set(build_names())

    pins = data.get("pins")
    state["pins"] = []
    if isinstance(pins, list):
        for name in pins:
            if isinstance(name, str) and name in names and name not in state["pins"] and len(state["pins"]) < PIN_MAX:
                state["pins"].append(name)

    state["timers"] = []
    for entry in _dict_entries(data.get("timers"))[:TIMER_MAX]:
        name = entry.get("n")
        ms = entry.get("ms")
        if (isinstance(name, str) and name.strip() and _is_int(ms) and TIMER_MIN_MS <= ms <= TIMER_MAX_MS
                and isinstance(entry.get("notify"), bool)):
            state["timers"].append({"n": name.strip()[:TIMER_NAME_MAX], "ms": ms, "notify": entry["notify"]})
    state["timers"].sort(key=lambda t: (t["ms"], t["n"].lower()))

    budget = data.get("budget")
    state["budget"] = {"credits": 0, "endo": 0}
    if isinstance(budget, dict):
        for key in ("credits", "endo"):
            value = budget.get(key)
            if _is_int(value) and 0 <= value <= BUDGET_MAX:
                state["budget"][key] = value

    mastery = data.get("mastery")
    state["mastery"] = {"base": 0, "items": []}
    if isinstance(mastery, dict):
        base = mastery.get("base")
        if _is_int(base) and 0 <= base <= MASTERY_BASE_MAX:
            state["mastery"]["base"] = base
        for entry in _dict_entries(mastery.get("items"))[:MASTERY_ITEM_MAX]:
            name = entry.get("n")
            if (isinstance(name, str) and name.strip() and _str_in(entry.get("t"), MASTERY_ITEM_XP)
                    and isinstance(entry.get("done"), bool)
                    and not any(i["n"].lower() == name.strip()[:MASTERY_NAME_MAX].lower() for i in state["mastery"]["items"])):
                state["mastery"]["items"].append({"n": name.strip()[:MASTERY_NAME_MAX], "t": entry["t"], "done": entry["done"]})

    state["completed"] = []
    for entry in _dict_entries(data.get("completed")):
        if _str_in(entry.get("n"), names) and _valid_date(entry.get("d")):
            state["completed"].append({"n": entry["n"], "d": entry["d"]})
    del state["completed"][:-COMPLETED_MAX]

    trader = data.get("trader")
    state["trader"] = {"last": "", "watch": []}
    if isinstance(trader, dict):
        if _valid_date(trader.get("last")):
            state["trader"]["last"] = trader["last"]
        watch = trader.get("watch")
        for text in watch if isinstance(watch, list) else []:
            text = text.strip()[:WATCH_TEXT_MAX] if isinstance(text, str) else ""
            if (text and len(state["trader"]["watch"]) < WATCH_MAX
                    and not any(w.lower() == text.lower() for w in state["trader"]["watch"])):
                state["trader"]["watch"].append(text)

    enough = data.get("enough")
    state["enough"] = sorted({n for n in enough if isinstance(n, str) and n in RESOURCE_LOCATIONS}) if isinstance(enough, list) else []

    state["tag_labels"] = []
    labels = data.get("tag_labels")
    for text in labels if isinstance(labels, list) else []:
        text = text.strip()[:TAG_LABEL_MAX] if isinstance(text, str) else ""
        if text and len(state["tag_labels"]) < TAG_CUSTOM_MAX and resolve_tag(text) is None:
            state["tag_labels"].append(text)
    tags = data.get("tags")
    state["tags"] = {
        n: resolve_tag(label) for n, label in tags.items()
        if isinstance(n, str) and n in names and isinstance(label, str) and resolve_tag(label) is not None
    } if isinstance(tags, dict) else {}

    state["goals"] = []
    for entry in _dict_entries(data.get("goals"))[:GOAL_MAX]:
        text = entry.get("text")
        if isinstance(text, str) and text.strip() and isinstance(entry.get("done"), bool):
            state["goals"].append({"text": text.strip()[:GOAL_TEXT_MAX], "done": entry["done"]})

    state["history"] = []
    for entry in _dict_entries(data.get("history")):
        if (isinstance(entry.get("t"), str) and _LOG_TIME_RE.match(entry["t"])
                and _is_int(entry.get("p")) and 0 <= entry["p"] <= 100):
            state["history"].append({"t": entry["t"], "p": entry["p"]})
    del state["history"][:-HISTORY_MAX]

    checklist = data.get("checklist")
    state["checklist"] = {"items": [], "ticks": {k: {"stamp": "", "done": []} for k in CHECK_KINDS}}
    if isinstance(checklist, dict):
        for entry in _dict_entries(checklist.get("items"))[:CHECK_MAX]:
            name, kind = entry.get("n"), entry.get("k")
            if (isinstance(name, str) and name.strip() and kind in CHECK_KINDS
                    and not any(i["n"].lower() == name.strip()[:CHECK_NAME_MAX].lower() and i["k"] == kind
                                for i in state["checklist"]["items"])):
                state["checklist"]["items"].append({"n": name.strip()[:CHECK_NAME_MAX], "k": kind})
        ticks = checklist.get("ticks")
        if isinstance(ticks, dict):
            for kind in CHECK_KINDS:
                entry = ticks.get(kind)
                if not isinstance(entry, dict):
                    continue
                kind_names = {i["n"] for i in state["checklist"]["items"] if i["k"] == kind}
                if _valid_date(entry.get("stamp")):
                    state["checklist"]["ticks"][kind]["stamp"] = entry["stamp"]
                    done = entry.get("done")
                    state["checklist"]["ticks"][kind]["done"] = sorted(
                        {n for n in done if isinstance(n, str) and n in kind_names}) if isinstance(done, list) else []

    state["loadouts"] = {}
    loadouts = data.get("loadouts")
    if isinstance(loadouts, dict):
        for name, entry in list(loadouts.items())[:len(names)]:
            if isinstance(name, str) and name in names and isinstance(entry, dict):
                mods, play = entry.get("mods"), entry.get("play")
                if isinstance(mods, str) and isinstance(play, str) and (mods.strip() or play.strip()):
                    state["loadouts"][name] = {"mods": mods.strip()[:LOADOUT_MAX], "play": play.strip()[:LOADOUT_MAX]}

    sources = data.get("inv_source")
    state["inv_source"] = {
        n: v for n, v in sources.items() if isinstance(n, str) and n in RESOURCE_LOCATIONS and _str_in(v, SOURCE_MARKS)
    } if isinstance(sources, dict) else {}

    state["edit_log"] = []
    for entry in _dict_entries(data.get("edit_log")):
        if (isinstance(entry.get("t"), str) and _LOG_TIME_RE.match(entry["t"]) and _str_in(entry.get("k"), EDIT_PHRASES)
                and _is_int(entry.get("d")) and 1 <= entry["d"] <= 100000):
            state["edit_log"].append({"t": entry["t"], "k": entry["k"], "d": entry["d"]})
    del state["edit_log"][:-EDIT_LOG_MAX]


# --- Rendering -------------------------------------------------------

# Tracks every proxy created by the current render() call so the previous
# render's proxies can be destroyed before new ones are created -- Pyodide
# does not garbage-collect create_proxy() objects on its own, so leaving
# the old ones attached to now-discarded DOM nodes would leak indefinitely
# over a long session (same bug class Canopy's own audit pass found and
# fixed in its plot-grid renderer).
_active_proxies = []


def _destroy_active_proxies():
    for proxy in _active_proxies:
        proxy.destroy()
    _active_proxies.clear()


def _el(tag, **attrs):
    node = document.createElement(tag)
    for key, value in attrs.items():
        if key == "text":
            node.textContent = value
        elif key == "html":
            node.innerHTML = value
        elif key == "class_":
            node.className = value
        else:
            node.setAttribute(key.replace("_", "-"), str(value))
    return node


# --- Toast / clipboard / confirm helpers --------------------------------

_toast_timer = {"id": None, "proxy": None}
TOAST_MS = 2200


def _toast(message):
    """Brief non-blocking confirmation ("Built!", "Copied!") in the
    #toast live region. Auto-hides; timer calls are skipped harmlessly when
    the JS timer API isn't available (tests)."""
    el = document.getElementById("toast")
    el.textContent = message
    el.hidden = False
    try:
        from js import clearTimeout, setTimeout  # noqa: PLC0415 -- Pyodide-only
    except ImportError:
        return
    if _toast_timer["id"] is not None:
        clearTimeout(_toast_timer["id"])
        if _toast_timer["proxy"] is not None:
            _toast_timer["proxy"].destroy()

    def hide():
        el.hidden = True
        _toast_timer["id"] = None

    proxy = create_proxy(hide)
    _toast_timer["proxy"] = proxy
    _toast_timer["id"] = setTimeout(proxy, TOAST_MS)


def _copy_text(text, label):
    try:
        from js import navigator  # noqa: PLC0415 -- Pyodide-only
        navigator.clipboard.writeText(text)
    except Exception:  # noqa: BLE001 -- no clipboard API / not permitted
        _toast(f"Couldn't copy {label} -- select the text and copy it manually.")
        return False
    _toast(f"Copied {label}!")
    return True


def _ask_confirm(action_id, message, confirm_label, on_confirm):
    """Uses the hub's shared ConfirmDialog when the page loaded it (it does,
    see index.html); otherwise falls back to a plain browser confirm()."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only
        dialog = getattr(window, "ConfirmDialog", None)
    except ImportError:
        dialog = None
    if dialog is None:
        if confirm(message):
            on_confirm()
        return
    proxy = create_proxy(on_confirm)
    _active_dialog_proxies.append(proxy)
    dialog.ask(id=action_id, message=message, confirmLabel=confirm_label, onConfirm=proxy)


_active_dialog_proxies = []


def _make_copy_handler(text_fn, label):
    def handler(_event):
        _copy_text(text_fn(), label)

    return handler


def _wiki_link(href, key):
    """Wiki anchor that remembers being clicked this session (a.visited-
    session), so it stays visually distinct across re-renders."""
    link = _el("a", href=href, target="_blank", rel="noopener", text="Wiki ↗")
    if key in _visited_wiki:
        link.className = "visited-session"

    def on_click(_event):
        _visited_wiki.add(key)
        link.className = "visited-session"

    proxy = create_proxy(on_click)
    link.addEventListener("click", proxy)
    _active_proxies.append(proxy)
    return link


def _make_part_change_handler(name, target_input, owned_input):
    """Closes directly over the row's own input elements rather than
    re-querying the DOM for them by attribute selector -- both because
    it's simpler than a CSS-attribute query and because it's exactly what
    render() already has in hand at the moment it creates these inputs."""

    def handler(_event):
        target = max(0, int(target_input.value or 0))
        owned = max(0, min(target, int(owned_input.value or 0)))
        part = state["parts"].setdefault(name, {})
        before = completion_snapshot()
        gained = owned - int(part.get("owned", 0))
        part["target"] = target
        part["owned"] = owned
        if gained > 0:
            note_edit("build", gained)
        record_completions(before)
        render()

    return handler


def _make_resource_change_handler(name, raw_input, built_input):
    def handler(_event):
        raw = max(0, int(raw_input.value or 0))
        built = max(0, int(built_input.value or 0))
        inv = state["inventory"].setdefault(name, {})
        if raw != int(inv.get("raw", 0)) or built != int(inv.get("built", 0)):
            note_edit("resource")
            set_source(name, "hand")
        log_gain(name, int(inv.get("raw", 0)) + int(inv.get("built", 0)), raw + built)
        inv["raw"] = raw
        inv["built"] = built
        render()

    return handler


def _make_blueprint_handler(name, box):
    def handler(_event):
        state["blueprints"][name] = bool(box.checked)
        render()

    return handler


def _make_build_handler(name):
    def handler(_event):
        ingredients = RECIPES.get(name, {}).get("ingredients", {})
        inventory = state["inventory"]
        if not has_enough_for_one(ingredients, inventory):
            document.getElementById("status-message").textContent = (
                f"Can't build {name}: not enough resources on hand for it anymore."
            )
            return

        # Consume built (refined) stock first, then raw, same priority
        # order the resource checklist itself uses to decide what's short.
        for resource, qty in ingredients.items():
            if resource == "Credits":
                continue
            inv = inventory.setdefault(resource, {"raw": 0, "built": 0})
            built = int(inv.get("built", 0))
            raw = int(inv.get("raw", 0))
            take_built = min(built, qty)
            take_raw = min(raw, qty - take_built)
            inv["built"] = built - take_built
            inv["raw"] = raw - take_raw

        before = completion_snapshot()
        part = state["parts"].setdefault(name, {})
        target = int(part.get("target", 0))
        part["owned"] = min(target, int(part.get("owned", 0)) + 1) if target else int(part.get("owned", 0)) + 1
        note_edit("build")
        record_completions(before)
        document.getElementById("status-message").textContent = f"Built {name}."
        _toast(f"Built! {name}")
        render()

    return handler


def _make_note_handler(name, textarea, summary):
    def handler(_event):
        text = str(textarea.value or "")[:NOTE_MAX_LEN]
        if text.strip():
            state["notes"][name] = text
        else:
            state["notes"].pop(name, None)
        summary.textContent = _note_summary(text)

    return handler


def _note_summary(text):
    text = (text or "").strip()
    if not text:
        return "note"
    return "note: " + (text[:28] + "…" if len(text) > 28 else text)


def _render_component_table(components):
    tbody = document.getElementById("components-body")
    tbody.innerHTML = ""
    last_category = None
    prefs = state["prefs"]
    sort_mode = prefs["sort"]
    rows = arrange_components(components, sort_mode, _search["text"], prefs["hide_complete"], _filters["tag"])

    if not rows:
        empty = _el("tr", class_="empty-row")
        empty.appendChild(_el("td", colspan="6", text="No parts match the current search/filter."))
        tbody.appendChild(empty)

    for rank, part in enumerate(rows, start=1):
        if sort_mode == "category" and part["category"] != last_category:
            info = CATEGORY_INFO.get(part["category"], {"label": part["category"], "note": ""})
            cat_row = _el("tr", class_="category-row")
            cat_cell = _el("td", colspan="6")
            cat_cell.innerHTML = f"<strong>{info['label']}</strong> <span class=\"category-note\">{info['note']}</span>"
            cat_row.appendChild(cat_cell)
            tbody.appendChild(cat_row)
            last_category = part["category"]

        row_class = "complete" if part["complete"] else ("buildable" if part["can_build"] else "")
        row = _el("tr", class_=row_class, **{"data-part": part["name"]})

        name_cell = _el("td")
        name_cell.innerHTML = f"<strong>{part['name']}</strong>" + (
            ' <span class="ready-badge">ready</span>' if part["can_build"] else ""
        )
        if sort_mode != "category":
            label = CATEGORY_INFO.get(part["category"], {}).get("label", part["category"])
            name_cell.innerHTML += f' <span class="tag">{label.replace(" builds", "")}</span>'
        if sort_mode == "priority" and not part["complete"]:
            name_cell.innerHTML += f' <span class="tag rank">#{rank}</span>'
        if part["missing"]:
            n = len(part["missing"])
            name_cell.appendChild(_el(
                "div", class_="missing-note",
                text=f"{n} resource{'s' if n != 1 else ''} short: " + ", ".join(sorted(part["missing"])),
            ))
        if part["name"] in PART_NOTES:
            name_cell.appendChild(_el("div", class_="part-tip", text=PART_NOTES[part["name"]]))
        note_details = _el("details", class_="part-note")
        note_summary = _el("summary", text=_note_summary(part["note"]))
        note_details.appendChild(note_summary)
        note_box = _el(
            "textarea", rows="2", maxlength=str(NOTE_MAX_LEN),
            aria_label=f"Note to self for {part['name']}", placeholder="Note to self…",
        )
        note_box.value = part["note"]
        note_details.appendChild(note_box)
        note_proxy = create_proxy(_make_note_handler(part["name"], note_box, note_summary))
        note_box.addEventListener("change", note_proxy)
        _active_proxies.append(note_proxy)
        name_cell.appendChild(note_details)
        name_cell.appendChild(_build_controls(part["name"]))
        row.appendChild(name_cell)

        target_cell = _el("td")
        target_input = _el("input", type="number", min="0", class_="target-input",
                           aria_label=f"{part['name']} target")
        target_input.value = str(part["target"])
        target_cell.appendChild(target_input)
        row.appendChild(target_cell)

        owned_cell = _el("td")
        owned_input = _el("input", type="number", min="0", **{"max": str(part["target"])}, class_="owned-input",
                          aria_label=f"{part['name']} owned")
        owned_input.value = str(part["owned"])
        owned_cell.appendChild(owned_input)
        row.appendChild(owned_cell)

        remaining_cell = _el("td", class_="remaining", text=str(part["remaining"]))
        row.appendChild(remaining_cell)

        wiki_cell = _el("td")
        wiki_cell.appendChild(_wiki_link(part["wiki"], part["name"]))
        row.appendChild(wiki_cell)

        build_cell = _el("td")
        build_btn = _el("button", class_="build-btn", text="Build")
        if not part["can_build"]:
            build_btn.setAttribute("disabled", "disabled")
        build_proxy = create_proxy(_make_build_handler(part["name"]))
        build_btn.addEventListener("click", build_proxy)
        _active_proxies.append(build_proxy)
        build_cell.appendChild(build_btn)
        row.appendChild(build_cell)

        tbody.appendChild(row)

        change_proxy = create_proxy(_make_part_change_handler(part["name"], target_input, owned_input))
        target_input.addEventListener("change", change_proxy)
        owned_input.addEventListener("change", change_proxy)
        _active_proxies.append(change_proxy)

    done = sum(1 for p in components if p["complete"])
    total = len(components)
    pct = round(done / total * 100) if total else 0
    document.getElementById("component-progress").textContent = f"{done} / {total} complete · {pct}%"
    bar = document.getElementById("progress-bar")
    bar.style.width = f"{pct}%"


def _progress_bar(label, done, total):
    """One labelled "X/Y" bar for the dashboard (role=progressbar)."""
    pct = round(done / total * 100) if total else 0
    wrap = _el("div", class_="cat-progress")
    wrap.appendChild(_el("span", class_="cat-progress-label", text=label))
    track = _el("div", class_="progress small", role="progressbar", aria_valuemin="0",
                aria_valuemax=str(total), aria_valuenow=str(done), aria_label=f"{label} progress")
    fill = _el("div", class_="progress-fill")
    fill.style.width = f"{pct}%"
    track.appendChild(fill)
    wrap.appendChild(track)
    wrap.appendChild(_el("span", class_="cat-progress-count", text=f"{done}/{total} parts complete"))
    return wrap


def _render_dashboard(components):
    days = days_since(DATA_UPDATED)
    if days is None:
        age = "Recipe data: last-updated date unknown"
    elif days == 0:
        age = f"Recipe data last updated {DATA_UPDATED} (today)"
    else:
        age = f"Recipe data last updated {DATA_UPDATED} ({days} day{'s' if days != 1 else ''} ago)"
    document.getElementById("data-updated").textContent = age

    holder = document.getElementById("category-progress")
    holder.innerHTML = ""
    for cat, (done, total) in category_progress(components).items():
        holder.appendChild(_progress_bar(CATEGORY_INFO[cat]["label"], done, total))

    blocking = whats_blocking(components)
    box = document.getElementById("blocking-summary")
    if blocking is None:
        pending = any(not p["complete"] for p in components)
        box.textContent = ("Nothing is blocking you -- everything unfinished has the resources it needs."
                           if pending else "Every part is built.")
    else:
        resource, count, names = blocking
        box.textContent = (
            f"What's blocking me: {resource} -- short for {count} unfinished build{'s' if count != 1 else ''} "
            f"({', '.join(names[:4])}{'…' if len(names) > 4 else ''})."
        )


def _render_resource_table(resources):
    tbody = document.getElementById("resources-body")
    tbody.innerHTML = ""

    for resource in resources:
        row_class = "complete" if resource["complete"] else ""
        if resource["enough"]:
            row_class = (row_class + " enough").strip()
        row = _el("tr", class_=row_class, **{"data-resource": resource["name"]})

        name_cell = _el("td")
        name_cell.innerHTML = (
            f"<strong>{resource['name']}</strong>"
            + (' <span class="grindy-flag" title="Large total requirement across your build list">grindy</span>'
               if resource["grindy"] and not resource["complete"] else "")
            + (' <span class="rare-flag" title="Hard to come by: a single place or a gated source. Do not spend it on things outside this list.">rare</span>'
               if resource["rarity"] == "rare" else "")
            + (f' <span class="market-price" title="Lowest online sell price on Warframe.market">~{resource["market_price"]:g} plat each</span>'
               if resource.get("market_price") else "")
        )
        copy_btn = _el("button", class_="copy-btn secondary", type="button", text="Copy",
                       aria_label=f"Copy resource name {resource['name']}", title="Copy resource name")
        copy_proxy = create_proxy(_make_copy_handler(lambda n=resource["name"]: n, resource["name"]))
        copy_btn.addEventListener("click", copy_proxy)
        _active_proxies.append(copy_proxy)
        name_cell.appendChild(copy_btn)
        enough_row = _el("label", class_="enough-row")
        enough_box = _el("input", type="checkbox", class_="enough-input",
                         aria_label=f"I have enough {resource['name']}")
        enough_box.checked = resource["enough"]
        enough_row.appendChild(enough_box)
        enough_row.appendChild(_el("span", text=" I have enough (stop counting it as a need)"))
        name_cell.appendChild(enough_row)
        enough_proxy = create_proxy(_make_enough_handler(resource["name"], enough_box))
        enough_box.addEventListener("change", enough_proxy)
        _active_proxies.append(enough_proxy)
        loc_icon = location_icon(resource["location"])
        name_cell.appendChild(
            _el("div", class_="resource-location", text=f"{loc_icon} {resource['location']}")
        )
        used_in = _el("details", class_="used-in")
        summary = _el("summary", text=(
            f"used in ({len(resource['used_in'])}) · "
            + (f"{resource['built_short']} still needed" if resource["built_short"] else "covered")
        ))
        used_in.appendChild(summary)
        ul = _el("ul")
        for usage in resource["used_in"]:
            li = _el("li")
            li.innerHTML = f"{usage['name']} <span class=\"used-in-qty\">×{usage['qty']}</span>"
            ul.appendChild(li)
        used_in.appendChild(ul)
        name_cell.appendChild(used_in)
        source = SYNDICATE_SOURCES.get(resource["name"])
        if source:
            owned = blueprint_owned(resource["name"])
            bp_row = _el("label", class_="blueprint-row")
            bp_box = _el("input", type="checkbox", class_="blueprint-input",
                         aria_label=f"Blueprint owned for {resource['name']}")
            bp_box.checked = owned
            bp_row.appendChild(bp_box)
            bp_row.appendChild(_el("span", text=(
                f" blueprint: {source['vendor']} ({source['faction']}), {source['standing']:,} standing, rank {source['rank']}"
                + (" (owned)" if owned else "")
            )))
            name_cell.appendChild(bp_row)
            bp_proxy = create_proxy(_make_blueprint_handler(resource["name"], bp_box))
            bp_box.addEventListener("change", bp_proxy)
            _active_proxies.append(bp_proxy)
        if resource.get("refinery"):
            plan = resource["refinery"]
            refine = _el("details", class_="used-in refinery")
            refine.appendChild(_el("summary", text=(
                f"refine: {plan['crafts']} craft(s) → {plan['produces']} {resource['name']}"
            )))
            ul = _el("ul")
            for material, qty in plan["ingredients"].items():
                ul.appendChild(_el("li", text=f"{material} ×{qty}"))
            ul.appendChild(_el("li", text=f"Credits ×{plan['credits']}"))
            refine.appendChild(ul)
            name_cell.appendChild(refine)
        row.appendChild(name_cell)

        needed_cell = _el("td", text=str(resource["needed"]))
        row.appendChild(needed_cell)

        built_cell = _el("td")
        built_input = _el("input", type="number", min="0", class_="built-input")
        built_input.value = str(resource["built_have"])
        built_cell.appendChild(built_input)
        src = state["inv_source"].get(resource["name"])
        if src:
            built_cell.appendChild(_el(
                "span", class_=f"src-marker src-{src}", text=SOURCE_MARKS[src],
                title=("Typed by hand" if src == "hand" else "Set by an inventory import"),
            ))
        row.appendChild(built_cell)

        raw_cell = _el("td")
        raw_input = _el("input", type="number", min="0", class_="raw-input")
        raw_input.value = str(resource["raw_have"])
        raw_cell.appendChild(raw_input)
        row.appendChild(raw_cell)

        short_cell = _el("td", class_="resource-remaining", text=str(resource["built_short"]))
        row.appendChild(short_cell)

        wiki_cell = _el("td")
        wiki_cell.appendChild(_wiki_link(resource["wiki"], resource["name"]))
        row.appendChild(wiki_cell)

        tbody.appendChild(row)

        change_proxy = create_proxy(_make_resource_change_handler(resource["name"], raw_input, built_input))
        built_input.addEventListener("change", change_proxy)
        raw_input.addEventListener("change", change_proxy)
        _active_proxies.append(change_proxy)


def _render_summary(components, all_resources):
    resources = active_rows(all_resources)  # resources marked "I have enough" stop counting as needs
    parts_left = sum(1 for p in components if not p["complete"])
    resources_short = sum(1 for r in resources if not r["complete"])
    ready_now = sum(1 for p in components if p["can_build"])

    if parts_left == 0:
        text = "Every requested part is built. Nothing left to farm for this list."
    else:
        text = (
            f"{parts_left} part(s) still needed, {resources_short} resource(s) still short. "
            f"{ready_now} part(s) are ready to build right now."
        )
    document.getElementById("summary").textContent = text
    market_box = document.getElementById("market-summary")
    market = market_text(resources)
    market_box.hidden = not market
    market_box.textContent = market
    syndicate_box = document.getElementById("syndicate-summary")
    syndicate = syndicate_text(resources)
    syndicate_box.hidden = not syndicate
    syndicate_box.textContent = syndicate
    route_box = document.getElementById("route-planner")
    route = route_text(resources)
    route_box.hidden = not route
    route_box.textContent = route
    totals = refinery_totals(resources)
    refinery_box = document.getElementById("refinery-summary")
    refinery_box.hidden = not totals
    refinery_box.textContent = (
        "To refine everything you are short on: "
        + ", ".join(f"{name} ×{qty}" for name, qty in sorted(totals.items()))
        + "."
    ) if totals else ""
    budget_box = _by_id("budget-summary")
    budget = budget_text(resources)
    budget_box.hidden = not budget
    budget_box.textContent = budget


def _sync_controls():
    prefs = state["prefs"]
    document.getElementById("sort-select").value = prefs["sort"]
    document.getElementById("hide-complete-toggle").checked = prefs["hide_complete"]


def render():
    _destroy_active_proxies()
    components, resources = calculate()
    shown = display_components(components)
    _sync_controls()
    _render_dashboard(shown)
    _render_component_table(shown)
    _render_resource_table(resources)
    _render_summary(components, resources)
    _render_tools(components, resources)
    document.getElementById("shopping-text").value = shopping_list_text(active_rows(resources))
    document.getElementById("farm-log-text").textContent = farm_log_text()
    document.getElementById("combo-compare").textContent = combos_text(components)


# --- Batch A UI ----------------------------------------------------------

TAB_KEYS = ("timers", "mastery", "trader", "dailies", "history", "goals", "share", "tags", "notes", "log")


def _by_id(element_id):
    return document.getElementById(element_id)


def _button(text, handler, aria=None, class_="secondary mini-btn"):
    """A small button whose click handler is destroyed with the next render()."""
    attrs = {"type": "button", "class_": class_, "text": text}
    if aria:
        attrs["aria_label"] = aria
    btn = _el("button", **attrs)
    proxy = create_proxy(handler)
    btn.addEventListener("click", proxy)
    _active_proxies.append(proxy)
    return btn


def _mini_row(text, buttons=(), class_=""):
    row = _el("div", class_=("mini-row " + class_).strip())
    row.appendChild(_el("span", class_="mini-text", text=text))
    for btn in buttons:
        row.appendChild(btn)
    return row


def _fill(container_id, rows, empty_text=""):
    box = _by_id(container_id)
    box.innerHTML = ""
    for row in rows:
        box.appendChild(row)
    if not rows and empty_text:
        box.appendChild(_el("p", class_="sync", text=empty_text))
    return box


def _say(message_id, message):
    _by_id(message_id).textContent = message


def _tag_pill(label):
    pill = _el("span", class_="build-tag", text=label)
    pill.style.borderLeftColor = tag_color(label)
    return pill


def _make_enough_handler(name, box):
    def handler(_event):
        set_enough(name, bool(box.checked))
        render()

    return handler


def _make_pin_handler(name):
    def handler(_event):
        ok, message = toggle_pin(name)
        _say("week-message", message)
        if not ok:
            _say("status-message", message)
        render()

    return handler


def _make_tag_select_handler(name, select):
    def handler(_event):
        ok, message = assign_tag(name, str(select.value or ""))
        _say("tag-message", message)
        render()

    return handler


def _build_controls(name):
    """The per-part pin star and colour-tag picker shown under a part's note."""
    wrap = _el("div", class_="build-controls")
    pinned = name in state["pins"]
    star = _el("button", type="button", class_="pin-btn secondary", text="★ pinned" if pinned else "☆ pin",
               aria_label=f"{'Unpin' if pinned else 'Pin'} {name} {'from' if pinned else 'to'} this week",
               aria_pressed="true" if pinned else "false")
    proxy = create_proxy(_make_pin_handler(name))
    star.addEventListener("click", proxy)
    _active_proxies.append(proxy)
    wrap.appendChild(star)
    select = _el("select", class_="tag-select", aria_label=f"Colour tag for {name}")
    none = _el("option", value="", text="no tag")
    select.appendChild(none)
    for label in tag_labels():
        select.appendChild(_el("option", value=label, text=label))
    select.value = state["tags"].get(name, "")
    proxy = create_proxy(_make_tag_select_handler(name, select))
    select.addEventListener("change", proxy)
    _active_proxies.append(proxy)
    wrap.appendChild(select)
    if name in state["tags"]:
        wrap.appendChild(_tag_pill(state["tags"][name]))
    return wrap


def _render_names_list():
    box = _by_id("build-names-list")
    box.innerHTML = ""
    for name in build_names():
        box.appendChild(_el("option", value=name))


def _render_tag_filter():
    select = _by_id("tag-filter-select")
    select.innerHTML = ""
    select.appendChild(_el("option", value="", text="All tags"))
    for label in tag_labels():
        select.appendChild(_el("option", value=label, text=label))
    if _filters["tag"] not in tag_labels():
        _filters["tag"] = ""
    select.value = _filters["tag"]
    assign = _by_id("tag-assign-select")
    assign.innerHTML = ""
    for label in tag_labels():
        assign.appendChild(_el("option", value=label, text=label))


def _render_week(components):
    rows = []
    for item in pin_status(components):
        row = _el("div", class_="pin-card")
        row.appendChild(_el("strong", text=item["name"]))
        row.appendChild(_el("span", class_="tag", text=item["kind"]))
        row.appendChild(_el("span", class_="pin-status", text=item["status"]))
        if item["name"] in state["tags"]:
            row.appendChild(_tag_pill(state["tags"][item["name"]]))
        row.appendChild(_button("Unpin", _make_pin_handler(item["name"]), aria=f"Unpin {item['name']}"))
        rows.append(row)
    _fill("week-pins", rows, f"Nothing pinned. Star up to {PIN_MAX} builds (parts above, or type a part or combo name) to keep them here.")
    strip = _by_id("recent-completed")
    strip.innerHTML = ""
    strip.hidden = not state["completed"]
    if state["completed"]:
        strip.appendChild(_el("strong", text="Recently completed: "))
        for entry in reversed(state["completed"]):
            text = f"{entry['n']} ({entry['d']})"
            if entry["n"] in state["loadouts"]:
                text += " · notes"
            strip.appendChild(_el("span", class_="recent-chip", text=text))


def _render_timers():
    now = _now_ms()
    rows = []
    for index, timer in enumerate(state["timers"]):
        ready = timer["ms"] <= now
        rows.append(_mini_row(
            timer_line(timer, now) + (" · notify on" if timer["notify"] else ""),
            [_button("Remove", _make_timer_remove_handler(index), aria=f"Remove timer {timer['n']}")],
            class_="timer-ready" if ready else "",
        ))
    _fill("timer-list", rows, "No craft timers yet.")
    permission = notification_permission()
    if permission is None:
        hint = "This browser has no notification support; timers still show their ready-at time."
    elif permission == "granted":
        hint = "Notifications are allowed. They only fire while this page stays open."
    elif permission == "denied":
        hint = "Notifications are blocked in this browser; timers still show their ready-at time."
    else:
        hint = "Press Enable notifications to allow a reminder while this page is open."
    _by_id("timer-hint").textContent = hint
    _by_id("timer-notify-button").hidden = permission in (None, "granted", "denied")
    schedule_notifications(now)


def _make_timer_remove_handler(index):
    def handler(_event):
        remove_timer(index)
        render()

    return handler


def _render_mastery():
    m = state["mastery"]
    _by_id("mastery-base-input").value = str(m["base"])
    _by_id("mastery-summary").textContent = mastery_text()
    rows = []
    for index, item in enumerate(m["items"]):
        row = _el("div", class_="mini-row")
        label = _el("label", class_="mini-text")
        box = _el("input", type="checkbox", class_="mastery-input", aria_label=f"Ranked {item['n']}")
        box.checked = item["done"]
        label.appendChild(box)
        label.appendChild(_el("span", text=f" {item['n']} ({MASTERY_ITEM_XP[item['t']]:,} points)"))
        row.appendChild(label)
        proxy = create_proxy(_make_mastery_tick_handler(index, box))
        box.addEventListener("change", proxy)
        _active_proxies.append(proxy)
        row.appendChild(_button("Remove", _make_mastery_remove_handler(index), aria=f"Remove {item['n']}"))
        rows.append(row)
    _fill("mastery-list", rows, "No items yet. Add the weapons and frames you plan to rank.")


def _make_mastery_tick_handler(index, box):
    def handler(_event):
        state["mastery"]["items"][index]["done"] = bool(box.checked)
        render()

    return handler


def _make_mastery_remove_handler(index):
    def handler(_event):
        del state["mastery"]["items"][index]
        render()

    return handler


def _render_trader():
    _by_id("trader-date-input").value = state["trader"]["last"]
    _by_id("trader-reminder").textContent = baro_text()
    rows = [
        _mini_row(text, [_button("Remove", _make_watch_remove_handler(i), aria=f"Stop watching for {text}")])
        for i, text in enumerate(state["trader"]["watch"])
    ]
    _fill("trader-list", rows, "Nothing on the watch list yet.")


def _make_watch_remove_handler(index):
    def handler(_event):
        del state["trader"]["watch"][index]
        render()

    return handler


def _render_checklist():
    roll_checklist()
    _by_id("checklist-reset-info").textContent = check_reset_text()
    for kind in CHECK_KINDS:
        rows = []
        for item in [i for i in state["checklist"]["items"] if i["k"] == kind]:
            row = _el("div", class_="mini-row")
            label = _el("label", class_="mini-text")
            box = _el("input", type="checkbox", class_="check-input", aria_label=f"{kind} task {item['n']}")
            box.checked = item["n"] in state["checklist"]["ticks"][kind]["done"]
            label.appendChild(box)
            label.appendChild(_el("span", text=f" {item['n']}"))
            row.appendChild(label)
            proxy = create_proxy(_make_check_tick_handler(item["n"], kind))
            box.addEventListener("change", proxy)
            _active_proxies.append(proxy)
            row.appendChild(_button("Remove", _make_check_remove_handler(item["n"], kind), aria=f"Remove {item['n']}"))
            rows.append(row)
        _fill(f"checklist-{kind}", rows, f"No {kind} tasks yet.")


def _make_check_tick_handler(name, kind):
    def handler(_event):
        toggle_check(name, kind)
        render()

    return handler


def _make_check_remove_handler(name, kind):
    def handler(_event):
        remove_check_item(name, kind)
        render()

    return handler


def _render_history():
    _by_id("history-chart").innerHTML = history_chart_svg()
    _by_id("history-summary").textContent = history_summary()


def _render_goals():
    rows = []
    for index, goal in enumerate(state["goals"]):
        row = _el("div", class_="mini-row")
        label = _el("label", class_="mini-text" + (" goal-done" if goal["done"] else ""))
        box = _el("input", type="checkbox", class_="goal-input", aria_label=f"Goal done: {goal['text']}")
        box.checked = goal["done"]
        label.appendChild(box)
        label.appendChild(_el("span", text=f" {goal['text']}"))
        row.appendChild(label)
        proxy = create_proxy(_make_goal_tick_handler(index, box))
        box.addEventListener("change", proxy)
        _active_proxies.append(proxy)
        row.appendChild(_button("Remove", _make_goal_remove_handler(index), aria=f"Remove goal {goal['text']}"))
        rows.append(row)
    _fill("goal-list", rows, "No long-term goals yet. These stay out of your shopping list.")


def _make_goal_tick_handler(index, box):
    def handler(_event):
        state["goals"][index]["done"] = bool(box.checked)
        render()

    return handler


def _make_goal_remove_handler(index):
    def handler(_event):
        del state["goals"][index]
        render()

    return handler


def _render_tags_panel():
    legend = _by_id("tag-legend")
    legend.innerHTML = ""
    for label in tag_labels():
        count = sum(1 for v in state["tags"].values() if v == label)
        pill = _tag_pill(label)
        pill.textContent = f"{label} ({count})"
        legend.appendChild(pill)


def _render_loadouts():
    rows = []
    for name, entry in sorted(state["loadouts"].items()):
        row = _el("div", class_="loadout-card")
        row.appendChild(_el("strong", text=name))
        if entry["mods"]:
            row.appendChild(_el("div", class_="loadout-line", text="Mods: " + entry["mods"]))
        if entry["play"]:
            row.appendChild(_el("div", class_="loadout-line", text="Playstyle: " + entry["play"]))
        row.appendChild(_button("Remove", _make_loadout_remove_handler(name), aria=f"Remove notes for {name}"))
        rows.append(row)
    _fill("loadout-list", rows, "No notes yet. Notes attach to finished builds.")


def _make_loadout_remove_handler(name):
    def handler(_event):
        state["loadouts"].pop(name, None)
        render()

    return handler


def _render_share(components, resources):
    _by_id("share-export-text").value = export_goals_code(components, resources)
    _by_id("wishlist-text").value = wishlist_text(components, resources)


def _select_tab(key):
    if key not in TAB_KEYS:
        return
    _ui["tab"] = key
    for k in TAB_KEYS:
        panel = _by_id(f"tab-{k}")
        button = _by_id(f"tab-btn-{k}")
        panel.hidden = k != key
        button.className = "tab-btn selected" if k == key else "tab-btn"
        button.setAttribute("aria-selected", "true" if k == key else "false")


def _render_tools(components, resources):
    _render_names_list()
    _render_tag_filter()
    _render_week(components)
    _render_timers()
    _render_mastery()
    _render_trader()
    _render_checklist()
    _render_history()
    _render_goals()
    _render_tags_panel()
    _render_loadouts()
    _render_share(components, resources)
    _by_id("edit-log-text").textContent = edit_log_text()
    _by_id("budget-credits-input").value = str(state["budget"]["credits"]) if state["budget"]["credits"] else ""
    _by_id("budget-endo-input").value = str(state["budget"]["endo"]) if state["budget"]["endo"] else ""
    _ui["sig"] = _tick_signature()


def _tick_signature():
    """What the minute tick watches: the two reset periods and which timers are
    ready. A change means the visible text is stale and worth a re-render."""
    now = _now_ms()
    stamps = period_stamps()
    return (stamps["daily"], stamps["weekly"], tuple(t["ms"] <= now for t in state["timers"]))


def tick_minute():
    """Called once a minute: re-renders only if a reset passed or a timer just
    became ready, so typing in a box is never interrupted for nothing."""
    if _tick_signature() != _ui["sig"]:
        render()
        return True
    return False


# --- Batch A event handlers ----------------------------------------------

def _int_input(element_id, limit):
    text = str(_by_id(element_id).value or "").strip()
    if not text:
        return 0
    try:
        return max(0, min(limit, int(float(text))))
    except (ValueError, OverflowError):
        return 0


def _on_pin_add(_event=None):
    _ok, message = toggle_pin(_by_id("week-pin-input").value)
    _say("week-message", message)
    if _ok:
        _by_id("week-pin-input").value = ""
    render()


def _on_timer_add(_event=None):
    start = parse_local_datetime(_by_id("timer-start-input").value)
    ready = parse_local_datetime(_by_id("timer-ready-input").value)
    duration = parse_duration_minutes(_by_id("timer-duration-input").value)
    if ready is None and str(_by_id("timer-ready-input").value or "").strip():
        _say("timer-message", "That ready-at time is not valid.")
        return
    if ready is None and str(_by_id("timer-duration-input").value or "").strip() and duration is None:
        _say("timer-message", "Duration should look like 12h, 1d 2h or 90m.")
        return
    ok, message = add_timer(_by_id("timer-name-input").value, start, duration, ready,
                            bool(_by_id("timer-notify-check").checked))
    _say("timer-message", message)
    if ok:
        note_edit("timer")
        for element_id in ("timer-name-input", "timer-start-input", "timer-duration-input", "timer-ready-input"):
            _by_id(element_id).value = ""
    render()


def _on_timer_notify(_event=None):
    if not request_notification_permission():
        _say("timer-message", "This browser cannot show notifications.")
    else:
        _say("timer-message", "Asked the browser for permission. Choose Allow in its prompt.")
    render()


def _on_budget(_event=None):
    state["budget"]["credits"] = _int_input("budget-credits-input", BUDGET_MAX)
    state["budget"]["endo"] = _int_input("budget-endo-input", BUDGET_MAX)
    render()


def _on_mastery_base(_event=None):
    state["mastery"]["base"] = _int_input("mastery-base-input", MASTERY_BASE_MAX)
    render()


def _on_mastery_add(_event=None):
    ok, message = add_mastery_item(_by_id("mastery-name-input").value, str(_by_id("mastery-type-select").value))
    _say("mastery-message", message)
    if ok:
        _by_id("mastery-name-input").value = ""
    render()


def _on_trader_date(_event=None):
    text = str(_by_id("trader-date-input").value or "").strip()
    state["trader"]["last"] = text if _valid_date(text) else ""
    render()


def _on_trader_add(_event=None):
    ok, message = add_watch(_by_id("trader-item-input").value)
    _say("trader-message", message)
    if ok:
        _by_id("trader-item-input").value = ""
    render()


def _on_check_add(_event=None):
    ok, message = add_check_item(_by_id("checklist-name-input").value, str(_by_id("checklist-kind-select").value))
    _say("checklist-message", message)
    if ok:
        _by_id("checklist-name-input").value = ""
    render()


def _on_snapshot(_event=None):
    take_snapshot()
    render()


def _on_clear_history(_event=None):
    state["history"] = []
    render()


def _on_goal_add(_event=None):
    ok, message = add_goal(_by_id("goal-input").value)
    _say("goal-message", message)
    if ok:
        note_edit("goal")
        _by_id("goal-input").value = ""
    render()


def _on_tag_add_label(_event=None):
    ok, message = add_tag_label(_by_id("tag-label-input").value)
    _say("tag-message", message)
    if ok:
        _by_id("tag-label-input").value = ""
    render()


def _on_tag_remove_label(_event=None):
    _ok, message = remove_tag_label(_by_id("tag-label-input").value)
    _say("tag-message", message)
    render()


def _on_tag_assign(_event=None):
    ok, message = assign_tag(_by_id("tag-name-input").value, str(_by_id("tag-assign-select").value))
    _say("tag-message", message)
    if ok:
        _by_id("tag-name-input").value = ""
    render()


def _on_tag_clear(_event=None):
    _ok, message = assign_tag(_by_id("tag-name-input").value, "")
    _say("tag-message", message)
    render()


def _on_tag_filter(_event=None):
    _filters["tag"] = str(_by_id("tag-filter-select").value or "")
    render()


def _on_loadout_save(_event=None):
    ok, message = set_loadout(_by_id("loadout-name-input").value, _by_id("loadout-mods-input").value,
                              _by_id("loadout-play-input").value)
    _say("loadout-message", message)
    if ok:
        for element_id in ("loadout-name-input", "loadout-mods-input", "loadout-play-input"):
            _by_id(element_id).value = ""
    render()


def _on_share_import(_event=None):
    data, error = parse_goals_code(_by_id("share-import-input").value)
    if data is None:
        _say("share-result", error)
        return
    _components, resources = calculate()
    _say("share-result", goals_comparison_text(data, resources))


def _on_clear_edit_log(_event=None):
    state["edit_log"] = []
    render()


def _make_tab_handler(key):
    def handler(_event):
        _select_tab(key)

    return handler


SHORTCUTS = (
    ("/", "Focus the part search box"),
    ("h", "Toggle Archive completed parts"),
    ("s", "Open the shopping list"),
    ("?", "Show or hide this cheat sheet"),
    ("Esc", "Close this cheat sheet"),
)


def _on_keydown(event):
    """Plain single-key shortcuts. Ignored while typing in a field and while
    Ctrl/Cmd/Alt is held, so browser and save-widget shortcuts are untouched."""
    key = str(getattr(event, "key", "") or "")
    if getattr(event, "ctrlKey", False) or getattr(event, "metaKey", False) or getattr(event, "altKey", False):
        return False
    target = getattr(event, "target", None)
    editable = str(getattr(target, "tagName", "") or "").upper() in ("INPUT", "TEXTAREA", "SELECT") or bool(
        getattr(target, "isContentEditable", False))
    overlay = _by_id("shortcut-overlay")
    if key == "Escape":
        if overlay.hidden:
            return False
        overlay.hidden = True
        event.preventDefault()
        return True
    if editable:
        return False
    if key == "?":
        overlay.hidden = not overlay.hidden
    elif key == "/":
        _by_id("search-input").focus()
    elif key in ("h", "H"):
        state["prefs"]["hide_complete"] = not state["prefs"]["hide_complete"]
        render()
    elif key in ("s", "S"):
        details = _by_id("shopping-details")
        details.open = True
        try:
            details.scrollIntoView()
        except Exception:  # noqa: BLE001, S110 -- no scrolling support: opening it is enough
            pass
    else:
        return False
    event.preventDefault()
    return True


def _on_help_button(_event=None):
    overlay = _by_id("shortcut-overlay")
    overlay.hidden = not overlay.hidden


def _on_close_help(_event=None):
    _by_id("shortcut-overlay").hidden = True


def _render_shortcuts():
    box = _by_id("shortcut-list")
    box.innerHTML = ""
    for key, text in SHORTCUTS:
        row = _el("div", class_="shortcut-row")
        row.appendChild(_el("kbd", text=key))
        row.appendChild(_el("span", text=" " + text))
        box.appendChild(row)


def _do_reset():
    state["parts"] = {name: {"target": qty, "owned": 0} for name, qty in DEFAULT_PARTS}
    state["inventory"] = {}
    state["inv_source"] = {}
    document.getElementById("status-message").textContent = "Inventory reset."
    _toast("Inventory reset to zero.")
    render()


def _on_add_combo(_event=None):
    name = document.getElementById("combo-name-input").value
    parts = str(document.getElementById("combo-parts-input").value or "").split(",")
    ok, message = add_combo(name, parts)
    document.getElementById("combo-message").textContent = message
    if ok:
        note_edit("combo")
        document.getElementById("combo-name-input").value = ""
        document.getElementById("combo-parts-input").value = ""
    render()


def _on_remove_combo(_event=None):
    name = str(document.getElementById("combo-remove-input").value or "").strip()
    document.getElementById("combo-message").textContent = (
        f"Removed {name}." if remove_combo(name) else "No custom combo with that name."
    )
    render()


def _on_clear_farm_log(_event=None):
    state["farm_log"] = []
    render()


def on_reset(_event=None):
    _ask_confirm(
        "warframe-tracker-reset-inventory",
        "Reset all component and resource inventory counts to zero? Your notes are kept. This can't be undone.",
        "Reset everything",
        _do_reset,
    )


def _on_search(_event=None):
    _search["text"] = str(document.getElementById("search-input").value or "")
    render()


def _on_sort(_event=None):
    value = str(document.getElementById("sort-select").value)
    if value in SORT_MODES:
        state["prefs"]["sort"] = value
    render()


def _on_hide_complete(_event=None):
    state["prefs"]["hide_complete"] = bool(document.getElementById("hide-complete-toggle").checked)
    render()


def setup():
    def wire(element_id, event, handler):
        proxy = create_proxy(handler)
        document.getElementById(element_id).addEventListener(event, proxy)

    wire("reset-button", "click", on_reset)
    wire("search-input", "input", _on_search)
    wire("sort-select", "change", _on_sort)
    wire("hide-complete-toggle", "change", _on_hide_complete)
    wire("clear-farm-log-button", "click", _on_clear_farm_log)
    wire("combo-add-button", "click", _on_add_combo)
    wire("combo-remove-button", "click", _on_remove_combo)
    wire("copy-shopping-button", "click",
         _make_copy_handler(lambda: document.getElementById("shopping-text").value, "shopping list"))
    wire("copy-wishlist-button", "click",
         _make_copy_handler(lambda: document.getElementById("wishlist-text").value, "wishlist"))
    wire("share-copy-button", "click",
         _make_copy_handler(lambda: document.getElementById("share-export-text").value, "goals code"))
    wire("week-pin-button", "click", _on_pin_add)
    wire("timer-add-button", "click", _on_timer_add)
    wire("timer-notify-button", "click", _on_timer_notify)
    wire("budget-credits-input", "change", _on_budget)
    wire("budget-endo-input", "change", _on_budget)
    wire("mastery-base-input", "change", _on_mastery_base)
    wire("mastery-add-button", "click", _on_mastery_add)
    wire("trader-date-input", "change", _on_trader_date)
    wire("trader-add-button", "click", _on_trader_add)
    wire("checklist-add-button", "click", _on_check_add)
    wire("history-snapshot-button", "click", _on_snapshot)
    wire("history-clear-button", "click", _on_clear_history)
    wire("goal-add-button", "click", _on_goal_add)
    wire("tag-add-label-button", "click", _on_tag_add_label)
    wire("tag-remove-label-button", "click", _on_tag_remove_label)
    wire("tag-assign-button", "click", _on_tag_assign)
    wire("tag-clear-button", "click", _on_tag_clear)
    wire("tag-filter-select", "change", _on_tag_filter)
    wire("loadout-save-button", "click", _on_loadout_save)
    wire("share-import-button", "click", _on_share_import)
    wire("clear-edit-log-button", "click", _on_clear_edit_log)
    wire("shortcut-help-button", "click", _on_help_button)
    wire("shortcut-close-button", "click", _on_close_help)
    for key in TAB_KEYS:
        wire(f"tab-btn-{key}", "click", _make_tab_handler(key))
    document.addEventListener("keydown", create_proxy(_on_keydown))
    _render_shortcuts()
    _select_tab(_ui["tab"])
    try:
        from js import setInterval  # noqa: PLC0415 -- Pyodide-only
        setInterval(create_proxy(tick_minute), 60000)
    except ImportError:
        pass  # no timer API (tests)
    render()


setup()
