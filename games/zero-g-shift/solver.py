"""Zero-G Shift -- the solver: breadth-first search over every position a bay can reach.

`Analysis(bay)` walks the whole graph of positions from the start (a position is the player's cell and the crates' cells),
then runs the search backwards from every cleared position. From that one table it answers, instantly and with no
guessing: the par (shortest solution), how many shortest solutions there are, whether a position can still be won, the
best next move, and one stored shortest line. The same code serves the page (hints, "Can I still win?") and the proofs in
tests. It never reads a clock or a random source; moves are tried in the fixed order Up, Down, Left, Right.
"""

import rules

MAX_STATES = 400000
ORDER = rules.DIRS


class Analysis:
    def __init__(self, bay, cap=MAX_STATES):
        self.bay = bay
        self.cap = cap
        self.index = {bay.start: 0}
        self.states = [bay.start]
        self.edges = []                # edges[i] = (U, D, L, R) as state numbers or -1
        self.complete = True
        step = rules.step
        index, states = self.index, self.states
        i = 0
        while i < len(states):
            state = states[i]
            row = []
            for d in ORDER:
                out = step(bay, state, d)
                if out is None:
                    row.append(-1)
                    continue
                nxt = out[0]
                j = index.get(nxt)
                if j is None:
                    if len(states) >= cap:
                        self.complete = False
                        row.append(-1)
                        continue
                    j = len(states)
                    index[nxt] = j
                    states.append(nxt)
                row.append(j)
            self.edges.append(tuple(row))
            i += 1
        n = len(states)
        reverse = [[] for _ in range(n)]
        for i, row in enumerate(self.edges):
            for j in row:
                if j >= 0:
                    reverse[j].append(i)
        cleared = bay.cleared
        self.dist = [-1] * n
        queue = [i for i in range(n) if cleared(states[i])]
        for i in queue:
            self.dist[i] = 0
        head = 0
        while head < len(queue):
            j = queue[head]
            head += 1
            for i in reverse[j]:
                if self.dist[i] < 0:
                    self.dist[i] = self.dist[j] + 1
                    queue.append(i)
        self.par = self.dist[0] if self.dist[0] > 0 else None
        self._counts = None

    # ---- queries -------------------------------------------------------------------------------------------------
    @property
    def size(self):
        return len(self.states)

    def distance(self, state):
        """Shortest number of moves to clear from `state`, or None when it can no longer be won (or is unknown)."""
        i = self.index.get(state)
        if i is None or self.dist[i] < 0:
            return None
        return self.dist[i]

    def known(self, state):
        return state in self.index

    def best_move(self, state):
        """The first move (in the fixed order) of a shortest line from `state`, or None."""
        i = self.index.get(state)
        if i is None or self.dist[i] <= 0:
            return None
        for d, j in zip(ORDER, self.edges[i]):
            if j >= 0 and self.dist[j] == self.dist[i] - 1:
                return d
        return None

    def line_from(self, state):
        """One shortest line from `state`, as a string of moves ('' when already clear, None when it cannot be won)."""
        if self.distance(state) is None:
            return None
        out = []
        i = self.index[state]
        while self.dist[i] > 0:
            for d, j in zip(ORDER, self.edges[i]):
                if j >= 0 and self.dist[j] == self.dist[i] - 1:
                    out.append(d)
                    i = j
                    break
        return "".join(out)

    def optimal_count(self):
        """How many different shortest move strings clear the bay from the start."""
        if self.par is None:
            return 0
        if self._counts is None:
            order = sorted(range(len(self.states)), key=lambda i: self.dist[i] if self.dist[i] >= 0 else 10 ** 9)
            counts = [0] * len(self.states)
            for i in order:
                if self.dist[i] == 0:
                    counts[i] = 1
                elif self.dist[i] > 0:
                    counts[i] = sum(counts[j] for j in self.edges[i] if j >= 0 and self.dist[j] == self.dist[i] - 1)
            self._counts = counts
        return self._counts[0]

    def all_optimal_lines(self, limit=10):
        """Every shortest line from the start, up to `limit` of them."""
        out = []
        stack = [(0, "")]
        while stack and len(out) < limit:
            i, line = stack.pop()
            if self.dist[i] == 0:
                out.append(line)
                continue
            for d, j in reversed(list(zip(ORDER, self.edges[i]))):
                if j >= 0 and self.dist[j] == self.dist[i] - 1:
                    stack.append((j, line + d))
        return sorted(out)

    def can_win_all_ways(self):
        """True when no reachable position is a dead end (a bay you can never get stuck in)."""
        return all(d >= 0 for d in self.dist)

    def dead_count(self):
        return sum(1 for d in self.dist if d < 0)

    def longest_slide_available(self):
        """The longest single slide (yours or a crate's) over every move from every reachable position."""
        best = 0
        for state in self.states:
            for d in ORDER:
                out = rules.step(self.bay, state, d)
                if out and out[1]["longest"] > best:
                    best = out[1]["longest"]
        return best


_CACHE = {}


def analysis(bay):
    """The cached analysis of a bay (one per bay id and rows)."""
    key = (bay.id, bay.rows, bay.door)
    found = _CACHE.get(key)
    if found is None:
        found = _CACHE[key] = Analysis(bay)
    return found


def first_broken_move(bay, line):
    """For a line of moves that ended in a position that cannot be won: the 1-based number of the move that made it
    unwinnable (the first prefix that cannot be won), or None when the whole line is still winnable. A prefix that can
    be won stays that way going backwards, so a binary search finds the edge."""
    played = rules.replay(bay, line)
    if played is None:
        return None
    states = played[0]
    a = analysis(bay)
    if a.distance(states[-1]) is not None:
        return None
    if a.distance(states[0]) is None:         # the bay itself cannot be cleared (never true of an authored bay)
        return 0
    low, high = 0, len(states) - 1          # states[low] is winnable, states[high] is not
    while high - low > 1:
        mid = (low + high) // 2
        if a.distance(states[mid]) is None:
            high = mid
        else:
            low = mid
    return high
