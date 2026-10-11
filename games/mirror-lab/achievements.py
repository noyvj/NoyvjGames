"""Mirror Lab -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the save).

Everything is computed from the benches the player has cleared, never stored separately, so a loaded save and a played one can never
disagree. Every one can be earned on every difficulty (the level only changes how much the hint ladder says), none is hidden, none rewards
time or how often you come back, and every one shows a number. A cleared bench keeps its best (fewest-piece) layout, and the facts below are
read from those layouts by tracing them again, so they are exactly as true as the bench clears are.
"""

import benches
import optics
import progress

CHAPTER_SIZE = 8
TOTAL = len(benches.ALL_BENCHES)
TURNS_NEEDED = 6

# (id, label, description, fact, need). `ch1` .. `ch5` are the benches cleared in that chapter.
ACHIEVEMENTS = (
    ("first_beam", "First Beam", "Clear your first bench.", "cleared", 1),
    ("ten_benches", "Ten Benches", "Clear 10 benches.", "cleared", 10),
    ("twenty_benches", "Twenty Benches", "Clear 20 benches.", "cleared", 20),
    ("all_forty", "All Forty", "Clear every bench.", "cleared", TOTAL),
    ("mirror_maker", "Mirror Maker", "Clear every bench in Flat Mirrors.", "ch1", CHAPTER_SIZE),
    ("splitting_hairs", "Splitting Hairs", "Clear every bench in Splitters.", "ch2", CHAPTER_SIZE),
    ("rainbow", "Rainbow", "Clear every bench in Prisms.", "ch3", CHAPTER_SIZE),
    ("clear_filter", "Clear Filter", "Clear every bench in Filters and Decoys.", "ch4", CHAPTER_SIZE),
    ("the_long_run", "The Long Run", "Clear every bench in The Long Run.", "ch5", CHAPTER_SIZE),
    ("fewest_pieces", "Fewest Pieces", "Earn 5 Fewest pieces tags.", "fewest", 5),
    ("fewest_pieces_again", "Fewest Pieces Again", "Earn 20 Fewest pieces tags.", "fewest", 20),
    ("double_bounce", "Double Bounce", "Clear a bench where one beam turns %d times." % TURNS_NEEDED, "turns", TURNS_NEEDED),
    ("light_both", "Light Both", "Clear a bench where a prism lights both an S and an L sensor.", "light_both", 1),
    ("quiet_decoys", "Quiet Decoys", "Clear a bench that has a decoy, keeping it dark.", "decoy", 1),
)
IDS = tuple(a[0] for a in ACHIEVEMENTS)
TOTAL_ACHIEVEMENTS = len(ACHIEVEMENTS)

_MEMO = {}            # (bench id, layout) -> (turns, light_both, decoy); a pure function of its key, so it is safe to keep


def _layout_key(bench_id, layout):
    return (bench_id, tuple(sorted(layout.items())))


def _bench_facts(bench, layout):
    """(most turns one beam made, a prism lit an S and an L sensor, the bench has a decoy), from tracing the cleared layout."""
    key = _layout_key(bench.id, layout)
    found = _MEMO.get(key)
    if found is None:
        tr = optics.trace(bench.board, layout)
        lit_kinds = {bench.board.sensors[cell] for cell in tr.lit}
        prism = any(piece == "prism" for piece, _state in layout.values())
        found = (tr.max_turns, bool(prism and tr.ok and "S" in lit_kinds and "L" in lit_kinds), bool(tr.ok and bench.board.decoys))
        if len(_MEMO) > 4000:
            _MEMO.clear()
        _MEMO[key] = found
    return found


def facts(cleared):
    """The numbers every achievement is read from, for a dict of cleared benches (bench id -> best layout)."""
    out = {"cleared": 0, "fewest": 0, "turns": 0, "light_both": 0, "decoy": 0}
    for number in range(1, len(benches.CHAPTERS) + 1):
        out["ch%d" % number] = progress.chapter_cleared(cleared, number)
    for bench in benches.ALL_BENCHES:
        layout = cleared.get(bench.id)
        if layout is None:
            continue
        out["cleared"] += 1
        if len(layout) <= bench.par:
            out["fewest"] += 1
        turns, both, decoy = _bench_facts(bench, layout)
        out["turns"] = max(out["turns"], turns)
        out["light_both"] += 1 if both else 0
        out["decoy"] += 1 if decoy else 0
    return out


def earned(fact_values):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need in ACHIEVEMENTS if fact_values.get(fact, 0) >= need]


def view(fact_values):
    out = []
    for i, label, description, fact, need in ACHIEVEMENTS:
        have = min(fact_values.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need, "have": have, "need": need})
    return out


def summary(fact_values):
    n = len(earned(fact_values))
    return {"earned": n, "total": TOTAL_ACHIEVEMENTS, "text": "%d of %d achievements earned" % (n, TOTAL_ACHIEVEMENTS)}
