"""Mirror Lab -- plain-text descriptions of the bench, so everything the picture shows is also said in words (for the announcer line,
the sensor list and the screen-reader label). Nothing here changes the game."""

import optics

SENSOR_WORDS = {"A": "takes any beam", "S": "needs an S (short) beam", "L": "needs an L (long) beam", "X": "is a decoy and must stay dark"}
NEED_NAMES = {"A": "any", "S": "S", "L": "L", "X": "decoy"}


def sensors_count(lit, need):
    """"2 of 3 sensors" / "1 of 1 sensor"."""
    return "%d of %d sensor%s" % (lit, need, "" if need == 1 else "s")


def brief(bench):
    """One sentence on what to do and what is in the tray."""
    board = bench.board
    n = len(board.required)
    text = "Light %s sensor%s" % ("the" if n == 1 else "all %d" % n, "" if n == 1 else "s")
    if board.decoys:
        text += " and keep the decoy%s dark" % ("" if len(board.decoys) == 1 else "s")
    pieces = ", ".join("%d %s" % (count, optics.piece_name(p) + ("" if count == 1 else "s")) for p, count in sorted(bench.tray.items()))
    return "%s. Tray: %s." % (text, pieces)


def emitter_lines(board):
    return ["Emitter at %s sends a white beam %s." % (optics.cell_name(r, c), optics.DIR_NAMES[d]) for r, c, d in board.emitters]


def sensor_lines(board, tr):
    out = []
    for (r, c), need in sorted(board.sensors.items()):
        lit = (r, c) in tr.lit
        hit = (r, c) in tr.dark_hit
        if need == "X":
            state = "lit, which is wrong" if hit else "dark, good"
        else:
            kinds = tr.hits.get((r, c), [])
            state = "lit" if lit else ("reached by the wrong kind of beam" if kinds else "dark")
        out.append({"r": r, "c": c, "need": need, "lit": lit, "hit": hit, "words": "sensor, %s: %s" % (SENSOR_WORDS[need], state),
                    "text": "Sensor at %s %s: %s." % (optics.cell_name(r, c), SENSOR_WORDS[need], state)})
    return out


def bench_label(bench, tr, layout):
    n = len(bench.board.required)
    return "Optics bench %s, %d by %d. %s lit. %d piece%s placed." % (bench.name, bench.board.w, bench.board.h, sensors_count(len(tr.lit), n), len(layout), "" if len(layout) == 1 else "s")
