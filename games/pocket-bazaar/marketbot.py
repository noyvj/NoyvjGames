"""Pocket Bazaar -- the plain greedy player the Daily Market's fairness bar is measured with.

It plays a `Day` directly with the same rules as a person at the counter: hand over whatever a customer will take (to
the customer closest to leaving), merge towards what is asked, open a crate for what is missing, sell when the counter
is full. It mirrors tests/bot.py, which plays through game.handle() by reading the view; a test keeps the two in step.
Nothing here is shown to the player and it uses no randomness and no clock.
"""

import goods


def _target(day):
    """The most urgent unfilled item at the stall: (family, tier), the customer closest to leaving first."""
    best = None
    for customer in day.window():
        tier_any = customer.info["mode"] == "any"
        for family, tier, done in customer.items:
            if done:
                continue
            tier = 1 if tier_any else tier
            key = (customer.left, tier)
            if best is None or key < best[0]:
                best = (key, family, tier)
    return (best[1], best[2]) if best else None


def step(day, families):
    """One action on the day; returns its outcome dict."""
    options = []
    for cell, takers in day.deliverable().items():
        for index in takers:
            options.append((day.window()[index].left, index, cell))
    if options:
        _left, index, cell = sorted(options)[0]
        return day.deliver(cell, index)
    target = _target(day)
    cells = day.board.cells
    if target:
        family, tier = target
        for t in range(1, tier):
            same = [i for i, g in enumerate(cells) if g and g[0] == family and g[1] == t]
            if len(same) >= 2:
                return day.drop(same[0], same[1])
        for i, g in enumerate(cells):
            partners = day.board.partners(i) if g else []
            if g and partners and (g[0] != family or g[1] < tier):
                if (1 if goods.is_wild(g) else g[1]) < 5:
                    return day.drop(i, partners[0])
    if not day.board.is_full():
        family = target[0] if target else families[0]
        return day.crate(family)
    held = sorted((goods.sell_value(g), i) for i, g in enumerate(cells) if g)
    return day.sell(held[0][1])


def play(day, families, limit=3000):
    """Play the day to its end. Returns the number of actions taken."""
    steps = 0
    while not day.is_over():
        step(day, families)
        steps += 1
        if steps >= limit:
            raise RuntimeError("the bot never finished the day")
    return steps
