"""Mirror Lab -- the Optics Bench Log: a shelf with one page per kind of piece (a page fills the first time you place that piece) and
a circuit card for every bench (a card fills when the bench is cleared). States only go up: nothing here is ever taken away."""

import benches
import optics
import progress
import render

# (family id, title, the pieces that fill it, what it does, in plain words)
SHELF = (
    ("mirror", "Mirror", ("mirror",),
     "Turns a beam a quarter turn. Slash (/) and backslash (\\) are the two ways round; tap a placed mirror to flip it. The beam keeps its kind."),
    ("splitter", "Splitter", ("splitter",),
     "Lets the beam carry straight on and sends a copy off to the left of its travel. One piece, two paths. It does not flip."),
    ("prism", "Prism", ("prism",),
     "Splits a white beam into a short (S) beam and a long (L) beam, one turning left and one turning right. Tap it to swap the sides. "
     "A beam that is already S or L cannot split again: it only bends towards its own side. (A simplified prism: two beams, not a rainbow.)"),
    ("filter", "Filter", ("filter_s", "filter_l"),
     "An S filter turns a white beam into an S beam, lets an S beam through and stops an L beam. An L filter does the same for L."),
    ("absorber", "Absorber", ("absorber",), "Stops any beam that enters it."),
)
FAMILY_OF = {piece: fid for fid, _t, pieces, _w in SHELF for piece in pieces}


def families_used(placed_pieces):
    """The shelf pages a set of piece names fills (an iterable of piece names)."""
    return {FAMILY_OF[p] for p in placed_pieces if p in FAMILY_OF}


def shelf(used_families):
    out = []
    for fid, title, pieces, words in SHELF:
        filled = fid in used_families
        out.append({"id": fid, "title": title, "filled": filled, "text": words if filled else "An empty page. Use this piece on a bench and it fills in.",
                    "icon": render.piece_icon(pieces[0])})
    return out


def cards(cleared):
    """One circuit card per bench, in play order."""
    out = []
    for b in benches.ALL_BENCHES:
        layout = cleared.get(b.id)
        card = {"id": b.id, "name": b.name, "chapter": b.chapter, "number": b.number, "filled": layout is not None, "par": b.par,
                "locked": not _open(cleared, b)}
        if layout is not None:
            used = {}
            for piece, _state in layout.values():
                used[piece] = used.get(piece, 0) + 1
            card.update({"pieces": len(layout), "fewest": len(layout) <= b.par, "line": b.line,
                         "used": ", ".join("%d %s" % (n, optics.PIECE_LABEL[p].lower()) for p, n in sorted(used.items()))})
        out.append(card)
    return out


def _open(cleared, bench):
    return progress.chapter_open(cleared, bench.chapter)


def summary(used_families, cleared):
    return {"pages": len(used_families), "pages_total": len(SHELF), "cards": len(cleared), "cards_total": len(benches.ALL_BENCHES)}
