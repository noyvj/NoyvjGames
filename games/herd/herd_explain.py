"""The 'explain this number' inspector (F-6): income, methane, coupling and pressure breakdown trees.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import html

from js import document

import herd_runstate as runstate
from herd_rules import (
    BASE_COUPLING_RATIO, DECOUPLING_MEASURES, GENETICS_RATIO_REDUCTION, HERD_INCOME_PER_UNIT, MAX_PRESSURE,
    MIN_COUPLING_RATIO, PLANT_BASED_EMISSIONS_MULTIPLIER, SUPPLY_CHAIN_MAX_UNITS, WELFARE_START,
)
from herd_model import pressure_scale, season_for_round


# ===========================================================================
# Round-5 batch (planning/TODO.md "GF + F. Herd"). F-6: an "explain this number" inspector.
# ===========================================================================
EXPLAIN_KINDS = {
    "income": "Income per round",
    "methane": "Methane per round",
    "coupling": "Coupling ratio",
    "pressure": "Pressure",
}


def _node(label, value, note="", children=None):
    return {"label": label, "value": value, "note": note, "children": children or []}


def _tree_html(nodes):
    if not nodes:
        return ""
    items = []
    for node in nodes:
        note = f' <span class="explain-note">{html.escape(node["note"])}</span>' if node["note"] else ""
        items.append(
            f'<li><span class="explain-label">{html.escape(node["label"])}</span> '
            f'<span class="explain-value">{html.escape(node["value"])}</span>{note}{_tree_html(node["children"])}</li>'
        )
    return f'<ul class="explain-tree">{"".join(items)}</ul>'


def _signed(value, digits=1):
    return f"{value:+.{digits}f}"


def explain_income_nodes():
    b = runstate.farm.income_breakdown()
    herd_children = []
    if runstate.farm.herd_size:
        herd_children.append(_node("Base income", f"{b['herd_base']:.1f}", f"{runstate.farm.herd_size} units x {HERD_INCOME_PER_UNIT} each"))
        if b["plant_fraction"] > 0:
            herd_children.append(_node(
                "Plant-based blend", f"x{b['plant_blend']:.3f}",
                f"{b['plant_fraction'] * 100:.0f}% of output is plant-based, which earns {runstate.farm.plant_income_multiplier():.2f} per unit",
            ))
        if runstate.farm.certified:
            herd_children.append(_node("Sustainable certification", f"x{b['certification']:.2f}", "permanent price premium"))
        if abs(b["welfare"] - 1) > 1e-9:
            herd_children.append(_node("Welfare", f"x{b['welfare']:.3f}", f"welfare score {runstate.farm.welfare():.0f} (neutral is {WELFARE_START:.0f})"))
    nodes = [_node("Herd income", f"{b['herd_income']:.1f}", "", herd_children)]
    if runstate.farm.poultry_size:
        nodes.append(_node("Poultry flock", _signed(b["poultry"]), f"{runstate.farm.poultry_size} birds, after housing upkeep"))
    if runstate.farm.satellite_size:
        nodes.append(_node("Satellite farm", _signed(b["satellite"]), f"{runstate.farm.satellite_size} units"))
    if runstate.farm.supply_chain_investment:
        nodes.append(_node("Supply chain", f"x{b['supply']:.2f}", f"{runstate.farm.supply_chain_investment} of {SUPPLY_CHAIN_MAX_UNITS} units"))
    if runstate.farm.variation_enabled:
        nodes.append(_node("Season", f"x{b['season']:.2f}", season_for_round(runstate.farm.round_number)[0]))
    if runstate.farm.label_rounds_left > 0:
        nodes.append(_node("Organic label trial", f"x{b['label']:.2f}", f"{runstate.farm.label_rounds_left} rounds left"))
    if abs(b["audit"] - 1) > 1e-9:
        reason = []
        if "goodwill" in runstate.farm.audit_perks:
            reason.append("Regulator's Goodwill")
        if runstate.farm.trust_rounds_left > 0:
            reason.append(f"market trust shaken for {runstate.farm.trust_rounds_left} more rounds")
        nodes.append(_node("Regulator standing", f"x{b['audit']:.3f}", ", ".join(reason)))
    nodes.append(_node("Income before pressure", f"{b['raw']:.1f}"))
    nodes.append(_node("Market/regulatory pressure", f"-{b['pressure'] * 100:.0f}%", f"takes {b['raw'] * b['pressure']:.1f} of it; see the Pressure breakdown"))
    if b["biogas"]:
        nodes.append(_node("Biogas sales", _signed(b["biogas"]), "from capture systems beyond the first two"))
    return [_node("Funds earned when you advance this round", _signed(b["total"]), "", nodes)]


def explain_methane_nodes():
    herd = _node(
        "Herd", f"{runstate.farm.herd_size * runstate.farm.coupling_ratio():.2f}",
        f"{runstate.farm.herd_size} units x {runstate.farm.coupling_ratio():.2f} each (the coupling ratio)",
    )
    nodes = [herd]
    if runstate.farm.poultry_size:
        nodes.append(_node("Poultry flock", f"{runstate.farm.poultry_size * runstate.farm.poultry_coupling_ratio():.2f}", f"{runstate.farm.poultry_size} birds x {runstate.farm.poultry_coupling_ratio():.2f} each (methane-equivalent)"))
    if runstate.farm.satellite_size:
        offset = runstate.farm.satellite_offset_fraction()
        nodes.append(_node(
            "Satellite farm", f"{runstate.farm.satellite_size * runstate.farm.satellite_coupling_ratio():.2f}",
            f"{runstate.farm.satellite_size} units x {runstate.farm.satellite_coupling_ratio():.2f} each ({runstate.farm.satellite_own_ratio():.2f} after retrofits, {offset * 100:.0f}% cancelled by the main farm)",
        ))
    nodes.append(_node("Added to your total when you advance", f"{runstate.farm.methane_this_round():.2f}", f"total so far {runstate.farm.methane:.1f}"))
    return [_node("Methane this round", f"{runstate.farm.methane_this_round():.2f}", "", nodes)]


def explain_coupling_nodes():
    children = [_node("Starting level", f"{BASE_COUPLING_RATIO:.2f}", "every herd unit begins fully coupled")]
    for measure, spec in DECOUPLING_MEASURES.items():
        count = runstate.farm.decoupling_investment[measure]
        if count:
            children.append(_node(spec["label"], f"-{count * spec['ratio_reduction']:.2f}", f"{count} units x {spec['ratio_reduction']:.2f}"))
    if runstate.farm.genetics_active:
        children.append(_node("Breeding program", f"-{runstate.farm.genetics_active * GENETICS_RATIO_REDUCTION:.2f}", f"{runstate.farm.genetics_active} matured units x {GENETICS_RATIO_REDUCTION:.2f}"))
    efficiency = runstate.farm._efficiency_coupling_ratio()
    children.append(_node("After efficiency measures", f"{efficiency:.2f}", f"never below {MIN_COUPLING_RATIO:.2f}"))
    fraction = runstate.farm.plant_based_fraction()
    if fraction > 0:
        children.append(_node("Plant-based pivot", f"x{(1 - fraction) + fraction * PLANT_BASED_EMISSIONS_MULTIPLIER:.3f}", f"{fraction * 100:.0f}% of output is plant-based and gives off almost nothing"))
    return [_node("Coupling ratio", f"{runstate.farm.coupling_ratio():.2f}", "methane per herd unit per round", children)]


def explain_pressure_nodes():
    children = [
        _node("All methane so far", f"{runstate.farm.methane:.1f}", "never resets"),
        _node("Divided by", f"{pressure_scale():.0f}", "the scale of the pressure curve"),
        _node("Pressure", f"{runstate.farm.methane / pressure_scale() * 100:.0f}%", f"stops at {MAX_PRESSURE * 100:.0f}%"),
    ]
    lost = runstate.farm.income_breakdown()
    children.append(_node("Income lost this round", f"{lost['raw'] * lost['pressure']:.1f}", f"of {lost['raw']:.1f} before pressure"))
    return [_node("Market/regulatory pressure", f"{runstate.farm.pressure_fraction() * 100:.0f}% of income", "", children)]


EXPLAIN_BUILDERS = {
    "income": explain_income_nodes,
    "methane": explain_methane_nodes,
    "coupling": explain_coupling_nodes,
    "pressure": explain_pressure_nodes,
}


def explain_html(kind):
    builder = EXPLAIN_BUILDERS.get(kind)
    return _tree_html(builder()) if builder else ""


def render_explain():
    output = document.getElementById("explain-output")
    output.innerHTML = explain_html(runstate.explain_kind) if runstate.explain_kind else ""
    output.hidden = runstate.explain_kind is None
    for kind in EXPLAIN_KINDS:
        button = document.getElementById(f"explain-{kind}-button")
        button.setAttribute("aria-pressed", "true" if kind == runstate.explain_kind else "false")
        if kind == runstate.explain_kind:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")


def _make_explain_handler(kind):
    def handler(event=None):
        runstate.explain_kind = None if runstate.explain_kind == kind else kind
        render_explain()
    return handler
