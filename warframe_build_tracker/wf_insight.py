"""Import diff (batch B #8), waste audit (#9) and endgame readiness score (#10).

All three are read-only over the tracker's numbers, except that the diff keeps the previous
import's resource counts and the readiness score keeps the mod ranks you type. None changes a
need calculation.

IMPORT DIFF: each import stores the built count of every matched resource ("last") and
shifts the one before it into "prev". The diff compares the two: new items (matched now
with a count above zero, absent or zero at the previous import), counts that ticked forward,
counts that went down (spent), and crafts the import newly marked as owned.

WASTE AUDIT: three hints, each a heuristic and none a verdict.
  * Overstocked: you hold at least OVERSTOCK_FACTOR times what the unfinished parts still
    need, with at least OVERSTOCK_MIN_SPARE units spare (built + raw counted together);
    plus tracked resources you hold in bulk that no unfinished part needs any more.
  * Refinable: a refined resource you are short on while you hold its raw precursor.
    Only the primary raw material is checked; the recipe's other ingredients are not.
  * Blueprint idle: a refined resource whose blueprint reads as owned but that no
    unfinished part needs any more ("never needed" means from here on; the note says
    when no part on your list uses it at all).

READINESS SCORE: a playful personal benchmark out of 100, not a game figure and not a
measure of how good a build is. 40 points for owned parts (owned over target), 20 for
Forma you say you have used (full marks at FORMA_FULL, an arbitrary 20) and 40 for the mod
ranks you type (sum of ranks over sum of max ranks). The breakdown is always shown.
"""

from wf_util import LOG_TIME_RE, clean, dict_entries, find_ci, is_int, str_in

OVERSTOCK_FACTOR = 2
OVERSTOCK_MIN_SPARE = 10
COUNT_MAX = 10 ** 9

FORMA_FULL = 20
PARTS_POINTS, FORMA_POINTS, MOD_POINTS = 40, 20, 40
MOD_MAX = 40
MOD_NAME_MAX = 30
MOD_RANK_MAX = 40
TITLES = (
    (0, "Fresh out of cryosleep"),
    (20, "Kuva-curious Tenno"),
    (40, "Steady grinder"),
    (60, "Steel Path regular"),
    (80, "Endgame-ready"),
    (95, "Beyond the Duviri sky"),
)


# --- import diff ----------------------------------------------------------

def default_imports():
    return {"last": None, "prev": None}


def record_import(imports, stamp, counts, newly_owned=()):
    """Shifts the last import into "prev" and stores this one. `counts` maps resource -> built count."""
    imports["prev"] = imports["last"]
    imports["last"] = {"t": stamp, "c": {k: int(v) for k, v in counts.items()}, "o": list(newly_owned)}


def diff_data(imports):
    """The change between the last two imports, or None until there are two."""
    last, prev = imports["last"], imports["prev"]
    if not last or not prev:
        return None
    new, up, down = [], [], []
    for name, count in sorted(last["c"].items()):
        before = prev["c"].get(name, 0)
        if count > 0 and before == 0:
            new.append({"name": name, "count": count})
        elif count > before:
            up.append({"name": name, "before": before, "after": count, "delta": count - before})
        elif count < before:
            down.append({"name": name, "before": before, "after": count, "delta": count - before})
    up.sort(key=lambda r: (-r["delta"], r["name"]))
    down.sort(key=lambda r: (r["delta"], r["name"]))
    unchanged = len(last["c"]) - len(new) - len(up) - len(down)
    return {"from": prev["t"], "to": last["t"], "new": new, "up": up, "down": down, "unchanged": max(0, unchanged),
            "owned": list(last.get("o", []))}


def diff_text(imports):
    if not imports["last"]:
        return "No import yet. Upload a lastData.dat or inventory.json above; the changes show here after the next one."
    data = diff_data(imports)
    if data is None:
        return (f"One import so far ({imports['last']['t']} UTC, {len(imports['last']['c'])} resources matched). "
                "Import again later to see what changed.")
    lines = [f"Since your import at {data['from']} UTC (this one: {data['to']} UTC):"]
    if data["new"]:
        lines.append("New: " + ", ".join(f"{r['name']} {r['count']:,}" for r in data["new"]) + ".")
    if data["up"]:
        lines.append("Ticked forward: " + ", ".join(
            f"{r['name']} +{r['delta']:,} ({r['before']:,} to {r['after']:,})" for r in data["up"][:15])
            + (" and more." if len(data["up"]) > 15 else "."))
    if data["down"]:
        lines.append("Went down (spent): " + ", ".join(
            f"{r['name']} {r['delta']:,} ({r['before']:,} to {r['after']:,})" for r in data["down"][:15])
            + (" and more." if len(data["down"]) > 15 else "."))
    if data["owned"]:
        lines.append("Newly marked owned by the import: " + ", ".join(data["owned"]) + ".")
    if len(lines) == 1:
        lines.append("No counts changed.")
    lines.append(f"{data['unchanged']} matched resource(s) unchanged.")
    return "\n".join(lines)


def export_imports(imports):
    out = {}
    for key in ("last", "prev"):
        if imports[key]:
            out[key] = {"t": imports[key]["t"], "c": dict(imports[key]["c"]), "o": list(imports[key]["o"])}
    return out


def _load_snapshot(value, tracked):
    if not isinstance(value, dict) or not (isinstance(value.get("t"), str) and LOG_TIME_RE.match(value["t"])):
        return None
    counts = value.get("c")
    if not isinstance(counts, dict):
        return None
    owned = value.get("o")
    return {
        "t": value["t"],
        "c": {k: v for k, v in counts.items() if str_in(k, tracked) and is_int(v) and 0 <= v <= COUNT_MAX},
        "o": [n.strip()[:40] for n in owned[:40] if isinstance(n, str) and n.strip()] if isinstance(owned, list) else [],
    }


def load_imports(data, tracked):
    imports = default_imports()
    if isinstance(data, dict):
        imports["last"] = _load_snapshot(data.get("last"), tracked)
        imports["prev"] = _load_snapshot(data.get("prev"), tracked) if imports["last"] else None
    return imports


# --- waste audit ---------------------------------------------------------

def waste_audit(rows, inventory, tracked, refinery_recipes, blueprint_owned, usage):
    """The three audit lists. `rows` are the resource rows (all resources some unfinished part still needs)."""
    row_names = {r["name"] for r in rows}
    overstock = []
    for r in rows:
        have = r["built_have"] + r["raw_have"]
        if r["needed"] > 0 and have >= OVERSTOCK_FACTOR * r["needed"] and have - r["needed"] >= OVERSTOCK_MIN_SPARE:
            overstock.append({"name": r["name"], "have": have, "need": r["needed"], "spare": have - r["needed"]})
    idle = []
    for name in tracked:
        if name in row_names:
            continue
        inv = inventory.get(name, {})
        have = int(inv.get("built", 0)) + int(inv.get("raw", 0))
        if have >= OVERSTOCK_MIN_SPARE:
            idle.append({"name": name, "have": have})
    refinable = []
    for r in rows:
        recipe = refinery_recipes.get(r["name"])
        if not recipe or r["built_short"] <= 0 or r["raw_have"] <= 0:
            continue
        per_craft = recipe["ingredients"].get(recipe["primary"], 0)
        crafts = r["raw_have"] // per_craft if per_craft else 0
        if crafts:
            refinable.append({"name": r["name"], "raw": r["raw_have"], "primary": recipe["primary"], "crafts": crafts,
                              "makes": crafts * recipe["output"], "short": r["built_short"]})
    blueprints = []
    for name in refinery_recipes:
        if name not in row_names and blueprint_owned(name):
            blueprints.append({"name": name, "used_anywhere": bool(usage(name))})
    overstock.sort(key=lambda o: (-o["spare"], o["name"]))
    idle.sort(key=lambda o: (-o["have"], o["name"]))
    return {"overstock": overstock, "idle": idle, "refinable": refinable, "blueprints": blueprints}


def audit_lines(audit):
    lines = []
    if audit["overstock"]:
        lines.append("Overstocked against what unfinished parts still need: " + "; ".join(
            f"{o['name']} (have {o['have']:,}, need {o['need']:,}, spare {o['spare']:,})" for o in audit["overstock"][:12])
            + (" and more." if len(audit["overstock"]) > 12 else "."))
    if audit["idle"]:
        lines.append("Held but no unfinished part needs it any more: " + ", ".join(
            f"{o['name']} ({o['have']:,})" for o in audit["idle"][:12]) + (" and more." if len(audit["idle"]) > 12 else "."))
    for r in audit["refinable"]:
        lines.append(f"Refinable now: {r['raw']:,} raw {r['primary']} could go into {r['crafts']} craft(s) of {r['name']} "
                     f"(up to {r['makes']:,}); you are short {r['short']:,}. Only the raw material was checked: the "
                     "recipe's other ingredients may still be missing.")
    for b in audit["blueprints"]:
        note = "" if b["used_anywhere"] else " No part on your list uses it at all."
        lines.append(f"Blueprint idle: the {b['name']} blueprint reads as owned but no unfinished part needs it any more.{note}")
    return lines or ["Nothing stands out: no overstock, no refinable raw stock, no idle blueprints."]


# --- readiness -----------------------------------------------------------

def default_readiness():
    return {"mods": []}


def add_mod(mods, name, rank, max_rank):
    name = clean(name, MOD_NAME_MAX)
    if not name:
        return False, "Give the mod a name."
    if not is_int(max_rank) or not 1 <= max_rank <= MOD_RANK_MAX:
        return False, f"Max rank must be 1 to {MOD_RANK_MAX}."
    if not is_int(rank) or not 0 <= rank <= max_rank:
        return False, "Rank must be from 0 up to the max rank."
    existing = find_ci([m["n"] for m in mods], name)
    if existing:
        for mod in mods:
            if mod["n"] == existing:
                mod["r"], mod["m"] = rank, max_rank
        return True, f"Updated {existing}."
    if len(mods) >= MOD_MAX:
        return False, f"You can list up to {MOD_MAX} mods."
    mods.append({"n": name, "r": rank, "m": max_rank})
    return True, f"Added {name} at rank {rank}/{max_rank}."


def remove_mod(mods, name):
    existing = find_ci([m["n"] for m in mods], name)
    if existing is None:
        return False
    mods[:] = [m for m in mods if m["n"] != existing]
    return True


def readiness(components, forma_used, mods):
    target = sum(c["target"] for c in components)
    owned = sum(min(c["owned"], c["target"]) for c in components)
    parts_frac = owned / target if target else 0.0
    forma_frac = min(1.0, forma_used / FORMA_FULL) if FORMA_FULL else 0.0
    max_ranks = sum(m["m"] for m in mods)
    mod_frac = sum(m["r"] for m in mods) / max_ranks if max_ranks else 0.0
    parts_pts = parts_frac * PARTS_POINTS
    forma_pts = forma_frac * FORMA_POINTS
    mod_pts = mod_frac * MOD_POINTS
    score = round(parts_pts + forma_pts + mod_pts)
    title = [t for floor, t in TITLES if score >= floor][-1]
    return {"score": score, "title": title,
            "parts": {"owned": owned, "target": target, "points": round(parts_pts, 1), "max": PARTS_POINTS},
            "forma": {"used": forma_used, "full": FORMA_FULL, "points": round(forma_pts, 1), "max": FORMA_POINTS},
            "mods": {"ranks": sum(m["r"] for m in mods), "max_ranks": max_ranks, "count": len(mods),
                     "points": round(mod_pts, 1), "max": MOD_POINTS}}


def readiness_lines(result):
    p, f, m = result["parts"], result["forma"], result["mods"]
    lines = [
        f"Parts: {p['owned']} of {p['target']} owned = {p['points']} of {p['max']} points.",
        f"Forma: {f['used']} used (full marks at {f['full']}, an arbitrary benchmark) = {f['points']} of {f['max']} points.",
    ]
    if m["max_ranks"]:
        lines.append(f"Mods: {m['ranks']} of {m['max_ranks']} ranks across {m['count']} typed mod(s) = {m['points']} of {m['max']} points.")
    else:
        lines.append(f"Mods: none typed yet = 0 of {m['max']} points. Add mods and their ranks below.")
    lines.append("A playful personal benchmark, not a game figure.")
    return lines


def export_readiness(rd):
    return {"mods": [dict(m) for m in rd["mods"]]}


def load_readiness(data):
    rd = default_readiness()
    if not isinstance(data, dict):
        return rd
    for entry in dict_entries(data.get("mods"))[:MOD_MAX]:
        name, rank, max_rank = entry.get("n"), entry.get("r"), entry.get("m")
        if (isinstance(name, str) and name.strip() and is_int(max_rank) and 1 <= max_rank <= MOD_RANK_MAX
                and is_int(rank) and 0 <= rank <= max_rank and not find_ci([m["n"] for m in rd["mods"]], name)):
            rd["mods"].append({"n": name.strip()[:MOD_NAME_MAX], "r": rank, "m": max_rank})
    return rd
