"""Evidence Hunt -- the practice house generator. A practice case is a pure function of (difficulty, seed): the same code always makes
the same house, so a code such as EH3-1K9X2 can be shared and replayed (the pattern of Dead Reckoning's practice codes).

Every house is built by rejection: lay out a house, choose the spirit(s), the restless rooms, the features and the account, then
ask the same solver the authored cases go through whether the house is sound, deducible and fair with a bag of its kit size, and
keep it only if a tool really matters. A seed that cannot be made fair within a few attempts moves on to the next nearby seed, so
the same code always gives the same house. No clock and no random source is used: a small integer hash stands in for both."""

import re

import casework as cw
import houses
import lexicon as lx
import solver

DIFFICULTIES = (1, 2, 3, 4, 5)
NAMES = {1: "A small house", 2: "A few rooms", 3: "Fooled readings", 4: "Two presences", 5: "A big house"}
SEED_LIMIT = 36 ** 6
ATTEMPTS = 40
MASK = (1 << 64) - 1
SPEC = {
    1: dict(layouts=("cottage", "lodge", "bungalow", "flat"), pool=(3, 4), n=(1,), restless=(1, 2), features=0, accounts=(0, 1), kit=3, keepsake=0.0, min_kit=1),
    2: dict(layouts=("terrace", "schoolhouse", "farmhouse", "shop"), pool=(4, 5), n=(1,), restless=(1, 2), features=1, accounts=(1, 1), kit=3, keepsake=0.0, min_kit=1),
    3: dict(layouts=("vicarage", "shop", "villa", "manor", "inn"), pool=(5, 6), n=(1,), restless=(1, 3), features=2, accounts=(0, 1), kit=3, keepsake=0.5, min_kit=2),
    4: dict(layouts=("villa", "manor", "inn", "vicarage", "farmhouse", "mill"), pool=(6, 7), n=(2,), restless=(1, 1), features=3, accounts=(2, 2), kit=3, keepsake=0.0, min_kit=2),
    5: dict(layouts=("mill", "abbey", "hotel", "theatre", "estate", "grand"), pool=(7, 8), n=(1, 2), restless=(2, 4), features=4, accounts=(0, 1), kit=4, keepsake=0.5, min_kit=3),
}
CODE_RE = re.compile(r"^EH([1-5])-([0-9A-Z]{1,6})$")
ID_RE = re.compile(r"^practice-([1-5])-([0-9a-z]{1,6})$")
_CACHE = {}
SIGN = ("tidy", "mover", "shy", "curious")


# --- codes ---------------------------------------------------------------------------------------
def to_base36(n):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


def case_id(difficulty, seed):
    return "practice-%d-%s" % (difficulty, to_base36(seed))


def code_of(difficulty, seed):
    return ("EH%d-%s" % (difficulty, to_base36(seed))).upper()


def parse(text):
    """(difficulty, seed) from a share code (any case, surrounding spaces ignored) or a case id, or None."""
    if not isinstance(text, str):
        return None
    t = text.strip()
    m = CODE_RE.match(t.upper()) or ID_RE.match(t.lower())
    if not m:
        return None
    seed = int(m.group(2), 36)
    return (int(m.group(1)), seed) if seed < SEED_LIMIT else None


def is_practice_id(text):
    return isinstance(text, str) and ID_RE.match(text) is not None


def next_seed(played, difficulty):
    """The seed of the next practice house at this difficulty: repeatable from how many have been opened, no randomness."""
    return ((played + 1) * 7919 + difficulty * 104729) % SEED_LIMIT


# --- a small repeatable source of numbers --------------------------------------------------------------
def _mix(seed, k):
    x = (seed * 0x9E3779B97F4A7C15 + k * 0xBF58476D1CE4E5B9 + 0x94D049BB133111EB) & MASK
    x ^= x >> 30
    x = (x * 0xBF58476D1CE4E5B9) & MASK
    x ^= x >> 27
    x = (x * 0x94D049BB133111EB) & MASK
    return x ^ (x >> 31)


class Rng:
    def __init__(self, seed):
        self.seed = seed
        self.k = 0

    def rand(self):
        self.k += 1
        return (_mix(self.seed, self.k) >> 11) / float(1 << 53)

    def between(self, lo, hi):
        return lo + min(hi - lo, int(self.rand() * (hi - lo + 1)))

    def pick(self, items):
        return items[min(len(items) - 1, int(self.rand() * len(items)))]

    def sample(self, items, n):
        pool = list(items)
        out = []
        while pool and len(out) < n:
            out.append(pool.pop(min(len(pool) - 1, int(self.rand() * len(pool)))))
        return out


# --- laying out a house ----------------------------------------------------------------------------------
def _attempt(difficulty, seed, attempt):
    spec = SPEC[difficulty]
    rng = Rng(seed * 1009 + attempt * 7919 + difficulty)
    layout = rng.pick(spec["layouts"])
    rooms = [r["id"] for r in houses.rooms_of(layout)]
    n = rng.pick(spec["n"])
    kinds = [k for k in lx.KIND_IDS if n == 1 or "roamer" not in lx.KIND_BEHAVIOURS[k]]
    truth = tuple(rng.sample(kinds, n))
    lo, hi = spec["restless"]
    slots, free = [], list(rooms)
    for kind in truth:
        bh = lx.KIND_BEHAVIOURS[kind]
        count = 1 if ("fond" in bh or n == 2) else rng.between(max(2, lo) if "roamer" in bh else lo, max(hi, 2) if "roamer" in bh else hi)
        count = min(count, len(free) - 1)
        chosen = rng.sample(free, count)
        free = [r for r in free if r not in chosen]
        slots.append(tuple(chosen))
    restless = [r for slot in slots for r in slot]
    features = {}
    for room in rng.sample(rooms, spec["features"]):
        features[room] = rng.pick(lx.FT_IDS)
    keepsake = None
    if n == 1 and len(slots[0]) >= 2 and rng.rand() < spec["keepsake"]:
        shows = [b for b in SIGN if b in lx.KIND_BEHAVIOURS[truth[0]]]
        if shows:
            keepsake = (rng.pick(slots[0]), rng.pick(lx.KS_IDS), rng.pick(shows))
    accounts = []
    wanted = rng.between(*spec["accounts"])
    for s, kind in enumerate(truth):
        shows = [b for b in SIGN if b in lx.KIND_BEHAVIOURS[kind]]
        if n == 2:
            accounts.append((rng.pick(shows), slots[s][0]))
        elif wanted and shows:
            accounts += [(b, None) for b in rng.sample(shows, min(wanted, len(shows)))]
    size = rng.between(*spec["pool"])
    others = rng.sample([k for k in lx.KIND_IDS if k not in truth], size - n)
    pool = tuple(truth) + tuple(others)
    data = {"id": case_id(difficulty, seed), "title": "Practice house", "layout": layout, "truth": truth, "pool": pool,
            "restless": tuple(slots), "kit": spec["kit"], "accounts": tuple(accounts), "features": features, "keepsake": keepsake,
            "client": "A caller with a code", "chapter": -1, "practice": True, "code": code_of(difficulty, seed), "names": {}}
    return data, restless


def _words(data):
    names = " and ".join(lx.KIND_NAME[k] for k in data["truth"])
    notes = " ".join(lx.KIND_NOTE[k] for k in data["truth"])
    layout = houses.LAYOUTS[data["layout"]][0].lower()
    data["title"] = "%s (%s)" % (houses.LAYOUTS[data["layout"]][0], data["code"])
    data["intro"] = "A practice house: a %s, made from the code %s. The same code always makes the same house, so you can share it or try it again." % (layout, data["code"])
    data["ending"] = "It was %s. %s" % (names, notes)
    return data


def _fair(data, spec):
    if solver.validate(data):
        return False
    info = solver.analyse(cw.Case(data))
    return info["min_kit"] is not None and spec["min_kit"] <= info["min_kit"] <= data["kit"] and max(len(c) for c in info["cands"]) >= 2


def make(difficulty, seed):
    """The practice case data for (difficulty, seed), or None for something that is not a valid code. A seed that does not give a fair
    house within ATTEMPTS tries moves on to the next seeds, so every valid code gives the same house every time."""
    if difficulty not in SPEC or not isinstance(seed, int) or not 0 <= seed < SEED_LIMIT:
        return None
    key = (difficulty, seed)
    if key in _CACHE:
        return _CACHE[key]
    found = None
    for step in range(6):
        for attempt in range(ATTEMPTS):
            data, _restless = _attempt(difficulty, (seed + step) % SEED_LIMIT, attempt)
            if _fair(data, SPEC[difficulty]):
                data["id"], data["code"] = case_id(difficulty, seed), code_of(difficulty, seed)
                found = _words(data)
                break
        if found:
            break
    _CACHE[key] = found
    return found


def data_for(cid):
    """The case data for a practice id or a share code, or None."""
    parsed = parse(cid)
    return make(*parsed) if parsed else None
