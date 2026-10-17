"""Chain Builder logic: paths, distances, evaluation, the solver, medals, the draft board, hints and the map drawing."""

import itertools

from fractions import Fraction

import trade_runstate as runstate
from trade_chain_rules import (
    CHAIN_BY_ID, CHAIN_CYCLE, CHAIN_GOODS, CHAIN_MAX_STAGES, CHAIN_PUZZLES, CHAIN_RAW_GOODS, CHAIN_RECIPES,
    CHAIN_SILVER_PERCENT,
)
from trade_crises import CRISIS_MEDAL_MARK
from trade_records import _saved_int, records
from trade_uikit import show_notice_toast


def chain_good_name(good):
    return CHAIN_GOODS.get(good, str(good))


def chain_path(good):
    """The goods along a product's recipe path, raw first and the product last ([] for an unknown good)."""
    path = [good]
    while path[-1] not in CHAIN_RAW_GOODS:
        recipe = CHAIN_RECIPES.get(path[-1])
        if recipe is None or len(path) > CHAIN_MAX_STAGES:
            return []
        path.append(recipe["from"])
    return path[::-1]


def chain_distance(puzzle, a, b):
    """Grid steps between two sites (never less than 1: a trip always takes some time)."""
    (ax, ay), (bx, by) = puzzle["sites"][a]["pos"], puzzle["sites"][b]["pos"]
    return max(1, abs(ax - bx) + abs(ay - by))


def chain_trips(puzzle, a, b):
    """Whole round trips one ship fits in a cycle on the leg a -> b (0 when the leg is too long)."""
    return CHAIN_CYCLE // (2 * chain_distance(puzzle, a, b))


def chain_fits(site, path, stage):
    """True when `site` may fill step `stage` of a chain whose goods run `path`."""
    if stage == 0:
        return site["kind"] == "source" and site["good"] == path[0]
    return site["kind"] == "refinery" and path[stage] in site["recipes"]


def chain_options(puzzle, index):
    """Every complete choice of sites (one list per product) whose legs are all short enough to run."""
    product = puzzle["products"][index]
    path = chain_path(product["good"])
    layers = [[sid for sid, site in puzzle["sites"].items() if chain_fits(site, path, k)] for k in range(len(path))]
    found = []
    for combo in itertools.product(*layers):
        if len(set(combo)) != len(combo):
            continue
        chain = list(combo) + [product["port"]]
        if all(chain_trips(puzzle, chain[k], chain[k + 1]) >= 1 for k in range(len(chain) - 1)):
            found.append(list(combo))
    return found


def _chain_flow(puzzle, plan, detail=False):
    """Runs one cycle of a (structurally valid) plan: returns (delivered per product, total ships, legs)."""
    sites = puzzle["sites"]
    left = {sid: site["cap"] for sid, site in sites.items() if site["kind"] != "port"}
    delivered, legs, total = [], [], 0
    cargo = puzzle["cargo"]
    for product, (chosen, ships) in zip(puzzle["products"], plan):
        path = chain_path(product["good"])
        chain = list(chosen) + [product["port"]]
        total += sum(ships)
        moved = produced = 0
        product_legs = []
        for k in range(len(path)):
            trips = chain_trips(puzzle, chain[k], chain[k + 1])
            capacity = ships[k] * cargo * trips
            if k == 0:
                moved = min(capacity, left[chain[0]])
                left[chain[0]] -= moved
            else:
                moved = min(capacity, produced)
            leg = None
            if detail:
                leg = {"from": chain[k], "to": chain[k + 1], "distance": chain_distance(puzzle, chain[k], chain[k + 1]),
                       "trips": trips, "per_ship": cargo * trips, "ships": ships[k], "capacity": capacity, "moved": moved,
                       "made": None}
                product_legs.append(leg)
            if k + 1 < len(path):  # arrives at a refinery: it makes whole runs from what it can take
                recipe = CHAIN_RECIPES[path[k + 1]]
                runs = min(moved, left[chain[k + 1]]) // recipe["take"]
                left[chain[k + 1]] -= runs * recipe["take"]
                produced = runs * recipe["make"]
                if leg is not None:
                    leg["made"] = produced
        delivered.append(moved)
        legs.append(product_legs)
    return delivered, total, legs


def chain_evaluate(puzzle, plan):
    """Checks a plan (a list of [sites, ships] per product) and runs it. Returns a dict:
    ok (the plan is well formed and runs), reason (why not), delivered / credited per product, ships, met (every
    order reached), score (a Fraction, units credited per ship) and legs (per product, details for the screen)."""
    result = {"ok": False, "reason": "", "delivered": [], "credited": [], "ships": 0, "met": False,
              "score": None, "legs": []}
    products, sites = puzzle["products"], puzzle["sites"]
    if not isinstance(plan, (list, tuple)) or len(plan) != len(products):
        result["reason"] = "A chain is needed for every order."
        return result
    clean = []
    for product, entry in zip(products, plan):
        path = chain_path(product["good"])
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            result["reason"] = "A chain is not well formed."
            return result
        chosen, ships = entry
        if not isinstance(chosen, (list, tuple)) or not isinstance(ships, (list, tuple)) \
                or len(chosen) != len(path) or len(ships) != len(path):
            result["reason"] = "A chain has the wrong number of steps."
            return result
        for k, site_id in enumerate(chosen):
            if not isinstance(site_id, str) or site_id not in sites or not chain_fits(sites[site_id], path, k):
                result["reason"] = "Choose a site that can do each step."
                return result
        if len(set(chosen)) != len(chosen):
            result["reason"] = "A chain cannot use the same site twice."
            return result
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in ships):
            result["reason"] = "Every leg needs at least one ship."
            return result
        full = list(chosen) + [product["port"]]
        if any(chain_trips(puzzle, full[k], full[k + 1]) < 1 for k in range(len(path))):
            result["reason"] = "A leg is too long for a ship to make a round trip in one cycle."
            return result
        clean.append((list(chosen), list(ships)))
    delivered, total, legs = _chain_flow(puzzle, clean, detail=True)
    if total > puzzle["fleet"]:
        result["reason"] = f"That is {total} ships and the fleet has {puzzle['fleet']}."
        result["ships"] = total
        return result
    credited = [min(d, p["want"]) for d, p in zip(delivered, products)]
    result.update(
        ok=True, delivered=delivered, credited=credited, ships=total, legs=legs,
        met=all(d >= p["need"] for d, p in zip(delivered, products)),
        score=Fraction(sum(credited), total),
    )
    return result


def _chain_compositions(parts, total):
    """Every way to give `parts` legs a positive whole number of ships, `total` ships at most (in order)."""
    if parts == 0:
        yield ()
        return
    for first in range(1, total - (parts - 1) + 1):
        for rest in _chain_compositions(parts - 1, total - first):
            yield (first,) + rest


def chain_solve(puzzle):
    """Exhaustive search: every site choice for every product and every split of the fleet over the legs.
    Returns None when nothing meets the orders, otherwise a dict: score (Fraction, the par), ships, plan
    (a list of [sites, ships] per product; ties go to the fewest ships, then the first found), valid (how many
    chains meet the orders) and evaluated (how many were tried)."""
    products = puzzle["products"]
    option_lists = [chain_options(puzzle, i) for i in range(len(products))]
    best_key, best_plan, valid, evaluated = None, None, 0, 0
    for combo in itertools.product(*option_lists):
        sizes = [len(c) for c in combo]
        for allocation in _chain_compositions(sum(sizes), puzzle["fleet"]):
            plan, at = [], 0
            for chosen, size in zip(combo, sizes):
                plan.append((chosen, allocation[at:at + size]))
                at += size
            delivered, total, _ = _chain_flow(puzzle, plan)
            evaluated += 1
            if all(d >= p["need"] for d, p in zip(delivered, products)):
                valid += 1
                score = Fraction(sum(min(d, p["want"]) for d, p in zip(delivered, products)), total)
                key = (score, -total)
                if best_key is None or key > best_key:
                    best_key, best_plan = key, [[list(c), list(s)] for c, s in plan]
    if best_key is None:
        return None
    return {"score": best_key[0], "ships": -best_key[1], "plan": best_plan, "valid": valid, "evaluated": evaluated}


def chain_par(puzzle):
    return Fraction(puzzle["par"][0], puzzle["par"][1])


def chain_silver_score(puzzle):
    return chain_par(puzzle) * CHAIN_SILVER_PERCENT / 100


def chain_medal_for(puzzle, units, ships):
    score = Fraction(units, ships)
    if score >= chain_par(puzzle):
        return "gold"
    return "silver" if score >= chain_silver_score(puzzle) else "bronze"


def chain_score_text(score):
    return f"{float(score):.2f}"


def _chain_clean_best(puzzle_id, item):
    """One saved best ({units, ships}) from an untrusted save, or None. A score above par is impossible, so such
    an entry (or one that does not even fill the orders) is dropped."""
    puzzle = CHAIN_BY_ID.get(puzzle_id) if isinstance(puzzle_id, str) else None
    if puzzle is None or not isinstance(item, dict):
        return None
    units = _saved_int(item.get("units"), 1, 10_000, 0)
    ships = _saved_int(item.get("ships"), 1, puzzle["fleet"], 0)
    if not units or not ships:
        return None
    if units < sum(p["need"] for p in puzzle["products"]) or units > sum(p["want"] for p in puzzle["products"]):
        return None
    if Fraction(units, ships) > chain_par(puzzle):
        return None
    return {"units": units, "ships": ships}


# --- Chain Builder: saved bests, entering and leaving, the draft chain ---------------------------------------------
def _chain_real_best():
    """The saved bests of the real game (while a puzzle runs, the live records belong to the puzzle board)."""
    if runstate._sandbox_real is None:
        return records["chain_best"]
    return (runstate._sandbox_real["snapshot"].get("records") or {}).get("chain_best") or {}


def _chain_better(units, ships, old):
    """True when (units, ships) scores higher than the saved best, or ties it with fewer ships."""
    if old is None:
        return True
    new_score, old_score = Fraction(units, ships), Fraction(old["units"], old["ships"])
    return new_score > old_score or (new_score == old_score and ships < old["ships"])


def chain_best_text(puzzle_id):
    entry = _chain_real_best().get(puzzle_id)
    if entry is None:
        return "Best: not solved yet"
    medal = chain_medal_for(CHAIN_BY_ID[puzzle_id], entry["units"], entry["ships"])
    return f"Best: {CRISIS_MEDAL_MARK[medal]}, {chain_score_text(Fraction(entry['units'], entry['ships']))} per ship"


def chain_medal_counts():
    """(puzzles solved, gold medals) in the real game."""
    best = _chain_real_best()
    golds = sum(1 for pid, e in best.items() if pid in CHAIN_BY_ID and chain_medal_for(CHAIN_BY_ID[pid], e["units"], e["ships"]) == "gold")
    return len([pid for pid in best if pid in CHAIN_BY_ID]), golds


def chain_solved_in_chapter(chapter):
    best = _chain_real_best()
    return sum(1 for p in CHAIN_PUZZLES if p["chapter"] == chapter and p["id"] in best)


def _chain_new_board(puzzle_id):
    """A blank chain for a puzzle: no sites chosen, one ship on every leg."""
    puzzle = CHAIN_BY_ID[puzzle_id]
    runstate.chain_active, runstate.chain_tab, runstate.chain_hint_rung, runstate.chain_done = puzzle_id, 0, 0, None
    runstate.chain_plan = []
    for product in puzzle["products"]:
        stages = len(chain_path(product["good"]))
        runstate.chain_plan.append({"sites": [None] * stages, "ships": [1] * stages})


def _chain_clear():
    runstate.chain_active, runstate.chain_plan, runstate.chain_tab, runstate.chain_hint_rung, runstate.chain_done = None, [], 0, 0, None


def chain_draft_complete():
    return runstate.chain_active is not None and all(site is not None for entry in runstate.chain_plan for site in entry["sites"])


def chain_draft_result():
    """chain_evaluate() of the chain on the board, or None while a site is still missing."""
    if not chain_draft_complete():
        return None
    return chain_evaluate(CHAIN_BY_ID[runstate.chain_active], [[e["sites"], e["ships"]] for e in runstate.chain_plan])


def chain_ships_on_board():
    return sum(sum(entry["ships"]) for entry in runstate.chain_plan)


def chain_set_site(product_index, stage, site_id):
    """Puts a site into one step of a chain ("" or None clears the step). False when it does not fit."""
    if runstate.chain_active is None or not isinstance(product_index, int) or not 0 <= product_index < len(runstate.chain_plan):
        return False
    puzzle = CHAIN_BY_ID[runstate.chain_active]
    entry = runstate.chain_plan[product_index]
    if not isinstance(stage, int) or isinstance(stage, bool) or not 0 <= stage < len(entry["sites"]):
        return False
    if not site_id:
        entry["sites"][stage] = None
        runstate.chain_done = None
        return True
    path = chain_path(puzzle["products"][product_index]["good"])
    site = puzzle["sites"].get(site_id) if isinstance(site_id, str) else None
    if site is None or not chain_fits(site, path, stage):
        return False
    if site_id in [s for k, s in enumerate(entry["sites"]) if k != stage]:
        return False
    entry["sites"][stage] = site_id
    runstate.chain_done = None
    return True


def chain_pick_site(site_id):
    """Map click: the site goes into the first step of the chosen product that it fits (clicking a site that is
    already in a step takes it out again). True when the board changed."""
    if runstate.chain_active is None or not runstate.chain_plan:
        return False
    puzzle = CHAIN_BY_ID[runstate.chain_active]
    site = puzzle["sites"].get(site_id) if isinstance(site_id, str) else None
    if site is None or site["kind"] == "port":
        return False
    index = min(runstate.chain_tab, len(runstate.chain_plan) - 1)
    entry = runstate.chain_plan[index]
    path = chain_path(puzzle["products"][index]["good"])
    fitting = [k for k in range(len(path)) if chain_fits(site, path, k)]
    for k in fitting:
        if entry["sites"][k] == site_id:
            return chain_set_site(index, k, "")
    for k in fitting:
        if entry["sites"][k] is None:
            return chain_set_site(index, k, site_id)
    return bool(fitting) and chain_set_site(index, fitting[0], site_id)


def chain_can_add_ship(product_index, stage):
    return (runstate.chain_active is not None and 0 <= product_index < len(runstate.chain_plan)
            and chain_ships_on_board() < CHAIN_BY_ID[runstate.chain_active]["fleet"])


def chain_adjust_ships(product_index, stage, delta):
    """One more or one fewer ship on a leg (never below 1, never past the fleet). True when it changed."""
    if runstate.chain_active is None or not 0 <= product_index < len(runstate.chain_plan) or delta not in (-1, 1):
        return False
    entry = runstate.chain_plan[product_index]
    if not 0 <= stage < len(entry["ships"]):
        return False
    new = entry["ships"][stage] + delta
    if new < 1 or (delta > 0 and not chain_can_add_ship(product_index, stage)):
        return False
    entry["ships"][stage] = new
    runstate.chain_done = None
    return True


def chain_clear_board():
    """Empties the chain on the board (one ship per leg again)."""
    if runstate.chain_active is not None:
        _chain_new_board(runstate.chain_active)


def chain_place_best():
    """Puts the stored par chain on the board."""
    if runstate.chain_active is None:
        return False
    best = CHAIN_BY_ID[runstate.chain_active]["best"]
    runstate.chain_plan[:] = [{"sites": list(s), "ships": list(n)} for s, n in zip(best["sites"], best["ships"])]
    runstate.chain_done = None
    return True


def chain_lock_in():
    """Locks in the chain on the board: when it meets every order the medal is worked out and the best is kept
    (written straight into the set-aside real game, so leaving keeps it)."""
    result = chain_draft_result()
    if result is None or not result["ok"] or not result["met"]:
        return False
    puzzle = CHAIN_BY_ID[runstate.chain_active]
    units, ships = sum(result["credited"]), result["ships"]
    medal = chain_medal_for(puzzle, units, ships)
    old = _chain_real_best().get(runstate.chain_active)
    improved = _chain_better(units, ships, old)
    first = not _chain_real_best()
    if improved:
        stored = runstate._sandbox_real["snapshot"].setdefault("records", {})
        stored.setdefault("chain_best", {})[runstate.chain_active] = {"units": units, "ships": ships}
    runstate.chain_done = {"medal": medal, "units": units, "ships": ships, "improved": improved}
    extra = " The First Link achievement is yours once you leave." if first else ""
    show_notice_toast(f"\U0001F517 {puzzle['title']}: {CRISIS_MEDAL_MARK[medal]}, {chain_score_text(Fraction(units, ships))} per ship.{extra}")
    return True


# --- Chain Builder: hints (each rung opens only on a press) --------------------------------------------------------
def chain_goods_line(puzzle, index):
    """'Ore to Alloy to Machinery' for a product."""
    return " to ".join(chain_good_name(g) for g in chain_path(puzzle["products"][index]["good"]))


def chain_hint_text(puzzle, rung):
    if rung == 1:
        recipes = ", ".join(
            f"{CHAIN_RECIPES[g]['name']} turns {CHAIN_RECIPES[g]['take']} {chain_good_name(CHAIN_RECIPES[g]['from'])} "
            f"into {CHAIN_RECIPES[g]['make']} {chain_good_name(g)}"
            for g in dict.fromkeys(g for p in puzzle["products"] for g in chain_path(p["good"])[1:])
        )
        carry = (f"A ship carries {puzzle['cargo']} units a trip and fits as many whole round trips into {CHAIN_CYCLE} ticks as "
                 "the leg allows (a round trip takes twice the steps), so short legs are worth far more ships' work.")
        return (recipes + ". " if recipes else "") + carry + " Aim for legs that move about the same amount, so none starves the next."
    best = puzzle["best"]
    if rung == 2:
        parts = []
        for index, names in enumerate(best["sites"]):
            parts.append(f"{chain_good_name(puzzle['products'][index]['good'])}: " + ", ".join(puzzle["sites"][s]["name"] for s in names))
        return "The par chain uses these sites, in order. " + "; ".join(parts) + "."
    parts = []
    for index, ships in enumerate(best["ships"]):
        parts.append(f"{chain_good_name(puzzle['products'][index]['good'])} " + ", ".join(str(n) for n in ships))
    total = sum(sum(s) for s in best["ships"])
    return "Ships on each leg of the par chain, first leg to last. " + "; ".join(parts) + f". That is {total} ships in all."


def chain_hint_label():
    return ("Would you like a suggestion?", "Would you like another suggestion?",
            "Would you like the ships as well?", "Place the par chain on the board")[min(runstate.chain_hint_rung, 3)]


def chain_hint_press():
    """Opens the next rung of the ladder; the press after the last rung places the par chain."""
    if runstate.chain_active is None:
        return False
    if runstate.chain_hint_rung < 3:
        runstate.chain_hint_rung += 1
        return True
    return chain_place_best()


# --- Chain Builder: the screen -------------------------------------------------------------------------------------
def _chain_esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def chain_site_line(puzzle, site_id):
    site = puzzle["sites"][site_id]
    where = f"({site['pos'][0]}, {site['pos'][1]})"
    if site["kind"] == "source":
        return f"{site['name']} {where}: source of {chain_good_name(site['good'])}, up to {site['cap']} per cycle."
    if site["kind"] == "refinery":
        makes = ", ".join(f"{CHAIN_RECIPES[r]['name']} ({chain_good_name(r)})" for r in site["recipes"])
        return f"{site['name']} {where}: refinery for {makes}, takes in up to {site['cap']} per cycle."
    return f"{site['name']} {where}: port."


def chain_stage_label(puzzle, index, stage):
    path = chain_path(puzzle["products"][index]["good"])
    if stage == 0:
        return f"Step 1, source: {chain_good_name(path[0])}"
    recipe = CHAIN_RECIPES[path[stage]]
    return f"Step {stage + 1}, {recipe['name']}: {recipe['take']} {chain_good_name(recipe['from'])} make {recipe['make']} {chain_good_name(path[stage])}"


def chain_distances_text(puzzle):
    """Every leg any chain of this puzzle could use, with its distance and what one ship moves on it."""
    seen, lines = set(), []
    for index, product in enumerate(puzzle["products"]):
        for combo in chain_options(puzzle, index):
            full = list(combo) + [product["port"]]
            for k in range(len(full) - 1):
                if (full[k], full[k + 1]) not in seen:
                    seen.add((full[k], full[k + 1]))
                    trips = chain_trips(puzzle, full[k], full[k + 1])
                    lines.append(
                        f"{puzzle['sites'][full[k]]['name']} to {puzzle['sites'][full[k + 1]]['name']}: "
                        f"{chain_distance(puzzle, full[k], full[k + 1])} steps, {trips} round trips a cycle, "
                        f"{trips * puzzle['cargo']} units per ship."
                    )
    return " ".join(lines)


def chain_map_svg(puzzle):
    """The map as an SVG string: sites as shapes (circle = source, square = refinery, diamond = port) with their
    names, a faint grid, and the chosen chain drawn as arrows (solid for the first order, dashed for the second)
    with the ships on each leg. Purely a picture: the controls beside it do the same job with the keyboard."""
    scale, pad = 46, 34
    xs = [s["pos"][0] for s in puzzle["sites"].values()]
    ys = [s["pos"][1] for s in puzzle["sites"].values()]
    width, height = pad * 2 + max(xs) * scale + 40, pad * 2 + max(ys) * scale + 14

    def at(site_id):
        x, y = puzzle["sites"][site_id]["pos"]
        return pad + x * scale, pad + y * scale

    used = {s for e in runstate.chain_plan for s in e["sites"] if s}
    parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">',
             '<defs><marker id="chain-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">'
             '<path d="M0,0 L8,4 L0,8 z" class="chain-arrowhead"/></marker></defs>']
    for gx in range(max(xs) + 1):
        parts.append(f'<line class="chain-grid" x1="{pad + gx * scale}" y1="{pad - 14}" x2="{pad + gx * scale}" y2="{pad + max(ys) * scale + 14}"/>')
    for gy in range(max(ys) + 1):
        parts.append(f'<line class="chain-grid" x1="{pad - 14}" y1="{pad + gy * scale}" x2="{pad + max(xs) * scale + 14}" y2="{pad + gy * scale}"/>')
    for index, entry in enumerate(runstate.chain_plan):
        full = entry["sites"] + [puzzle["products"][index]["port"]]
        for k in range(len(full) - 1):
            if full[k] is None or full[k + 1] is None:
                continue
            (x1, y1), (x2, y2) = at(full[k]), at(full[k + 1])
            off = 5 * index
            dash = ' stroke-dasharray="6 4"' if index else ""
            parts.append(f'<line class="chain-leg" x1="{x1 + off}" y1="{y1 + off}" x2="{x2 + off}" y2="{y2 + off}"{dash} marker-end="url(#chain-arrow)"/>')
            parts.append(f'<text class="chain-leg-label" x="{(x1 + x2) / 2 + off + 4}" y="{(y1 + y2) / 2 + off - 4}">x{entry["ships"][k]}</text>')
    for site_id, site in puzzle["sites"].items():
        x, y = at(site_id)
        cls = "chain-node chain-node--" + site["kind"] + (" chain-node--used" if site_id in used else "")
        if site["kind"] == "source":
            shape = f'<circle cx="{x}" cy="{y}" r="11"/>'
        elif site["kind"] == "refinery":
            shape = f'<rect x="{x - 10}" y="{y - 10}" width="20" height="20"/>'
        else:
            shape = f'<polygon points="{x},{y - 13} {x + 13},{y} {x},{y + 13} {x - 13},{y}"/>'
        parts.append(f'<g class="{cls}" data-site="{_chain_esc(site_id)}">{shape}<text x="{x}" y="{y + 27}" text-anchor="middle">{_chain_esc(site["name"])}</text></g>')
    parts.append("</svg>")
    return "".join(parts)


def chain_goal_lines(puzzle, result):
    """The three goals on the strip: meet the orders, silver, gold. Each is a (done, text) pair."""
    par, silver = chain_par(puzzle), chain_silver_score(puzzle)
    ready = result is not None and result["ok"]
    orders = "; ".join(
        f"{chain_good_name(p['good'])} {result['delivered'][i] if ready else 0} of {p['need']} needed" for i, p in enumerate(puzzle["products"])
    )
    score = result["score"] if ready else None
    met = ready and result["met"]
    return [
        (met, "Meet every order: " + orders + "."),
        (met and score >= silver, f"Silver: score {chain_score_text(silver)} or more per ship ({CHAIN_SILVER_PERCENT}% of par)."),
        (met and score >= par, f"Gold: reach par, {chain_score_text(par)} per ship."),
    ]


def chain_result_lines(puzzle, result):
    if result is None:
        return ["Choose a site for every step to see how the chain runs."]
    if not result["ok"]:
        return [result["reason"]]
    lines = []
    for index, product in enumerate(puzzle["products"]):
        legs = result["legs"][index]
        flow = ", then ".join(
            f"{leg['moved']} on {puzzle['sites'][leg['from']]['name']} to {puzzle['sites'][leg['to']]['name']}" for leg in legs
        )
        lines.append(f"{chain_good_name(product['good'])}: {flow}. Delivered {result['delivered'][index]} (needs {product['need']}, takes up to {product['want']}).")
    verdict = "Every order is met." if result["met"] else "An order is short: add ships to a starved leg, or choose other sites."
    score = f"{chain_score_text(result['score'])} units per ship ({sum(result['credited'])} units, {result['ships']} ships)"
    return lines + [f"Your score: {score}. Par: {chain_score_text(chain_par(puzzle))}. {verdict}"]


def chain_status_text():
    if runstate.chain_active is None:
        return ("Pick a puzzle to play. Your real corporation is set aside and comes back unchanged; nothing in Chain Builder "
                "can be lost, there is no timer and no fail state.")
    puzzle = CHAIN_BY_ID[runstate.chain_active]
    line = f"{puzzle['title']}: {chain_best_text(runstate.chain_active)}."
    if runstate.chain_done is not None:
        line += f" Locked in: {CRISIS_MEDAL_MARK[runstate.chain_done['medal']]}, {chain_score_text(Fraction(runstate.chain_done['units'], runstate.chain_done['ships']))} per ship."
        line += "" if runstate.chain_done["improved"] else " (Your saved best is better, so it stays.)"
    return line


def _chain_signature():
    best = _chain_real_best()
    return (
        runstate.chain_open, runstate.chain_active, runstate.chain_tab, runstate.chain_hint_rung,
        tuple((tuple(e["sites"]), tuple(e["ships"])) for e in runstate.chain_plan),
        tuple(sorted((pid, e["units"], e["ships"]) for pid, e in best.items())),
        None if runstate.chain_done is None else tuple(sorted(runstate.chain_done.items())),
    )
