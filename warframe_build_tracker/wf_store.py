"""Save/load plumbing for the batch B state keys, kept out of game.py.

Keys (each written by export() only when not at its default, every one fully validated
by load(): wrong types, bad bounds and unknown names are dropped, missing keys fall back
to defaults, so saves from before batch B load unchanged):

  relics     void relic planner        (wf_relics)
  crafts     crafting tracker          (wf_crafting)
  pets       companion/pet log         (wf_crafting)
  forma      forma planner             (wf_forma)
  imports    last two import snapshots (wf_insight)
  readiness  typed mod ranks           (wf_insight)
"""

import wf_crafting
import wf_forma
import wf_insight
import wf_relics

KEYS = ("relics", "crafts", "pets", "forma", "imports", "readiness")


def default_state():
    return {
        "relics": wf_relics.default_relics(),
        "crafts": [],
        "pets": [],
        "forma": wf_forma.default_forma(),
        "imports": wf_insight.default_imports(),
        "readiness": wf_insight.default_readiness(),
    }


def export(state):
    out = {}
    relics = wf_relics.export(state["relics"])
    if relics:
        out["relics"] = relics
    if state["crafts"]:
        out["crafts"] = wf_crafting.export_crafts(state["crafts"])
    if state["pets"]:
        out["pets"] = wf_crafting.export_pets(state["pets"])
    forma = wf_forma.export(state["forma"])
    if forma:
        out["forma"] = forma
    imports = wf_insight.export_imports(state["imports"])
    if imports:
        out["imports"] = imports
    if state["readiness"]["mods"]:
        out["readiness"] = wf_insight.export_readiness(state["readiness"])
    return out


def plan_targets(state, build_names):
    """The names a Forma plan may target: the tracker's builds plus crafting-tracker items."""
    return list(build_names) + [c["n"] for c in state["crafts"]]


def load(state, data, build_names, tracked):
    """Validates and installs every batch B key. Must run after combos are loaded (a Forma plan may name one)."""
    state["relics"] = wf_relics.load(data.get("relics"))
    state["crafts"] = wf_crafting.load_crafts(data.get("crafts"))
    state["pets"] = wf_crafting.load_pets(data.get("pets"))
    state["forma"] = wf_forma.load(data.get("forma"), set(plan_targets(state, build_names)))
    state["imports"] = wf_insight.load_imports(data.get("imports"), set(tracked))
    state["readiness"] = wf_insight.load_readiness(data.get("readiness"))


def prune(state, build_names):
    """Drops Forma plans that point at a build that no longer exists (a removed custom combo)."""
    wf_forma.prune(state["forma"], set(plan_targets(state, build_names)))
