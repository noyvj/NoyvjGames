"""Lighthouse -- the mysteries and the small oddities, as data: the dread ledger.

THE PROMISE (planning/lighthouse-plan.md section 6, and tests/test_dread_ledger.py which enforces it):
  * Anticipation only. Every odd detail leads to an ordinary, kind or funny explanation.
  * Every mystery has exactly one `resolve` beat, last, warm, inside its `resolves_by` night.
  * No on-screen harm to anyone, ever; nothing here may use the banned words.
  * Nothing punishes the player for being afraid, and the keeper is never alone in the bad way: a ship is always
    safe by morning.
Beat kinds: `odd` (something is off), `moment` (the beat that looks like the horror film's moment, written to stop
just short), `kind` (a plain warm beat that lets the pressure out), `resolve` (the warm explanation).
Each beat: id, kind, window (first and last year-night it may fall on), at (dusk, deep, dawn or morning), fog (it
prefers a hazy or foggy night), text, technique (the design's name for how it unsettles), and optionally visual.
Optional keys: gap (least nights after the beat before), room (a change to the room picture), visual (something the scene
draws), board (a ship the harbour board lists that never comes), font (a different hand for the letters panel), gift (taken when
the beat is shown). Placeholders in text: {passed} ships brought safely by tonight, {hours} lamp-hours tonight, {board} the names
of tonight's ships.
"""

MYSTERIES = {
    "second_light": {
        "title": "The Second Light",
        "season": 0,
        "resolves_by": 12,
        "who": "berit",
        "tags": ["warm", "company"],
        "summary": "A small steady light off the north-east horizon, where the chart shows nothing but open water. It was a retired fisher who could not sleep, keeping you company with a copy of your own beam, and she brought jam.",
        "beats": [
            {"id": "sl1", "kind": "odd", "window": (4, 6), "fog": True, "at": "deep", "technique": "off-chart light",
             "text": "Far off to the north-east, over water where the chart shows nothing, a small steady light has appeared. It was not there at dusk. It does not move.",
             "visual": {"light": [250, 188], "blink": False}},
            {"id": "sl2", "kind": "odd", "window": (6, 8), "fog": True, "at": "deep", "technique": "off-chart light",
             "text": "The small light again, a little nearer. It seems to wait until your beam has passed, and then brighten.",
             "visual": {"light": [330, 204], "blink": False}},
            {"id": "sl3", "kind": "kind", "window": (7, 9), "fog": False, "at": "morning", "technique": "domestic ease",
             "text": "In the morning a gull lands on the rail and eats a whole crab with enormous dignity. The rock is, for a moment, entirely ordinary."},
            {"id": "sl4", "kind": "odd", "window": (8, 9), "fog": True, "at": "deep", "technique": "repetition with drift",
             "text": "The light blinks: two long, one short. A moment later your own beam sweeps over the same patch of water, and it blinks back, two long, one short, a few seconds late, like someone learning you.",
             "visual": {"light": [410, 214], "blink": True}},
            {"id": "sl5", "kind": "moment", "window": (9, 10), "fog": True, "at": "dawn", "technique": "withheld camera",
             "text": "The little light is much closer than it should be, almost at the foot of the rock, low and yellow, and under it the water makes a soft, regular sound. You hold the lamp steady and do not look away. The light stays exactly where the beam does not quite reach.",
             "visual": {"light": [560, 262], "blink": False}},
            {"id": "sl6", "kind": "resolve", "window": (10, 12), "fog": False, "at": "morning", "technique": "reframing",
             "text": "In the first grey light a small boat is bumping gently against your dock. In it sits Berit Sorrel, retired fisher, one hand on a hooded lantern and the other holding a jar of plum preserves. 'Couldn't sleep,' she says. 'I thought you might like the company, so I copied your light. I hope that was all right.' It was. She rows home with the tide, and the jar stays on your table."},
        ],
    },
    "chair": {
        "title": "The Chair Facing the Sea",
        "season": 0,
        "resolves_by": 26,
        "who": "dunstan",
        "tags": ["warm", "funny"],
        "summary": "The chair in the day room turned a little more each week because the floor slopes, a few degrees a year, as the rock settles. The previous keeper thought it was friendly for eleven years, and has decided it is friendly as well.",
        "beats": [
            {"id": "ch1", "kind": "odd", "window": (10, 13), "fog": False, "at": "morning", "technique": "sparse odd objects",
             "text": "The chair by the window is turned a few degrees toward the sea. You are fairly sure it was square to the table when you went to bed.",
             "room": {"chair": 6}},
            {"id": "ch2", "kind": "odd", "window": (14, 17), "fog": False, "at": "morning", "technique": "repetition with drift",
             "text": "The chair has turned a little more. A neat pale arc in the dust on the floor shows where it swung, slowly, all the way round.",
             "room": {"chair": 12}},
            {"id": "ch3", "kind": "kind", "window": (15, 19), "fog": False, "at": "morning", "technique": "domestic ease",
             "text": "A slow, golden morning. The porridge does not burn, the kettle sings, and the whole rock smells of warm bread from a loaf you actually remembered to bake."},
            {"id": "ch4", "kind": "odd", "window": (17, 19), "fog": False, "at": "morning", "technique": "domestic wrongness",
             "text": "The chair has turned again overnight, and the cushion is dented, faintly, as if someone had only just got up from it.",
             "room": {"chair": 18}},
            {"id": "ch5", "kind": "moment", "window": (18, 19), "fog": False, "at": "deep", "technique": "long pause",
             "text": "In the small hours the floor of the day room gives a long, slow creak, and the chair turns another degree in front of you, patient as the tide. You hold very still. It stops, and the room goes back to being a room.",
             "room": {"chair": 24}},
            {"id": "ch6", "kind": "resolve", "window": (19, 26), "fog": False, "at": "morning", "technique": "reframing",
             "text": "You borrow a carpenter's level from the dock and set it on the floor. The bubble slides to one side and stays there. The floor of the day room slopes, a few degrees a year, as the rock settles, and the chair on its worn rockers simply goes where the room goes. The next boat brings a letter from Dunstan Yarrow that is laughing so hard the ink has blotted."},
        ],
    },
    "cistern": {
        "title": "The Knocking at the Cistern",
        "season": 1,
        "resolves_by": 22,
        "who": None,
        "tags": ["warm", "funny", "pet"],
        "summary": "A seal pup had wedged itself behind the cistern pipe and was drumming on it with a shell, extremely pleased with the noise. It now lives on the rock, and has opinions about fish.",
        "beats": [
            {"id": "cs1", "kind": "odd", "window": (12, 14), "fog": False, "at": "deep", "technique": "repetition with drift",
             "text": "From the cistern room below: three taps, a pause, three taps. You go down with the lamp. The pipe is cold and the room is empty, and the taps do not come again."},
            {"id": "cs2", "kind": "odd", "window": (15, 17), "fog": False, "at": "deep", "gap": 3, "technique": "repetition with drift",
             "text": "The taps come again, an hour later than last time: three, a pause, three. You listen from the stairs, and they stop, politely, the moment you stop breathing."},
            {"id": "cs3", "kind": "kind", "window": (16, 19), "fog": False, "at": "morning", "technique": "domestic ease",
             "text": "Toast, and a bright cold morning with the whole sea laid out like a tablecloth. You eat standing in the doorway of the pump room, feeling like someone with nothing to worry about."},
            {"id": "cs4", "kind": "moment", "window": (18, 19), "fog": False, "at": "deep", "gap": 3, "technique": "withheld camera",
             "text": "Tonight the taps come from inside the wall beside the cistern pipe. You press your ear to the cold stone and your own knuckle taps back, once. Something behind the wall shifts, and a small, wet, patient scraping answers you."},
            {"id": "cs5", "kind": "resolve", "window": (19, 22), "fog": False, "at": "morning", "technique": "reframing", "gift": "seal_pup",
             "text": "In the grey morning you move the pipe's cover and find a seal pup, no longer than your arm, wedged in the gap and dragging a shell against the pipe, looking extremely pleased with its drumming. It watches you with enormous dark eyes, then flops into your lap and falls asleep. You are, apparently, now someone's."},
        ],
    },
    "extra_cup": {
        "title": "The Extra Cup",
        "season": 2,
        "resolves_by": 32,
        "who": "ilse",
        "tags": ["warm", "shy"],
        "summary": "The mail-boat captain had been letting herself in at dawn to leave a hot drink for a keeper who never leaves the rock, because she was too shy to knock.",
        "beats": [
            {"id": "ec1", "kind": "odd", "window": (22, 24), "fog": False, "at": "morning", "technique": "domestic wrongness",
             "text": "A second cup stands on the table, set out for someone. It is still warm.",
             "room": {"cup": 1}},
            {"id": "ec2", "kind": "odd", "window": (24, 26), "fog": False, "at": "morning", "technique": "repetition with drift",
             "text": "The second cup again, and now a small plate beside it. The kettle was cold when you woke.",
             "room": {"cup": 1}},
            {"id": "ec3", "kind": "kind", "window": (26, 28), "fog": False, "at": "morning", "technique": "domestic ease",
             "text": "A calm bright morning. Everything is exactly where you left it, and the cup you set out yourself is empty and in the right place. You feel unreasonably pleased about that.",
             "room": {"cup": 1}},
            {"id": "ec4", "kind": "odd", "window": (27, 29), "fog": False, "at": "dawn", "technique": "sparse odd objects",
             "text": "The back door stands open a hand's width, though you locked it. The second cup has tea in it, sweet the way you take it.",
             "room": {"cup": 1}},
            {"id": "ec5", "kind": "moment", "window": (29, 30), "fog": False, "at": "dawn", "technique": "long pause",
             "text": "Footsteps on the stair, slow and quiet, in the grey before light. You wait with the lamp turned low. The latch lifts.",
             "room": {"cup": 1}},
            {"id": "ec6", "kind": "resolve", "window": (30, 32), "fog": False, "at": "morning", "technique": "reframing",
             "text": "It is Ilse Verrick, in her oilskin, holding a tin kettle. She has been letting herself in at dawn for a week to leave a hot drink, because you never leave the rock, and she did not know how to knock. 'Do not make a thing of it,' she says, and then sits down and has the tea with you."},
        ],
    },
    "unsigned": {
        "title": "The Unsigned Letters",
        "season": 2,
        "resolves_by": 38,
        "who": "pip",
        "tags": ["warm", "child"],
        "summary": "A child on the ferry reads the harbour board every evening and writes down what they imagine keeper life is. The mail-boat captain, who cannot keep a secret, has been leaving the letters on your step.",
        "beats": [
            {"id": "ul1", "kind": "odd", "window": (26, 30), "fog": False, "at": "morning", "technique": "wrong handwriting",
             "text": "A letter lies on the doormat, though no boat landed. It describes your night: '{board} went by, and the lamp stayed lit.' It is written in a round, careful hand, and signed with nothing.",
             "font": "hand"},
            {"id": "ul2", "kind": "odd", "window": (29, 32), "fog": False, "at": "morning", "technique": "wrong handwriting",
             "text": "Another letter, in the same round hand, a little bolder: it lists the ships of the night by name and every name is right. Nothing is signed.",
             "font": "hand"},
            {"id": "ul3", "kind": "kind", "window": (30, 34), "fog": False, "at": "morning", "technique": "domestic ease",
             "text": "A quiet morning with nothing in it but sunlight on the stair and the smell of the sea. You sweep the gallery just to be doing something nice."},
            {"id": "ul4", "kind": "odd", "window": (32, 35), "fog": False, "at": "morning", "technique": "wrong handwriting",
             "text": "This morning's letter is shorter: 'You looked tired on the gallery. I hope you slept.' The hand leans forward as if in a hurry. You were on the gallery; nobody could have seen you but the sea.",
             "font": "hand"},
            {"id": "ul5", "kind": "moment", "window": (34, 36), "fog": False, "at": "dawn", "technique": "withheld camera",
             "text": "The letter this morning says only: 'Look out of the window.' You do. A ferry is passing a mile out with every window lit, and at her rail a very small figure is waving a lantern over their head as hard as they can."},
            {"id": "ul6", "kind": "resolve", "window": (35, 38), "fog": False, "at": "morning", "technique": "reframing",
             "text": "Ilse Verrick brings the mail, and at the dock, red to the ears, confesses that she has been leaving a child's letters on your step at dawn. 'It is the one thing I am bad at, keeping a secret. Do not tell Pip I told you.' Pip's own letter is in the bag, signed at last, and the secret is not very secret at all."},
        ],
    },
    "wrong_ship": {
        "title": "The Wrong Ship",
        "season": 3,
        "resolves_by": 40,
        "who": "hesper",
        "tags": ["warm", "ambiguous"],
        "summary": "An old ferry, long since taken apart, listed on the harbour board and passing a mile out in the fog, saluting the light. Her old crew say it is only a hired skiff and a borrowed lamp. The retired captain would rather it were the Lark, and you can never be sure.",
        "beats": [
            {"id": "ws1", "kind": "odd", "window": (32, 35), "fog": False, "at": "deep", "technique": "ghost entries", "board": "Lantern Lark",
             "text": "The harbour board lists a ferry for tonight, the Lantern Lark. You watch for her all night long. She does not come."},
            {"id": "ws2", "kind": "odd", "window": (34, 36), "fog": True, "at": "deep", "technique": "ghost entries", "board": "Lantern Lark",
             "text": "The Lantern Lark is on the board again. There is a line for her in the register in your own handwriting that you do not remember writing. You write beside it: nothing seen."},
            {"id": "ws3", "kind": "kind", "window": (35, 37), "fog": False, "at": "morning", "technique": "domestic ease",
             "text": "A good clean wind, and every ship that passed in the night lifted a hand or a lamp to you. You find yourself lifting one back, alone on the gallery, grinning like an idiot."},
            {"id": "ws4", "kind": "odd", "window": (36, 38), "fog": True, "at": "deep", "technique": "withheld camera",
             "text": "In the fog a long hull slides past a mile out, a row of lit windows along her side. She does not answer the beam and does not seem to look at anything. You count the windows: twelve. The shape stays just past where the light reaches.",
             "visual": {"phantom": [330, 236, 0.7]}},
            {"id": "ws5", "kind": "moment", "window": (38, 39), "fog": True, "at": "deep", "technique": "long pause",
             "text": "The Lantern Lark is back, and tonight she is close enough to hear, a low old engine throb. Your beam finds the paint on her bow, black on white, and her name. One long salute from a horn that has not been blown in years. Then she is not there, and the sea is empty and quiet and very, very calm.",
             "visual": {"phantom": [430, 262, 1.0]}},
            {"id": "ws6", "kind": "resolve", "window": (39, 40), "fog": False, "at": "morning", "technique": "reframing",
             "text": "Hesper Lund, who captained the Lantern Lark for nineteen years, is on your dock when the Gannet comes in, hat in her hands. 'She was retired three winters ago to be taken apart for her brass,' she says. 'On the anniversary the old crew hire a skiff, hang a borrowed lamp on it, and sail her old route a mile out, in the fog, to salute the light we all steered by. Some say that is all it was. I have never asked. I would rather it were the Lark.' She gives you a ship in a bottle, and says the crew are sorry they never stopped to say hello. They are bad at goodbyes."},
        ],
    },
}

# Small oddities that can come on any night once the story is on: each is explained, kindly, within a few nights.
TRIFLES = {
    "tally": {"technique": "wrong-count detail", "at": "morning", "delay": 1,
              "odd": "The tally on the wall says one lamp-hour more than your log. You count again. It still says one more.",
              "resolve": "The last page of the log had stuck to the one before it. The extra hour was written down all along, in your own tidy hand."},
    "door": {"technique": "sparse odd objects", "at": "morning", "delay": 2,
             "odd": "The back door stands open two degrees. You are fairly sure you closed it.",
             "resolve": "The latch is worn thin. The wind has been leaning on it for years, and last night it finally won. You wedge it with a folded chart and feel faintly sorry for the wind."},
    "kettle": {"technique": "domestic wrongness", "at": "morning", "delay": 1,
               "odd": "The kettle is warm when you come into the room, though the stove has been out since last night.",
               "resolve": "The sun came through the west window all afternoon and sat on the black kettle like a cat. It is only the sun. It is lovely."},
    "steps": {"technique": "sparse odd objects", "at": "morning", "delay": 2,
              "odd": "There are wet footprints on the third stair, small and bare, going up. You look for the ones coming down.",
              "resolve": "They are yours, from the tideline yesterday. The stair dries slowly in the damp, and only the going-up half had been scrubbed away."},
    "hum": {"technique": "repetition with drift", "at": "deep", "delay": 2,
            "odd": "Something hums in the lantern room, one low long note that sags and rises. It stops when you listen and starts again when you do not.",
            "resolve": "The wind has found the gap in the lens housing and plays it like a bottle. You stuff a rag in the gap, then take it out again. You like the tune."},
    "shape": {"technique": "withheld camera", "at": "deep", "delay": 1, "fog": True,
              "odd": "At the very edge of the beam, in the fog, something tall stands quite still on the water. The shape stays just past where the light reaches.",
              "resolve": "In the morning the fog lifts from an old channel marker, a bare pole with a very pleased gull on top. The tide had walked it a little closer in the night."},
    "hand": {"technique": "wrong handwriting", "at": "morning", "delay": 2,
             "odd": "A line in the logbook is in a hand that is not yours: 'Oil low.' It is correct.",
             "resolve": "The previous keeper wrote it on the page beneath, and the damp has brought it through. He was right, too. You have been meaning to order more oil."},
    "window": {"technique": "sparse odd objects", "at": "dawn", "delay": 1,
               "odd": "Coming back from the dock at dawn you see a light in the window of your own room. The room is empty.",
               "resolve": "It is the lantern's reflection, thrown across the rock by the glass. You wave at it anyway, and feel less foolish than you expected."},
}
TRIFLE_ORDER = tuple(TRIFLES)

UNEASE_CAP = 100
