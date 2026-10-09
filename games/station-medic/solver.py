"""Station Medic -- the solver. It decides whether a shift can always be finished with no cost, whatever the scans turn out to
say, and it gives the hint ladder its next step.

A shift is FAIR when a careful medic has a plan that works for EVERY set of conditions the signs allow (the player cannot know
which look-alike a patient really has, so a plan that only works for one of them would be luck). The search is therefore an
AND-OR search: the player picks an action, and for a scan the world answers every way it can. The careful policy:

  * scan a patient only when more than one set of conditions still fits, and only with a scan that would split them;
  * treat a patient when one set fits (or when one treatment would cure every set that still fits, if each is a single
    condition), with a treatment the chart does not forbid and that does not clash with one already given;
  * steady a shaking patient before anything else, and put a patient who might be contagious in the cold room before
    scanning or treating them; never guess, borrow or comfort.

The state is the shift's own state without the costs. Every move is permanent (readings fill in, patients are settled, bands
are used), so the graph has no cycles and a memo of won and lost states is safe.
"""

import lexicon as lx
from shift import CLOSED, ISO, STEADY, READ, CURED, GIVEN


class Solver:
    def __init__(self, case, limit=2000000):
        if case.errors:
            raise ValueError("; ".join(case.errors))
        self.case = case
        self.memo = {}
        self.limit = limit
        self.steps = 0
        self.exhausted = False
        pool = case.pool
        # the pool bit of every condition, and the cures of each
        self.combo_mask = {}
        for pd in case.patients:
            for combo, _r in pd.cands:
                self.combo_mask[combo] = sum(1 << i for i in combo)
        self.item_of_tx = [case.item_ix[lx.TX_BY_ID[t]["item"]] for t in case.tx]
        self.item_of_test = [case.item_ix[lx.TEST_BY_ID[t]["item"]] for t in case.tests]
        self.cures = [[(i, case.tx[x] in lx.COND[pool[i]]["cures"]) for i in range(len(pool))] for x in range(len(case.tx))]
        self.cure_mask = [sum(1 << i for i, c in row if c) for row in self.cures]

    # ---- state ------------------------------------------------------------------------------------------------------
    def start(self):
        return self.from_state(self.case.new_state())

    def from_state(self, st):
        """The solver's state (stock, patients) from a real shift state."""
        case = self.case
        pats = []
        for p, pat in enumerate(st[1]):
            pd = case.patients[p]
            cured = 0
            for k in range(len(pd.truth)):
                if pat[CURED] >> k & 1 and k < len(pd.truth_ix):
                    cured |= 1 << pd.truth_ix[k]
            pats.append((pat[CLOSED], pat[ISO], pat[STEADY], pat[READ], cured, pat[GIVEN]))
        return (st[0], tuple(pats))

    # ---- the moves --------------------------------------------------------------------------------------------------
    def moves(self, st):
        """[(action, [child states that must all be won])] in the order the search tries them."""
        case = self.case
        stock, pats = st
        treats, steadies, beds, scans = [], [], [], []
        for p, pat in enumerate(pats):
            closed, iso, steady, read, cured, given = pat
            if closed:
                continue
            pd = case.patients[p]
            if pd.shaking and not steady:
                bi = case.item_ix.get(lx.BAND_ITEM)
                if bi is not None and stock[bi] >= 1:
                    steadies.append((("band", p), [(_set(stock, bi, stock[bi] - 1), _put(pats, p, STEADY, 1))]))
                if case.robots and sum(1 for q in pats if q[STEADY] == 2) < case.robots:
                    steadies.append((("robot", p), [(stock, _put(pats, p, STEADY, 2))]))
                continue
            cands = [combo for combo, reading in pd.cands if all(r == -1 or r == v for r, v in zip(read, reading))]
            risky = any(sp for (combo, reading), sp in zip(pd.cands, pd.cand_spreads)
                        if all(r == -1 or r == v for r, v in zip(read, reading)))
            if risky and not iso:
                if case.beds and sum(1 for q in pats if q[ISO] and not q[CLOSED]) < case.beds:
                    beds.append((("isolate", p), [(stock, _put(pats, p, ISO, 1))]))
                continue
            for x in range(len(case.tx)):
                if stock[self.item_of_tx[x]] < 1 or case.tx_forbidden(p, x) or case.tx_clashes(x, given):
                    continue
                if len(cands) == 1:
                    mask = self.combo_mask[cands[0]]
                    gain = self.cure_mask[x] & mask & ~cured
                    if not gain:
                        continue
                    new = (cured | gain)
                    done = new == mask
                    child = (done, 0 if done else iso, steady, read, new, given | (1 << x))
                    treats.append((("treat", p, x), [(_set(stock, self.item_of_tx[x], stock[self.item_of_tx[x]] - 1), _swap(pats, p, child))]))
                elif all(len(c) == 1 for c in cands) and all(self.cure_mask[x] >> c[0] & 1 for c in cands):
                    child = (1, 0, steady, read, 0, given | (1 << x))
                    treats.append((("treat", p, x), [(_set(stock, self.item_of_tx[x], stock[self.item_of_tx[x]] - 1), _swap(pats, p, child))]))
            if len(cands) > 1:
                for t in range(len(case.tests)):
                    if read[t] != -1 or stock[self.item_of_test[t]] < 1:
                        continue
                    outcomes = sorted({reading[t] for combo, reading in pd.cands if combo in cands})
                    if len(outcomes) < 2:
                        continue
                    s2 = _set(stock, self.item_of_test[t], stock[self.item_of_test[t]] - 1)
                    kids = []
                    for v in outcomes:
                        kids.append((s2, _swap(pats, p, (closed, iso, steady, read[:t] + (v,) + read[t + 1:], cured, given))))
                    scans.append((("scan", p, t), kids))
        return treats + steadies + beds + scans

    # ---- the search -------------------------------------------------------------------------------------------------
    def wins(self, st):
        if all(pat[CLOSED] for pat in st[1]):
            return True
        if st in self.memo:
            return self.memo[st]
        self.steps += 1
        if self.steps > self.limit:
            self.exhausted = True
            return False
        result = False
        for _act, kids in self.moves(st):
            if all(self.wins(k) for k in kids):
                result = True
                break
        self.memo[st] = result
        return result

    def best_move(self, st):
        """The first action that still wins from this solver state (see from_state), or None."""
        for act, kids in self.moves(st):
            if all(self.wins(k) for k in kids):
                return act
        return None

    def solvable(self):
        return self.wins(self.start())


def _set(tup, i, v):
    return tup[:i] + (v,) + tup[i + 1:]


def _swap(pats, p, new):
    return pats[:p] + (new,) + pats[p + 1:]


def _put(pats, p, field, value):
    pat = list(pats[p])
    pat[field] = value
    return pats[:p] + (tuple(pat),) + pats[p + 1:]


def solve_truth(case, solver=None):
    """Play the shift with the strategy the solver finds, against the real truth. Returns (plan, final state, cost)."""
    solver = solver or Solver(case)
    st = case.new_state()
    plan = []
    for _ in range(200):
        if case.done(st):
            break
        act = solver.best_move(solver.from_state(st))
        if act is None:
            return plan, st, None
        st2, info = case.apply(st, act)
        if st2 is None:
            return plan, st, None
        plan.append(act)
        st = st2
    return plan, st, case.total_cost(st)


def next_hint(case, st, solver=None):
    """The next careful action for a real state, or None if a clean finish is no longer possible from here."""
    solver = solver or Solver(case)
    return solver.best_move(solver.from_state(st))
