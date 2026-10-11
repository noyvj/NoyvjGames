"""Mirror Lab -- one bench: the board, the tray and the frozen proof data."""

import optics


class Bench:
    def __init__(self, data, chapter, number):
        self.id = data["id"]
        self.name = data["name"]
        self.chapter = chapter
        self.number = number                      # 1 to 8 inside its chapter
        self.rows = tuple(data["rows"])
        self.board = optics.Board(self.rows)
        self.tray = dict(data["tray"])
        self.solution = tuple(tuple(x) for x in data["solution"])
        self.par = data["par"]                    # the fewest pieces any solution uses (the "Fewest pieces" tag)
        self.count = data["count"]                # how many distinct solutions the solver found
        self.line = data["line"]                  # the operator's dry log line, shown when the bench is cleared

    @property
    def unique(self):
        return self.count == 1

    @property
    def tray_size(self):
        return sum(self.tray.values())

    def solution_layout(self):
        return {(r, c): (piece, state) for r, c, piece, state in self.solution}
