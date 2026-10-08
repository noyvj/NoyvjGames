"""Lighthouse -- stateless deterministic randomness.

Nothing in the game holds a random generator: every "random" choice is a pure function of the run seed and a
few integers or words naming the choice (night, tick, part, ...). That is what makes a night replayable from
its seed, a mid-night save safe (there is no generator state to lose), and pause or fast-forward irrelevant
to the outcome. The sim never reads the clock and never imports `random`.
"""

MASK = (1 << 64) - 1


def _fold(h, value):
    """Fold one int or str into a 64-bit hash (FNV-1a over the value, then a splitmix64 finaliser)."""
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, int):
        chunks = [(value >> (8 * i)) & 0xFF for i in range(8)] if value >= 0 else [0xFF] + [(-value >> (8 * i)) & 0xFF for i in range(8)]
    else:
        chunks = list(str(value).encode("utf-8"))
    for byte in chunks:
        h ^= byte
        h = (h * 0x100000001B3) & MASK
    h ^= h >> 30
    h = (h * 0xBF58476D1CE4E5B9) & MASK
    h ^= h >> 27
    h = (h * 0x94D049BB133111EB) & MASK
    h ^= h >> 31
    return h


def mix(*parts):
    """A 64-bit hash of the parts, order-sensitive."""
    h = 0xCBF29CE484222325
    for part in parts:
        h = _fold(h, part)
    return h


def unit(*parts):
    """A float in [0, 1) that depends only on the parts."""
    return (mix(*parts) >> 11) / float(1 << 53)


def rint(lo, hi, *parts):
    """An int in [lo, hi] (inclusive)."""
    return lo + int(unit(*parts) * (hi - lo + 1))


def pick(options, *parts):
    return options[int(unit(*parts) * len(options))]


def weighted(options, weights, *parts):
    """Pick one option with probability proportional to its weight (all weights >= 0, not all zero)."""
    total = float(sum(weights))
    r = unit(*parts) * total
    acc = 0.0
    for option, weight in zip(options, weights):
        acc += weight
        if r < acc:
            return option
    return options[-1]
