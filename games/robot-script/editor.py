"""Robot Script -- the structured list editor (engine side).

The player builds a program by putting instructions at a cursor. A *list address* names one list of instructions: a
tuple such as ("main",) or ("main", 2, 2) (the body of the block at index 2 of main; for an `if`, element 3 is the else
list). A *statement address* is a list address plus the statement's index. Every edit builds a candidate program and runs
it through dsl.check with the room's toolbox, so the editor can never hold something the interpreter cannot run.
Edits are undoable (the history is a session thing and is never saved).
"""

import dsl

HISTORY = 60


def parse_addr(text):
    """'main/2/2' -> ('main', 2, 2). Returns None for anything malformed."""
    if not isinstance(text, str) or not text:
        return None
    parts = text.split("/")
    if parts[0] not in dsl.ROUTINES:
        return None
    out = [parts[0]]
    for p in parts[1:]:
        if not p.isdigit():
            return None
        out.append(int(p))
    return tuple(out)


def fmt_addr(addr):
    return "/".join(str(p) for p in addr)


def get_list(prog, addr):
    """The list at a list address, or None if it does not exist."""
    if not addr or addr[0] not in prog or len(addr) % 2 == 0:
        return None
    items = prog[addr[0]]
    rest = addr[1:]
    for i in range(0, len(rest), 2):
        index, element = rest[i], rest[i + 1]
        if index >= len(items) or not isinstance(items[index], list) or element >= len(items[index]) \
                or not isinstance(items[index][element], list):
            return None
        items = items[index][element]
    return items


def _routine_of(addr):
    return addr[0]


class Editor:
    def __init__(self, prog=None, allow="F"):
        self.allow = allow
        self.prog = dsl.copy(prog) if prog else dsl.new_program()
        self.cursor = (("main",), len(self.prog["main"]))
        self.history = []
        self.last_error = ""

    # ---- helpers ---------------------------------------------------------------------------------------------------
    def _snapshot(self):
        self.history.append((dsl.copy(self.prog), self.cursor))
        del self.history[:-HISTORY]

    def _commit(self, candidate, cursor):
        reason = dsl.check(candidate, self.allow)
        if reason:
            self.last_error = reason
            return False
        self._snapshot()
        self.prog = candidate
        self.cursor = cursor
        self.last_error = ""
        return True

    def size(self):
        return dsl.size(self.prog)

    def is_empty(self):
        return self.size() == 0

    # ---- edits -----------------------------------------------------------------------------------------------------
    def insert(self, stmt):
        """Put `stmt` at the cursor. Returns True on success; on refusal `last_error` says why."""
        addr, index = self.cursor
        candidate = dsl.copy(self.prog)
        items = get_list(candidate, addr)
        if items is None:
            self.last_error = "That place no longer exists."
            return False
        index = min(index, len(items))
        items.insert(index, stmt)
        if isinstance(stmt, list) and stmt[0] in dsl.BLOCKS:
            cursor = (addr + (index, 2), 0)
        else:
            cursor = (addr, index + 1)
        return self._commit(candidate, cursor)

    def can_insert(self, stmt):
        """None when `stmt` could be inserted at the cursor now, else the reason it could not."""
        addr, index = self.cursor
        candidate = dsl.copy(self.prog)
        items = get_list(candidate, addr)
        if items is None:
            return "That place no longer exists."
        items.insert(min(index, len(items)), stmt)
        return dsl.check(candidate, self.allow)

    def set_cursor(self, addr, index):
        items = get_list(self.prog, addr)
        if items is None or not isinstance(index, int) or isinstance(index, bool) or not 0 <= index <= len(items):
            return False
        self.cursor = (addr, index)
        return True

    def go_routine(self, name):
        if name not in self.prog and name in dsl.ROUTINES:
            self.prog[name] = []
        if name not in dsl.ROUTINES or name not in self.prog:
            return False
        self.cursor = ((name,), len(self.prog[name]))
        return True

    def remove(self, addr):
        """Remove the statement at a statement address."""
        if len(addr) < 2:
            return False
        list_addr, index = addr[:-1], addr[-1]
        candidate = dsl.copy(self.prog)
        items = get_list(candidate, list_addr)
        if items is None or index >= len(items):
            self.last_error = "That step is already gone."
            return False
        del items[index]
        return self._commit(candidate, self._cursor_after_removal(list_addr, index))

    def _cursor_after_removal(self, list_addr, index):
        cur_addr, cur_index = self.cursor
        n = len(list_addr)
        if cur_addr == list_addr:
            return (cur_addr, cur_index - 1 if cur_index > index else cur_index)
        if cur_addr[:n] == list_addr and len(cur_addr) > n:
            j = cur_addr[n]
            if j == index:
                return (list_addr, index)
            if j > index:
                return (cur_addr[:n] + (j - 1,) + cur_addr[n + 1:], cur_index)
        return (cur_addr, cur_index)

    def move(self, addr, delta):
        list_addr, index = addr[:-1], addr[-1]
        candidate = dsl.copy(self.prog)
        items = get_list(candidate, list_addr)
        if items is None or not 0 <= index < len(items) or delta not in (-1, 1) or not 0 <= index + delta < len(items):
            return False
        items[index], items[index + delta] = items[index + delta], items[index]
        # the cursor goes to the gap after the moved statement, in its list
        return self._commit(candidate, (list_addr, index + delta + 1))

    def _statement(self, candidate, addr):
        items = get_list(candidate, addr[:-1])
        if items is None or addr[-1] >= len(items):
            return None
        return items[addr[-1]]

    def set_count(self, addr, n):
        candidate = dsl.copy(self.prog)
        stmt = self._statement(candidate, addr)
        if not isinstance(stmt, list) or stmt[0] != "rep":
            return False
        stmt[1] = n
        return self._commit(candidate, self.cursor)

    def set_cond(self, addr, cond):
        candidate = dsl.copy(self.prog)
        stmt = self._statement(candidate, addr)
        if not isinstance(stmt, list) or stmt[0] not in ("until", "if"):
            return False
        stmt[1] = cond
        return self._commit(candidate, self.cursor)

    def clear(self):
        if self.is_empty():
            return False
        self._snapshot()
        self.prog = dsl.new_program()
        self.cursor = (("main",), 0)
        return True

    def load(self, prog):
        """Replace the whole list (an answer or a saved best). Undoable."""
        reason = dsl.check(prog, self.allow)
        if reason:
            self.last_error = reason
            return False
        self._snapshot()
        self.prog = dsl.copy(prog)
        self.prog.setdefault("main", [])
        self.cursor = (("main",), len(self.prog["main"]))
        return True

    def undo(self):
        if not self.history:
            return False
        self.prog, self.cursor = self.history.pop()
        return True
