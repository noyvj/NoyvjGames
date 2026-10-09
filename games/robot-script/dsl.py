"""Robot Script -- programs as data, and as text.

A program is a dict of routines, `{"main": [stmt, ...], "A": [...], "B": [...]}` (A and B only when used).
A statement is one of:
    "F" "L" "R" "G" "P" "S"                 an action (forward, turn left, turn right, grab, place, switch)
    ["rep", n, [body]]                      repeat the body n times (2 to 9)
    ["until", cond, [body]]                 repeat the body until the condition is true (checked before each pass)
    ["if", cond, [then], [else]]            run `then` when the condition is true, otherwise `else`
    ["call", "A"]                           run a saved routine
A condition is one of CONDS, optionally with a leading "!" for "not".

Everything the player can build is checked here; the only untrusted entry is `from_text` (a save, a pasted list), so
it either returns a clean program or raises ValueError. Nothing in this module reads a clock or a random source.
"""

ACTIONS = ("F", "L", "R", "G", "P", "S")
ACTION_NAMES = {"F": "Forward", "L": "Turn left", "R": "Turn right", "G": "Pick up", "P": "Place", "S": "Switch"}
CONDS = ("blocked", "part", "socket", "switch", "carrying", "exit")
COND_NAMES = {"blocked": "the way is blocked", "part": "there is a part here", "socket": "there is an empty socket here",
              "switch": "there is an unlit switch here", "carrying": "the robot is carrying a part",
              "exit": "the robot is on the exit"}
ROUTINES = ("main", "A", "B")
CALLABLE = {"main": ("A", "B"), "A": (), "B": ("A",)}     # who may call whom: no recursion is possible
BLOCKS = ("rep", "until", "if")
REP_MIN, REP_MAX = 2, 9
MAX_SIZE = 40
MAX_DEPTH = 3
CONSTRUCTS = ("rep", "until", "if", "call")


def new_program():
    return {"main": []}


def cond_ok(cond):
    return isinstance(cond, str) and cond.lstrip("!") in CONDS and cond.count("!") <= 1 and not cond.startswith("!!")


def cond_text(cond):
    return ("not " if cond.startswith("!") else "") + cond.lstrip("!")


def _count(items):
    total = 0
    for stmt in items:
        total += 1
        if isinstance(stmt, list):
            for part in stmt:
                if isinstance(part, list):
                    total += _count(part)
    return total


def size(prog):
    """The score: every instruction counts one (a block's header, a call, and everything inside every routine)."""
    return sum(_count(prog.get(name, [])) for name in ROUTINES)


def uses(prog):
    """The set of constructs a program contains: a subset of CONSTRUCTS."""
    found = set()

    def walk(items):
        for stmt in items:
            if isinstance(stmt, list):
                found.add(stmt[0])
                for part in stmt:
                    if isinstance(part, list):
                        walk(part)
    for name in ROUTINES:
        walk(prog.get(name, []))
    return found


def counts(prog):
    """How many of each construct a program contains: {"rep": n, "until": n, "if": n, "call": n}."""
    found = {kind: 0 for kind in CONSTRUCTS}

    def walk(items):
        for stmt in items:
            if isinstance(stmt, list):
                found[stmt[0]] += 1
                for part in stmt:
                    if isinstance(part, list):
                        walk(part)
    for name in ROUTINES:
        walk(prog.get(name, []))
    return found


def routines_used(prog):
    return [name for name in ROUTINES if name != "main" and prog.get(name)]


def copy(prog):
    def clone(items):
        out = []
        for stmt in items:
            if isinstance(stmt, list):
                out.append([clone(p) if isinstance(p, list) else p for p in stmt])
            else:
                out.append(stmt)
        return out
    return {name: clone(prog[name]) for name in ROUTINES if name in prog}


def depth(items):
    best = 0
    for stmt in items:
        if isinstance(stmt, list):
            inner = [depth(p) for p in stmt if isinstance(p, list)]
            best = max(best, 1 + (max(inner) if inner else 0))
    return best


def allowed_ops(allow):
    """`allow` is a string of tokens such as "F L R G P S rep A B"; returns the set."""
    return set(allow.split()) if isinstance(allow, str) else set(allow)


def check(prog, allow=None):
    """Return None when `prog` is a well-formed program using only what `allow` permits, else a short reason."""
    if not isinstance(prog, dict) or "main" not in prog:
        return "A program needs a main list."
    ops = allowed_ops(allow) if allow is not None else None
    for name in prog:
        if name not in ROUTINES:
            return "There is no routine called " + str(name) + "."
        if not isinstance(prog[name], list):
            return "A routine is a list."
        if ops is not None and name != "main" and name not in ops:
            return "Routine " + name + " is not available in this room."
        reason = _check_list(prog[name], name, ops, 1)
        if reason:
            return reason
    if size(prog) > MAX_SIZE:
        return "A list can hold at most " + str(MAX_SIZE) + " instructions."
    return None


def _check_list(items, routine, ops, level):
    if level > MAX_DEPTH + 1:
        return "Blocks go at most " + str(MAX_DEPTH) + " deep."
    for stmt in items:
        if isinstance(stmt, str):
            if stmt not in ACTIONS:
                return "Unknown instruction " + repr(stmt) + "."
            if ops is not None and stmt not in ops:
                return ACTION_NAMES[stmt] + " is not available in this room."
            continue
        if not isinstance(stmt, list) or not stmt or stmt[0] not in CONSTRUCTS:
            return "Unknown instruction."
        kind = stmt[0]
        if ops is not None and kind != "call" and kind not in ops:
            return "That block is not available in this room."
        if kind == "rep":
            if len(stmt) != 3 or isinstance(stmt[1], bool) or not isinstance(stmt[1], int) or not REP_MIN <= stmt[1] <= REP_MAX or not isinstance(stmt[2], list):
                return "A repeat needs a count from " + str(REP_MIN) + " to " + str(REP_MAX) + "."
            bodies = [stmt[2]]
        elif kind == "until":
            if len(stmt) != 3 or not cond_ok(stmt[1]) or not isinstance(stmt[2], list):
                return "An until block needs a condition."
            bodies = [stmt[2]]
        elif kind == "if":
            if len(stmt) != 4 or not cond_ok(stmt[1]) or not isinstance(stmt[2], list) or not isinstance(stmt[3], list):
                return "An if block needs a condition."
            bodies = [stmt[2], stmt[3]]
        else:
            if len(stmt) != 2 or stmt[1] not in ("A", "B") or stmt[1] not in CALLABLE[routine]:
                return "Routine " + routine + " cannot call that."
            if ops is not None and stmt[1] not in ops:
                return "Routine " + str(stmt[1]) + " is not available in this room."
            continue
        for body in bodies:
            reason = _check_list(body, routine, ops, level + 1)
            if reason:
                return reason
    return None


# ---- text form --------------------------------------------------------------------------------------------------------

def _fmt(items):
    out = []
    for stmt in items:
        if isinstance(stmt, str):
            out.append(stmt)
        elif stmt[0] == "rep":
            out.append("rep %d { %s }" % (stmt[1], _fmt(stmt[2])) if stmt[2] else "rep %d { }" % stmt[1])
        elif stmt[0] == "until":
            out.append("until %s { %s }" % (stmt[1], _fmt(stmt[2])) if stmt[2] else "until %s { }" % stmt[1])
        elif stmt[0] == "if":
            then = "if %s { %s }" % (stmt[1], _fmt(stmt[2])) if stmt[2] else "if %s { }" % stmt[1]
            if stmt[3]:
                then += " else { %s }" % _fmt(stmt[3])
            out.append(then)
        else:
            out.append("call " + stmt[1])
    return " ".join(out)


def to_text(prog):
    """One line per routine: `main: F F rep 3 { F L }`. The save format and the 'answer' form."""
    lines = []
    for name in ROUTINES:
        if name in prog and (prog[name] or name == "main"):
            lines.append(name + ": " + _fmt(prog[name]))
    return "\n".join(lines)


def to_lines(prog):
    """A readable multi-line form for the answer rung: one instruction per line, blocks indented."""
    lines = []

    def walk(items, indent):
        pad = "  " * indent
        for stmt in items:
            if isinstance(stmt, str):
                lines.append(pad + ACTION_NAMES[stmt])
            elif stmt[0] == "rep":
                lines.append(pad + "Repeat %d times" % stmt[1])
                walk(stmt[2], indent + 1)
            elif stmt[0] == "until":
                lines.append(pad + "Repeat until " + cond_text(stmt[1]))
                walk(stmt[2], indent + 1)
            elif stmt[0] == "if":
                lines.append(pad + "If " + cond_text(stmt[1]))
                walk(stmt[2], indent + 1)
                if stmt[3]:
                    lines.append(pad + "Otherwise")
                    walk(stmt[3], indent + 1)
            else:
                lines.append(pad + "Call routine " + stmt[1])
    for name in ROUTINES:
        if name in prog and (prog[name] or name == "main"):
            lines.append("Routine " + name if name != "main" else "Main")
            walk(prog[name], 1)
    return lines


def from_text(text):
    """Parse the text form. Raises ValueError on anything that is not a well-formed program."""
    if not isinstance(text, str) or len(text) > 4000:
        raise ValueError("not a program")
    tokens = text.replace("{", " { ").replace("}", " } ").split()
    prog = {}
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        token = peek()
        if token is None:
            raise ValueError("unexpected end")
        pos[0] += 1
        return token

    def block():
        if take() != "{":
            raise ValueError("expected {")
        items = []
        while peek() != "}":
            if peek() is None:
                raise ValueError("missing }")
            items.append(statement())
        take()
        return items

    def statement():
        token = take()
        if token in ACTIONS:
            return token
        if token == "rep":
            count = take()
            if not count.isdigit():
                raise ValueError("bad count")
            return ["rep", int(count), block()]
        if token == "until":
            cond = take()
            return ["until", cond, block()]
        if token == "if":
            cond = take()
            then = block()
            other = []
            if peek() == "else":
                take()
                other = block()
            return ["if", cond, then, other]
        if token == "call":
            return ["call", take()]
        if token in ("A", "B"):
            return ["call", token]
        raise ValueError("unknown token " + token)

    while peek() is not None:
        head = take()
        if not head.endswith(":") or head[:-1] not in ROUTINES or head[:-1] in prog:
            raise ValueError("expected a routine name")
        name = head[:-1]
        items = []
        while peek() is not None and not (peek().endswith(":") and peek()[:-1] in ROUTINES):
            items.append(statement())
        prog[name] = items
    if "main" not in prog:
        prog["main"] = []
    reason = check(prog)
    if reason:
        raise ValueError(reason)
    return prog


def parse(text):
    """`from_text` that returns None instead of raising."""
    try:
        return from_text(text)
    except (ValueError, RecursionError):
        return None
