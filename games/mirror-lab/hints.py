"""Mirror Lab -- the hint ladder, built on the bench's stored (proved) solution. Three rungs per bench, all free, none touching a bench's
status or any record; each opens only when the player asks:

  1 Nudge   which kind of piece matters most here and roughly where on the bench (an area, never a cell)
  2 Hint    one piece of the solution, the first one the beam needs, drawn as a ghost on its cell and described in words
  3 Answer  the whole stored solution drawn as ghosts, with a "Place them" button (the page asks first, except on Easy)

Difficulty (AN-17): Normal is the ladder above. Easy opens the nudge and the hint together on the first press and "Place them" needs no
confirm. Hard has no third rung. Everything is a pure function of the bench and the layout, so the same bench always gives the same hints."""

import optics

KEY_ORDER = ("prism", "splitter", "filter_s", "filter_l", "absorber")      # the piece kinds worth naming in a nudge, most telling first
ROW_WORDS = ("top", "middle", "bottom")
COL_WORDS = ("left", "middle", "right")


def area_words(bench, r, c):
    """Where on the bench a cell is, as a short phrase that reads after "Look": "in the top left of the bench", "on the left of the bench"."""
    v = min(2, r * 3 // bench.board.h)
    h = min(2, c * 3 // bench.board.w)
    if v == 1 and h == 1:
        return "in the middle of the bench"
    if v == 1:
        return "on the %s of the bench" % COL_WORDS[h]
    if h == 1:
        return "along the %s of the bench" % ROW_WORDS[v]
    return "in the %s %s of the bench" % (ROW_WORDS[v], COL_WORDS[h])


def kind_name(piece):
    """A piece kind in running text: "mirror", "S filter" (the letter stays a capital)."""
    return optics.piece_name(piece)


def _article(name):
    return "an" if name[0] in "aeiouSL" and (name[0] in "aeiou" or name[1] == " ") else "a"


def ordered_solution(bench):
    """The stored solution's pieces in the order the beam first needs them: trace with every unplaced solution cell held back, take the held
    cell nearest the emitter (ties by row, then column), place it, repeat. Deterministic."""
    remaining = {(r, c): (p, s) for r, c, p, s in bench.solution}
    er, ec, _d = bench.board.emitters[0]
    placed, out = {}, []
    while remaining:
        tr = optics.trace(bench.board, placed, halt=frozenset(remaining))
        pending = [cell for cell in tr.pending if cell in remaining] or list(remaining)
        cell = min(pending, key=lambda x: (abs(x[0] - er) + abs(x[1] - ec), x))
        piece, state = remaining.pop(cell)
        placed[cell] = (piece, state)
        out.append((cell[0], cell[1], piece, state))
    return out


def _key_piece(bench, order):
    for kind in KEY_ORDER:
        for r, c, piece, _s in order:
            if piece == kind:
                return r, c, piece
    r, c, piece, _s = order[0]
    return r, c, piece


def nudge_text(bench):
    order = ordered_solution(bench)
    r, c, piece = _key_piece(bench, order)
    name = kind_name(piece)
    where = area_words(bench, r, c)
    if piece == "mirror":
        return "Follow the beam from the emitter. The first piece it needs is a mirror, %s." % where
    return "This bench needs %s %s. Look %s." % (_article(name), name, where)


def piece_line(item):
    r, c, piece, state = item
    words = ""
    if piece == "mirror":
        words = ", slash" if state == 0 else ", backslash"
    elif piece == "prism":
        words = ", S beam leaves on the %s of its travel" % ("left" if state == 0 else "right")
    return "%s at %s%s" % (optics.PIECE_LABEL[piece], optics.cell_name(r, c), words)


def lower_first(text):
    return text if text[:2] in ("S ", "L ") else text[0].lower() + text[1:]


def hint_text(bench):
    first = ordered_solution(bench)[0]
    return "Try this: %s. It is drawn as a dotted ghost on the bench." % lower_first(piece_line(first))


def answer_lines(bench):
    return [piece_line(item) for item in ordered_solution(bench)]


def rung_cap(difficulty):
    """The last rung on offer: Hard has no answer step."""
    return 2 if difficulty == "hard" else 3


def next_rung(rung, difficulty):
    """The rung one press opens from `rung`, or None when there is nothing more to open. Easy's first press opens rungs 1 and 2 together."""
    cap = rung_cap(difficulty)
    if rung >= cap:
        return None
    if difficulty == "easy" and rung == 0:
        return 2
    return rung + 1


def ghost_items(bench, rung):
    """The pieces to draw as ghosts at `rung` (a list of (r, c, piece, state))."""
    if rung >= 3:
        return ordered_solution(bench)
    if rung == 2:
        return ordered_solution(bench)[:1]
    return []


def view(bench, rung, difficulty="normal"):
    cap = rung_cap(difficulty)
    rung = max(0, min(rung, cap))
    out = {"rung": rung, "max": cap, "nudge": "", "hint": "", "answer": False, "answer_lines": [], "can_ask": rung < cap, "difficulty": difficulty,
           "ghosts": [{"r": r, "c": c, "piece": p, "state": s, "words": piece_line((r, c, p, s))} for r, c, p, s in ghost_items(bench, rung)]}
    if rung >= 1:
        out["nudge"] = nudge_text(bench)
    if rung >= 2:
        out["hint"] = hint_text(bench)
    if rung >= 3:
        out["answer"] = True
        out["answer_lines"] = answer_lines(bench)
    return out
