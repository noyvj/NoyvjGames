"""Logic Gates -- chapters 4 and 5 (levels 25-40): adders, then a tiny computer. Bus names run most significant first."""
from levels_a import num


def lamps(**kw):
    return " ".join(f"{k}={v}" for k, v in kw.items())


def _bits(prefix, value, n):
    return {f"{prefix}{i}": (value >> i) & 1 for i in range(n - 1, -1, -1)}


def _reg_bit_steps():
    return ("D=1 LD=1 CLR=0 CLK=0 -> Q=0; CLK=1 -> Q=1; CLK=0 -> Q=1; D=0 LD=0 -> Q=1; CLK=1 -> Q=1; CLK=0 -> Q=1; "
            "LD=1 -> Q=1; CLK=1 -> Q=0; CLK=0 -> Q=0; D=1 LD=0 -> Q=0; CLK=1 -> Q=0; CLK=0 -> Q=0; LD=1 -> Q=0; "
            "CLK=1 -> Q=1; CLK=0 -> Q=1; CLR=1 -> Q=1; CLK=1 -> Q=0; CLK=0 -> Q=0")


def _reg4_steps():
    lines, q = ["D3=0 D2=0 D1=0 D0=0 LD=0 CLR=0 CLK=0 -> " + lamps(Q3=0, Q2=0, Q1=0, Q0=0)], 0

    def load(value, ld):
        nonlocal q
        sets = " ".join(f"{k}={v}" for k, v in _bits("D", value, 4).items())
        if ld:
            q = value
        want = lamps(**_bits("Q", q, 4))
        lines.extend([f"{sets} LD={ld} CLK=1 -> {want}", f"CLK=0 -> {want}"])
    load(9, 1)
    load(6, 0)
    load(6, 1)
    load(15, 1)
    load(3, 0)
    lines.append("CLR=1 CLK=1 -> " + lamps(**_bits("Q", 0, 4)))
    lines.append("CLK=0 -> " + lamps(**_bits("Q", 0, 4)))
    return "; ".join(lines)


def _pc_steps():
    lines = ["RST=1 CLK=0 -> P1=0 P0=0", "CLK=1 -> P1=0 P0=0", "CLK=0 -> P1=0 P0=0", "RST=0 -> P1=0 P0=0"]
    n = 0
    for _ in range(6):
        n = (n + 1) % 4
        want = lamps(P1=n >> 1, P0=n & 1)
        lines += [f"CLK=1 -> {want}", f"CLK=0 -> {want}"]
    lines += ["RST=1 -> " + want, "CLK=1 -> P1=0 P0=0", "CLK=0 -> P1=0 P0=0"]
    return "; ".join(lines)


# The tiny computer: a 4-bit accumulator ACC and a 2-bit program counter. Each rising edge runs the instruction at the counter:
# ACC = ACC <op> number, where the word W3 W2 picks the op (00 add, 01 and, 10 or, 11 xor) and W1 W0 is the number (0 to 3).
def _alu(op, a, b):
    return [(a + b) & 15, a & b, a | b, a ^ b][op]


def word(op, imm):
    return (op << 2) | imm


PROGRAM_A = [word(2, 3), word(0, 2), word(3, 3), word(0, 3)]       # OR 3, ADD 2, XOR 3, ADD 3
PROGRAM_B = [word(2, 1), word(0, 3), word(0, 3), word(3, 2)]       # OR 1, ADD 3, ADD 3, XOR 2


def trace(program, ticks=8):
    acc, pc, out = 0, 0, []
    for _ in range(ticks):
        w = program[pc]
        acc = _alu(w >> 2, acc, w & 3)
        pc = (pc + 1) % 4
        out.append(acc)
    return out


def _machine_steps(program, only_last=None):
    lines = ["RST=1 CLK=0", "CLK=1", "CLK=0", "RST=0 -> " + lamps(**_bits("ACC", 0, 4))]
    values = trace(program)
    for n, acc in enumerate(values, start=1):
        want = lamps(**_bits("ACC", acc, 4))
        if only_last is not None and n != only_last:
            lines += ["CLK=1", "CLK=0"]
        else:
            lines += [f"CLK=1 -> {want}", f"CLK=0 -> {want}"]
        if only_last is not None and n == only_last:
            break
    return "; ".join(lines)


ADD4_INS = ["A3", "A2", "A1", "A0", "B3", "B2", "B1", "B0"]
CH4 = [
    {"id": "half-adder", "name": "Half Adder", "ins": ["A", "B"], "outs": ["SUM", "CARRY"],
     "goal": "Add two one-bit numbers: SUM is the low bit of A plus B and CARRY is the bit that spills into the next place.",
     "fn": lambda v: {"SUM": (v["A"] + v["B"]) & 1, "CARRY": (v["A"] + v["B"]) >> 1},
     "ref": "SUM := xor(A, B); CARRY := and(A, B)", "unlock": "half_add", "label": "HALF ADDER",
     "nudge": "1 plus 1 is 10 in binary. Which gate gives the 0 and which gives the 1?",
     "hint": "SUM is XOR of the two bits. CARRY is AND of the two bits.",
     "log": "Adder board 1. Vale's note: 'carry the one, then blame the cooling line.' The page is torn after that."},
    {"id": "full-adder", "name": "Full Adder", "ins": ["A", "B", "CIN"], "outs": ["SUM", "COUT"],
     "goal": "Add three bits, A and B and a carry coming in (CIN). SUM is the low bit of the total and COUT the carry out.",
     "fn": lambda v: {"SUM": (v["A"] + v["B"] + v["CIN"]) & 1, "COUT": (v["A"] + v["B"] + v["CIN"]) >> 1},
     "ref": "h1 = half_add(A, B); h2 = half_add(h1.SUM, CIN); SUM := h2.SUM; COUT := or(h1.CARRY, h2.CARRY)",
     "unlock": "full_add", "label": "FULL ADDER",
     "nudge": "Add A and B first, then add the carry in to that.",
     "hint": "HALF ADDER 1 adds A and B. HALF ADDER 2 adds its SUM and CIN. COUT is OR of the two carries.",
     "log": "Adder board 2. Now a column can accept what the column to its right spilled over."},
    {"id": "two-bit-adder", "name": "Two-Bit Adder", "ins": ["A1", "A0", "B1", "B0"], "outs": ["S2", "S1", "S0"],
     "goal": "Add the two-bit numbers A1 A0 and B1 B0. The answer is up to three bits, S2 S1 S0.",
     "fn": lambda v: _bits("S", num(v, "A", 2) + num(v, "B", 2), 3),
     "ref": "h = half_add(A0, B0); f = full_add(A1, B1, h.CARRY); S0 := h.SUM; S1 := f.SUM; S2 := f.COUT",
     "unlock": "add2", "label": "ADD 2-BIT",
     "nudge": "The right-hand column has no carry in. The left-hand column takes the right one's carry.",
     "hint": "A HALF ADDER for the low bits, a FULL ADDER for the high bits fed by the half adder's CARRY. S2 is the full adder's COUT.",
     "log": "Adder board 3. Two columns, one carry, one small miracle."},
    {"id": "four-bit-adder", "name": "Four-Bit Adder", "ins": ADD4_INS + ["CIN"], "outs": ["COUT", "S3", "S2", "S1", "S0"],
     "goal": "Add the four-bit numbers A and B plus a carry in. COUT S3 S2 S1 S0 is the five-bit answer.",
     "fn": lambda v: dict(_bits("S", (num(v, "A", 4) + num(v, "B", 4) + v["CIN"]) & 15, 4), COUT=(num(v, "A", 4) + num(v, "B", 4) + v["CIN"]) >> 4),
     "ref": "f0 = full_add(A0, B0, CIN); f1 = full_add(A1, B1, f0.COUT); f2 = full_add(A2, B2, f1.COUT); f3 = full_add(A3, B3, f2.COUT); "
            "S0 := f0.SUM; S1 := f1.SUM; S2 := f2.SUM; S3 := f3.SUM; COUT := f3.COUT",
     "unlock": "add4", "label": "ADD 4-BIT",
     "nudge": "Four columns, each a full adder, each passing its carry left.",
     "hint": "Chain four FULL ADDERs: CIN goes into the right one, each COUT goes to the next CIN. Each SUM is one S output; the last COUT is COUT.",
     "log": "Adder board 4. Four bits is enough to count the days since the shutdown, if you stop at fifteen."},
    {"id": "add-subtract", "name": "Add/Subtract", "ins": ADD4_INS + ["SUB"], "outs": ["R3", "R2", "R1", "R0"],
     "goal": "With SUB off, R is A plus B. With SUB on, R is A minus B. Only the low four bits count (wrap around).",
     "fn": lambda v: _bits("R", (num(v, "A", 4) + (-num(v, "B", 4) if v["SUB"] else num(v, "B", 4))) & 15, 4),
     "ref": "x0 = xor(B0, SUB); x1 = xor(B1, SUB); x2 = xor(B2, SUB); x3 = xor(B3, SUB); a = add4(A3, A2, A1, A0, x3, x2, x1, x0, SUB); "
            "R0 := a.S0; R1 := a.S1; R2 := a.S2; R3 := a.S3",
     "unlock": "addsub4", "label": "ADD/SUB",
     "nudge": "To subtract, flip every bit of B and add one more.",
     "hint": "XOR each bit of B with SUB (that flips them when SUB is on). Feed those to an ADD 4-BIT, with SUB also wired to its CIN.",
     "log": "Adder board 5. Subtraction is addition with a mirror. Vale's ledger used both, and balanced neither."},
    {"id": "zero-detector", "name": "Zero Detector", "ins": ["A3", "A2", "A1", "A0"], "outs": ["Z"],
     "goal": "Lamp Z lights only when all four bits are 0.",
     "fn": lambda v: {"Z": 1 if num(v, "A", 4) == 0 else 0},
     "ref": "o1 = or(A3, A2); o2 = or(A1, A0); Z := nor(o1, o2)", "unlock": "zero4", "label": "IS ZERO",
     "nudge": "Zero means none of the bits is on.",
     "hint": "OR the bits in pairs, then NOR the two results.",
     "log": "Adder board 6. A zero flag: the machine's way of saying 'nothing left'."},
    {"id": "equal", "name": "Equal", "ins": ADD4_INS, "outs": ["EQ"],
     "goal": "Lamp EQ lights only when the four-bit numbers A and B are the same.",
     "fn": lambda v: {"EQ": 1 if num(v, "A", 4) == num(v, "B", 4) else 0},
     "ref": "x0 = xnor(A0, B0); x1 = xnor(A1, B1); x2 = xnor(A2, B2); x3 = xnor(A3, B3); a = and(x0, x1); b = and(x2, x3); EQ := and(a, b)",
     "unlock": "eq4", "label": "EQUAL 4",
     "nudge": "Every pair of bits must match.",
     "hint": "XNOR each pair of bits, then AND all four results (two ANDs, then one more).",
     "log": "Adder board 7. Chapter four done. Numbers can be added, compared and told apart."},
]

CH5 = [
    {"id": "register-bit", "name": "Register Bit", "ins": ["D", "LD", "CLR", "CLK"], "outs": ["Q"], "loops": True,
     "goal": "On each rising edge of CLK: if CLR is 1, Q becomes 0; otherwise if LD is 1, Q takes D; otherwise Q holds.",
     "seq": _reg_bit_steps(),
     "ref": "f = dff(g, CLK); m = mux2(f, D, LD); nc = not(CLR); g = and(m, nc); Q := f", "unlock": "reg_bit", "label": "REGISTER BIT",
     "nudge": "A flip-flop whose input is chosen: its own output (hold) or D (load), and forced to 0 by CLR.",
     "hint": "MUX 2:1 picks between Q (select 0) and D (select 1), with LD as the select. AND that with NOT CLR and feed the FLIP-FLOP.",
     "log": "Machine board 1. A register bit: a thing that can be told to keep a number or to let it go."},
    {"id": "register", "name": "Register", "ins": ["D3", "D2", "D1", "D0", "LD", "CLR", "CLK"], "outs": ["Q3", "Q2", "Q1", "Q0"], "loops": True,
     "goal": "Four register bits sharing LD, CLR and CLK: a four-bit number you can load, hold or clear on a clock edge.",
     "seq": _reg4_steps(),
     "ref": "b0 = reg_bit(D0, LD, CLR, CLK); b1 = reg_bit(D1, LD, CLR, CLK); b2 = reg_bit(D2, LD, CLR, CLK); b3 = reg_bit(D3, LD, CLR, CLK); "
            "Q0 := b0; Q1 := b1; Q2 := b2; Q3 := b3",
     "unlock": "reg4", "label": "REGISTER",
     "nudge": "Four copies of the chip you just built.",
     "hint": "Four REGISTER BIT chips. Each gets its own D, and all share LD, CLR and CLK.",
     "log": "Machine board 2. Memory you can name. Vale's key was in register 4."},
    {"id": "alu-slice", "name": "ALU Slice", "ins": ["A", "B", "CIN", "OP1", "OP0"], "outs": ["R", "COUT"],
     "goal": "R is chosen by the two-bit OP: 00 gives A plus B plus CIN (low bit), 01 gives A AND B, 10 gives A OR B, 11 gives A XOR B. COUT is always the carry of A plus B plus CIN.",
     "fn": lambda v: {"R": [(v["A"] + v["B"] + v["CIN"]) & 1, v["A"] & v["B"], v["A"] | v["B"], v["A"] ^ v["B"]][2 * v["OP1"] + v["OP0"]],
                      "COUT": (v["A"] + v["B"] + v["CIN"]) >> 1},
     "ref": "f = full_add(A, B, CIN); a = and(A, B); o = or(A, B); x = xor(A, B); r = mux4(f.SUM, a, o, x, OP1, OP0); R := r; COUT := f.COUT",
     "unlock": "alu_slice", "label": "ALU SLICE",
     "nudge": "Compute all four answers, then let OP pick one.",
     "hint": "A FULL ADDER, an AND, an OR and an XOR all see A and B. A MUX 4:1 chooses among their results (D0 add, D1 and, D2 or, D3 xor) using OP1 OP0.",
     "log": "Machine board 3. One slice of the arithmetic unit: a tiny chef that can cook four dishes."},
    {"id": "alu", "name": "ALU", "ins": ADD4_INS + ["OP1", "OP0"], "outs": ["R3", "R2", "R1", "R0"],
     "goal": "A four-bit arithmetic unit: R = A + B, A AND B, A OR B or A XOR B (low four bits), picked by OP1 OP0 as before.",
     "fn": lambda v: _bits("R", [(num(v, "A", 4) + num(v, "B", 4)) & 15, num(v, "A", 4) & num(v, "B", 4),
                                 num(v, "A", 4) | num(v, "B", 4), num(v, "A", 4) ^ num(v, "B", 4)][2 * v["OP1"] + v["OP0"]], 4),
     "ref": "s0 = alu_slice(A0, B0, 0, OP1, OP0); s1 = alu_slice(A1, B1, s0.COUT, OP1, OP0); s2 = alu_slice(A2, B2, s1.COUT, OP1, OP0); "
            "s3 = alu_slice(A3, B3, s2.COUT, OP1, OP0); R0 := s0.R; R1 := s1.R; R2 := s2.R; R3 := s3.R",
     "unlock": "alu4", "label": "ALU",
     "nudge": "Four slices, with the carry passed along like the adder.",
     "hint": "Four ALU SLICEs. The lowest has CIN tied to 0; each COUT feeds the next CIN. OP1 and OP0 go to all four.",
     "log": "Machine board 4. The arithmetic unit is done. The station can now do sums, and so can its accountants."},
    {"id": "program-counter", "name": "Program Counter", "ins": ["CLK", "RST"], "outs": ["P1", "P0"], "loops": True,
     "goal": "A two-bit counter that goes up by one on every rising edge of CLK (00, 01, 10, 11, 00 ...) and returns to 00 on an edge where RST is 1.",
     "seq": _pc_steps(),
     "ref": "r = reg4(0, 0, h1.SUM, h0.SUM, 1, RST, CLK); h0 = half_add(r.Q0, 1); h1 = half_add(r.Q1, h0.CARRY); P0 := r.Q0; P1 := r.Q1",
     "unlock": "pc2", "label": "PROGRAM COUNTER",
     "nudge": "A register that always loads its own value plus one.",
     "hint": "A REGISTER with LD tied to 1 and CLR to RST. Its input is its output plus 1: HALF ADDER on Q0 and 1, then HALF ADDER on Q1 and the first carry.",
     "log": "Machine board 5. It points at the next thing to do. Vale never let anyone read it past 3."},
    {"id": "program-rom", "name": "Program ROM", "ins": ["A1", "A0"], "outs": ["W3", "W2", "W1", "W0"],
     "goal": "A read-only memory with four words. Address 0 holds 1011, address 1 holds 0010, address 2 holds 1111, address 3 holds 0011 (W3 W2 W1 W0).",
     "fn": lambda v: _bits("W", PROGRAM_A[2 * v["A1"] + v["A0"]], 4),
     "ref": "d = dec2(A1, A0); o = or(d.Y0, d.Y2); W0 := or(o, d.Y3); W1 := 1; W2 := d.Y2; W3 := o",
     "unlock": "rom_a", "label": "ROM A",
     "nudge": "A decoder turns the address into one lit line per word. Each output bit ORs the words that have a 1 there.",
     "hint": "Use a DECODER. W1 is 1 in every word, so tie it to 1. W2 is 1 only for address 2. W3 is 1 for addresses 0 and 2. W0 is 1 for addresses 0, 2 and 3.",
     "log": "Machine board 6. The station's first program, burned into four words. Someone wrote it in a hurry."},
    {"id": "fetch-and-execute", "name": "Fetch and Execute", "ins": ["CLK", "RST"], "outs": ["ACC3", "ACC2", "ACC1", "ACC0"], "loops": True,
     "goal": "Build the machine. On each rising edge the word at the program counter runs: ACC = ACC op number (W3 W2 pick the ALU op, W1 W0 is the number 0 to 3, wired as the ALU's B input with B3 and B2 tied to 0). RST clears the accumulator and the counter.",
     "seq": _machine_steps(PROGRAM_A),
     "ref": "pc = pc2(CLK, RST); rom = rom_a(pc.P1, pc.P0); alu = alu4(acc.Q3, acc.Q2, acc.Q1, acc.Q0, 0, 0, rom.W1, rom.W0, rom.W3, rom.W2); "
            "acc = reg4(alu.R3, alu.R2, alu.R1, alu.R0, 1, RST, CLK); ACC3 := acc.Q3; ACC2 := acc.Q2; ACC1 := acc.Q1; ACC0 := acc.Q0",
     "unlock": "core", "label": "CPU CORE",
     "chip_pins": (["W3", "W2", "W1", "W0", "CLK", "RST"], ["ACC3", "ACC2", "ACC1", "ACC0", "P1", "P0"]),
     "chip_net": "pc = pc2(CLK, RST); alu = alu4(acc.Q3, acc.Q2, acc.Q1, acc.Q0, 0, 0, W1, W0, W3, W2); "
                 "acc = reg4(alu.R3, alu.R2, alu.R1, alu.R0, 1, RST, CLK); ACC3 := acc.Q3; ACC2 := acc.Q2; ACC1 := acc.Q1; ACC0 := acc.Q0; P1 := pc.P1; P0 := pc.P0",
     "nudge": "The counter picks a ROM word, the ROM word drives the ALU, the ALU result goes back into the accumulator register.",
     "hint": "PROGRAM COUNTER -> ROM A (P1, P0 as address). ALU: A is the accumulator, B3 B2 are 0, B1 B0 are W1 W0, OP1 OP0 are W3 W2. REGISTER (the accumulator) loads the ALU result every edge: LD is 1, CLR is RST.",
     "log": "Machine board 7. It runs. Eight steps of the first program, and the numbers come out as the paper said they would."},
    {"id": "second-program", "name": "Second Program", "ins": ["CLK", "RST"], "outs": ["ACC3", "ACC2", "ACC1", "ACC0"], "loops": True,
     "goal": "Same machine, new program: OR 1, ADD 3, ADD 3, XOR 2 (words 1001, 0011, 0011, 1110). The accumulator should read 1, 4, 7, 5, 5, 8, 11, 9. Use the CPU CORE and make your own ROM.",
     "seq": _machine_steps(PROGRAM_B),
     "ref": "c = core(w3, d.Y3, w1, w0, CLK, RST); d = dec2(c.P1, c.P0); w0 = not(d.Y3); w1 = not(d.Y0); w3 = or(d.Y0, d.Y3); "
            "ACC3 := c.ACC3; ACC2 := c.ACC2; ACC1 := c.ACC1; ACC0 := c.ACC0",
     "unlock": "rom_b", "label": "ROM B",
     "chip_pins": (["A1", "A0"], ["W3", "W2", "W1", "W0"]),
     "chip_net": "d = dec2(A1, A0); W0 := not(d.Y3); W1 := not(d.Y0); W2 := d.Y3; W3 := or(d.Y0, d.Y3)",
     "nudge": "The core has no ROM inside. Its P1 P0 outputs are the address; the words go back into W3 W2 W1 W0.",
     "hint": "DECODER on P1 P0. W0 is 1 for addresses 0, 1, 2 (NOT Y3). W1 is 1 for 1, 2, 3 (NOT Y0). W2 is 1 for address 3 only (Y3). W3 is 1 for 0 and 3 (OR Y0, Y3).",
     "log": "Machine board 8. A different program, same machine. Vale's version only ever ran one."},
    {"id": "wake-the-station", "name": "Wake the Station", "ins": ["CLK", "RST"], "outs": ["ACC3", "ACC2", "ACC1", "ACC0"], "loops": True,
     "goal": "Write your own four-word program so that after the fourth clock edge after RST the accumulator reads 1001 (9). Any program that does it is right.",
     "seq": "RST=1 CLK=0; CLK=1; CLK=0; RST=0; CLK=1; CLK=0; CLK=1; CLK=0; CLK=1; CLK=0; CLK=1 -> ACC3=1 ACC2=0 ACC1=0 ACC0=1; CLK=0 -> ACC3=1 ACC2=0 ACC1=0 ACC0=1",
     "ref": "c = core(w3, 0, w1, w0, CLK, RST); d = dec2(c.P1, c.P0); w0 = not(d.Y3); w1 = not(d.Y3); w3 = or(d.Y0, d.Y3); "
            "ACC3 := c.ACC3; ACC2 := c.ACC2; ACC1 := c.ACC1; ACC0 := c.ACC0",
     "unlock": "tiny4", "label": "TINY-4",
     "chip_pins": (["CLK", "RST"], ["ACC3", "ACC2", "ACC1", "ACC0"]),
     "chip_net": "r = rom_a(c.P1, c.P0); c = core(r.W3, r.W2, r.W1, r.W0, CLK, RST); "
                 "ACC3 := c.ACC3; ACC2 := c.ACC2; ACC1 := c.ACC1; ACC0 := c.ACC0",
     "nudge": "One way: OR 3 (reads 3), ADD 3 (6), ADD 3 (9), then something that changes nothing, like OR 0.",
     "hint": "Words 1011, 0011, 0011, 1000 give 3, 6, 9, 9. W0 and W1 are 1 for addresses 0 to 2 (NOT Y3), W2 is 0 always, W3 is 1 for addresses 0 and 3.",
     "log": "Machine board 9. The core wakes. Vale's note on the last page reads only: 'I turned it off so no one would see what I did.'"},
]
