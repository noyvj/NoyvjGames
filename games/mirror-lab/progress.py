"""Mirror Lab -- progress is a function of the cleared benches; nothing here counts time.

`cleared` is a dict bench id -> the best clearing layout, {(row, col): (piece, state)}, so the number of pieces used is its length."""

import benches


def chapter_cleared(cleared, number):
    return sum(1 for b in benches.CHAPTERS[number - 1]["benches"] if b.id in cleared)


def chapter_open(cleared, number):
    """Chapter 1 is always open; chapter n+1 opens when 5 of chapter n are cleared. Once open it stays open (clearing never goes down)."""
    if number <= 1:
        return True
    if number > len(benches.CHAPTERS):
        return False
    return chapter_cleared(cleared, number - 1) >= benches.OPEN_AT or chapter_cleared(cleared, number) > 0


def bench_open(cleared, bench_id):
    bench = benches.BY_ID.get(bench_id)
    return bench is not None and chapter_open(cleared, bench.chapter)


def fewest_tags(cleared):
    return sum(1 for bid, layout in cleared.items() if bid in benches.BY_ID and len(layout) <= benches.BY_ID[bid].par)


def sensors_lit(cleared):
    """Needed sensors lit on the benches cleared so far (each bench counts its own sensors once)."""
    return sum(len(benches.BY_ID[bid].board.required) for bid in cleared if bid in benches.BY_ID)


def totals(cleared):
    return {"benches": len(benches.ALL_BENCHES), "cleared": len(cleared), "sensors": sensors_lit(cleared), "fewest": fewest_tags(cleared),
            "chapters": len(benches.CHAPTERS), "chapters_cleared": sum(1 for ch in benches.CHAPTERS if chapter_cleared(cleared, ch["number"]) == len(ch["benches"]))}


def next_bench(cleared, bench_id):
    """The next open bench after `bench_id` that is not yet cleared, going round once; None when every open bench is cleared."""
    order = benches.ORDER
    if bench_id not in order:
        return None
    start = order.index(bench_id)
    for other in order[start + 1:] + order[:start]:
        if other not in cleared and bench_open(cleared, other):
            return other
    return None
