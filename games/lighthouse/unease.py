"""Lighthouse -- when the odd things happen: the year's schedule of mystery beats, the small oddities and the
hidden unease meter.

The schedule is a pure function of the seed (like the weather), so the build-up to a mystery is the same however the
keeper plays, a save needs only the list of beats already shown, and the dread ledger can be proved for a thousand
seeded years without playing one. The rules the schedule keeps (and tests/test_dread_ledger.py proves):
  * at most two odd or moment beats on any night;
  * none on night 1 to 3, the first night of a season, or the festival night;
  * never three nights running with an odd beat and no kind beat between (a night with a kind beat or a resolve breaks the run);
  * a beat falls inside its window, in order, and prefers a hazy or foggy night (fog is the curtain);
  * every mystery's resolve beat falls on or before its `resolves_by` night.
"""

from clock import is_festival, night_len
from data import NIGHTS_PER_SEASON, NIGHTS_PER_YEAR
from mysteries import MYSTERIES, TRIFLE_ORDER, TRIFLES, UNEASE_CAP
from rng import unit
from weather import weather

ODD_KINDS = ("odd", "moment")
AT_FRACTION = {"dusk": 0.12, "deep": 0.5, "dawn": 0.86}
MAX_ODD_PER_NIGHT = 2
MAX_RUN = 2
FIRST_ODD_NIGHT = 4

_cache = {}


def mystery_order():
    return sorted(MYSTERIES, key=lambda m: MYSTERIES[m]["beats"][0]["window"][0])


def hazy(seed, night):
    return any(c in (1, 2) for c in weather(seed, night).cond)


def odd_allowed(night):
    return (night >= FIRST_ODD_NIGHT and (night - 1) % NIGHTS_PER_SEASON != 0 and not is_festival(night))


def run_length(night, odd, kind):
    """How many consecutive odd nights (no kind beat between) the night `night` sits inside, itself included."""
    def odd_here(n):
        return n in odd and n not in kind
    if night in kind:
        return 0
    left = 0
    n = night - 1
    while n >= 1 and odd_here(n):
        left += 1
        n -= 1
    right = 0
    n = night + 1
    while n <= NIGHTS_PER_YEAR and odd_here(n):
        right += 1
        n += 1
    return left + 1 + right


def schedule(seed):
    """{beat_id: year_night} for the first year. Raises ValueError if the data cannot be fitted (a data bug).

    A depth-first search places every beat in order, trying the foggy nights of its window first, and backs up
    when a later beat has no room: so a window never has to be tuned around the weather."""
    hit = _cache.get(seed)
    if hit is not None:
        return dict(hit)
    flat = []
    for mid in mystery_order():
        prev_id = None
        for beat in MYSTERIES[mid]["beats"]:
            flat.append((beat, prev_id))
            prev_id = beat["id"]
    placed = {}
    odd_count = {}

    def fits(beat, n, kind_nights):
        is_odd = beat["kind"] in ODD_KINDS
        if is_odd and not (odd_allowed(n) and odd_count.get(n, 0) < MAX_ODD_PER_NIGHT):
            return False
        odd_nights = {k for k, v in odd_count.items() if v} | ({n} if is_odd else set())
        kinds = kind_nights | (set() if is_odd else {n})
        return all(run_length(k, odd_nights, kinds) <= MAX_RUN for k in odd_nights)

    def place(i, kind_nights):
        if i == len(flat):
            return True
        beat, prev_id = flat[i]
        first, last = beat["window"]
        if prev_id is not None:
            first = max(first, placed[prev_id] + beat.get("gap", 1))
        options = list(range(first, last + 1))
        if beat.get("fog"):
            options = [n for n in options if hazy(seed, n)] + [n for n in options if not hazy(seed, n)]
        is_odd = beat["kind"] in ODD_KINDS
        for n in options:
            if not fits(beat, n, kind_nights):
                continue
            placed[beat["id"]] = n
            if is_odd:
                odd_count[n] = odd_count.get(n, 0) + 1
            if place(i + 1, kind_nights if is_odd else kind_nights | {n}):
                return True
            if is_odd:
                odd_count[n] -= 1
            del placed[beat["id"]]
        return False

    if not place(0, frozenset()):
        raise ValueError("the mystery beats cannot be fitted into the year")
    if len(_cache) > 64:
        _cache.clear()
    _cache[seed] = dict(placed)
    return placed


def beat_tick(night, at):
    """The tick a beat shows at, or -1 for the morning."""
    if at == "morning":
        return -1
    return min(night_len(night) - 2, int(night_len(night) * AT_FRACTION[at]))


def beats_on(seed, night):
    """[(mystery_id, beat)] scheduled for this global night (the first year only)."""
    if night > NIGHTS_PER_YEAR:
        return []
    plan = schedule(seed)
    out = []
    for mid in mystery_order():
        for beat in MYSTERIES[mid]["beats"]:
            if plan[beat["id"]] == night:
                out.append((mid, beat))
    return out


def odd_nights(seed):
    plan = schedule(seed)
    odd = set()
    kind = set()
    for mid in MYSTERIES:
        for beat in MYSTERIES[mid]["beats"]:
            (odd if beat["kind"] in ODD_KINDS else kind).add(plan[beat["id"]])
    return odd, kind


# ---- the hidden meter -------------------------------------------------------------------------------------
def clamp(value):
    return max(0, min(UNEASE_CAP, int(value)))


def meter_after_night(unease, worst_cond, fog_ticks, letters_delivered, resolved):
    """How the meter moves over one night. Fog and storms raise it; a letter, a gift or a solved mystery drops it
    sharply; a quiet night with no good news lets it creep."""
    if worst_cond == 4:
        unease += 10
    elif fog_ticks >= 8:
        unease += 7
    else:
        unease += 2
    if letters_delivered:
        unease -= 22
    if resolved:
        unease -= 40
    return clamp(unease)


def trifle_chance(unease):
    return 0.05 + 0.4 * unease / float(UNEASE_CAP)


def trifle_tonight(seed, night, unease, fired, odd_set, kind_set):
    """The id of the small oddity that falls tonight, or None. At most one is ever waiting to be explained."""
    if not odd_allowed(night) or night in odd_set or len(fired) >= len(TRIFLE_ORDER):
        return None
    if unit(seed, "trifle", night) >= trifle_chance(unease):
        return None
    if run_length(night, odd_set | {night}, kind_set) > MAX_RUN:
        return None
    left = [t for t in TRIFLE_ORDER if t not in fired]
    pick = left[int(unit(seed, "trifle-pick", night) * len(left))]
    if TRIFLES[pick].get("fog") and not hazy(seed, night):
        return None
    return pick
