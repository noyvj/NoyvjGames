"""Dead Reckoning -- plane geometry on the chart.

The chart is a plane in nautical miles: x grows east, y grows north. A heading is degrees clockwise from
north (0 = north, 90 = east), so the unit vector of a heading is (sin, cos). Everything here is pure maths
with no state, so the simulation and the chart renderer share one definition of bearing and distance.
"""

import math

EPS = 1e-9


def norm_deg(d):
    """A heading folded into 0 <= d < 360."""
    return d % 360.0


def unit(heading):
    """The unit vector of a heading in degrees."""
    r = math.radians(heading)
    return (math.sin(r), math.cos(r))


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def scale(v, k):
    return (v[0] * k, v[1] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def bearing(a, b):
    """The heading from a to b, in degrees (0 when the two points coincide)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) < EPS and abs(dy) < EPS:
        return 0.0
    return norm_deg(math.degrees(math.atan2(dx, dy)))


def angle_diff(a, b):
    """The smallest signed turn from heading a to heading b, in -180 < d <= 180."""
    d = (b - a) % 360.0
    return d - 360.0 if d > 180.0 else d


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def seg_circle_hit(p0, p1, c, r):
    """The first parameter t in [0, 1] at which the segment p0->p1 is on or inside the circle (centre c,
    radius r), or None. A segment that starts inside the circle hits at t = 0."""
    if dist(p0, c) <= r:
        return 0.0
    d = sub(p1, p0)
    f = sub(p0, c)
    a = dot(d, d)
    if a < EPS:
        return None
    b = 2.0 * dot(f, d)
    cc = dot(f, f) - r * r
    disc = b * b - 4.0 * a * cc
    if disc < 0:
        return None
    root = math.sqrt(disc)
    t = (-b - root) / (2.0 * a)
    if 0.0 <= t <= 1.0:
        return t
    return None


def seg_point_dist(p0, p1, c):
    """The shortest distance from point c to the segment p0->p1."""
    d = sub(p1, p0)
    a = dot(d, d)
    if a < EPS:
        return dist(p0, c)
    t = max(0.0, min(1.0, dot(sub(c, p0), d) / a))
    return dist(lerp(p0, p1, t), c)


def seg_seg_hit(p0, p1, q0, q1):
    """The parameter t along p0->p1 where it crosses q0->q1, or None (parallel segments never cross)."""
    r = sub(p1, p0)
    s = sub(q1, q0)
    denom = cross(r, s)
    if abs(denom) < EPS:
        return None
    qp = sub(q0, p0)
    t = cross(qp, s) / denom
    u = cross(qp, r) / denom
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return t
    return None


def seg_seg_dist(p0, p1, q0, q1):
    """The shortest distance between two segments (0 if they cross)."""
    if seg_seg_hit(p0, p1, q0, q1) is not None:
        return 0.0
    return min(seg_point_dist(p0, p1, q0), seg_point_dist(p0, p1, q1),
               seg_point_dist(q0, q1, p0), seg_point_dist(q0, q1, p1))


def point_in_polygon(pt, poly):
    """Even-odd test: is the point inside the polygon (a list of (x, y))?"""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


def seg_polygon_hit(p0, p1, poly):
    """The first parameter t at which the segment touches the polygon (0 if it starts inside), or None."""
    if point_in_polygon(p0, poly):
        return 0.0
    best = None
    n = len(poly)
    for i in range(n):
        t = seg_seg_hit(p0, p1, poly[i], poly[(i + 1) % n])
        if t is not None and (best is None or t < best):
            best = t
    return best


def seg_polygon_dist(p0, p1, poly):
    """The shortest distance from the segment to the polygon's outline or inside (0 if it touches)."""
    if point_in_polygon(p0, poly) or point_in_polygon(p1, poly):
        return 0.0
    n = len(poly)
    return min(seg_seg_dist(p0, p1, poly[i], poly[(i + 1) % n]) for i in range(n))


def in_rect(pt, rect):
    x0, y0, x1, y1 = rect
    return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1


def rnd(v):
    """Round to 0.01 nm so tracks are stable across platforms and easy to compare in tests."""
    return round(v, 2) + 0.0
