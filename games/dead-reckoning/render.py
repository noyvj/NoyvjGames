"""Dead Reckoning -- the chart as inline SVG, built in Python so the markup can be tested as a string.

Nothing here is colour-only: land is hatched and labelled, reefs are hatched circles, shoals dotted circles,
rocks solid circles with a cross, a current is an outlined zone with an arrow AND a number range, and the
tracks differ by dash style (the estimate is dashed, the truth solid). Colour comes from CSS classes
(style.css) and is decoration only.

`render_chart` never receives the true track unless the caller is revealing it: the view code decides that.
"""

import math
from xml.sax.saxutils import escape

from geom import unit

PX = 480.0          # the drawn size of the sea in viewBox units, whatever the chart's size in nm
LEFT, RIGHT, TOP, BOTTOM = 40.0, 16.0, 56.0, 30.0
HEAD = 8.0          # arrowhead wing length


def f(v):
    return "%.1f" % v


class Frame:
    """Chart nm to viewBox units."""

    def __init__(self, chart):
        self.size = float(chart["size"])
        self.s = PX / self.size
        self.width = LEFT + PX + RIGHT
        self.height = TOP + PX + BOTTOM

    def x(self, nm):
        return LEFT + nm * self.s

    def y(self, nm):
        return TOP + (self.size - nm) * self.s

    def xy(self, pt):
        return (self.x(pt[0]), self.y(pt[1]))

    def pts(self, points):
        return " ".join("%s,%s" % (f(self.x(p[0])), f(self.y(p[1]))) for p in points)


def svg_point(chart, x, y):
    """A chart position as (svg x, svg y), for the page's animation code."""
    fr = Frame(chart)
    return [round(fr.x(x), 1), round(fr.y(y), 1)]


def _arrow(x, y, heading, length, cls):
    """An arrow centred on (x, y) pointing along a heading, as one path."""
    ux, uy = unit(heading)
    dx, dy = ux, -uy                                   # svg y runs down
    x0, y0 = x - dx * length / 2, y - dy * length / 2
    x1, y1 = x + dx * length / 2, y + dy * length / 2
    back = math.atan2(dy, dx) + math.pi
    wings = [(x1 + HEAD * math.cos(back + side), y1 + HEAD * math.sin(back + side)) for side in (0.5, -0.5)]
    return ('<path class="%s" d="M%s,%s L%s,%s M%s,%s L%s,%s L%s,%s"/>'
            % (cls, f(x0), f(y0), f(x1), f(y1), f(wings[0][0]), f(wings[0][1]), f(x1), f(y1), f(wings[1][0]), f(wings[1][1])))


def _label(x, y, text, cls="dr-label", anchor="middle"):
    return '<text class="%s" x="%s" y="%s" text-anchor="%s">%s</text>' % (cls, f(x), f(y), anchor, escape(text))


def deg3(h):
    return "%03d" % (round(h) % 360)


def range_text(pair, unit_text="kn"):
    lo, hi = pair
    if abs(hi - lo) < 1e-9:
        return "%g %s" % (lo, unit_text)
    return "%g to %g %s" % (lo, hi, unit_text)


def _defs():
    return (
        '<defs>'
        '<pattern id="dr-pat-land" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect class="dr-pat-bg-land" width="8" height="8"/><line class="dr-hatch" x1="0" y1="0" x2="0" y2="8"/></pattern>'
        '<pattern id="dr-pat-reef" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
        '<rect class="dr-pat-bg-reef" width="6" height="6"/><line class="dr-hatch-reef" x1="0" y1="0" x2="0" y2="6"/></pattern>'
        '<pattern id="dr-pat-shoal" width="7" height="7" patternUnits="userSpaceOnUse">'
        '<rect class="dr-pat-bg-shoal" width="7" height="7"/>'
        '<circle class="dr-dot" cx="2" cy="2" r="1.1"/><circle class="dr-dot" cx="5.5" cy="5.5" r="1.1"/></pattern>'
        '</defs>')


def _grid(fr):
    step_minor = 1 if fr.size <= 24 else 2
    out = ['<g class="dr-grid">']
    n = int(fr.size)
    for v in range(0, n + 1, step_minor):
        major = v % 5 == 0
        cls = "dr-grid-major" if major else "dr-grid-minor"
        out.append('<line class="%s" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (cls, f(fr.x(v)), f(fr.y(0)), f(fr.x(v)), f(fr.y(fr.size))))
        out.append('<line class="%s" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (cls, f(fr.x(0)), f(fr.y(v)), f(fr.x(fr.size)), f(fr.y(v))))
    for v in range(0, n + 1, 5):
        out.append(_label(fr.x(v), fr.y(0) + 16, str(v), "dr-tick"))
        out.append(_label(fr.x(0) - 6, fr.y(v) + 4, str(v), "dr-tick", "end"))
    out.append('</g>')
    return "".join(out)


def _land(chart, fr):
    out = []
    for land in chart.get("land", ()):
        pts = fr.pts(land["poly"])
        cx = sum(p[0] for p in land["poly"]) / len(land["poly"])
        cy = sum(p[1] for p in land["poly"]) / len(land["poly"])
        out.append('<g class="dr-land" data-id="%s"><polygon class="dr-land-shape" points="%s" fill="url(#dr-pat-land)"/>%s</g>'
                   % (escape(land["id"]), pts, _label(fr.x(cx), fr.y(cy) + 4, land["name"], "dr-label dr-label-land")))
    return "".join(out)


def _currents(chart, fr):
    out = []
    for zone in chart.get("currents", ()):
        x0, y0, x1, y1 = zone["rect"]
        x0c, y0c = max(0.0, x0), max(0.0, y0)
        x1c, y1c = min(fr.size, x1), min(fr.size, y1)
        if x1c <= x0c or y1c <= y0c:
            continue
        cx, cy = fr.x((x0c + x1c) / 2), fr.y((y0c + y1c) / 2)
        tide = zone.get("tide")
        text = range_text(zone["drift_range"]) + (" peak, tidal" if tide else "")
        out.append('<g class="dr-current%s" data-id="%s">' % (" dr-current-tidal" if tide else "", escape(zone["id"])))
        out.append('<rect class="dr-current-zone" x="%s" y="%s" width="%s" height="%s"/>'
                   % (f(fr.x(x0c)), f(fr.y(y1c)), f((x1c - x0c) * fr.s), f((y1c - y0c) * fr.s)))
        out.append(_arrow(cx, cy - 6, zone["set"], 44.0, "dr-current-arrow"))
        if tide:
            out.append(_arrow(cx, cy - 6, zone["set"] + 180.0, 44.0, "dr-current-arrow dr-current-arrow-back"))
        out.append(_label(cx, cy + 16, text, "dr-label dr-label-current"))
        out.append('</g>')
    return "".join(out)


def visible_hazards(chart, discovered=(), reveal=False):
    """Hazards the chart shows: charted ones, ones the crew has found, and (on the reveal) all of them."""
    found = set(discovered)
    return [h for h in chart.get("hazards", ()) if h.get("charted", True) or h["id"] in found or reveal]


def _hazards(chart, fr, discovered, reveal):
    out = []
    found = set(discovered)
    for hz in visible_hazards(chart, discovered, reveal):
        cx, cy, r = fr.x(hz["x"]), fr.y(hz["y"]), hz["r"] * fr.s
        marked = hz.get("charted", True)
        cls = "dr-hazard dr-hazard-%s%s" % (hz["kind"], "" if marked else " dr-hazard-unmarked")
        label = hz["name"] if marked else hz["name"] + (" (found)" if hz["id"] in found else " (unmarked)")
        fill = {"reef": "url(#dr-pat-reef)", "shoal": "url(#dr-pat-shoal)"}.get(hz["kind"], "none")
        out.append('<g class="%s" data-id="%s"><circle class="dr-hazard-shape" cx="%s" cy="%s" r="%s" fill="%s"/>'
                   % (cls, escape(hz["id"]), f(cx), f(cy), f(r), fill))
        if hz["kind"] == "rock":
            c = max(3.0, r * 0.5)
            out.append('<path class="dr-hazard-cross" d="M%s,%s L%s,%s M%s,%s L%s,%s"/>'
                       % (f(cx - c), f(cy - c), f(cx + c), f(cy + c), f(cx - c), f(cy + c), f(cx + c), f(cy - c)))
        out.append(_label(cx, cy - r - 4, label, "dr-label dr-label-hazard"))
        out.append('</g>')
    return "".join(out)


def _landmark_glyph(kind, x, y):
    if kind == "lighthouse":
        return ('<path class="dr-landmark-shape" d="M%s,%s L%s,%s L%s,%s Z"/>'
                '<path class="dr-landmark-ray" d="M%s,%s L%s,%s M%s,%s L%s,%s"/>'
                % (f(x - 5), f(y + 7), f(x + 5), f(y + 7), f(x), f(y - 8), f(x - 7), f(y - 8), f(x - 12), f(y - 10),
                   f(x + 7), f(y - 8), f(x + 12), f(y - 10)))
    if kind == "headland":
        return '<path class="dr-landmark-shape" d="M%s,%s L%s,%s L%s,%s L%s,%s Z"/>' % (f(x), f(y - 8), f(x + 8), f(y), f(x), f(y + 8), f(x - 8), f(y))
    return ('<circle class="dr-landmark-shape" cx="%s" cy="%s" r="5"/><path class="dr-landmark-ray" d="M%s,%s L%s,%s"/>'
            % (f(x), f(y), f(x), f(y - 5), f(x), f(y - 12)))


def _landmarks(chart, fr):
    out = []
    for lm in chart.get("landmarks", ()):
        x, y = fr.x(lm["x"]), fr.y(lm["y"])
        out.append('<g class="dr-landmark dr-landmark-%s" data-id="%s">%s%s</g>'
                   % (lm["kind"], escape(lm["id"]), _landmark_glyph(lm["kind"], x, y), _label(x, y + 22, lm["name"], "dr-label dr-label-landmark")))
    return "".join(out)


def _rose(fr):
    cx, cy, r = fr.width - RIGHT - 24.0, 28.0, 17.0
    out = ['<g class="dr-rose" role="img" aria-label="Compass rose, north is up">',
           '<circle class="dr-rose-ring" cx="%s" cy="%s" r="%s"/>' % (f(cx), f(cy), f(r)),
           '<path class="dr-rose-needle" d="M%s,%s L%s,%s L%s,%s Z"/>' % (f(cx), f(cy - r), f(cx - 4.5), f(cy), f(cx + 4.5), f(cy)),
           '<path class="dr-rose-tail" d="M%s,%s L%s,%s M%s,%s L%s,%s"/>' % (f(cx), f(cy), f(cx), f(cy + r), f(cx - r), f(cy), f(cx + r), f(cy))]
    out.append(_label(cx, cy - r - 3, "N", "dr-rose-letter"))
    out.append('</g>')
    return "".join(out)


def _scale_bar(fr):
    nm = 5 if fr.size <= 30 else 10
    x0, y = LEFT, 20.0
    out = ['<g class="dr-scale" role="img" aria-label="Scale bar, %d nautical miles">' % nm,
           '<path class="dr-scale-bar" d="M%s,%s L%s,%s M%s,%s L%s,%s M%s,%s L%s,%s"/>'
           % (f(x0), f(y), f(x0 + nm * fr.s), f(y), f(x0), f(y - 5), f(x0), f(y + 5), f(x0 + nm * fr.s), f(y - 5), f(x0 + nm * fr.s), f(y + 5))]
    out.append(_label(x0 + nm * fr.s / 2, y + 16, "%d nm" % nm, "dr-scale-label"))
    out.append('</g>')
    return "".join(out)


def _wind(chart, fr):
    wind = chart.get("wind")
    if not wind:
        return ""
    cx, cy = fr.width / 2 + 10.0, 22.0
    out = ['<g class="dr-wind" role="img" aria-label="Wind from %s, %s">' % (deg3(wind["from"]), escape(range_text(wind["range"])))]
    out.append(_arrow(cx, cy, wind["from"] + 180.0, 30.0, "dr-wind-arrow"))
    out.append(_label(cx, cy + 27, "Wind from %s, %s" % (deg3(wind["from"]), range_text(wind["range"])), "dr-label dr-label-wind"))
    out.append('</g>')
    return "".join(out)


def _endpoints(chart, fr):
    sx, sy = fr.xy(chart["start"])
    dx, dy = fr.xy(chart["dest"])
    ring = chart["arrival_radius"] * fr.s
    out = ['<g class="dr-start"><circle class="dr-start-ring" cx="%s" cy="%s" r="8"/><circle class="dr-start-dot" cx="%s" cy="%s" r="2.5"/>%s</g>'
           % (f(sx), f(sy), f(sx), f(sy), _label(sx, sy + 24, "Start", "dr-label dr-label-start"))]
    out.append('<g class="dr-dest"><circle class="dr-arrival-ring" cx="%s" cy="%s" r="%s"/>'
               '<path class="dr-flag-pole" d="M%s,%s L%s,%s"/><path class="dr-flag" d="M%s,%s L%s,%s L%s,%s Z"/>%s</g>'
               % (f(dx), f(dy), f(ring), f(dx), f(dy), f(dx), f(dy - 22), f(dx), f(dy - 22), f(dx + 15), f(dy - 17), f(dx), f(dy - 12),
                  _label(dx, dy + ring + 15, "Landfall", "dr-label dr-label-dest")))
    return "".join(out)


def plan_marks(legs, est):
    """Where each leg of a plan ends on the estimated track (for the numbered markers)."""
    marks = []
    clock = 0.0
    for leg in legs:
        clock += leg["hours"]
        for entry in est:
            if abs(entry[0] - clock) < 1e-6 and not (len(entry) > 3 and entry[3]):
                marks.append([entry[1], entry[2]])
                break
    return marks


def _plan(fr, est, marks, sailed_legs=0):
    if not est:
        return ""
    pts = [(p[1], p[2]) for p in est]
    out = ['<g class="dr-plan"><polyline class="dr-est-track" points="%s"/>' % fr.pts(pts)]
    for i, (x, y) in enumerate(marks, 1):
        px, py = fr.xy((x, y))
        cls = "dr-leg-mark dr-leg-sailed" if i <= sailed_legs else "dr-leg-mark"
        out.append('<g class="%s"><circle cx="%s" cy="%s" r="8"/>%s</g>' % (cls, f(px), f(py), _label(px, py + 4, str(i), "dr-leg-number")))
    out.append('</g>')
    return "".join(out)


def _truth(fr, true_track, est):
    pts = [(p[1], p[2]) for p in true_track]
    out = ['<g class="dr-truth"><g class="dr-ribbons" id="dr-ribbons">']
    est_by_t = {round(e[0], 3): e for e in est if not (len(e) > 3 and e[3])}
    for t, x, y in true_track:
        e = est_by_t.get(round(t, 3))
        if e is None or abs(t - round(t)) > 1e-6 or t < 0.5:
            continue
        ex, ey = fr.xy((e[1], e[2]))
        tx, ty = fr.xy((x, y))
        out.append('<line class="dr-ribbon" data-t="%g" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (t, f(ex), f(ey), f(tx), f(ty)))
    out.append('</g>')
    out.append('<polyline class="dr-true-track" id="dr-true-track" points="%s"/>' % fr.pts(pts))
    out.append('<g class="dr-ship" id="dr-ship"><path class="dr-ship-shape" d="M0,-9 L6,7 L0,3 L-6,7 Z" transform="translate(%s,%s)"/></g>'
               % (f(fr.x(pts[-1][0])), f(fr.y(pts[-1][1]))))
    out.append('</g>')
    return "".join(out)


def _point(fr, pt):
    if pt is None:
        return ""
    x, y = fr.xy(pt)
    return ('<g class="dr-point"><path class="dr-point-cross" d="M%s,%s L%s,%s M%s,%s L%s,%s"/>%s</g>'
            % (f(x - 8), f(y), f(x + 8), f(y), f(x), f(y - 8), f(x), f(y + 8), _label(x + 11, y - 7, "P", "dr-label dr-label-point", "start")))


def _believed(fr, pos):
    if pos is None:
        return ""
    x, y = fr.xy(pos)
    return ('<g class="dr-believed"><path class="dr-believed-shape" d="M%s,%s L%s,%s L%s,%s L%s,%s Z"/>%s</g>'
            % (f(x), f(y - 9), f(x + 9), f(y), f(x), f(y + 9), f(x - 9), f(y), _label(x + 13, y + 4, "You are here (believed)", "dr-label dr-label-believed", "start")))


def _fixes(fr, fixes):
    out = []
    for fx in fixes:
        x, y = fr.xy(fx)
        out.append('<rect class="dr-fix" x="%s" y="%s" width="9" height="9" transform="rotate(45 %s %s)"/>'
                   % (f(x - 4.5), f(y - 4.5), f(x), f(y)))
    return "".join(out)


def _par(fr, par_track):
    if not par_track:
        return ""
    return '<polyline class="dr-par-track" points="%s"/>' % fr.pts([(p[1], p[2]) for p in par_track])


def render_chart(chart, est=None, marks=(), sailed_legs=0, true_track=None, discovered=(), reveal=False,
                 point=None, believed=None, fixes=(), par_track=None):
    """The whole chart as one svg string.

    est        the estimated track [[t, x, y, fixed], ...] (the player's own plot)
    marks      leg-end positions for the numbered markers
    true_track the true track [[t, x, y], ...]; pass it ONLY when the passage is being revealed
    discovered hazard ids the crew has found (uncharted ones then appear)
    reveal     True on the reveal: show every hazard, marked or not
    point      the ruler's marked point, believed the believed position in Watch-by-watch, fixes fix positions
    par_track  the authored plan's plotted track (a dotted line), drawn only after the player has asked to see it"""
    fr = Frame(chart)
    notes = chart_notes(chart, discovered)
    parts = [
        '<svg class="dr-chart" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" role="img" aria-labelledby="dr-chart-title dr-chart-desc" id="dr-chart">'
        % (f(fr.width), f(fr.height)),
        '<title id="dr-chart-title">%s</title>' % escape("Chart of " + chart["name"]),
        '<desc id="dr-chart-desc">%s</desc>' % escape(" ".join(notes)),
        _defs(),
        '<rect class="dr-sea" x="%s" y="%s" width="%s" height="%s"/>' % (f(LEFT), f(TOP), f(PX), f(PX)),
        _grid(fr), _land(chart, fr), _currents(chart, fr), _hazards(chart, fr, discovered, reveal), _landmarks(chart, fr),
        _scale_bar(fr), _wind(chart, fr), _rose(fr), _endpoints(chart, fr),
    ]
    parts.append(_par(fr, par_track))
    if est:
        parts.append(_plan(fr, est, marks, sailed_legs))
    if true_track:
        parts.append(_truth(fr, true_track, est or []))
    parts.append(_fixes(fr, fixes))
    parts.append(_point(fr, point))
    parts.append(_believed(fr, believed))
    parts.append('</svg>')
    return "".join(parts)


# --- the chart in words (the accessible twin of the picture, also its <desc>) ------------------------
def tide_table(zone, lo=0.0, hi=24.0):
    """The stream's timetable as words (clock hours lo..hi): when it peaks, when it slackens, which way it runs."""
    tide = zone["tide"]
    period, phase = tide["period"], tide["phase"]
    out = []
    for k in range(-3, 4):
        base = phase + k * period
        for hour, what in ((base, "peaks toward %s (%s)" % (deg3(zone["set"]), range_text(zone["drift_range"]))),
                           (base + period / 4.0, "is slack"),
                           (base + period / 2.0, "peaks toward %s (%s)" % (deg3(zone["set"] + 180.0), range_text(zone["drift_range"]))),
                           (base + 3 * period / 4.0, "is slack")):
            if lo <= hour <= hi:
                out.append((hour, what))
    out.sort()
    return ["Hour %g: the stream %s." % (h, w) for h, w in out]


def chart_notes(chart, discovered=()):
    notes = [
        "Start at %g east, %g north. The flag is at %g east, %g north; arrive within %g nm of it. Deadline %g hours. Ship speed %s."
        % (chart["start"][0], chart["start"][1], chart["dest"][0], chart["dest"][1], chart["arrival_radius"], chart["deadline"],
           range_text(chart["speeds"])),
    ]
    for land in chart.get("land", ()):
        xs = [p[0] for p in land["poly"]]
        ys = [p[1] for p in land["poly"]]
        notes.append("Land: %s, between %g and %g east and %g and %g north." % (land["name"], min(xs), max(xs), min(ys), max(ys)))
    for hz in chart.get("hazards", ()):
        if hz.get("charted", True) or hz["id"] in set(discovered):
            notes.append("%s: a %s at %g east, %g north, %g nm across." % (hz["name"], hz["kind"], hz["x"], hz["y"], hz["r"] * 2))
    for zone in chart.get("currents", ()):
        x0, y0, x1, y1 = zone["rect"]
        text = ("Current %s: sets toward %s (%s), %s, between %g and %g east and %g and %g north."
                % (zone.get("name", zone["id"]), deg3(zone["set"]), "tidal stream" if zone.get("tide") else "steady",
                   range_text(zone["drift_range"]) + (" at its peak" if zone.get("tide") else ""), max(0, x0), x1, max(0, y0), y1))
        notes.append(text)
        if zone.get("tide"):
            notes.extend(tide_table(zone, chart.get("start_hour", 0.0), chart.get("start_hour", 0.0) + chart["deadline"] + 1))
    if chart.get("wind"):
        notes.append("Wind from %s, %s. It pushes the ship sideways a little (leeway)." % (deg3(chart["wind"]["from"]), range_text(chart["wind"]["range"])))
    if chart.get("compass"):
        lo, hi = chart["compass"]["range"]
        notes.append("Compass error: %s degrees %s of true. True heading = compass heading + error." % (
            "%g to %g" % (abs(lo), abs(hi)) if lo != hi else "%g" % abs(lo), "east" if mid_sign(lo, hi) >= 0 else "west"))
    for lm in chart.get("landmarks", ()):
        notes.append("%s: a %s at %g east, %g north, seen from up to %g nm%s." % (
            lm["name"], lm["kind"], lm["x"], lm["y"], lm["visible"], " (not in fog)" if chart.get("fog") else ""))
    if chart.get("fog"):
        notes.append("Fog: landmarks cannot be seen, and some dangers are not on the chart.")
    return notes


def mid_sign(lo, hi):
    return (lo + hi) / 2.0
