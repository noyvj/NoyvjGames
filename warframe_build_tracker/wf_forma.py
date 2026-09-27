"""Forma planner (batch B #5).

For a chosen build (a part or combo from the tracker, or an item from the crafting
tracker) you type its current slot polarities and the ones you want; the planner
lists which slots need a Forma and in what order, keeps a running total across
every active plan, compares it with the Forma you hold, and shows external
Overframe links.

Facts (Warframe Wiki, read 2026-09-27):
  * https://wiki.warframe.com/w/Forma: a Forma changes the polarity of a mod slot
    and resets the item's affinity to Unranked; it can only be used on a max-rank
    Warframe, companion or weapon.
  * https://wiki.warframe.com/w/Polarity: polarity names Madurai, Vazarin, Naramon,
    Zenurik, Unairu, Penjaga, Umbra and Any; a mod in a matching slot costs 50%
    less (rounded up), in a mismatched slot 25% more.

OVERFRAME LINKS are plain external links, never scraped. Verified with WebFetch on
2026-09-27 (each returned a real page): the build lists /builds/warframes/,
/builds/primary-weapons/, /builds/secondary-weapons/, /builds/melee-weapons/,
/builds/sentinels/ and the item lists /items/warframe/, /items/melee/, /items/primary/,
/items/secondary/, /items/pet/, /items/all/. The site's own item pages need a numeric
id (/items/arsenal/<id>/<name>/) that cannot be guessed, so per-item links go to its
search page (/search/?q=<name>); that page rendered "No Results" to a non-browser
fetch, so it may fill in only in a real browser. The links say so.
"""

from urllib.parse import quote

from wf_util import clean, dict_entries, find_ci, is_int

OVERFRAME = "https://overframe.gg"
POLARITY_FACTS_URL = "https://wiki.warframe.com/w/Polarity"
FORMA_FACTS_URL = "https://wiki.warframe.com/w/Forma"
FACTS_DATE = "2026-09-27"

POLARITIES = ("madurai", "vazarin", "naramon", "zenurik", "unairu", "penjaga", "umbra", "any", "none")
ALIASES = {"-": "none", "": "none", "empty": "none", "no": "none", "universal": "any", "o": "any"}
SLOT_MAX = 12
PLAN_MAX = 20
COUNT_MAX = 9999
BUILD_NAME_MAX = 40

# category -> [(label, path)], every path verified (see the module docstring).
LINK_SETS = {
    "warframe": [("Top Warframe builds", "/builds/warframes/"), ("Warframe items", "/items/warframe/")],
    "zaw": [("Top melee builds", "/builds/melee-weapons/"), ("Melee items", "/items/melee/")],
    "kitgun": [("Top primary builds", "/builds/primary-weapons/"), ("Top secondary builds", "/builds/secondary-weapons/")],
    "amp": [("All items", "/items/all/")],
    "companion": [("Companion items", "/items/pet/"), ("Top sentinel builds", "/builds/sentinels/")],
    "weapon": [("Top primary builds", "/builds/primary-weapons/"), ("Top secondary builds", "/builds/secondary-weapons/"),
               ("Top melee builds", "/builds/melee-weapons/")],
}
LINK_NOTE = (
    "Plain external links to overframe.gg, not scraped. The build and item lists were checked with a live fetch on "
    f"{FACTS_DATE}; the search link (last) rendered no results to a non-browser fetch, so it may only fill in when opened in your browser."
)


def default_forma():
    return {"have": 0, "used": 0, "plans": []}


def is_default(forma):
    return not forma["have"] and not forma["used"] and not forma["plans"]


def parse_polarities(text):
    """"madurai, vazarin, -" -> ["madurai", "vazarin", "none"], or None when any name is unknown
    or the list is empty or longer than SLOT_MAX."""
    pieces = [p.strip().lower() for p in str(text or "").split(",")]
    if not str(text or "").strip() or len(pieces) > SLOT_MAX:
        return None
    out = []
    for piece in pieces:
        piece = ALIASES.get(piece, piece)
        if piece not in POLARITIES:
            return None
        out.append(piece)
    return out


def find_plan(forma, name):
    for plan in forma["plans"]:
        if plan["n"].lower() == str(name or "").strip().lower():
            return plan
    return None


def add_plan(forma, name, current_text, wanted_text, known_names):
    """Adds or replaces the plan for a build. `known_names` are the names a plan may target."""
    name = find_ci(known_names, name)
    if name is None:
        return False, "That is not a part, combo or crafting item. Add it first, then plan its Forma."
    cur, want = parse_polarities(current_text), parse_polarities(wanted_text)
    if cur is None or want is None:
        return False, ("Type slot polarities separated by commas: madurai, vazarin, naramon, zenurik, unairu, penjaga, umbra, "
                       "any, or - for an empty slot.")
    if len(cur) != len(want):
        return False, "The current and wanted lists need the same number of slots."
    existing = find_plan(forma, name)
    if existing is None:
        if len(forma["plans"]) >= PLAN_MAX:
            return False, f"You can keep up to {PLAN_MAX} plans."
        forma["plans"].append({"n": name, "cur": cur, "want": want, "on": True})
    else:
        existing["cur"], existing["want"] = cur, want
    return True, f"Saved the Forma plan for {name}."


def remove_plan(forma, name):
    plan = find_plan(forma, name)
    if plan is None:
        return False
    forma["plans"].remove(plan)
    return True


def set_active(forma, name, flag):
    plan = find_plan(forma, name)
    if plan is None:
        return False
    plan["on"] = bool(flag)
    return True


def steps(plan):
    """The slots that need a Forma, in slot order: [{"slot", "from", "to"}]."""
    return [{"slot": i + 1, "from": a, "to": b}
            for i, (a, b) in enumerate(zip(plan["cur"], plan["want"])) if a != b]


def totals(forma):
    """Running Forma total across active plans against the Forma held."""
    needed = sum(len(steps(p)) for p in forma["plans"] if p["on"])
    return {"needed": needed, "have": forma["have"], "short": max(0, needed - forma["have"]),
            "used": forma["used"], "active": sum(1 for p in forma["plans"] if p["on"])}


def step_text(plan):
    todo = steps(plan)
    if not todo:
        return "Already matches: no Forma needed."
    lines = []
    for n, step in enumerate(todo, 1):
        lines.append(f"Forma {n} of {len(todo)}: slot {step['slot']}, {step['from']} to {step['to']}")
    return "; ".join(lines) + ". Rank the item back to max after each one (a Forma resets it to Unranked)."


def totals_text(forma):
    t = totals(forma)
    if not forma["plans"]:
        return "No plans yet."
    text = f"{t['needed']} Forma needed across {t['active']} active plan(s)."
    if forma["have"]:
        text += f" You hold {forma['have']}: " + (f"still short {t['short']}." if t["short"] else "that covers it.")
    else:
        text += " Enter the Forma you hold to see what is short."
    if forma["used"]:
        text += f" You have already used {forma['used']} (typed by you)."
    return text


def overframe_links(name, category=None):
    """Up to three plain Overframe links for a build: the verified list pages for its category, then
    the search page for its name (see the module docstring for what is and is not verified)."""
    links = [(label, OVERFRAME + path) for label, path in LINK_SETS.get(category, [("All items", "/items/all/")])][:2]
    links.append((f"Search Overframe for {name}", f"{OVERFRAME}/search/?q={quote(str(name))}"))
    return links


# --- save/load -----------------------------------------------------------

def export(forma):
    out = {}
    if forma["have"]:
        out["have"] = forma["have"]
    if forma["used"]:
        out["used"] = forma["used"]
    if forma["plans"]:
        out["plans"] = [{"n": p["n"], "cur": list(p["cur"]), "want": list(p["want"]), "on": p["on"]} for p in forma["plans"]]
    return out


def load(data, known_names):
    forma = default_forma()
    if not isinstance(data, dict):
        return forma
    for key in ("have", "used"):
        value = data.get(key)
        if is_int(value) and 0 <= value <= COUNT_MAX:
            forma[key] = value
    for entry in dict_entries(data.get("plans"))[:PLAN_MAX]:
        name = entry.get("n")
        cur, want, on = entry.get("cur"), entry.get("want"), entry.get("on")
        if not (isinstance(name, str) and name in known_names and isinstance(on, bool)
                and isinstance(cur, list) and isinstance(want, list)
                and 1 <= len(cur) == len(want) <= SLOT_MAX
                and all(isinstance(p, str) and p in POLARITIES for p in cur + want)):
            continue
        if not find_plan(forma, name):
            forma["plans"].append({"n": name, "cur": list(cur), "want": list(want), "on": on})
    return forma


def prune(forma, known_names):
    forma["plans"] = [p for p in forma["plans"] if p["n"] in known_names]


def clean_name(text):
    return clean(text, BUILD_NAME_MAX)
