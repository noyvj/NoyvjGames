"""Lighthouse -- the weather of a night, and the barometer's honest guess at it.

`weather(seed, night)` is a pure function: the same seed and night always give the same ticks, so the night
that was forecast is the night that happens, a save never stores weather, and pausing or fast-forwarding cannot
change a thing. A night has a *severity* (calm, unsettled, rough, dangerous) drawn from the season's weights,
and the severity decides which weather shapes are laid onto the clear sky: a haze patch, a fog bank, a pair of
squalls, or a storm with a rise, a peak and a fade.
"""

from clock import is_festival, night_len, season_of
from data import SEVERITY_WEIGHTS
from rng import rint, unit, weighted

_cache = {}
CACHE_MAX = 64

WIND_RANGE = ((0, 1), (1, 2), (1, 3), (2, 3))        # the wind's floor and ceiling by severity
FOG_WEIGHT = (0.4, 0.3, 0.65, 0.5)      # how often a rough night's bad weather is fog rather than squalls, by season


class NightWeather(object):
    """The conditions for every tick of one night."""

    __slots__ = ("severity", "cond", "wind")

    def __init__(self, severity, cond, wind):
        self.severity = severity
        self.cond = cond            # list of 0..4 (clear, haze, fog, squall, storm), one per tick
        self.wind = wind            # list of 0..4, one per tick

    def worst(self):
        return max(self.cond) if self.cond else 0


def severity(seed, night):
    """0..3. The first nights are gentle and the festival night is always calm."""
    if night == 1 or is_festival(night):
        return 0
    sev = weighted((0, 1, 2, 3), SEVERITY_WEIGHTS[season_of(night)], seed, "severity", night)
    if night <= 3:
        sev = min(sev, 1)
    return sev


def _lay(cond, start, length, value):
    for i in range(start, min(len(cond), start + length)):
        cond[i] = max(cond[i], value)


def weather(seed, night):
    key = (seed, night)
    hit = _cache.get(key)
    if hit is not None:
        return hit
    length = night_len(night)
    sev = severity(seed, night)
    cond = [0] * length

    def r(*parts):
        return unit(seed, "wx", night, *parts)

    def start_in(span, label):
        return rint(0, max(0, length - span), seed, "wx-start", night, label)

    if sev == 0:
        if not is_festival(night) and r("patch") < 0.3:
            _lay(cond, start_in(8, "haze"), rint(4, 8, seed, "wx-len", night, "haze"), 1)
    elif sev == 1:
        if r("kind") < FOG_WEIGHT[season_of(night)] * 0.6:
            span = rint(4, 10, seed, "wx-len", night, "fog")
            _lay(cond, start_in(span, "fog"), span, 2)
        else:
            span = rint(8, 18, seed, "wx-len", night, "haze")
            _lay(cond, start_in(span, "haze"), span, 1)
    elif sev == 2:
        if r("kind") < FOG_WEIGHT[season_of(night)]:
            span = rint(12, 24, seed, "wx-len", night, "bank")
            begin = start_in(span, "bank")
            _lay(cond, max(0, begin - 3), span + 6, 1)          # fog thickens out of haze and thins into it
            _lay(cond, begin, span, 2)
        else:
            for n in range(2):
                span = rint(3, 5, seed, "wx-len", night, "squall", n)
                begin = start_in(span, "squall%d" % n)
                _lay(cond, max(0, begin - 2), span + 4, 1)
                _lay(cond, begin, span, 3)
    else:
        peak = rint(8, 14, seed, "wx-len", night, "peak")
        total = peak + 6
        begin = rint(2, max(2, length - total - 4), seed, "wx-start", night, "storm")
        _lay(cond, max(0, begin - 4), 4, 1)
        _lay(cond, begin, 3, 3)                                  # rise
        _lay(cond, begin + 3, peak, 4)                           # peak
        _lay(cond, begin + 3 + peak, 3, 3)                       # fade
    wind = []
    lo, hi = WIND_RANGE[sev]
    for t in range(length):
        base = lo + int(unit(seed, "wind", night, t // 6) * (hi - lo + 1))
        if cond[t] == 3:
            base += 1
        elif cond[t] == 4:
            base += 2
        wind.append(min(4, base))
    result = NightWeather(sev, cond, wind)
    if len(_cache) >= CACHE_MAX:
        _cache.clear()
    _cache[key] = result
    return result


def forecast(seed, night, vane=False):
    """The barometer's reading for a night: an inclusive severity band (lo, hi).

    Truthful on average and wrong sometimes: the true severity lies inside the band nine times in ten (nineteen
    in twenty with the wind vane). The band is two steps wide, or one step wide on a vane night that is
    sure of itself."""
    truth = severity(seed, night)
    miss = unit(seed, "baro", night, "miss") >= (0.95 if vane else 0.9)
    side = unit(seed, "baro", night, "side") < 0.5
    sure = vane and unit(seed, "baro", night, "sure") < 0.5 and not miss
    if sure:
        return (truth, truth)
    if miss:
        lo, hi = (truth + 1, truth + 2) if side else (truth - 2, truth - 1)
    else:
        lo, hi = (truth, truth + 1) if side else (truth - 1, truth)
    if lo < 0:
        lo, hi = 0, 1
    if hi > 3:
        lo, hi = 2, 3
    return (lo, hi)
