"""Readings as glyphs, the result label, the share text and the radio-room flavour lines."""

from signal_rules import ASCII_GLYPHS, GLYPHS, PRESETS


# --------------------------------------------------------------------------
# Glyphs, flavour text, share text


def reading_level(reading, top):
    """0-7 bar height for a reading (0 stays 0; anything above top is 7)."""
    if reading <= 0:
        return 0
    return min(7, max(1, -(-reading * 7 // top)))


def reading_fill(reading, top):
    return round(min(1.0, max(0.0, reading / float(top))), 2)


def glyph_for(level, ascii_mode=False):
    if ascii_mode:
        return ASCII_GLYPHS[level // 2]
    return GLYPHS[level]


def result_label(rec):
    return rec["result"]


def build_share_text(rec, mode, number, ascii_mode=False):
    """No positions, no per-tile numbers: just the rhythm of your readings."""
    preset = PRESETS[mode]
    won = rec["result"] == "won"
    used = "%d/%d" % (rec["pings_used"], preset["budget"]) if won else "X/%d" % preset["budget"]
    kind = rec.get("kind")
    if kind == "practice":
        head = "Signal practice %s %s %s" % (rec.get("code", ""), preset["label"].lower(), used)
    elif kind == "archive":
        head = "Signal #%d %s (archive) %s" % (number, preset["label"].lower(), used)
    else:
        head = "Signal #%d %s %s" % (number, preset["label"].lower(), used)
    if not ascii_mode:
        head += " ⚡"
    strip = "".join(
        glyph_for(reading_level(ping[2], preset["top"]), ascii_mode) for ping in rec["pings"]
    )
    if not strip:
        strip = "-"
    if ascii_mode:
        tail = "OK" if won else "X"
    else:
        tail = "✔" if won else "✖"
    return "%s\n%s %s" % (head, strip, tail)


_LINES = {
    "zero": [
        "Static. Nothing on this tile.",
        "Dead air. Good to know.",
        "Silence. That is data too.",
        "Nothing here but the hiss.",
        "The needle does not move.",
    ],
    "low": [
        "A faint carrier, somewhere close by.",
        "Barely a whisper on the dial.",
        "Something is out there. Not near.",
        "Weak, but it is real.",
    ],
    "mid": [
        "A clear signal. Someone is broadcasting.",
        "The needle lifts. Interesting.",
        "Good strength. Not the whole story yet.",
        "That is a busy stretch of sky.",
    ],
    "stacked": [
        "Two fields stacking. That is no single transmitter.",
        "Overlap. The dial climbs higher than one source can push it.",
        "Stronger than any one tower. They are close together.",
        "Fields overlapping. Now we are getting somewhere.",
        "The needle pins. More than one voice here.",
    ],
    "win": [
        "Locked on. Every transmitter found.",
        "Clean copy. The room goes quiet.",
        "All stations accounted for.",
        "Signal confirmed. Nicely done.",
    ],
    "win_par": [
        "At par or better. The operator is showing off.",
        "Textbook. The solver could not do it faster.",
        "Tuned in on the fewest pings. Very tidy.",
        "Right on the money, and quickly.",
    ],
    "win_last": [
        "On the very last ping. Do not tell anyone how close that was.",
        "Final ping, right answer. The tape was running out.",
        "Out of budget and into the win.",
    ],
    "lose": [
        "Lost the signal. Everyone loses one.",
        "Wrong stations. The static wins this round.",
        "Not this time. The board is revealed below.",
        "Dead air on the wrong tiles. Reveal follows.",
        "The transmitters were elsewhere. Study the reveal.",
    ],
    "near": [
        "So close. Part of it was right.",
        "Some of those were right. Not all.",
        "Half a chord. Not the whole one.",
    ],
    "gave_up": [
        "Off the air. The board is revealed.",
        "Signing off early. Here is where they were.",
    ],
    "start": [
        "Receiver on. Ping a tile to listen.",
        "Headphones on. Where would you listen first?",
        "The band is open. Pick a tile.",
        "Someone is out there. Find them.",
    ],
}


def _pick(kind, salt):
    options = _LINES[kind]
    return options[salt % len(options)]


def flavour_for_reading(reading, radius, salt):
    if reading <= 0:
        return _pick("zero", salt)
    if reading > radius:
        return _pick("stacked", salt)
    if reading <= max(1, radius // 2):
        return _pick("low", salt)
    return _pick("mid", salt)
