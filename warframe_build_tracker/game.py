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

import copy

from js import confirm, document
from pyodide.ffi import create_proxy

WIKI_BASE = "https://wiki.warframe.com/w/"

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
}


def calculate():
    parts = state["parts"]
    inventory = state["inventory"]

    raw_need = {}
    component_status = []

    for name, default_target in DEFAULT_PARTS:
        info = parts.get(name, {})
        target = int(info.get("target", default_target))
        owned = min(int(info.get("owned", 0)), target)

        remaining_parts = max(0, target - owned)
        ingredients = RECIPES.get(name, {}).get("ingredients", {})
        component_status.append({
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
        })

    return component_status, resource_rows


def get_state():
    return {
        "parts": copy.deepcopy(state["parts"]),
        "inventory": copy.deepcopy(state["inventory"]),
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

    render()


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


def _make_part_change_handler(name, target_input, owned_input):
    """Closes directly over the row's own input elements rather than
    re-querying the DOM for them by attribute selector -- both because
    it's simpler than a CSS-attribute query and because it's exactly what
    render() already has in hand at the moment it creates these inputs."""

    def handler(_event):
        target = max(0, int(target_input.value or 0))
        owned = max(0, min(target, int(owned_input.value or 0)))
        part = state["parts"].setdefault(name, {})
        part["target"] = target
        part["owned"] = owned
        render()

    return handler


def _make_resource_change_handler(name, raw_input, built_input):
    def handler(_event):
        raw = max(0, int(raw_input.value or 0))
        built = max(0, int(built_input.value or 0))
        inv = state["inventory"].setdefault(name, {})
        inv["raw"] = raw
        inv["built"] = built
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

        part = state["parts"].setdefault(name, {})
        target = int(part.get("target", 0))
        part["owned"] = min(target, int(part.get("owned", 0)) + 1) if target else int(part.get("owned", 0)) + 1
        document.getElementById("status-message").textContent = f"Built {name}."
        render()

    return handler


def _render_component_table(components):
    tbody = document.getElementById("components-body")
    tbody.innerHTML = ""
    last_category = None

    for part in components:
        if part["category"] != last_category:
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
        row.appendChild(name_cell)

        target_cell = _el("td")
        target_input = _el("input", type="number", min="0", class_="target-input")
        target_input.value = str(part["target"])
        target_cell.appendChild(target_input)
        row.appendChild(target_cell)

        owned_cell = _el("td")
        owned_input = _el("input", type="number", min="0", **{"max": str(part["target"])}, class_="owned-input")
        owned_input.value = str(part["owned"])
        owned_cell.appendChild(owned_input)
        row.appendChild(owned_cell)

        remaining_cell = _el("td", class_="remaining", text=str(part["remaining"]))
        row.appendChild(remaining_cell)

        wiki_cell = _el("td")
        wiki_link = _el("a", href=part["wiki"], target="_blank", text="Wiki ↗")
        wiki_cell.appendChild(wiki_link)
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
    document.getElementById("component-progress").textContent = f"{done} / {total} complete"
    bar = document.getElementById("progress-bar")
    bar.style.width = f"{(done / total * 100) if total else 0}%"


def _render_resource_table(resources):
    tbody = document.getElementById("resources-body")
    tbody.innerHTML = ""

    for resource in resources:
        row_class = "complete" if resource["complete"] else ""
        row = _el("tr", class_=row_class, **{"data-resource": resource["name"]})

        name_cell = _el("td")
        name_cell.innerHTML = (
            f"<strong>{resource['name']}</strong>"
            f"<div class=\"resource-location\">📍 {resource['location']}</div>"
        )
        used_in = _el("details", class_="used-in")
        summary = _el("summary", text=f"used in ({len(resource['used_in'])})")
        used_in.appendChild(summary)
        ul = _el("ul")
        for usage in resource["used_in"]:
            li = _el("li")
            li.innerHTML = f"{usage['name']} <span class=\"used-in-qty\">×{usage['qty']}</span>"
            ul.appendChild(li)
        used_in.appendChild(ul)
        name_cell.appendChild(used_in)
        row.appendChild(name_cell)

        needed_cell = _el("td", text=str(resource["needed"]))
        row.appendChild(needed_cell)

        built_cell = _el("td")
        built_input = _el("input", type="number", min="0", class_="built-input")
        built_input.value = str(resource["built_have"])
        built_cell.appendChild(built_input)
        row.appendChild(built_cell)

        raw_cell = _el("td")
        raw_input = _el("input", type="number", min="0", class_="raw-input")
        raw_input.value = str(resource["raw_have"])
        raw_cell.appendChild(raw_input)
        row.appendChild(raw_cell)

        short_cell = _el("td", class_="resource-remaining", text=str(resource["built_short"]))
        row.appendChild(short_cell)

        wiki_cell = _el("td")
        wiki_link = _el("a", href=resource["wiki"], target="_blank", text="Wiki ↗")
        wiki_cell.appendChild(wiki_link)
        row.appendChild(wiki_cell)

        tbody.appendChild(row)

        change_proxy = create_proxy(_make_resource_change_handler(resource["name"], raw_input, built_input))
        built_input.addEventListener("change", change_proxy)
        raw_input.addEventListener("change", change_proxy)
        _active_proxies.append(change_proxy)


def _render_summary(components, resources):
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


def render():
    _destroy_active_proxies()
    components, resources = calculate()
    _render_component_table(components)
    _render_resource_table(resources)
    _render_summary(components, resources)


def on_reset(_event=None):
    if not confirm("Reset all component and resource inventory counts?"):
        return
    state["parts"] = {name: {"target": qty, "owned": 0} for name, qty in DEFAULT_PARTS}
    state["inventory"] = {}
    document.getElementById("status-message").textContent = "Inventory reset."
    render()


def setup():
    reset_proxy = create_proxy(on_reset)
    document.getElementById("reset-button").addEventListener("click", reset_proxy)
    render()


setup()
