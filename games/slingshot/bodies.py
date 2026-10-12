"""Slingshot -- the bodies: the Sun, the planets and the moons, built from the dated real numbers in bodies_data.py.

Everything is a circle. A planet moves on a circle around the Sun and a moon on a circle around its planet, at the semi-major axis the
source gives, at the rate Kepler's third law gives for that radius (the sum of the two GMs, so the two-body motion is exact for a
circle). The real orbits are slightly oval (Mars most of all, 9 percent), so a planet's drawn place can be off its real place by up to a
few degrees: the About page says so. Sizes, masses, radii and periods are the real ones.

The starting angle of each planet on a given date is its mean longitude from the JPL table (longitude at J2000 plus its rate times the
centuries since); a moon starts at an angle a mission sets, because the desk picks the phasing for each puzzle.

A sphere of influence (SOI) is the Laplace radius a * (GM_body / GM_parent) ** 0.4, the usual patched-conic size.
"""

import math

import bodies_data as D

J2000 = 2451545.0
SIDEREAL_DAY_S = 86400.0


def julian_date(year, month, day):
    """Julian date at 0h of a Gregorian calendar date (integer arithmetic, no clock)."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn - 0.5


def soi_radius(a_km, gm_body, gm_parent):
    return a_km * (gm_body / gm_parent) ** 0.4


def planet(name):
    """A planet as a dict: gm, radius, a (km from the Sun), n (rad/s), L0 and rate in degrees, soi."""
    gm, radius, a_au, l0, rate, period_y = D.PLANETS[name]
    a = a_au * D.AU_KM
    return {"id": name, "kind": "planet", "parent": "sun", "gm": gm, "radius": radius, "a": a,
            "n": math.sqrt((D.GM_SUN + gm) / a ** 3), "L0": l0, "rate": rate, "soi": soi_radius(a, gm, D.GM_SUN),
            "period_y": period_y}


def moon(name):
    parent, gm, radius, a, period_d = D.MOONS[name]
    gm_parent = D.PLANETS[parent][0]
    return {"id": name, "kind": "moon", "parent": parent, "gm": gm, "radius": radius, "a": a,
            "n": math.sqrt((gm_parent + gm) / a ** 3), "soi": soi_radius(a, gm, gm_parent), "period_d": period_d}


def sun():
    return {"id": "sun", "kind": "star", "parent": None, "gm": D.GM_SUN, "radius": 695700.0, "a": 0.0, "n": 0.0, "soi": None}


def body(name):
    if name == "sun":
        return sun()
    if name in D.PLANETS:
        return planet(name)
    return moon(name)


def planet_angle(name, jd):
    """The planet's heliocentric angle (radians) on a Julian date, from its mean longitude."""
    p = D.PLANETS[name]
    return math.radians(p[3] + p[4] * (jd - J2000) / 36525.0)


def period_seconds(b):
    return 2.0 * math.pi / b["n"]


def label(name):
    return {"sun": "the Sun"}.get(name, "the Moon" if name == "moon" else name.capitalize())


def label_plain(name):
    return {"sun": "Sun", "moon": "Moon"}.get(name, name.capitalize())
