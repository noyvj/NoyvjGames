"""Whole-chain planning (batch B #1 and #4). Pure functions over the tracker's own numbers.

META BUILD PLANNER: pick a named build (the tracker's KNOWN_COMBOS plus your own combos)
and see its whole chain as one plan: parts still to farm, the resources those parts still
need against your built stock, the refinery crafts and credits for the refined ones, and
one completion bar. Only one community build is named by a source the tracker can point
at (the "177" Amp on the Wiki's Amp page); the rest are your own, so nothing is invented.

COMPLETION BAR: every part of the build is worth an equal share. A built part is worth its
whole share; a part still to build is worth half its share scaled by how much of its
resources you hold (the average, over its needed resources, of have divided by need,
capped at 1), the other half being the actual Build. So holding every resource reads as
half way through that part, and clicking Build finishes it.

DROP-SOURCE OPTIMIZER: builds on route_suggestions(). It picks up to three places greedily:
the place that covers the most still-short resources first, then the place that adds the
most resources not yet covered, and so on. "Coverage" is the share of your still-short
resources that drop at those places (resources refined from another material name no place,
so they count against the percentage). It says where the resources drop, not how many
runs are needed.
"""

from wf_tips import tip

META_HALF = 0.5
SESSION_STOPS = 3


def meta_plan(combo, components, inventory, recipes, refine):
    """The chain for one combo. `refine(resource, short, raw_have)` is the tracker's refinery_plan."""
    by_name = {c["name"]: c for c in components}
    built, to_farm = [], []
    for part in combo["parts"]:
        info = by_name.get(part)
        (built if info is not None and info["owned"] >= 1 else to_farm).append(part)
    need = {}
    for part in to_farm:
        for resource, qty in recipes.get(part, {}).get("ingredients", {}).items():
            if resource != "Credits":
                need[resource] = need.get(resource, 0) + qty
    rows = []
    for resource in sorted(need):
        inv = inventory.get(resource, {})
        have = int(inv.get("built", 0))
        raw_have = int(inv.get("raw", 0))
        short = max(0, need[resource] - have)
        rows.append({"name": resource, "need": need[resource], "have": have, "short": short,
                     "refinery": refine(resource, short, raw_have)})
    credits = sum(r["refinery"]["credits"] for r in rows if r["refinery"])
    materials = {}
    for row in rows:
        for name, qty in (row["refinery"] or {}).get("ingredients", {}).items():
            materials[name] = materials.get(name, 0) + qty
    coverage = sum(min(1.0, r["have"] / r["need"]) for r in rows) / len(rows) if rows else 1.0
    parts = len(combo["parts"])
    percent = round((len(built) + len(to_farm) * META_HALF * coverage) / parts * 100) if parts else 0
    return {"combo": combo, "built": built, "to_farm": to_farm, "rows": rows, "credits": credits,
            "materials": materials, "percent": percent, "complete": not to_farm}


def meta_text(plan):
    combo = plan["combo"]
    if plan["complete"]:
        return f"{combo['name']} ({combo['category']}, source: {combo['source']}): every part is built."
    lines = [f"{combo['name']} ({combo['category']}, source: {combo['source']}): {plan['percent']}% of the chain done."]
    lines.append(f"Built: {', '.join(plan['built']) or 'none yet'}. Still to farm: {', '.join(plan['to_farm'])}.")
    short = [r for r in plan["rows"] if r["short"]]
    if short:
        lines.append("Resources still needed: " + ", ".join(f"{r['name']} x{r['short']}" for r in short) + ".")
    else:
        lines.append("Every resource for the remaining parts is on hand.")
    refined = [r for r in plan["rows"] if r["refinery"]]
    if refined:
        lines.append("Refinery: " + "; ".join(
            f"{r['name']} {r['refinery']['crafts']} craft(s)" for r in refined) + f". Credits for refining: {plan['credits']:,}.")
    return "\n".join(lines)


def farm_session(resources, places_of, top=SESSION_STOPS):
    """A greedy farming session over the resources you are still short on. `resources` are resource rows
    (name, built_short, location); `places_of(location)` is the tracker's location_places."""
    short = [r for r in resources if r["built_short"] > 0]
    units = {r["name"]: r["built_short"] for r in short}
    where = {r["name"]: set(places_of(r["location"])) for r in short}
    remaining = {name for name, places in where.items() if places}
    steps = []
    while remaining and len(steps) < top:
        options = {}
        for name in remaining:
            for place in where[name]:
                options.setdefault(place, []).append(name)
        place = min(options, key=lambda p: (-len(options[p]), -sum(units[n] for n in options[p]), p))
        covered = sorted(options[place])
        steps.append({"place": place, "resources": covered, "units": sum(units[n] for n in covered),
                      "tips": [t for t in (tip(n) for n in covered) if t and t["text"]][:2]})
        remaining -= set(covered)
    covered_names = {n for s in steps for n in s["resources"]}
    total = len(short)
    covered_units = sum(units[n] for n in covered_names)
    total_units = sum(units.values())
    return {
        "steps": steps, "total": total, "covered": len(covered_names),
        "percent": round(len(covered_names) / total * 100) if total else 0,
        "units_percent": round(covered_units / total_units * 100) if total_units else 0,
        "unplaced": sorted(n for n in units if not where[n]),
    }


def session_lines(session):
    if not session["total"]:
        return ["Nothing left to farm: every requirement is covered."]
    if not session["steps"]:
        return ["None of your short resources drop at a named place (they are refined from other materials): farm the raw materials instead."]
    lines = []
    for n, step in enumerate(session["steps"], 1):
        names = ", ".join(step["resources"][:8]) + (" and more" if len(step["resources"]) > 8 else "")
        lines.append(f"{n}. {step['place']}: {len(step['resources'])} short resource(s) ({names}), {step['units']:,} units still short.")
        for t in step["tips"]:
            lines.append(f"   Wiki tip for {t['resource']} ({t['section']}, read {t['date']}): {t['text']}")
    lines.append(
        f"Doing these {len(session['steps'])} place(s) in this order covers where {session['percent']}% of your "
        f"{session['total']} short resource(s) drop ({session['units_percent']}% of the units still short)."
    )
    if session["unplaced"]:
        lines.append("Not covered (no named place, farm their raw material): " + ", ".join(session["unplaced"][:10])
                     + (" and more." if len(session["unplaced"]) > 10 else "."))
    return lines
