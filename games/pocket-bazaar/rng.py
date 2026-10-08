"""Pocket Bazaar -- the seeded random numbers.

Everything random in a market day (customer draws, festival tie-breaks, wildcard drops) goes through one
Rng that is stored in the save as {"seed", "draws"}. Integer maths only (a mulberry32 step), so a saved day
resumes to exactly the same next number on any platform and the tests can pin exact values.
"""

MASK = 0xFFFFFFFF
MAX_DRAWS = 1_000_000          # a saved count above this is rejected rather than replayed


def _step(state):
    state = (state + 0x6D2B79F5) & MASK
    t = state
    t = ((t ^ (t >> 15)) * (t | 1)) & MASK
    t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & MASK)) & MASK
    return state, (t ^ (t >> 14)) & MASK


class Rng:
    def __init__(self, seed=1, draws=0):
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= MASK:
            raise ValueError("seed must be an integer 0..2**32-1")
        if not isinstance(draws, int) or isinstance(draws, bool) or not 0 <= draws <= MAX_DRAWS:
            raise ValueError("draws must be a small non-negative integer")
        self.seed = seed
        self._state = seed
        self.draws = 0
        for _ in range(draws):          # replay: the position in the stream is all the save needs
            self.next_u32()

    def next_u32(self):
        self._state, value = _step(self._state)
        self.draws += 1
        return value

    def below(self, n):
        """An integer 0..n-1."""
        if n <= 0:
            raise ValueError("n must be positive")
        return self.next_u32() % n

    def between(self, low, high):
        """An integer low..high inclusive."""
        return low + self.below(high - low + 1)

    def choice(self, seq):
        return seq[self.below(len(seq))]

    def chance(self, num, den):
        """True with probability num/den."""
        return self.below(den) < num

    def weighted(self, pairs):
        """pairs = [(item, weight)] with integer weights; one draw."""
        total = sum(w for _item, w in pairs)
        pick = self.below(total)
        for item, weight in pairs:
            if pick < weight:
                return item
            pick -= weight
        return pairs[-1][0]

    def to_dict(self):
        return {"seed": self.seed, "draws": self.draws}

    @classmethod
    def from_dict(cls, data):
        return cls(data["seed"], data["draws"])


def mix(*parts):
    """Combine small integers into one 32-bit seed (for the day seed from the day number etc.)."""
    h = 2166136261
    for part in parts:
        h = ((h ^ (part & MASK)) * 16777619) & MASK
        h ^= h >> 13
    return h & MASK
