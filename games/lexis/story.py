"""Lexis -- the story spine, as data.

An original ship, crew and set of worlds (nothing from any existing franchise). The story is what pulls the
player forward and rewards each decoded language; it is never the puzzle. Two rules keep it honest:

  * A beat is unlocked by contact with a planet and by nothing else, so it is derived from the contact flags
    and never stored in the save (a loaded save and a played one cannot disagree).
  * No beat, and not the brief, ever says what any sign means. It speaks of the worlds in ordinary words;
    tests/test_story.py scans every line for the true glosses of every sign and fails the build on a leak.
    (The contact report in report.py is the one place the game states the answers, after the fact.)

House style: plain and warm, no hype, no exclamation marks, no dashes used as punctuation.
"""

SHIP = "Marigold"

BRIEF = {
    "title": "Mission brief",
    "lines": (
        ("Ship's log", "The survey ship Marigold carries eleven people and one job: to say hello properly to "
                       "worlds that are already talking. You are the communications officer. Nothing aboard can "
                       "translate for you, so every word you learn, you learn by watching what happens when it is used."),
        ("Captain Ines Varga", "I do not need a lecture on grammar. I need to tell them yes or no, and I need them "
                               "to understand which one I meant."),
        ("Engineer Dov Mensah", "Give me a number I can plan around. Hours, crates, anything. Give me a number "
                                "and I will take care of the rest."),
        ("Navigator Pell", "Take your time. The next world is not going anywhere, and neither are we until you say so."),
    ),
}

# One beat per planet, unlocked by contact with that planet, then a closing beat that also unlocks with the
# last planet in range. `planet` is the contact key; `id` is stable (the view and the tests key on it).
BEATS = (
    {
        "id": "planet1", "planet": "pulse", "title": "Planet 1: the quiet beacon",
        "lines": (
            ("Ship's log", "The beacon on the quiet world had been repeating itself for longer than the Marigold "
                           "has existed. When you answered in its own marks, it stopped repeating and started "
                           "responding. Whoever built it wanted a visitor to be able to learn it, and you did."),
            ("Captain Ines Varga", "That is a yes in any language. Log it as first contact."),
            ("Engineer Dov Mensah", "It did exactly what you told it, down to the last one. I like a world that does that."),
            ("Navigator Pell", "There is a second world on the chart, a long way out, sending something stranger. "
                               "It is not pulses. It looks more like writing."),
        ),
    },
    {
        "id": "planet2", "planet": "compound", "title": "Planet 2: the market world",
        "lines": (
            ("Ship's log", "The market world does not send pulses. It sends signs, and each sign is built from "
                           "parts. You learned the parts, then read signs nobody had shown you, and the tray "
                           "filled with exactly what you meant."),
            ("Captain Ines Varga", "They gave us something we never taught them. That is when I stop worrying "
                                   "that this is luck."),
            ("Engineer Dov Mensah", "Two things I did not expect to see on that tray, and there they are. Good."),
            ("Navigator Pell", "A station on a third world is only a few days out. Its messages carry numbers. "
                               "You will like those."),
        ),
    },
    {
        "id": "planet3", "planet": "bridge", "title": "Planet 3: the counting station",
        "lines": (
            ("Ship's log", "The counting station speaks in messages you could almost read already: things from the "
                           "market world, numbers from the beacon, and a few extra marks that change what a "
                           "message does. You worked out those marks, and the station kept an exact tally to prove it."),
            ("Captain Ines Varga", "The right amount of the right thing, and the station knows that we know. "
                                   "Tell them thank you."),
            ("Engineer Dov Mensah", "Now that is bookkeeping I can trust. I would hand them our whole inventory."),
            ("Navigator Pell", "The chart is clear to the edge of our range. Nothing else is close enough to reach on this trip."),
        ),
    },
    {
        "id": "closing", "planet": "bridge", "title": "Heading on",
        "lines": (
            ("Ship's log", "The Marigold holds her place above the counting station for one more night. Three "
                           "languages, three worlds, and a crew that has stopped wondering whether the signals mean "
                           "anything. Past the edge of the chart there are more worlds, fainter and further, and "
                           "the receivers have begun to catch the first marks of two of them. They are not ready "
                           "to be read yet."),
            ("Captain Ines Varga", "Log it for the next voyage: there are at least two more voices out there, and "
                                   "they are patient. So are we."),
            ("Engineer Dov Mensah", "I will start on the antenna. Two more worlds means a better ear."),
            ("Navigator Pell", "Plotting the course now. It will be a long way round, and I am looking forward to it."),
        ),
    },
)


def unlocked_beats(contact):
    """The beats earned so far, oldest first. `contact` maps planet key to bool."""
    return [beat for beat in BEATS if contact.get(beat["planet"])]


def _entry(beat):
    return {"id": beat.get("id", "brief"), "title": beat["title"],
            "lines": [{"speaker": speaker, "text": text} for speaker, text in beat["lines"]]}


def view(contact):
    """What the page draws: the brief (always) and the unlocked beats, newest first."""
    return {
        "brief": _entry(BRIEF),
        "beats": [_entry(beat) for beat in reversed(unlocked_beats(contact))],
    }


def all_text():
    """Every line of story text, for the tests that scan for answer leaks and house style."""
    lines = [text for _speaker, text in BRIEF["lines"]]
    for beat in BEATS:
        lines.append(beat["title"])
        lines.extend(text for _speaker, text in beat["lines"])
    return lines
