"""Slingshot -- the Moon Atlas: a schematic chart of the destinations (not to scale) and a card of real numbers for each one.

Every destination is a body (a moon, a planet, or the Sun's inner space); a mark on the chart is one mission that goes there. The cards are
built from the dated numbers in bodies_data.py (JPL and NASA, read on bodies_data.READ), so nothing on them is typed by hand: radius, period, size
of the pull, and how large the sphere of influence is in the game's model.
"""

import bodies
import bodies_data as D

# destination id -> (label, kind, parent, order). The chart lays the destinations out left to right, near the Sun first.
DESTS = {
    "sun": ("Sunward", "space", None, 0),
    "mercury": ("Mercury's orbit", "planet", None, 1),
    "venus": ("Venus", "planet", None, 2),
    "moon": ("The Moon", "moon", "earth", 3),
    "mars": ("Mars", "planet", None, 4),
    "phobos": ("Phobos", "moon", "mars", 5),
    "deimos": ("Deimos", "moon", "mars", 6),
}


def label(dest):
    return DESTS[dest][0]


def order():
    return sorted(DESTS, key=lambda d: DESTS[d][3])


def _grouped(x, digits=0):
    return "{:,.{d}f}".format(x, d=digits)


def card(dest):
    """Lines of real numbers for a destination: [(title, text), ...], and the source line."""
    if dest in D.MOONS:
        parent, gm, radius, a, period_d = D.MOONS[dest]
        parent_gm = D.PLANETS[parent][0]
        b = bodies.moon(dest)
        lines = [("Size", "Mean radius %s km." % _grouped(radius, 1 if radius < 100 else 0)),
                 ("Orbit", "Goes round %s every %s at %s km from its centre." % (parent.capitalize(), _days(period_d), _grouped(a))),
                 ("Pull", "Its pull (GM) is %s km^3/s^2, about 1/%s of %s's." % (_sig(gm), _grouped(parent_gm / gm), parent.capitalize())),
                 ("In the game", "A sphere of influence of %s km." % _grouped(b["soi"]) if dest == "moon" else "Too small to have a real sphere of influence: you meet it by rendezvous.")]
        source = "JPL Planetary Satellite Physical Parameters (radius, GM) and Mean Elements (orbit), read %s." % D.READ
        return lines, source
    if dest in D.PLANETS:
        gm, radius, a_au, l0, rate, period_y = D.PLANETS[dest]
        b = bodies.planet(dest)
        lines = [("Size", "Mean radius %s km." % _grouped(radius)),
                 ("Orbit", "Goes round the Sun every %s years at %s AU (%s million km)." % (_sig(period_y), _sig(a_au), _grouped(a_au * D.AU_KM / 1e6))),
                 ("Pull", "Its pull (GM) is %s km^3/s^2, about 1/%s of the Sun's." % (_grouped(gm), _grouped(D.GM_SUN / gm))),
                 ("In the game", "A sphere of influence of %s km: inside it only this planet pulls." % _grouped(b["soi"], 0))]
        source = "JPL Planetary Physical Parameters, Astrodynamic Parameters and Approximate Positions of the Planets, read %s." % D.READ
        return lines, source
    return [("Sunward", "The Sun holds 99.8 percent of the Solar System's mass. Its pull (GM) is %s km^3/s^2. A probe that starts at Earth's distance "
             "(1 AU) has to give up most of Earth's sideways speed to fall in close." % _grouped(D.GM_SUN))], \
        "JPL Astrodynamic Parameters, read %s." % D.READ


def _days(period_d):
    if period_d < 2.0:
        return "%.1f hours" % (period_d * 24.0)
    return "%s days" % _sig(period_d)


def _sig(x):
    if x >= 1000:
        return _grouped(x)
    if x >= 100:
        return "%.0f" % x
    if x >= 10:
        return "%.1f" % x
    if x >= 1:
        return "%.2f" % x
    return "%.4g" % x
