"""A greedy bot that plays the game through game.handle() exactly as the page does (it only reads the view). Used to
check that days are fair: a plain strategy serves most customers on every campaign day and can never jam."""

import json

import game


def call(**request):
    return json.loads(game.handle(json.dumps(request)))


def _cells(view):
    return view["board"]["cells"]


def _target(view):
    """The most urgent unfilled item at the stall: (family, tier), preferring the customer closest to leaving."""
    best = None
    for c in view["customers"]:
        for item in c["items"]:
            if item["done"]:
                continue
            key = (c["patience"], item["tier"])
            if best is None or key < best[0]:
                best = (key, item["family"], item["tier"])
    return (best[1], best[2]) if best else None


def step(view):
    """One action. Returns the new view."""
    # 1. hand over anything a customer will take, to the customer closest to leaving
    options = []
    for cell, takers in view["deliverable"].items():
        for index in takers:
            options.append((view["customers"][index]["patience"], index, int(cell)))
    if options:
        _p, index, cell = sorted(options)[0]
        return call(action="deliver", **{"from": cell, "to": index})
    target = _target(view)
    cells = _cells(view)
    if target:
        family, tier = target
        # 2. merge the lowest pair of that family below the target tier
        for t in range(1, tier):
            same = [i for i, c in enumerate(cells) if c and c["family"] == family and c["tier"] == t]
            if len(same) >= 2:
                return call(action="drop", **{"from": same[0], "to": same[1]})
        # 3. any other pair that exists is progress too
        for i, c in enumerate(cells):
            if c and view["partners"].get(str(i)) and (c["family"] != family or c["tier"] < tier):
                if c["tier"] < 5:
                    return call(action="drop", **{"from": i, "to": view["partners"][str(i)][0]})
    # 4. open a crate for what is needed, or make room
    if not view["full"]:
        family = target[0] if target else view["crates"][0]["family"]
        return call(action="crate", family=family)
    goods = [(c["sell"], i) for i, c in enumerate(cells) if c]
    return call(action="sell", at=sorted(goods)[0][1])


def play_day(view=None, limit=3000):
    view = view or call(action="start_day")
    steps = 0
    while view["phase"] == "open":
        view = step(view)
        steps += 1
        assert steps < limit, "the bot never finished the day"
    return view, steps
