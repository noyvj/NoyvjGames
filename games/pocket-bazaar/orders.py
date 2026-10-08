"""Pocket Bazaar -- customers and their orders.

A customer wants 1-3 goods (a bulk buyer up to 4) at given tiers. Patience is counted in BEATS (one crate tap, one
merge, one sweep or one successful hand-over), never seconds, so nothing here reads a clock and nothing expires
while the player is away. Every customer's patience is set when they are made, from what their order costs to
build, so a slow customer is slow because their order is big, not because of a hidden difficulty dial.

Order matching: most customers take the tier asked for or any better one of the same family; a Critic wants the
exact tier; a Tourist takes any tier of the family (and pays by the tier handed over).
"""

from goods import MAX_TIER, VALUE, crate_beats, good_label, good_name, is_wild

NAMES = ("Tomas", "Ines", "Bao", "Lucia", "Oskar", "Priya", "Henrik", "Zainab", "Felix", "Noor", "Anselm", "Yuki",
         "Rosa", "Dmitri", "Amara", "Leif", "Sana", "Mateo", "Elsie", "Kofi", "Wren", "Idris", "Petra", "Jun",
         "Odette", "Rafael", "Thea", "Gus", "Mabel", "Cyrus", "Linnea", "Bashir", "Hana", "Pavel", "Imogen")

# pay_pct: share of the goods' value paid; wait_pct: share of the normal patience; mode: how a good may match.
ARCHETYPES = {
    "regular": {"name": "Regular", "pay_pct": 100, "wait_pct": 100, "mode": "atleast", "blurb": "Takes the tier asked for or better."},
    "haggler": {"name": "Haggler", "pay_pct": 150, "wait_pct": 60, "mode": "atleast", "blurb": "Pays half again as much but waits less."},
    "critic": {"name": "Critic", "pay_pct": 125, "wait_pct": 100, "mode": "exact", "blurb": "Wants exactly that tier, nothing better."},
    "bulk": {"name": "Bulk buyer", "pay_pct": 115, "wait_pct": 100, "mode": "atleast", "blurb": "One big order of the same simple goods."},
    "child": {"name": "Child with a coin", "pay_pct": 70, "wait_pct": 150, "mode": "atleast", "tip_pct": 100,
              "blurb": "A tiny order, a very patient customer, and a big tip for quick service."},
    "tourist": {"name": "Tourist", "pay_pct": 55, "wait_pct": 100, "mode": "any",
                "blurb": "Takes any tier of the family and pays for the tier you hand over."},
    "crowd": {"name": "Rush crowd", "pay_pct": 100, "wait_pct": 100, "mode": "atleast",
              "blurb": "Arrives with two friends. Serve all three for a group bonus."},
}

MAX_ITEMS = 4
MAX_NAME = 24
BASE_BEATS = 3                # a little extra patience on every order
TIP_PCT = 25                  # served with at least half the patience left


class Customer:
    def __init__(self, name, archetype, items, patience_max, patience_left=None, group=0):
        self.group = group
        self.name = name
        self.archetype = archetype
        self.items = items                        # list of [family, tier, done]
        self.max = patience_max
        self.left = patience_max if patience_left is None else patience_left

    # ---- what the order is -----------------------------------------------------------------------
    @property
    def info(self):
        return ARCHETYPES[self.archetype]

    def wanted(self):
        return [(f, t) for f, t, done in self.items if not done]

    def is_complete(self):
        return all(done for _f, _t, done in self.items)

    def cost_in_beats(self):
        """Beats to fill the whole order from scratch (taps + merges, plus one beat per hand-over)."""
        return sum(crate_beats(t) + 1 for _f, t, _d in self.items)

    def pay(self, pay_pct=100, scales=False, only_done=False, family_pct=None):
        """What the order pays: the goods' value, times the archetype's share, times the day's `pay_pct`. With
        `scales` goods of tier 3 and up count a tenth more; `only_done` counts just what was handed over."""
        total = 0
        for f, t, done in self.items:
            if only_done and not done:
                continue
            value = VALUE[t]
            if scales and t >= 3:
                value = value * 110 // 100
            if family_pct and f in family_pct:
                value = value * family_pct[f] // 100
            total += value
        return max(1, total * self.info["pay_pct"] // 100 * pay_pct // 100)

    def tip(self, pay_pct=100, scales=False, tip_pct=TIP_PCT, family_pct=None):
        """A tip for quick service: served with at least half the patience left. A child's tip is always big."""
        tip_pct = max(tip_pct, self.info.get("tip_pct", 0))
        return self.pay(pay_pct, scales, family_pct=family_pct) * tip_pct // 100 if self.left * 2 >= self.max else 0

    def fill(self, index, good):
        """Mark an item handed over. A Tourist is paid by the tier actually handed over."""
        self.items[index][2] = 1
        if self.info["mode"] == "any":
            self.items[index][1] = good[1]

    # ---- handing over -------------------------------------------------------------------------------
    def match(self, good):
        """The index of the item this good would fill, or None. The tightest fit wins."""
        if good is None or is_wild(good):
            return None
        family, tier = good
        best = None
        for index, (f, t, done) in enumerate(self.items):
            if done or f != family:
                continue
            if self.info["mode"] == "exact" and t != tier:
                continue
            if t > tier:
                continue
            if best is None or t > self.items[best][1]:
                best = index
        return best

    def why_not(self, good):
        """A plain sentence for a refused hand-over."""
        if good is None:
            return "There is nothing there to hand over."
        if is_wild(good):
            return "A wildcard is not a finished good: merge it into something first."
        family, tier = good
        mine = [(f, t) for f, t, done in self.items if not done]
        if not mine:
            return f"{self.name} has everything already."
        if not any(f == family for f, _t in mine):
            return f"{self.name} is not asking for {good_name(good).lower()}s or anything like them."
        if self.info["mode"] == "exact":
            return f"{self.name} is a Critic and wants exactly the tier asked for, not {good_label(good)}."
        return f"{self.name} wants a better one than {good_label(good)}."

    # ---- saves ---------------------------------------------------------------------------------------------
    def to_dict(self):
        items = []
        for f, t, done in self.items:
            item = {"f": f, "t": t}
            if done:
                item["d"] = 1
            items.append(item)
        data = {"name": self.name, "arch": self.archetype, "items": items, "max": self.max, "left": self.left}
        if self.group:
            data["grp"] = self.group
        return data

    @classmethod
    def from_dict(cls, data, families):
        """Validated rebuild; raises ValueError for anything malformed."""
        if not isinstance(data, dict):
            raise ValueError("customer must be an object")
        name, arch = data.get("name"), data.get("arch")
        if not isinstance(name, str) or not 1 <= len(name) <= MAX_NAME or arch not in ARCHETYPES:
            raise ValueError("bad customer")
        raw = data.get("items")
        if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_ITEMS:
            raise ValueError("bad order")
        items = []
        for entry in raw:
            if not isinstance(entry, dict):
                raise ValueError("bad item")
            f, t = entry.get("f"), entry.get("t")
            if f not in families or isinstance(t, bool) or not isinstance(t, int) or not 1 <= t <= MAX_TIER:
                raise ValueError("bad item")
            items.append([f, t, 1 if entry.get("d") else 0])
        patience_max, left = data.get("max"), data.get("left")
        for number in (patience_max, left):
            if isinstance(number, bool) or not isinstance(number, int) or not 0 < number <= 9999:
                raise ValueError("bad patience")
        if left > patience_max:
            raise ValueError("bad patience")
        group = data.get("grp", 0)
        if isinstance(group, bool) or not isinstance(group, int) or not 0 <= group <= 64:
            raise ValueError("bad group")
        return cls(name, arch, items, patience_max, left, group)


def patience_for(items, archetype, slack_pct):
    """Beats this customer will wait: the order's build cost plus a little, times the day's slack, times the
    archetype's patience share. `slack_pct` is 100 * the slack factor (e.g. 300 for 3.0)."""
    cost = sum(crate_beats(t) + 1 for _f, t, _d in items)
    raw = (cost + BASE_BEATS) * slack_pct * ARCHETYPES[archetype]["wait_pct"]
    return max(6, -(-raw // 10000))               # ceiling division


def _tier(rng, max_tier, weights=None):
    options = [(t, (weights or {}).get(t, 1)) for t in range(1, max_tier + 1)]
    return rng.weighted(options)


def make_customer(rng, spec, families, used_names):
    """One customer from the day's spec. All randomness comes from `rng`, so a day is reproducible."""
    archetype = rng.weighted(spec["archetypes"])
    max_tier = spec["max_tier"]
    if archetype == "crowd":
        archetype = "regular"                  # a crowd is built in make_queue; one drawn alone is just a regular
    if archetype == "child":
        items = [[rng.choice(families), rng.between(1, min(2, max_tier)), 0]]
    elif archetype == "tourist":
        items = [[rng.choice(families), 1, 0] for _ in range(rng.between(1, 2))]
    elif archetype == "bulk":
        family = rng.choice(families)
        tier = rng.between(1, min(2, max_tier))
        count = 3 if spec["max_items"] < 4 else rng.between(3, 4)
        items = [[family, tier, 0] for _ in range(count)]
    else:
        count = rng.weighted([(n, w) for n, w in enumerate(spec["item_weights"], 1) if n <= spec["max_items"]])
        if archetype in ("haggler", "critic"):
            count = min(count, 2)
        items = [[rng.choice(families), _tier(rng, max_tier, spec.get("tier_weights")), 0] for _ in range(count)]
    name = rng.choice(NAMES)
    for _ in range(6):                           # avoid two of the same name in one queue where we can
        if name not in used_names:
            break
        name = rng.choice(NAMES)
    used_names.add(name)
    return Customer(name, archetype, items, patience_for(items, archetype, spec["slack_pct"]))


def make_crowd(rng, spec, families, used_names, group):
    """Three customers who arrive together and want goods from one family; a group bonus if all three are served."""
    family = rng.choice(families)
    crowd = []
    for _ in range(3):
        count = rng.between(1, min(2, spec["max_items"]))
        items = [[family, _tier(rng, min(3, spec["max_tier"]), spec.get("tier_weights")), 0] for _ in range(count)]
        name = rng.choice(NAMES)
        for _try in range(6):
            if name not in used_names:
                break
            name = rng.choice(NAMES)
        used_names.add(name)
        crowd.append(Customer(name, "crowd", items, patience_for(items, "crowd", spec["slack_pct"]), group=group))
    return crowd


def make_queue(rng, spec, families, count=None):
    used, queue, group = set(), [], 0
    target = count or spec["customers"]
    crowd_weight = dict(spec["archetypes"]).get("crowd", 0)
    while len(queue) < target:
        if crowd_weight and target - len(queue) >= 3 and rng.chance(crowd_weight, sum(w for _a, w in spec["archetypes"])):
            group += 1
            queue.extend(make_crowd(rng, spec, families, used, group))
        else:
            queue.append(make_customer(rng, spec, families, used))
    return queue


def order_is_reachable(customer, board):
    """True when every good in the order can be built from an empty counter of this board's size: building one
    good of tier t needs t cells at once (see goods.cells_needed), and goods are handed over one at a time."""
    from board import plan_build
    for f, t, _d in customer.items:
        if plan_build(board.__class__(board.width, board.height), f, t) is None:
            return False
    return True
