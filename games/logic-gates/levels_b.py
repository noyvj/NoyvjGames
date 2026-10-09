"""Logic Gates -- chapter 3, memory (levels 18-24). Sequences: each step sets some inputs (the rest keep their value, all start
at 0) and says which lamps must read what once the circuit has settled. Power-on state is all zeros. Loops are allowed here.

The step lists are produced by small Python models that know nothing about the reference circuits."""


def lamps(**kw):
    return " ".join(f"{k}={v}" for k, v in kw.items())


def _counter_steps():
    lines, n = ["CLK=0 -> Q1=0 Q0=0"], 0
    for _ in range(6):
        n = (n + 1) % 4
        want = lamps(Q1=n >> 1, Q0=n & 1)
        lines += [f"CLK=1 -> {want}", f"CLK=0 -> {want}"]
    return "; ".join(lines)


def _shift_steps():
    lines, reg = ["IN=0 CLK=0 -> Q0=0 Q1=0 Q2=0"], [0, 0, 0]
    for bit in (1, 0, 1, 1, 0, 0, 0):
        reg = [bit, reg[0], reg[1]]
        want = lamps(Q0=reg[0], Q1=reg[1], Q2=reg[2])
        lines += [f"IN={bit} CLK=1 -> {want}", f"CLK=0 -> {want}"]
    return "; ".join(lines)


def _pulse_steps():
    """P = A and not (A as it was at the last rising clock edge); right after an edge that is always 0."""
    lines, prev = ["A=0 CLK=0 -> P=0"], 0
    for a in (1, 1, 0, 1, 0, 0, 1):
        lines.append(f"A={a} -> P={a & (1 - prev)}")
        lines += ["CLK=1 -> P=0", "CLK=0 -> P=0"]
        prev = a
    return "; ".join(lines)


def _toggle_steps():
    lines, q = ["CLK=0 -> Q=0"], 0
    for _ in range(4):
        q ^= 1
        lines += [f"CLK=1 -> Q={q}", f"CLK=0 -> Q={q}"]
    return "; ".join(lines)


CH3 = [
    {"id": "latch-up", "name": "Latch Up", "ins": ["S", "R"], "outs": ["Q", "QN"], "loops": True,
     "goal": "Build a memory from two NOR gates. A pulse on S sets Q to 1, a pulse on R sets Q to 0, and with both at 0 Q keeps its last value. QN is always the opposite of Q.",
     "seq": "S=0 R=1 -> Q=0 QN=1; S=1 R=0 -> Q=1 QN=0; S=0 -> Q=1 QN=0; R=1 -> Q=0 QN=1; R=0 -> Q=0 QN=1; S=1 -> Q=1 QN=0; S=0 -> Q=1 QN=0",
     "ref": "q = nor(R, qn); qn = nor(S, q); Q := q; QN := qn", "unlock": "sr",
     "nudge": "A circuit remembers when its output feeds back into its own input. Wiring a chip's output back is allowed here.",
     "hint": "Two NOR chips. The first takes R and the second's output; the second takes S and the first's output. Q is the first output, QN the second.",
     "log": "Memory board 1. Vale's note, underlined twice: 'forget'. The board remembers anyway."},
    {"id": "gated-latch", "name": "Gated Latch", "ins": ["D", "E"], "outs": ["Q"], "loops": True,
     "goal": "While E is 1, Q follows D. While E is 0, Q holds whatever it was. Build it on the SR LATCH chip.",
     "seq": "D=0 E=1 -> Q=0; D=1 -> Q=1; E=0 -> Q=1; D=0 -> Q=1; D=1 -> Q=1; E=1 D=0 -> Q=0; D=1 -> Q=1; E=0 D=0 -> Q=1; E=1 -> Q=0",
     "ref": "s = and(D, E); nd = not(D); r = and(nd, E); l = sr(s, r); Q := l.Q", "unlock": "dlatch", "label": "D LATCH",
     "nudge": "Only let a set or a reset reach the latch while E is 1.",
     "hint": "Set = D AND E. Reset = (NOT D) AND E. Feed those to S and R of an SR LATCH and read Q.",
     "log": "Memory board 2. A latch with a gate: it remembers only when told to listen."},
    {"id": "edge-catcher", "name": "Edge Catcher", "ins": ["D", "CLK"], "outs": ["Q"], "loops": True,
     "goal": "Q takes the value of D at the instant CLK rises from 0 to 1 and ignores D at every other time.",
     "seq": "D=1 CLK=0 -> Q=0; CLK=1 -> Q=1; D=0 -> Q=1; CLK=0 -> Q=1; D=1 -> Q=1; CLK=1 -> Q=1; CLK=0 -> Q=1; D=0 -> Q=1; CLK=1 -> Q=0; CLK=0 -> Q=0",
     "ref": "nc = not(CLK); m = dlatch(D, nc); s = dlatch(m, CLK); Q := s", "unlock": "dff", "label": "FLIP-FLOP",
     "nudge": "Two latches back to back, listening at opposite times.",
     "hint": "The first D LATCH listens when CLK is 0 (use a NOT on CLK for its E). The second listens when CLK is 1 and reads the first. Q is the second.",
     "log": "Memory board 3. The clock edge: one instant when the whole station agrees what now means."},
    {"id": "toggle", "name": "Toggle", "ins": ["CLK"], "outs": ["Q"], "loops": True,
     "goal": "Q flips between 0 and 1 on every rising edge of CLK. It starts at 0.",
     "seq": _toggle_steps(),
     "ref": "f = dff(d, CLK); d = not(f); Q := f", "unlock": "tff", "label": "TOGGLE",
     "nudge": "A flip-flop that is always told to take the opposite of what it holds.",
     "hint": "FLIP-FLOP with D wired to a NOT of its own Q, and CLK to CLK.",
     "log": "Memory board 4. It counts to one, forever. Vale called it 'the heartbeat'."},
    {"id": "two-bit-counter", "name": "Two-Bit Counter", "ins": ["CLK"], "outs": ["Q1", "Q0"], "loops": True,
     "goal": "Q1 Q0 count 00, 01, 10, 11, 00 ... one step per rising edge of CLK.",
     "seq": _counter_steps(),
     "ref": "a = tff(CLK); n = not(a); b = tff(n); Q0 := a; Q1 := b", "unlock": "ctr2", "label": "COUNTER",
     "nudge": "The second bit should flip when the first bit falls from 1 to 0.",
     "hint": "Toggle one is clocked by CLK. Put its output through a NOT and use that as the clock of toggle two.",
     "log": "Memory board 5. A counter built of toggles. Vale counted days with it, and stopped at 11."},
    {"id": "shift-register", "name": "Shift Register", "ins": ["IN", "CLK"], "outs": ["Q0", "Q1", "Q2"], "loops": True,
     "goal": "On each rising edge of CLK the value on IN enters Q0, Q0 moves to Q1 and Q1 moves to Q2.",
     "seq": _shift_steps(),
     "ref": "a = dff(IN, CLK); b = dff(a, CLK); c = dff(b, CLK); Q0 := a; Q1 := b; Q2 := c", "unlock": "shift3", "label": "SHIFT 3",
     "nudge": "Three flip-flops in a row, on the same clock.",
     "hint": "FLIP-FLOP 1 takes IN, FLIP-FLOP 2 takes flip-flop 1's Q, FLIP-FLOP 3 takes flip-flop 2's Q. All share CLK.",
     "log": "Memory board 6. A queue of bits. The oldest message in it is a date Vale would rather not read out."},
    {"id": "pulse-catcher", "name": "Pulse Catcher", "ins": ["A", "CLK"], "outs": ["P"], "loops": True,
     "goal": "P is 1 while A is on and A was off at the last rising edge of CLK. Holding A on only gives one pulse per press.",
     "seq": _pulse_steps(),
     "ref": "p = dff(A, CLK); n = not(p); P := and(A, n)", "unlock": "edge", "label": "EDGE",
     "nudge": "Remember what A was at the last clock edge, and compare.",
     "hint": "A FLIP-FLOP holds the old A. P = A AND NOT(old A).",
     "log": "Memory board 7. One press, one event. Chapter three done: the board can hold a thought."},
]
