"""Station Medic -- the shift rules, a pure function of the case and the list of actions.

A `Case` is a compiled authored shift (see cases.py). A state is a plain tuple, so the solver can memoise it:

    state   = (stock, patients, borrowed)
    stock   = counts in the order of `case.items`
    patient = (closed, isolated, steady, readings, cured, cost, exposed, given)
      closed   1 once the patient is settled (cured, eased, reacted or comforted)
      steady   0 not steadied, 1 a band, 2 Tally
      readings one value per scan in `case.tests`: -1 not run, 0 clear, 1 positive
      cured    bit k set once the patient's k-th true condition is cured
      cost     the cost of this patient's care so far
      exposed  1 once the ward was exposed by handling a contagious patient in the open
      given    bit x set once treatment x of `case.tx` was given to this patient

Nothing here reads a clock or a random source. Actions are tuples:
  ("scan", p, t) ("treat", p, x) ("band", p) ("robot", p) ("isolate", p) ("release", p) ("comfort", p) ("borrow", item)
"""

import itertools

import cast
import lexicon as lx

CLOSED, ISO, STEADY, READ, CURED, COST, EXPOSED, GIVEN = range(8)

COST_EASE = 1
COST_WASTE = 1
COST_COMFORT = 1
COST_BORROW = 1
COST_REACTION = 2
COST_EXPOSURE = 2

GRADE_NAMES = {0: "none", 1: "rough", 2: "steady", 3: "clean"}


def grade_of(cost):
    """3 clean (no cost), 2 steady (a cost of 1 or 2), 1 rough (3 or more)."""
    return 3 if cost <= 0 else 2 if cost <= 2 else 1


class Patient:
    __slots__ = ("crew", "name", "first", "role", "truth", "traits", "forbids", "signs", "say", "shaking", "spreads",
                 "cands", "cand_spreads", "truth_read", "truth_ix")


class Case:
    def __init__(self, d):
        self.id = d["id"]
        self.title = d["title"]
        self.intro = d["intro"]
        self.pool = tuple(d["pool"].split()) if isinstance(d["pool"], str) else tuple(d["pool"])
        self.tests = tuple(d.get("tests", "").split())
        stock = d["stock"]
        self.items = tuple(i for i in lx.ITEM_IDS if i in stock)
        self.item_ix = {i: k for k, i in enumerate(self.items)}
        self.stock0 = tuple(int(stock[i]) for i in self.items)
        self.tx = tuple(t for t in lx.TX_IDS if lx.TX_BY_ID[t]["item"] in self.item_ix)
        self.band = lx.BAND_ITEM in self.item_ix
        self.beds = int(d.get("beds", 0))
        self.robots = int(d.get("robots", 0))
        self.maxc = int(d.get("maxc", 1))
        self.patients = tuple(self._patient(pd) for pd in d["patients"])
        self.errors = self._check()

    # ---- compile ---------------------------------------------------------------------------------------------------
    def _patient(self, pd):
        p = Patient()
        member = cast.CREW_BY_ID[pd["crew"]]
        p.crew = pd["crew"]
        p.name = member["name"]
        p.first = member["name"].split()[0]
        p.role = member["role"]
        p.truth = tuple(pd["truth"].split())
        p.traits = tuple(pd.get("traits", "").split())
        p.forbids = frozenset(lx.TRAITS[t][0] for t in p.traits)
        p.say = pd.get("say", "")
        signs = set()
        for c in p.truth:
            signs |= lx.COND[c]["signs"]
        p.signs = frozenset(signs)
        p.shaking = lx.SHAKING in p.signs
        p.spreads = any(lx.COND[c]["spreads"] for c in p.truth)
        p.truth_read = tuple(1 if any(t in lx.COND[c]["findings"] for c in p.truth) else 0 for t in self.tests)
        p.truth_ix = tuple(self.pool.index(c) for c in p.truth if c in self.pool)
        p.cands, p.cand_spreads = [], []
        for r in range(1, self.maxc + 1):
            for combo in itertools.combinations(range(len(self.pool)), r):
                conds = [lx.COND[self.pool[i]] for i in combo]
                union = set()
                for c in conds:
                    union |= c["signs"]
                if union != p.signs:
                    continue
                reading = tuple(1 if any(t in c["findings"] for c in conds) else 0 for t in self.tests)
                p.cands.append((combo, reading))
                p.cand_spreads.append(any(c["spreads"] for c in conds))
        return p

    def _check(self):
        errs = []
        for c in self.pool:
            if c not in lx.COND:
                errs.append("unknown condition " + c)
        for t in self.tests:
            if t not in lx.TEST_BY_ID:
                errs.append("unknown test " + t)
            elif lx.TEST_BY_ID[t]["item"] not in self.item_ix:
                errs.append("test %s has no supply on the shelf" % t)
        for i in self.items:
            if i not in lx.ITEM_IDS:
                errs.append("unknown item " + i)
        for p in self.patients:
            if not set(p.truth) <= set(self.pool):
                errs.append("%s: true condition not in the pool" % p.first)
            elif not p.cands or tuple(sorted(p.truth_ix)) not in [c[0] for c in p.cands]:
                errs.append("%s: true condition is not among the sign matches (maxc %d)" % (p.first, self.maxc))
            if len(p.truth) > self.maxc:
                errs.append("%s: more conditions than maxc" % p.first)
        return errs

    # ---- states ----------------------------------------------------------------------------------------------------
    def new_state(self):
        blank = (-1,) * len(self.tests)
        return (self.stock0, tuple((0, 0, 0, blank, 0, 0, 0, 0) for _ in self.patients), 0)

    def candidates(self, p, readings):
        """Every set of pool conditions that fits the patient's signs and the readings so far (indexes into the pool)."""
        out = []
        for combo, reading in self.patients[p].cands:
            if all(r == -1 or r == v for r, v in zip(readings, reading)):
                out.append(combo)
        return out

    def maybe_spreads(self, p, readings):
        """True if any condition that still fits could spread."""
        pat = self.patients[p]
        for (combo, reading), spreads in zip(pat.cands, pat.cand_spreads):
            if spreads and all(r == -1 or r == v for r, v in zip(readings, reading)):
                return True
        return False

    def tx_forbidden(self, p, x):
        return bool(lx.TX_BY_ID[self.tx[x]]["tags"] & self.patients[p].forbids)

    def tx_clashes(self, x, given):
        if lx.CLASH_TAG not in lx.TX_BY_ID[self.tx[x]]["tags"]:
            return False
        return any(given >> y & 1 and lx.CLASH_TAG in lx.TX_BY_ID[self.tx[y]]["tags"] for y in range(len(self.tx)))

    def stock_of(self, st, item):
        return st[0][self.item_ix[item]] if item in self.item_ix else 0

    def beds_used(self, st):
        return sum(1 for pat in st[1] if pat[ISO] and not pat[CLOSED])

    def robots_used(self, st):
        return sum(1 for pat in st[1] if pat[STEADY] == 2)

    def total_cost(self, st):
        return sum(pat[COST] for pat in st[1]) + st[2]

    def done(self, st):
        return all(pat[CLOSED] for pat in st[1])

    # ---- the one rule function -----------------------------------------------------------------------------------
    def apply(self, st, act):
        """Return (new_state, info). A refused action returns (None, info) with ok False and changes nothing and costs
        nothing. info: ok, msg, delta (cost added), kind, p, and for a scan: positive."""
        stock, pats, borrowed = st
        kind = act[0]
        if kind == "borrow":
            ix = act[1]
            if isinstance(ix, bool) or not isinstance(ix, int) or not 0 <= ix < len(self.items):
                return None, _no("There is no such shelf.")
            stock2 = stock[:ix] + (stock[ix] + 1,) + stock[ix + 1:]
            name = lx.ITEM_NAME[self.items[ix]]
            return (stock2, pats, borrowed + COST_BORROW), _ok("A spare from the ring's reserve: one %s added. Cost %d." % (name.lower(), COST_BORROW), COST_BORROW, "borrow")
        p = act[1] if len(act) > 1 else None
        if isinstance(p, bool) or not isinstance(p, int) or not 0 <= p < len(pats):
            return None, _no("There is no such patient.")
        pat, pd = pats[p], self.patients[p]
        who = pd.first
        if pat[CLOSED]:
            return None, _no("%s has already been seen to." % who)
        if kind == "comfort":
            new = _put(pat, CLOSED, 1, ISO, 0, COST, pat[COST] + COST_COMFORT)
            return (stock, _swap(pats, p, new), borrowed), _ok("%s is settled with comfort care and a quiet bed. Cost %d." % (who, COST_COMFORT), COST_COMFORT, "comfort", p, closed=True)
        if kind == "isolate":
            if pat[ISO]:
                return None, _no("%s is already in the cold room." % who)
            if self.beds <= 0:
                return None, _no("There is no cold room on this shift.")
            if self.beds_used(st) >= self.beds:
                return None, _no("The cold room bed is taken. Free it first.")
            return (stock, _swap(pats, p, _put(pat, ISO, 1)), borrowed), _ok("%s moves to the cold room." % who, 0, "isolate", p)
        if kind == "release":
            if not pat[ISO]:
                return None, _no("%s is not in the cold room." % who)
            return (stock, _swap(pats, p, _put(pat, ISO, 0)), borrowed), _ok("%s comes back to the ward." % who, 0, "release", p)
        if kind == "band":
            if not pd.shaking:
                return None, _no("%s is not shaking." % who)
            if pat[STEADY]:
                return None, _no("%s is already steady." % who)
            if not self.band or self.stock_of(st, lx.BAND_ITEM) < 1:
                return None, _no("There are no steadying bands left. Tally can help, or you can borrow one at a cost." if self.robots else "There are no steadying bands left. You can borrow one at a cost.")
            ix = self.item_ix[lx.BAND_ITEM]
            stock2 = stock[:ix] + (stock[ix] - 1,) + stock[ix + 1:]
            return (stock2, _swap(pats, p, _put(pat, STEADY, 1)), borrowed), _ok("%s is steadied with a band." % who, 0, "steady", p)
        if kind == "robot":
            if not pd.shaking:
                return None, _no("%s is not shaking." % who)
            if pat[STEADY]:
                return None, _no("%s is already steady." % who)
            if self.robots <= 0:
                return None, _no("Tally is not on this shift.")
            if self.robots_used(st) >= self.robots:
                return None, _no("Tally is already steadying someone.")
            return (stock, _swap(pats, p, _put(pat, STEADY, 2)), borrowed), _ok("Tally steadies %s." % who, 0, "steady", p)
        if kind not in ("scan", "treat"):
            return None, _no("That is not something the infirmary does.")
        if pd.shaking and not pat[STEADY]:
            return None, _no("%s is shaking too hard for that. Steady %s first." % (who, who))
        if kind == "scan":
            t = act[2] if len(act) > 2 else None
            if isinstance(t, bool) or not isinstance(t, int) or not 0 <= t < len(self.tests):
                return None, _no("There is no such scan.")
            if pat[READ][t] != -1:
                return None, _no("That scan has already been run on %s." % who)
            test = lx.TEST_BY_ID[self.tests[t]]
            need = self.item_ix[test["item"]]
            if stock[need] < 1:
                return None, _no("No %s left. You can borrow one at a cost, or work with what you have." % lx.ITEM_NAME[test["item"]].lower())
            stock2 = stock[:need] + (stock[need] - 1,) + stock[need + 1:]
            positive = pd.truth_read[t]
            reading = pat[READ][:t] + (positive,) + pat[READ][t + 1:]
            new, delta, extra = self._expose(pd, _put(pat, READ, reading))
            word = test["positive"] if positive else "shows nothing"
            msg = "%s on %s: it %s." % (test["name"], who, word)
            return (stock2, _swap(pats, p, new), borrowed), _ok(msg + extra, delta, "scan", p, positive=bool(positive))
        # treat
        x = act[2] if len(act) > 2 else None
        if isinstance(x, bool) or not isinstance(x, int) or not 0 <= x < len(self.tx):
            return None, _no("There is no such treatment.")
        tx = lx.TX_BY_ID[self.tx[x]]
        need = self.item_ix[tx["item"]]
        if stock[need] < 1:
            return None, _no("No %s left. You can borrow one at a cost, or work with what you have." % lx.ITEM_NAME[tx["item"]].lower())
        stock2 = stock[:need] + (stock[need] - 1,) + stock[need + 1:]
        new, delta, extra = self._expose(pd, pat)
        given_before = new[GIVEN]
        new = _put(new, GIVEN, given_before | (1 << x))
        name = tx["name"]
        if tx["tags"] & pd.forbids:
            delta += COST_REACTION
            new = _put(new, CLOSED, 1, ISO, 0, COST, new[COST] + COST_REACTION)
            msg = "%s reacts to the %s, which the chart warned about. Tally's night round settles %s later. Cost %d." % (who, name.lower(), who, COST_REACTION)
            return (stock2, _swap(pats, p, new), borrowed), _ok(msg + extra, delta, "reaction", p, closed=True)
        if self.tx_clashes(x, given_before):
            delta += COST_REACTION
            new = _put(new, CLOSED, 1, ISO, 0, COST, new[COST] + COST_REACTION)
            msg = "Two heavy treatments together: %s reacts. Tally's night round settles %s later. Cost %d." % (who, who, COST_REACTION)
            return (stock2, _swap(pats, p, new), borrowed), _ok(msg + extra, delta, "clash", p, closed=True)
        cured = new[CURED]
        for k, c in enumerate(pd.truth):
            if not cured >> k & 1 and self.tx[x] in lx.COND[c]["cures"]:
                cured |= 1 << k
        if cured != new[CURED]:
            new = _put(new, CURED, cured)
            if cured == (1 << len(pd.truth)) - 1:
                new = _put(new, CLOSED, 1, ISO, 0)
                msg = "The %s works: %s is settled." % (name.lower(), who)
                return (stock2, _swap(pats, p, new), borrowed), _ok(msg + extra, delta, "cure", p, closed=True)
            return (stock2, _swap(pats, p, new), borrowed), _ok("The %s takes hold. There is more to treat for %s." % (name.lower(), who) + extra, delta, "partial", p)
        for k, c in enumerate(pd.truth):
            if not new[CURED] >> k & 1 and lx.COND[c]["ease"] == self.tx[x]:
                delta += COST_EASE
                new = _put(new, CLOSED, 1, ISO, 0, COST, new[COST] + COST_EASE)
                msg = "The %s only eases it. Tally's night round settles %s later. Cost %d." % (name.lower(), who, COST_EASE)
                return (stock2, _swap(pats, p, new), borrowed), _ok(msg + extra, delta, "ease", p, closed=True)
        delta += COST_WASTE
        new = _put(new, COST, new[COST] + COST_WASTE)
        return (stock2, _swap(pats, p, new), borrowed), _ok("The %s does nothing for %s. That supply is wasted. Cost %d." % (name.lower(), who, COST_WASTE) + extra, delta, "waste", p)

    def _expose(self, pd, pat):
        """Handling a contagious patient outside the cold room costs once per patient."""
        if pd.spreads and not pat[ISO] and not pat[EXPOSED]:
            return _put(pat, EXPOSED, 1, COST, pat[COST] + COST_EXPOSURE), COST_EXPOSURE, \
                " %s was handled in the open ward, so the ward needs airing. Cost %d." % (pd.first, COST_EXPOSURE)
        return pat, 0, ""


# ---- small helpers ---------------------------------------------------------------------------------------------------
def _ok(msg, delta, kind, p=None, **extra):
    info = {"ok": True, "msg": msg, "delta": delta, "kind": kind, "p": p}
    info.update(extra)
    return info


def _no(msg):
    return {"ok": False, "msg": msg, "delta": 0, "kind": "refused", "p": None}


def _swap(pats, p, new):
    return pats[:p] + (new,) + pats[p + 1:]


def _put(pat, *pairs):
    items = list(pat)
    for i in range(0, len(pairs), 2):
        items[pairs[i]] = pairs[i + 1]
    return tuple(items)


# ---- action tokens (the save stores the unfinished shift as a list of these) -----------------------------------------------
def to_token(act):
    return ":".join(str(x) for x in act)


def from_token(token):
    """Parse a token back into an action tuple, or None if it is not one."""
    if not isinstance(token, str):
        return None
    parts = token.split(":")
    kinds = {"scan": 3, "treat": 3, "band": 2, "robot": 2, "isolate": 2, "release": 2, "comfort": 2, "borrow": 2}
    if parts[0] not in kinds or len(parts) != kinds[parts[0]]:
        return None
    try:
        nums = [int(x) for x in parts[1:]]
    except ValueError:
        return None
    if any(n < 0 or n > 99 for n in nums):
        return None
    return (parts[0],) + tuple(nums)


def replay(case, tokens):
    """Run a list of tokens from a fresh state. Returns (state, infos) or (None, None) if any action is refused."""
    st = case.new_state()
    infos = []
    for token in tokens:
        act = from_token(token)
        if act is None:
            return None, None
        st2, info = case.apply(st, act)
        if st2 is None:
            return None, None
        st = st2
        infos.append(info)
    return st, infos
