"""Pocket Bazaar -- a text harness for the board: play it from a script, no page needed.

    >>> board, log = play("crate P\\ncrate P\\nmerge 0 1\\nshow")

Commands (one per line, '#' starts a comment): crate P|T|C|S|D, merge A B (a merge, or a move/swap when the two do
not merge), sell A, broom A, show. The log has one line per command. The coin counter in the log is the sell
money only; customers and the day loop live in game.py.
"""

from board import Board
from goods import LETTER_TO_FAMILY, sell_value


def play(script, board=None, rules=None):
    board = board or Board()
    log = []
    coins = 0
    for raw in script.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        cmd = parts[0]
        if cmd == "crate":
            family = LETTER_TO_FAMILY.get(parts[1].upper()) if len(parts) > 1 else None
            at = board.place((family, 1)) if family else None
            log.append(f"crate {parts[1]} -> cell {at}" if at is not None else "crate refused: the board is full")
        elif cmd == "merge":
            result = board.drop(int(parts[1]), int(parts[2]), rules)
            if not result.ok:
                log.append("refused: " + result.reason)
            elif result.links:
                log.append(f"merge -> {result.links} links")
            else:
                log.append("moved")
        elif cmd == "sell":
            index = int(parts[1])
            good = board.cells[index] if board.valid_index(index) else None
            value = board.sell(index)
            if value is not None:
                coins += value
                log.append(f"sold {good} for {sell_value(good)} (total {coins})")
            else:
                log.append("sell refused: nothing there")
        elif cmd == "broom":
            log.append("swept" if board.broom(int(parts[1])) else "broom refused: nothing there")
        elif cmd == "show":
            log.append(board.render())
        else:
            raise ValueError(f"unknown command {cmd!r}")
    return board, log
