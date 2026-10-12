#!/usr/bin/env python3
"""Build the frozen chart modules (charts_s1.py, charts_s2.py, ...) from data/snapshot.json and tools/chart_specs.py.

Usage: python3 tools/build_charts.py           (rewrites every charts_sN.py; prints a proof table)

For each constellation: take the traditional figure from the snapshot, trim it as the spec says, project it flat, round to whole numbers,
choose the candidate lines, derive the clues (tools/figures.py) and PROVE them: exactly one valid figure by the exhaustive solver, the same
count from the independent second counter, and the unique figure is the traditional one. Nothing is written for a chart that fails.
"""

import datetime
import json
import os
import pprint
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import chart_specs  # noqa: E402
import figures  # noqa: E402
import sky  # noqa: E402

GREEK = {"Alp": "Alpha", "Bet": "Beta", "Gam": "Gamma", "Del": "Delta", "Eps": "Epsilon", "Zet": "Zeta", "Eta": "Eta", "The": "Theta",
         "Iot": "Iota", "Kap": "Kappa", "Lam": "Lambda", "Mu": "Mu", "Nu": "Nu", "Xi": "Xi", "Omi": "Omicron", "Pi": "Pi", "Rho": "Rho",
         "Sig": "Sigma", "Tau": "Tau", "Ups": "Upsilon", "Phi": "Phi", "Chi": "Chi", "Psi": "Psi", "Ome": "Omega"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MODULE_NAMES = ["charts_s%d.py" % (i + 1) for i in range(len(chart_specs.SEASONS))]


def star_name(row, genitive):
    """A proper name if the star has one, else its Bayer letter, else its Flamsteed number, in the usual 'Zeta Orionis' form."""
    if row["proper"]:
        return row["proper"]
    bayer = row["bayer"]
    if bayer:
        base, _dash, sup = bayer.partition("-")
        word = GREEK.get(base, base)
        return "%s%s %s" % (word, "-" + sup if sup else "", genitive)
    if row["flam"]:
        return "%s %s" % (row["flam"], genitive)
    return "HIP %s" % row["hip"]


def best_month(ra_hours):
    """The month when the constellation stands highest in the evening (9 pm local time) for northern middle latitudes: the Sun's right
    ascension then is the constellation's minus nine hours."""
    day = 80 + (((ra_hours - 9.0) % 24.0) / 24.0) * 365.25
    day = int(day) % 365
    start = datetime.date(2001, 1, 1) + datetime.timedelta(days=day)
    return MONTHS[start.month - 1]


def build_chart(snap, spec, season_index, number):
    code = spec["code"]
    fig_hip = figures.figure_edges(snap["lines"][code], spec.get("drop", ()), spec.get("cap"), snap["stars"])
    hips = sorted({h for e in fig_hip for h in e})
    proj, (ra0, dec0) = figures.project(snap["stars"], hips)
    pix, width, height, (ox, oy), scale = figures.layout(proj, sorted(fig_hip))
    # letters run left to right
    hips.sort(key=lambda h: (pix[h][0], pix[h][1]))
    index = {h: i for i, h in enumerate(hips)}
    pts = [pix[h] for h in hips]
    fig = {(min(index[a], index[b]), max(index[a], index[b])) for a, b in fig_hip}
    cand = figures.candidates(pts, fig)
    cross_ok = figures.crossing_pairs(pts, fig)          # only the Southern Cross: its two traditional lines cross, and the chart says so
    stars = []
    for h in hips:
        row = dict(snap["stars"][str(h)], hip=h)
        stars.append({"hip": h, "x": pix[h][0], "y": pix[h][1], "mag": round(float(row["mag"]), 2),
                      "name": star_name(row, spec["genitive"]), "proper": bool(row["proper"]),
                      "bayer": ("%s %s" % (row["bayer"], row["con"])) if row["bayer"] else ""})
    chart = sky.Chart(dict({"id": spec["id"], "stars": stars, "edges": cand, "clues": {}}, **({"cross_ok": cross_ok} if cross_ok else {})))
    degree, must, never, level = figures.best_clues(chart, fig)
    if level == 0:
        raise SystemExit("%s: no clue set can be finished by line logic" % spec["id"])
    proven = chart.with_clues(degree, must, never)
    figure_idx = {chart.index[e] for e in fig}
    found = sky.solutions(proven, 3)
    assert len(found) == 1 and set(found[0]) == figure_idx, "%s is not uniquely the traditional figure" % spec["id"]
    assert sky.count_by_stars(proven, 3) == 1, "%s: the second counter disagrees" % spec["id"]
    brightest = min(stars, key=lambda s: (s["mag"], s["name"]))
    if spec.get("south"):
        best = "best seen on evenings around %s (from the southern hemisphere; low or out of sight from the north)" % best_month(ra0)
    else:
        best = spec.get("best") or "best seen on evenings around %s (from the northern middle latitudes)" % best_month(ra0)
    out = {
        "id": spec["id"], "season": season_index, "number": number, "code": code,
        "name": spec["name"], "meaning": spec["meaning"], "note": spec["note"], "best": best,
        "brightest": {"name": brightest["name"], "mag": brightest["mag"]},
        "w": width, "h": height,
        "stars": stars,
        "edges": [list(e) for e in cand],
        "figure": [list(e) for e in sorted(fig)],
        "clues": {"degree": dict(sorted(degree.items())), "must": [list(e) for e in sorted(must)], "never": [list(e) for e in sorted(never)]},
        "logic": level,
        "source": {"stars": "HYG star database v4.1 (github.com/astronexus/HYG-Database)",
                   "figure": "Stellarium modern sky culture, the IAU constellation figures (stellarium.org)", "read": snap["read"]},
        "atlas": {"ra": round(ra0, 2), "dec": round(dec0, 1), "ox": ox, "oy": oy, "scale": round(scale, 1)},
    }
    if cross_ok:
        out["cross_ok"] = [[list(a), list(b)] for a, b in cross_ok]
    return out


def main():
    snap = json.load(open(os.path.join(ROOT, "data", "snapshot.json"), encoding="utf-8"))
    for s_index, season in enumerate(chart_specs.SEASONS):
        built = []
        for spec in season["charts"]:
            built.append(build_chart(snap, spec, s_index, 0))
        built.sort(key=lambda c: (len(c["stars"]), c["name"]))
        for n, c in enumerate(built, start=1):
            c["number"] = n
        header = ('"""Constellations, season %d: %s (%d charts). GENERATED by tools/build_charts.py from data/snapshot.json (read %s) and '
                  'tools/chart_specs.py; do not edit by hand.\n\nEach chart: real star positions projected flat onto a %d wide canvas (whole numbers), the '
                  'candidate lines, the traditional figure, and the clues that make that figure the only valid one.\n"""\n\n'
                  % (s_index + 1, season["name"], len(built), snap["read"], figures.CANVAS_W))
        body = "SEASON = %s\n\nCHARTS = %s\n" % (
            pprint.pformat({"id": season["id"], "name": season["name"], "blurb": season["blurb"]}, width=150, sort_dicts=False),
            pprint.pformat(built, width=170, sort_dicts=False, compact=True))
        with open(os.path.join(ROOT, MODULE_NAMES[s_index]), "w", encoding="utf-8") as f:
            f.write(header + body)
        for c in built:
            print("%-16s %2d stars %2d lines  numbers %2d  must %d never %d  logic %d  %s" % (
                c["id"], len(c["stars"]), len(c["edges"]), len(c["clues"]["degree"]), len(c["clues"]["must"]), len(c["clues"]["never"]), c["logic"], c["best"]))
    print("wrote", ", ".join(MODULE_NAMES))


if __name__ == "__main__":
    main()
