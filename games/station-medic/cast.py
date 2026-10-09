"""Station Medic -- the crew of Lowlight Station. Names and roles live here; each crew member's short story (their beats)
is added in the crew-files milestone. Everyone is flawed and gentle; nobody dies; the medic is not a hero either."""

# id, name, role
CREW = (
    ("maren", "Maren Oyelaran", "hydroponics tech"),
    ("dov", "Dov Kestrel", "chief engineer"),
    ("imre", "Imre Solace", "cadet"),
    ("nell", "Nell Archer", "quartermaster"),
    ("teo", "Teo Banik", "night cook"),
    ("halloran", "Halloran Pike", "pilot"),
    ("yusra", "Yusra Delacroix", "comms officer"),
    ("kit", "Kit Marlowe", "drone wrangler"),
    ("orla", "Orla Venn", "station commander"),
    ("pell", "Pell Ansgar", "retired surveyor"),
)
CREW_IDS = tuple(c[0] for c in CREW)
CREW_BY_ID = {c[0]: {"id": c[0], "name": c[1], "role": c[2]} for c in CREW}


# Each crew member's story is six short beats. Beat k is told on that crew member's BEAT_AT[k]-th appearance in the authored
# order of shifts (see codex.py), so the order you play a chapter in never changes which beat comes next.
BEAT_AT = (1, 3, 5, 7, 10, 13)

BEATS = {
    "maren": (
        "Maren talks to the seedlings in a low voice and apologises to them when she prunes. She says it keeps her hands steady.",
        "Under her bunk there is a ledger of seed stock that is larger than the one on the station's books. She has been quietly keeping some back.",
        "The last tender was eleven weeks late once, and she watched a whole bay go to waste for want of seed. She says the ledger is not greed, it is a promise to the plants.",
        "She trades a tray of greens to Nell for a recount. Neither of them says what the recount is really for.",
        "Maren opens the ledger to you. \"Take what the sheet needs,\" she says. \"I did not think I could say that out loud.\"",
        "The back bay is planted in full: enough for everyone, and a little over for the lean month. She names the first row after nobody in particular.",
    ),
    "dov": (
        "Dov says it is nothing, whatever it is, and goes back to the engine deck. He has said it three times this month.",
        "There is a cracked-weld report in his drawer, unsigned, with a date from the spring.",
        "He did not file it because a failed inspection might mean the ring is closed and everyone sent home, and for some of the crew home is not a place. He says this very quietly.",
        "He lets you look at his hands. The tremor is old, and he has hidden it in his pockets for years.",
        "He files the report. Orla reads it in silence and approves a repair schedule the same day. Dov goes pale and then, slowly, looks relieved.",
        "He welds the seam himself and leaves a small bead of cooled weld metal on your desk. There is no note.",
    ),
    "imre": (
        "Imre insists he is twenty-one. He says it a little too fast.",
        "His papers say nineteen. When the training school closed he kept quiet about his age so he would not be sent away from the ring.",
        "Teo has started leaving a covered plate at the end of the galley counter, late, with nothing said about why.",
        "Halloran has been teaching him the star charts. Imre writes his first log in his own handwriting and keeps it under his pillow.",
        "He tells Orla the truth about his age. She says she has known since the first week, and that the form will stay in a drawer, where it belongs.",
        "Imre signs his real age on the roster. Nobody makes anything of it, which is the kindest thing anyone could do.",
    ),
    "nell": (
        "Nell counts everything twice and says the numbers aloud, as if the shelf might argue.",
        "The cabinet's count has been one unit high for years. She adds a spare to every shelf, in case of a bad week.",
        "She grew up on a ring where the lean season was long. The spare is how she stays calm. She is not proud of it, and she is not sorry.",
        "She stops adding spares and starts writing them down. \"It is not hoarding,\" she says, \"if it is written.\"",
        "Nell asks you to sign her ledger. It is the first time anyone but her has held the book.",
        "The back shelf is a line in the ledger now, with your initials beside hers.",
    ),
    "teo": (
        "Teo cooks at three in the morning because he cannot sleep, and leaves the pots on the lowest flame.",
        "He talks to the plants in the galley, and the plants, it must be said, have grown.",
        "He used to cook for a crew of forty on a ship that has since been scrapped. He still lays the table for forty, out of habit.",
        "Kit and Imre sit at his table late at night. For a little while it is full.",
        "He sleeps four hours in a row for the first time in a year. He wakes up and tells no one, and cooks something plain.",
        "He cooks at noon, in daylight, and says the soup tastes different. Better, he decides, with some suspicion.",
    ),
    "halloran": (
        "Halloran keeps a pair of flight gloves in his pocket. He has not flown since a hard landing years ago, in which nobody was hurt.",
        "He says the gloves are for warmth.",
        "He lends Imre a battered book of star charts, and watches carefully as it is opened.",
        "He admits the landing. He froze for half a second, everyone walked away, and the half-second has never left.",
        "He sits in the shuttle's cockpit for an hour and does not start it. Afterwards he says it was a very good hour.",
        "He flies the shuttle one slow lap round the ring, at walking pace, and docks it cleanly. Imre claps. Halloran pretends not to hear.",
    ),
    "yusra": (
        "Yusra listens to channel nine, which carries only static. She says it helps her think.",
        "Her sister's survey ship went quiet on channel nine six years ago. No wreck, no word. Just quiet.",
        "She gave herself an hour-by-hour rota for listening, and has missed meals and sleep to keep it. She tells you so with a small, ashamed smile.",
        "Kit builds a little drone that sweeps channel nine on its own, so that Yusra can sleep. She is furious, and then she sleeps for eleven hours.",
        "The drone logs two seconds of faint tone. Yusra writes it down and does not tell anyone for a whole day.",
        "She tells Orla. They answer with the ring's own beacon and keep listening, a little less hard than before.",
    ),
    "kit": (
        "Kit's jokes land half a beat late. The drones are the only ones who laugh, and they laugh on cue.",
        "Kit has named every drone after a bad idea that turned out to work. The oldest is called Probably Fine.",
        "Kit has not taken leave in four years. \"There is nobody to go home to,\" Kit says, and looks at an unopened letter on the shelf.",
        "Kit reads the letter at last. It is an invitation to a wedding that happened two years ago.",
        "Kit sends congratulations, very late. The reply comes within the day: \"Come anyway.\"",
        "Kit puts in for leave on the next tender and leaves Probably Fine behind to keep an eye on things. It does, with some enthusiasm.",
    ),
    "orla": (
        "Orla signs everything with a single initial and never explains. She is brisk, and she does not like to be asked how she is.",
        "Last winter she cut power to the outer ring. People were cold for nine days. She has not forgiven herself.",
        "Dr. Aurel left after Orla cut the infirmary's quotas. She says it to the wall, not to you: \"I asked for the wrong number.\"",
        "She asks you what the infirmary needs, and writes the answer down herself.",
        "She restores the shelf quotas on her own authority and signs the order with her full name, for the first time anyone can remember.",
        "She sleeps in the commander's cabin for the first time since winter. The corridor lights stay on, \"for anyone\".",
    ),
    "pell": (
        "Pell rambles about the moons he surveyed and loses the thread in the middle of a sentence.",
        "He forgets your name twice in one visit and covers it with a map.",
        "He admits that his memory has been going. He writes everyone's name on the back of his hand each morning.",
        "Teo and Maren take it in turns to write the names fresh on his hand while he is still half asleep.",
        "Pell draws a chart of Lowlight Station from memory. It is perfect, and every person on it has the right name.",
        "He gives you the chart, signed: \"To the medic, whose name I have written correctly.\"",
    ),
}

# Tally, the second medic robot, appears from chapter 6. Its beats are told on the shifts where it is on duty (see codex.py).
TALLY_BEATS = (
    "Tally was an inventory robot for eleven years before the ring reassigned it. It counts everything it passes and does not seem to mind.",
    "It keeps a tally of things it has helped with. Today it adds one, and its small display flickers, which it calls a cosmetic fault.",
    "Tally asks why a person who says they are fine never sits down. You do not have a good answer. It writes that down too.",
    "It steadies a patient for a whole shift without moving and says afterwards that the shift was one of its best. It does not say why.",
    "The count on its display reads a number you did not expect. \"People I have kept company with,\" says Tally. \"It seemed the right thing to count.\"",
)

# One note per chapter: the medic's own log, unlocked when every shift of the chapter is done. The medic is not a hero either.
STATION_NOTES = (
    "Log, first week. Dr. Aurel's keys are still on the hook. I have not moved them. I have also not eaten dinner twice this week, and I am writing that here so I can pretend it did not happen.",
    "Log. Scans are the part of the job I trust most. A reading does not care who is asking. People, on the other hand, say fine and mean three other words.",
    "Log. Charts are a way of listening to someone you cannot ask. Dr. Aurel wrote notes in the margins. I am starting to answer them.",
    "Log. The supply tender is late again. Nell and Maren are not speaking about the thing they are both being very careful not to speak about. I have decided it is not my place. I keep deciding that.",
    "Log. The cold room is quiet at night. I sit in the doorway more than I need to. It is the only room in the ring where I do not have to be good company.",
    "Log. Tally asked why I stand at the door instead of the bedside. I said it was for a better view. Tally wrote that down in its book and did not argue.",
    "Log. Two things at once, in one body. I think I know what that is like. I do not say so to anyone, which I suspect is the point.",
    "Log, the long night. Everyone is settled. The shelf is thin, the tender is nearly here, and I have, for once, sat down at the bedside. Dr. Aurel's keys are still on the hook. I think I will leave them there.",
)
