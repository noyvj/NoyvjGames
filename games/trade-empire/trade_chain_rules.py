"""Chain Builder rules and content: goods, recipes, chapters and the hand-made puzzle table."""


# ---------------------------------------------------------------------------
# J-5 -- Chain Builder (its own window): a separate puzzle mode where you plan multi-step production chains
# (Ore to Alloy to Machinery) with intermediate refining colonies and score them by throughput per ship.
# Nothing here touches the main economy: the intermediate goods and recipes below exist ONLY in this mode, and
# a puzzle runs inside the practice-sandbox machinery (the real corporation is set aside whole as a get_state()
# snapshot and loaded back unchanged, the real game does not tick while a puzzle is open, nothing can be lost,
# there is no timer and no fail state). Everything is whole-number arithmetic with no clock and no randomness.
#
# The model (one "cycle" is CHAIN_CYCLE ticks of steady running):
#   - A product is a good the port wants, made along a recipe path (raw good -> refined -> ... -> final good).
#     You pick one site per step (a source for the raw good, a refinery for each recipe) and put ships on each
#     leg of the chain, including the last leg into the port. Ships are dedicated to their leg.
#   - A ship on a leg A -> B carries `cargo` units per trip and fits CHAIN_CYCLE // (2 x distance) whole round
#     trips in a cycle (distance = grid steps between the sites, at least 1), so short legs are worth far more.
#   - A source supplies up to its `cap` per cycle; a refinery processes up to its `cap` units of INPUT per cycle
#     (shared by every product that uses it, the first product listed served first) and turns `take` units of
#     input into `make` units of output, whole runs only.
#   - A product is MET when the port receives at least `need` per cycle; the port takes up to `want`.
#   - Score = units delivered (up to `want`, over all products) / ships used. Par is the best score over every
#     chain that meets all the orders within the fleet (found by an exhaustive search, chain_solve, and pinned
#     by tests for every puzzle). Gold = par, silver = at least CHAIN_SILVER_PERCENT of par, bronze = met.
# ---------------------------------------------------------------------------
CHAIN_CYCLE = 24
CHAIN_SILVER_PERCENT = 85
CHAIN_MAX_PRODUCTS = 2
CHAIN_MAX_STAGES = 3
CHAIN_GOODS = {
    "ore": "Ore", "alloy": "Alloy", "machinery": "Machinery", "plating": "Plating",
    "grain": "Grain", "flour": "Flour", "rations": "Rations",
    "ice": "Ice", "coolant": "Coolant", "cells": "Power cells",
    "silica": "Silica", "glass": "Glass", "lenses": "Lenses",
}
CHAIN_RAW_GOODS = ("ore", "grain", "ice", "silica")
CHAIN_RECIPES = {  # output good -> its one input, units taken, units made, name
    "alloy": {"from": "ore", "take": 2, "make": 1, "name": "Smelting"},
    "machinery": {"from": "alloy", "take": 2, "make": 1, "name": "Forging"},
    "plating": {"from": "alloy", "take": 1, "make": 1, "name": "Rolling"},
    "flour": {"from": "grain", "take": 2, "make": 1, "name": "Milling"},
    "rations": {"from": "flour", "take": 1, "make": 1, "name": "Packing"},
    "coolant": {"from": "ice", "take": 1, "make": 1, "name": "Filtering"},
    "cells": {"from": "coolant", "take": 3, "make": 2, "name": "Cell assembly"},
    "glass": {"from": "silica", "take": 2, "make": 1, "name": "Melting"},
    "lenses": {"from": "glass", "take": 1, "make": 1, "name": "Grinding"},
}
CHAIN_CHAPTERS = {
    1: ("Single hop", "Ship a raw good straight to the port; pick the right source and the right number of ships."),
    2: ("Two hops", "A refinery sits on the way: balance the two legs so neither starves the other."),
    3: ("Shared refiners", "Two orders at once, and the works that serve them are shared."),
    4: ("Bottlenecks", "Small holds, tight fleets and small refineries: every ship has to earn its place."),
}


def _cb_source(name, x, y, good, cap):
    return {"name": name, "pos": (x, y), "kind": "source", "good": good, "cap": cap}


def _cb_refinery(name, x, y, recipes, cap):
    return {"name": name, "pos": (x, y), "kind": "refinery", "recipes": tuple(recipes), "cap": cap}


def _cb_port(name, x, y):
    return {"name": name, "pos": (x, y), "kind": "port"}


def _cb_product(good, port, need, want):
    return {"good": good, "port": port, "need": need, "want": want}


CHAIN_PUZZLES = [
    {"id": "first_delivery", "chapter": 1, "title": "First Delivery", "blurb": "Port Vesper wants ore. Two mines can supply it: one close, one rich.",
     "cargo": 4, "fleet": 6,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 3, 1, "ore", 30),
         "brack": _cb_source("Brack Pit", 5, 2, "ore", 60),
         "vesper": _cb_port("Port Vesper", 1, 0),
     },
     "products": [_cb_product("ore", "vesper", 24, 36)],
     "par": (15, 1), "best": {"sites": [["cinder"]], "ships": [[2]]}},
    {"id": "thin_seam", "chapter": 1, "title": "Thin Seam", "blurb": "Vesper's order has grown, and the nearer mine can no longer cover it alone.",
     "cargo": 4, "fleet": 6,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 3, 1, "ore", 30),
         "brack": _cb_source("Brack Pit", 5, 2, "ore", 60),
         "vesper": _cb_port("Port Vesper", 1, 0),
     },
     "products": [_cb_product("ore", "vesper", 36, 48)],
     "par": (8, 1), "best": {"sites": [["brack"]], "ships": [[5]]}},
    {"id": "near_or_plenty", "chapter": 1, "title": "Near or Plenty", "blurb": "Three mines, one port. Closer is quicker, but how much can each seam give?",
     "cargo": 4, "fleet": 6,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 3, 1, "ore", 40),
         "brack": _cb_source("Brack Pit", 4, 3, "ore", 80),
         "harrow": _cb_source("Harrow Seam", 1, 4, "ore", 22),
         "vesper": _cb_port("Port Vesper", 1, 1),
     },
     "products": [_cb_product("ore", "vesper", 30, 48)],
     "par": (20, 1), "best": {"sites": [["cinder"]], "ships": [[2]]}},
    {"id": "orchard_run", "chapter": 1, "title": "Orchard Run", "blurb": "Lantern Dock needs grain by the hold. The biggest orchard is not always the best run.",
     "cargo": 6, "fleet": 6,
     "sites": {
         "low": _cb_source("Low Orchard", 2, 1, "grain", 36),
         "high": _cb_source("High Orchard", 5, 3, "grain", 90),
         "fen": _cb_source("Fen Farm", 0, 5, "grain", 54),
         "lantern": _cb_port("Lantern Dock", 1, 2),
     },
     "products": [_cb_product("grain", "lantern", 40, 72)],
     "par": (18, 1), "best": {"sites": [["fen"]], "ships": [[3]]}},
    {"id": "ice_for_the_tern", "chapter": 1, "title": "Ice for the Tern", "blurb": "Small holds and a long way: ice for Tern Landing from the quay or the far shelf.",
     "cargo": 3, "fleet": 7,
     "sites": {
         "quay": _cb_source("Frost Quay", 4, 1, "ice", 50),
         "shelf": _cb_source("Long Shelf", 8, 3, "ice", 120),
         "tern": _cb_port("Tern Landing", 1, 1),
     },
     "products": [_cb_product("ice", "tern", 30, 60)],
     "par": (12, 1), "best": {"sites": [["quay"]], "ships": [[3]]}},
    {"id": "dune_glass", "chapter": 1, "title": "Dune Glass", "blurb": "Silica for Vesper from the dunes, the spit or the reef. Mind how many ships you spend.",
     "cargo": 5, "fleet": 8,
     "sites": {
         "dunes": _cb_source("Glass Dunes", 6, 0, "silica", 100),
         "spit": _cb_source("Salt Spit", 2, 4, "silica", 45),
         "reef": _cb_source("Red Reef", 4, 4, "silica", 70),
         "vesper": _cb_port("Port Vesper", 1, 1),
     },
     "products": [_cb_product("silica", "vesper", 45, 90)],
     "par": (15, 1), "best": {"sites": [["spit"]], "ships": [[3]]}},
    {"id": "ore_to_alloy", "chapter": 2, "title": "Ore to Alloy", "blurb": "Smelt ore into alloy on the way to port. Two smelters; two ore make one alloy.",
     "cargo": 4, "fleet": 8,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 0, 0, "ore", 60),
         "kiln": _cb_refinery("Kiln Station", 3, 1, ("alloy",), 40),
         "anvil": _cb_refinery("Anvil Yard", 4, 4, ("alloy",), 60),
         "vesper": _cb_port("Port Vesper", 6, 1),
     },
     "products": [_cb_product("alloy", "vesper", 8, 16)],
     "par": (4, 1), "best": {"sites": [["cinder", "kiln"]], "ships": [[2, 1]]}},
    {"id": "mill_choice", "chapter": 2, "title": "Mill Choice", "blurb": "Turn grain into flour at the Mill Hub or the Press Dock. Two grain make one flour.",
     "cargo": 6, "fleet": 8,
     "sites": {
         "low": _cb_source("Low Orchard", 0, 3, "grain", 60),
         "fen": _cb_source("Fen Farm", 3, 5, "grain", 60),
         "mill": _cb_refinery("Mill Hub", 2, 2, ("flour",), 36),
         "press": _cb_refinery("Press Dock", 5, 3, ("flour",), 36),
         "lantern": _cb_port("Lantern Dock", 7, 2),
     },
     "products": [_cb_product("flour", "lantern", 8, 18)],
     "par": (6, 1), "best": {"sites": [["low", "mill"]], "ships": [[1, 1]]}},
    {"id": "cold_work", "chapter": 2, "title": "Cold Work", "blurb": "Ice becomes coolant at either works. The two legs differ in length, so split your ships to match.",
     "cargo": 3, "fleet": 9,
     "sites": {
         "quay": _cb_source("Frost Quay", 0, 1, "ice", 90),
         "shelf": _cb_source("Long Shelf", 1, 5, "ice", 90),
         "cold": _cb_refinery("Cold Works", 3, 1, ("coolant",), 60),
         "frost": _cb_refinery("Frost Hall", 4, 5, ("coolant",), 60),
         "tern": _cb_port("Tern Landing", 7, 3),
     },
     "products": [_cb_product("coolant", "tern", 24, 36)],
     "par": (4, 1), "best": {"sites": [["quay", "cold"]], "ships": [[2, 4]]}},
    {"id": "packing_house", "chapter": 2, "title": "Packing House", "blurb": "Flour for Lantern Dock. Both mills can make it, but only one sits on the way.",
     "cargo": 5, "fleet": 8,
     "sites": {
         "low": _cb_source("Low Orchard", 0, 2, "grain", 80),
         "mill": _cb_refinery("Mill Hub", 2, 2, ("flour", "rations",), 40),
         "pack": _cb_refinery("Pack Yard", 5, 4, ("flour", "rations",), 40),
         "lantern": _cb_port("Lantern Dock", 7, 1),
     },
     "products": [_cb_product("flour", "lantern", 10, 20)],
     "par": (5, 1), "best": {"sites": [["low", "mill"]], "ships": [[1, 1]]}},
    {"id": "lens_line", "chapter": 2, "title": "Lens Line", "blurb": "Silica melts into glass at the small Melt House or the big Furnace Ring.",
     "cargo": 4, "fleet": 9,
     "sites": {
         "dunes": _cb_source("Glass Dunes", 0, 0, "silica", 70),
         "reef": _cb_source("Red Reef", 2, 5, "silica", 70),
         "melt": _cb_refinery("Melt House", 3, 2, ("glass",), 30),
         "furn": _cb_refinery("Furnace Ring", 5, 0, ("glass",), 70),
         "vesper": _cb_port("Port Vesper", 7, 4),
     },
     "products": [_cb_product("glass", "vesper", 10, 20)],
     "par": (3, 1), "best": {"sites": [["reef", "melt"]], "ships": [[2, 2]]}},
    {"id": "coolant_rush", "chapter": 2, "title": "Coolant Rush", "blurb": "Plenty of ice, two coolant plants and a port that wants more than the small plant can give.",
     "cargo": 4, "fleet": 10,
     "sites": {
         "quay": _cb_source("Frost Quay", 0, 2, "ice", 100),
         "shelf": _cb_source("Long Shelf", 2, 0, "ice", 100),
         "cold": _cb_refinery("Cold Works", 3, 3, ("coolant",), 30),
         "frost": _cb_refinery("Frost Hall", 5, 1, ("coolant",), 100),
         "tern": _cb_port("Tern Landing", 7, 4),
     },
     "products": [_cb_product("coolant", "tern", 20, 40)],
     "par": (24, 5), "best": {"sites": [["quay", "cold"]], "ships": [[2, 3]]}},
    {"id": "one_smelter_two_orders", "chapter": 3, "title": "One Smelter, Two Orders", "blurb": "Alloy for Vesper and plating for Tern, and the near smelter cannot feed both. The first order listed is served first.",
     "cargo": 4, "fleet": 10,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 0, 2, "ore", 90),
         "kiln": _cb_refinery("Kiln Station", 2, 2, ("alloy",), 24),
         "anvil": _cb_refinery("Anvil Yard", 3, 5, ("alloy",), 60),
         "roll": _cb_refinery("Rolling Mill", 5, 3, ("plating",), 40),
         "vesper": _cb_port("Port Vesper", 8, 2),
         "tern": _cb_port("Tern Landing", 7, 5),
     },
     "products": [_cb_product("alloy", "vesper", 6, 12), _cb_product("plating", "tern", 4, 8)],
     "par": (20, 7), "best": {"sites": [["cinder", "kiln"], ["cinder", "anvil", "roll"]], "ships": [[1, 2], [2, 1, 1]]}},
    {"id": "mill_and_pack", "chapter": 3, "title": "Mill and Pack", "blurb": "Flour and rations from the same two mills. Rations are flour that has been packed again.",
     "cargo": 5, "fleet": 10,
     "sites": {
         "low": _cb_source("Low Orchard", 0, 1, "grain", 100),
         "fen": _cb_source("Fen Farm", 1, 5, "grain", 100),
         "mill": _cb_refinery("Mill Hub", 3, 2, ("flour", "rations",), 40),
         "press": _cb_refinery("Press Dock", 4, 5, ("flour", "rations",), 40),
         "lantern": _cb_port("Lantern Dock", 8, 1),
         "tern": _cb_port("Tern Landing", 7, 4),
     },
     "products": [_cb_product("flour", "lantern", 6, 12), _cb_product("rations", "tern", 6, 12)],
     "par": (17, 5), "best": {"sites": [["low", "mill"], ["fen", "press", "mill"]], "ships": [[1, 1], [1, 1, 1]]}},
    {"id": "two_docks_one_forge", "chapter": 3, "title": "Two Docks, One Forge", "blurb": "Two ports want machinery and the forges are small. Share them well.",
     "cargo": 4, "fleet": 10,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 0, 3, "ore", 120),
         "kiln": _cb_refinery("Kiln Station", 2, 3, ("alloy",), 60),
         "forge": _cb_refinery("Forge Ring", 4, 2, ("machinery",), 30),
         "anvil": _cb_refinery("Anvil Yard", 4, 5, ("machinery",), 30),
         "vesper": _cb_port("Port Vesper", 8, 1),
         "tern": _cb_port("Tern Landing", 8, 5),
     },
     "products": [_cb_product("machinery", "vesper", 4, 8), _cb_product("machinery", "tern", 4, 8)],
     "par": (2, 1), "best": {"sites": [["cinder", "kiln", "forge"], ["cinder", "kiln", "anvil"]], "ships": [[1, 1, 1], [1, 1, 1]]}},
    {"id": "glass_and_lenses", "chapter": 3, "title": "Glass and Lenses", "blurb": "Glass for one port and ground lenses for the other, both from the same two works.",
     "cargo": 5, "fleet": 10,
     "sites": {
         "dunes": _cb_source("Glass Dunes", 0, 0, "silica", 100),
         "reef": _cb_source("Red Reef", 1, 4, "silica", 100),
         "melt": _cb_refinery("Melt House", 3, 1, ("glass", "lenses",), 36),
         "furn": _cb_refinery("Furnace Ring", 4, 4, ("glass", "lenses",), 80),
         "vesper": _cb_port("Port Vesper", 8, 0),
         "lantern": _cb_port("Lantern Dock", 8, 4),
     },
     "products": [_cb_product("glass", "vesper", 6, 12), _cb_product("lenses", "lantern", 6, 12)],
     "par": (22, 7), "best": {"sites": [["reef", "furn"], ["dunes", "melt", "furn"]], "ships": [[1, 2], [2, 1, 1]]}},
    {"id": "cold_chain", "chapter": 3, "title": "Cold Chain", "blurb": "Coolant for one port and power cells for another, with two plants that can do either.",
     "cargo": 3, "fleet": 10,
     "sites": {
         "quay": _cb_source("Frost Quay", 0, 1, "ice", 80),
         "cold": _cb_refinery("Cold Works", 2, 2, ("coolant", "cells",), 36),
         "frost": _cb_refinery("Frost Hall", 3, 5, ("coolant", "cells",), 60),
         "tern": _cb_port("Tern Landing", 7, 1),
         "vesper": _cb_port("Port Vesper", 7, 5),
     },
     "products": [_cb_product("coolant", "tern", 6, 12), _cb_product("cells", "vesper", 4, 8)],
     "par": (3, 1), "best": {"sites": [["quay", "cold"], ["quay", "cold", "frost"]], "ships": [[1, 2], [1, 1, 1]]}},
    {"id": "crowded_forge", "chapter": 3, "title": "Crowded Forge", "blurb": "Machinery and plating, two mines and three busy works: the first crowded map.",
     "cargo": 4, "fleet": 10,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 0, 2, "ore", 120),
         "brack": _cb_source("Brack Pit", 1, 5, "ore", 120),
         "kiln": _cb_refinery("Kiln Station", 3, 3, ("alloy", "plating",), 40),
         "anvil": _cb_refinery("Anvil Yard", 4, 0, ("alloy", "plating", "machinery",), 80),
         "forge": _cb_refinery("Forge Ring", 6, 3, ("machinery", "plating",), 30),
         "vesper": _cb_port("Port Vesper", 9, 1),
         "tern": _cb_port("Tern Landing", 9, 4),
     },
     "products": [_cb_product("machinery", "vesper", 4, 8), _cb_product("plating", "tern", 4, 8)],
     "par": (16, 9), "best": {"sites": [["cinder", "kiln", "forge"], ["cinder", "anvil", "forge"]], "ships": [[3, 1, 1], [2, 1, 1]]}},
    {"id": "small_holds", "chapter": 4, "title": "Small Holds", "blurb": "Holds of only two units and long legs. Balance the legs so none starves the next.",
     "cargo": 2, "fleet": 9,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 0, 1, "ore", 90),
         "brack": _cb_source("Brack Pit", 1, 4, "ore", 90),
         "kiln": _cb_refinery("Kiln Station", 2, 2, ("alloy",), 40),
         "anvil": _cb_refinery("Anvil Yard", 3, 4, ("alloy",), 40),
         "forge": _cb_refinery("Forge Ring", 5, 2, ("machinery",), 24),
         "press": _cb_refinery("Press Dock", 5, 5, ("machinery",), 24),
         "vesper": _cb_port("Port Vesper", 7, 3),
     },
     "products": [_cb_product("machinery", "vesper", 4, 8)],
     "par": (6, 5), "best": {"sites": [["brack", "anvil", "forge"]], "ships": [[2, 2, 1]]}},
    {"id": "choke_point", "chapter": 4, "title": "Choke Point", "blurb": "The nearest mill is tiny. Is it still the right one?",
     "cargo": 3, "fleet": 10,
     "sites": {
         "low": _cb_source("Low Orchard", 0, 2, "grain", 120),
         "mill": _cb_refinery("Mill Hub", 2, 2, ("flour",), 12),
         "press": _cb_refinery("Press Dock", 3, 5, ("flour",), 60),
         "pack": _cb_refinery("Pack Yard", 5, 3, ("rations",), 30),
         "cannery": _cb_refinery("Cannery", 6, 5, ("rations",), 30),
         "lantern": _cb_port("Lantern Dock", 8, 2),
     },
     "products": [_cb_product("rations", "lantern", 6, 12)],
     "par": (2, 1), "best": {"sites": [["low", "mill", "pack"]], "ships": [[1, 1, 1]]}},
    {"id": "the_last_ship", "chapter": 4, "title": "The Last Ship", "blurb": "Six ships for a three-step chain: every ship has to earn its place.",
     "cargo": 2, "fleet": 6,
     "sites": {
         "quay": _cb_source("Frost Quay", 0, 0, "ice", 60),
         "shelf": _cb_source("Long Shelf", 0, 4, "ice", 60),
         "cold": _cb_refinery("Cold Works", 2, 1, ("coolant",), 30),
         "frost": _cb_refinery("Frost Hall", 2, 4, ("coolant",), 30),
         "assay": _cb_refinery("Assay Ring", 4, 2, ("cells",), 24),
         "dock": _cb_refinery("Cell Dock", 4, 5, ("cells",), 24),
         "tern": _cb_port("Tern Landing", 6, 3),
     },
     "products": [_cb_product("cells", "tern", 4, 8)],
     "par": (2, 1), "best": {"sites": [["shelf", "frost", "assay"]], "ships": [[1, 2, 1]]}},
    {"id": "tight_fleet", "chapter": 4, "title": "Tight Fleet", "blurb": "Two orders, eight ships and a forge that both orders may want.",
     "cargo": 3, "fleet": 8,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 0, 3, "ore", 100),
         "kiln": _cb_refinery("Kiln Station", 3, 2, ("alloy",), 36),
         "anvil": _cb_refinery("Anvil Yard", 3, 5, ("alloy",), 36),
         "forge": _cb_refinery("Forge Ring", 6, 2, ("machinery", "plating",), 24),
         "roll": _cb_refinery("Rolling Mill", 6, 5, ("plating",), 24),
         "vesper": _cb_port("Port Vesper", 9, 2),
         "tern": _cb_port("Tern Landing", 9, 5),
     },
     "products": [_cb_product("machinery", "vesper", 3, 6), _cb_product("plating", "tern", 4, 8)],
     "par": (5, 4), "best": {"sites": [["cinder", "kiln", "forge"], ["cinder", "kiln", "forge"]], "ships": [[2, 1, 1], [2, 1, 1]]}},
    {"id": "far_fields", "chapter": 4, "title": "Far Fields", "blurb": "A long haul across the reach, where only whole round trips count.",
     "cargo": 4, "fleet": 9,
     "sites": {
         "low": _cb_source("Low Orchard", 0, 0, "grain", 100),
         "fen": _cb_source("Fen Farm", 0, 5, "grain", 100),
         "mill": _cb_refinery("Mill Hub", 3, 2, ("flour",), 40),
         "press": _cb_refinery("Press Dock", 5, 5, ("flour",), 60),
         "pack": _cb_refinery("Pack Yard", 8, 1, ("rations",), 30),
         "cannery": _cb_refinery("Cannery", 9, 5, ("rations",), 30),
         "lantern": _cb_port("Lantern Dock", 12, 3),
     },
     "products": [_cb_product("rations", "lantern", 6, 12)],
     "par": (2, 1), "best": {"sites": [["low", "mill", "pack"]], "ships": [[2, 1, 1]]}},
    {"id": "grand_chain", "chapter": 4, "title": "Grand Chain", "blurb": "Two three-step chains and twelve ships: the full workshop.",
     "cargo": 3, "fleet": 12,
     "sites": {
         "cinder": _cb_source("Cinder Mine", 0, 1, "ore", 120),
         "brack": _cb_source("Brack Pit", 0, 5, "ore", 120),
         "kiln": _cb_refinery("Kiln Station", 3, 2, ("alloy",), 36),
         "anvil": _cb_refinery("Anvil Yard", 3, 5, ("alloy",), 60),
         "forge": _cb_refinery("Forge Ring", 6, 1, ("machinery", "plating",), 24),
         "roll": _cb_refinery("Rolling Mill", 6, 4, ("machinery", "plating",), 24),
         "vesper": _cb_port("Port Vesper", 9, 2),
         "tern": _cb_port("Tern Landing", 9, 5),
     },
     "products": [_cb_product("machinery", "vesper", 4, 8), _cb_product("plating", "tern", 4, 8)],
     "par": (14, 9), "best": {"sites": [["brack", "anvil", "roll"], ["brack", "anvil", "roll"]], "ships": [[2, 2, 1], [2, 1, 1]]}},
]
CHAIN_BY_ID = {p["id"]: p for p in CHAIN_PUZZLES}
CHAIN_IDS = tuple(p["id"] for p in CHAIN_PUZZLES)
CHAIN_GOLD_ACHIEVEMENT = 5  # gold medals for the At Par achievement
