"""Logic Gates -- the "About" page: the real ideas behind the game, each with its source named on screen and the date it was read.

Every fact below was read live from the named page on the date given and is reworded here, never copied. The game is a SIMPLIFICATION,
not a hardware simulator: it has no gate delays, its memory cells are idealised and its tiny computer is invented. A fact with no source
would be left out."""

DATE_READ = "2026-10-09"

FRAMING = ("Logic Gates is a game, not a hardware simulator. It has no gate delays or voltages, its memory chips are idealised, and the "
           "four-instruction computer at the end is invented. The ideas behind it are real, and these are some of the places they come from.")

FACTS = (
    {
        "id": "logic-gate", "heading": "What a gate is",
        "fact": "A logic gate is a device that takes one or more binary inputs and produces one binary output by applying a Boolean operation. "
                "Most gates today are built from MOSFET transistors acting as electronic switches.",
        "tie_in": "Your seven starting chips are exactly these: each one reads 0s and 1s and answers with a single 0 or 1.",
        "source": {"title": "Logic gate", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Logic_gate"},
    },
    {
        "id": "universal", "heading": "One gate is enough",
        "fact": "NAND and NOR are called universal gates: either one alone can build every other gate. Peirce showed this in the 1880s, though it "
                "stayed unpublished until 1933, and Sheffer published the first proof in 1913.",
        "tie_in": "The sandbox lets you check it. Every one of The Sixteen two-input functions can be made from NAND chips alone.",
        "source": {"title": "Logic gate", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Logic_gate"},
    },
    {
        "id": "shannon", "heading": "Switches that do algebra",
        "fact": "Claude Shannon's 1937 master's thesis showed that electrical switching circuits could carry out Boolean algebra, that this could "
                "simplify the relays used in telephone call routing, and that such circuits could solve any problem Boolean algebra could. It "
                "included a four-bit full adder.",
        "tie_in": "Every level is that idea: a truth table on one side, switches and lamps on the other, and a circuit that makes them agree.",
        "source": {"title": "Claude Shannon", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Claude_Shannon"},
    },
    {
        "id": "latch", "heading": "Memory from a loop",
        "fact": "An SR latch can be made from two NOR gates, each output fed back into the other gate. Set makes the output 1, reset makes it 0, and "
                "with both inputs at 0 it holds its state. Setting both at once is called a forbidden state. A latch follows its input while "
                "enabled, whereas a flip-flop changes only at a clock edge.",
        "tie_in": "Latch Up is exactly this loop. Edge Catcher builds the clock-edge version from two latches.",
        "source": {"title": "Flip-flop (electronics)", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Flip-flop_(electronics)"},
    },
    {
        "id": "adder", "heading": "Adding in columns",
        "fact": "A half adder is one XOR and one AND gate. A full adder can be built from two half adders and an OR gate. Chaining full adders so each "
                "carry feeds the next is a ripple-carry adder, which is simple but slow because each stage waits for the one before.",
        "tie_in": "The Adders chapter is this ladder: half adder, full adder, then four columns in a row.",
        "source": {"title": "Adder (electronics)", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Adder_(electronics)"},
    },
    {
        "id": "agc", "heading": "A real computer made of NOR gates",
        "fact": "The Apollo Guidance Computer was built from integrated circuits that each held a three-input NOR gate. Its words were 16 bits, and "
                "the later model had 2,048 words of erasable core memory and 36,864 words of fixed core rope memory.",
        "tie_in": "Your tiny computer has four-bit words and four instructions, but it is the same kind of machine: gates, remembered bits, and a counter.",
        "source": {"title": "Apollo Guidance Computer", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Apollo_Guidance_Computer"},
    },
)


def view():
    return {"framing": FRAMING, "date_read": DATE_READ,
            "facts": [dict(f, source=dict(f["source"], date_read=DATE_READ)) for f in FACTS]}
