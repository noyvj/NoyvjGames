"""Hull Repair -- the repair log: one short, quiet line from the station's records for each room, found when the room is
patched. The names are always visible; only the lines wait to be found. Voices are tired crew and managers who cut
corners, because nobody here is a hero. Nothing in the log is needed to play, and none of it is timed or missable."""

import boards

LOGS = {
    "airlock-two": "Cycled by hand again. The sensor lies about the seal, so we stopped trusting it and started trusting each other. That went fine until it didn't. - Pell, dock tech",
    "cargo-hold": "Manifest says forty crates. I counted thirty-one and signed for forty. It was the end of a long shift and I wanted my bunk. - Ines",
    "tool-locker": "Three torque wrenches missing since spring. Nobody admits to anything. I bought a lock; the lock is also missing. - Supply log",
    "suit-room": "Suit eleven has a slow leak in the left glove. I tagged it 'fine for short jobs'. It is not my best sentence. - Pell",
    "dock-control": "Told the freighter we had a clear berth. We had a berth. Whether it was clear is a conversation for the inquiry. - Control",
    "cargo-lift": "The lift stuck between floors for an hour with a case of oranges. Best hour of the quarter. We shared them out and nobody wrote it up. - Ines",
    "waiting-lounge": "Nobody has waited here in months. The chairs still face the window as if a ship might be late. - cleaner's note",
    "mail-room": "Forty letters never forwarded. I read two. One was an apology, unsent for a year. I am not proud of reading it. - Odalys",
    "mess-hall": "The menu board still says Tuesday: stew. Tuesday has been a long time. Someone ought to wipe it. Someone won't. - Hale",
    "bunk-row": "Bunk nine, quilt folded square. Whoever slept here left like they meant to come back, or wanted us to think so. - Odalys",
    "laundry": "Six dryers, one working, and it eats socks. I kept a tally of what it took. The tally is longer than the roster. - Hale",
    "gym": "The treadmill belt frayed in January. I filed a ticket. The ticket says 'low priority: morale'. Morale was the problem. - Ines",
    "library-nook": "Forty paper books, all returned late. Fines were waived by the supervisor, who never returned hers. - Odalys",
    "medbay": "Dr. Ruan logged the cough on this deck as 'recycled air'. Nine people had it. She was one of them and logged herself last. - Medbay",
    "greenhouse-closet": "The tomatoes came in. Seven. Marit took four for the supervisors' table and we called that fair, because arguing was tiring. - Hale",
    "observation-window": "The window cracked in a line as thin as a hair. Someone taped over it and wrote ART on the tape. Funny, until it wasn't. - Pell",
    "pump-room": "Pump four is loud. Loud means working. That is a rule I made up, and I have been wrong about it twice. - Tomas",
    "cable-gallery": "The bundles are labelled in three different hands, two of them mine, one of them wrong. I know which. I am not telling. - Tomas",
    "coolant-loop": "Marit asked for the loop to be rerouted through the crew deck to save a week. I said it needed a pressure check. She said we would check later. - Tomas",
    "backup-battery": "The cells are at sixty percent and holding. Holding is a generous word. - Siv",
    "welding-shop": "The weld on junction six is ugly but strong. The weld on junction seven is pretty and I would not trust it with a houseplant. - Siv",
    "spares-store": "Spare gaskets: two. Gaskets needed: eleven. I requested forty on four forms and received a poster about teamwork. - Siv",
    "control-cabinet": "The dials were taped over because the alarm was 'noise'. I peeled the tape off once. Someone put it back before my shift ended. - Tomas",
    "heat-exchanger": "It ran hot all week. I wrote 'monitor' in the log, which is what you write when you have decided not to decide. - Tomas",
    "air-scrubbers": "The filters were changed on schedule, mostly. The 'mostly' is mine. - Fenn",
    "water-recycler": "It tastes like coins and old rain, and we called it coffee for years. Nobody complained; there was no one to complain to. - Fenn",
    "algae-tanks": "The tanks grew faster than we could harvest. Green is a good colour on a station. Green is a loud colour in a log. - Fenn",
    "pressure-doors": "Door fourteen closes two seconds late. We put a sign on it that says 'brisk'. - Hale",
    "filter-bank": "I swapped in the cheaper filters. The air smells fine. The air always smells fine, right up until it doesn't. - Fenn",
    "humidity-control": "The dehumidifier sings at night, three notes, always the same three. I have started humming them. - Odalys",
    "waste-processing": "Nothing glamorous here. Everything that leaves the station passes through this room, including most of our mistakes. - Fenn",
    "garden-deck": "Someone planted a row of marigolds against the rules. The row is alive. The rule is dead. I am leaving both. - Fenn",
    "power-core": "Running at the edge of the chart. The chart was drawn by the lowest bidder. - Siv",
    "core-control": "Three alarms, one real. By the time we knew which, it did not matter which. - Control",
    "comms-mast": "We kept sending 'all well' on the hour. By the end it was habit, not a report. - Odalys",
    "navigation-room": "Course plotted for a quiet place to wait. We were told it would be temporary. - Pell",
    "supervisors-office": "Marit's chair is still turned toward the door. Her notes say 'will check tomorrow' on nineteen pages. - Hale",
    "black-box-vault": "The record is complete and unflattering, and it does not forget. I will read it once and not twice. - Tomas",
    "emergency-bridge": "Everyone reached the lifeboats in order. Nobody was brave. They were just in a queue. It worked. - Ines",
    "the-quiet-room": "All the lights are back. The station is not sorry, and neither is the fix. It was always going to be someone's turn to mend it. - the repair link",
}


def entries(st):
    """One entry per board in play order: its name, its deck, and its line once the room is patched."""
    out = []
    for bid in boards.ORDER:
        b = boards.BY_ID[bid]
        found = st.get(bid, 0) >= 1
        out.append({"id": bid, "name": b.name, "deck": boards.CHAPTER_LIST[b.chapter]["name"], "found": found, "line": LOGS.get(bid, "") if found else ""})
    return out


def line_for(bid):
    return LOGS.get(bid, "")
