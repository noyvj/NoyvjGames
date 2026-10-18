import boards
import hints


def test_exits_counts_open_neighbors_on_a_plain_board():
    """Normal case 1: a cell in Deck 1 (no mixers) counts only non-port neighbors."""
    b = boards.BY_ID[boards.ORDER[0]]
    for y in range(len(b.rows)):
        for x in range(len(b.rows[0])):
            if (x, y) not in b.port_at and (x, y) not in b.mixers:
                count = hints.exits(b, (x, y))
                expected = sum(1 for nb in b.neighbours((x, y))
                               if nb not in b.port_at and nb not in b.mixers)
                assert count == expected
                break


def test_exits_skips_mixers_on_a_board_with_mixers():
    """Normal case 2: a cell next to a mixer does not count the mixer as an exit."""
    b = None
    for bid in boards.ORDER:
        if boards.BY_ID[bid].mixers:
            b = boards.BY_ID[bid]
            break
    assert b is not None, "Expected at least one board with mixers"

    for y in range(len(b.rows)):
        for x in range(len(b.rows[0])):
            if (x, y) not in b.port_at and (x, y) not in b.mixers:
                neighbors = list(b.neighbours((x, y)))
                has_mixer_neighbor = any(nb in b.mixers for nb in neighbors)
                if has_mixer_neighbor:
                    count = hints.exits(b, (x, y))
                    expected = sum(1 for nb in neighbors
                                   if nb not in b.port_at and nb not in b.mixers)
                    assert count == expected
                    break
        else:
            continue
        break


def test_exits_handles_boundary_cells():
    """Edge case: a cell on the board edge has fewer than 4 neighbors, exits() must not crash."""
    b = boards.BY_ID[boards.ORDER[0]]
    corner = (0, 0)
    if corner in b.port_at or corner in b.mixers:
        corner = (len(b.rows[0]) - 1, len(b.rows) - 1)
    count = hints.exits(b, corner)
    expected = sum(1 for nb in b.neighbours(corner)
                   if nb not in b.port_at and nb not in b.mixers)
    assert count == expected
    assert count < 4
