"""Stranded -- the day titles, Harbour's narrator lines and the Archive (log entries, found items, recordings). All fiction."""

# day -> (title, narrator line). The narrator is Harbour, the plain voice on the line, who has a bad habit of getting the first
# message wrong. The narrator can be switched off with the site's Story toggle; nothing needed to play is in it.
DAYS = {
    1: ("Static", "Harbour's log. My first night on the Orrin line, and my first message was 'is this thing on?'. It was. She has never let me forget it."),
    2: ("The Count", "Harbour's log. Eleven meal packs, one classified chocolate bar. I have been trusted with numbers before. Never with anything this small."),
    3: ("Bit", "Harbour's log. Day three, and the relay house has something in the corner. I am told to be professional. I am hoping it is a friend."),
    4: ("The Amber Light", "Harbour's log. She is good at joking and bad at being asked things. Today I asked one anyway."),
    5: ("Dust", "Harbour's log. Weather on another moon is a thing you can only watch happen to someone else. I do not recommend it."),
    6: ("Pavel", "Harbour's log. There is a message she has not opened. I have one of those too, from a person I will not name."),
    7: ("Under the Dust", "Harbour's log. The camp is bigger than we thought. It is always bigger than we thought, and quieter."),
    8: ("Three Roads", "Harbour's log. Three ways forward, one of which involves a spanner and the moon. I would like it noted that I stayed calm."),
    9: ("Work", "Harbour's log. A day of doing, which is better than a day of worrying and about as tiring."),
    10: ("The Middle", "Harbour's log. The long middle of anything. Nobody writes songs about it. We sat in it together."),
    11: ("The Last Day Before", "Harbour's log. Tomorrow something happens. Tonight I tried to type calmly, and mostly managed."),
    12: ("The Ending", "Harbour's log. The last day. I will say how it went and then I will keep the line open."),
}

KINDS = ("log", "item", "rec")
KIND_NAME = {"log": "Log entries", "item": "Found items", "rec": "Recordings"}

# id -> (kind, title, text, hint: where to look, shown while unfound)
COLLECT = [
    ("log_01", "log", "Day 1: Landed", "Landed in dust. Dish up, line open to someone called Harbour who asks good questions. Hut is cold. Lander is complaining. Me: fine.", "Day 1: talk her through the mast joint"),
    ("log_02", "log", "The Fuel Line", "A split in the ascent line you could slide a coin into. Told Harbour. Nobody has seen it but the two of us and the coin.", "Day 2: ask what is really wrong, once she trusts you"),
    ("log_03", "log", "Bit's Map", "A robot drew me a map of the wiring on the wall with its own lamp. I have been out-diagrammed by a bin.", "Day 3: ask Bit to scan the wall"),
    ("log_04", "log", "What Harbour Said", "Everyone has a light they wish they'd obeyed. I wrote it inside my glove to prove I can be kind to myself on paper.", "Day 4: be kind about the amber light"),
    ("log_05", "log", "Labels", "Labelled everything: THINGS, MORE THINGS, DO NOT TOUCH. Harbour once sent 'is this thing on' to an emergency band. We are even.", "Day 4: help her label the spares"),
    ("log_06", "log", "After the Storm", "Dust on everything. The camp looks like a bakery. The unopened message sits in the tablet like a loaf nobody will cut.", "Day 6: any path"),
    ("log_07", "log", "Kestrel's Belly", "Pipe, a sleeve, patience, nerves. In ascending order of scarcity. I have two of the four.", "Day 7: look under the lander"),
    ("log_08", "log", "For Whoever's Lonely", "A tin under the bench. Sugar. A tiny paper boat. Someone before me looked after the next person. I intend to be that someone.", "Day 9, waiting: read the note in the tin"),
    ("log_09", "log", "Dear Review Board", "On the morning of launch I overrode an amber warning and wrote 'nominal'. This is the true record.", "Day 10, waiting: the honest debrief"),
    ("log_10", "log", "Wiring", "Eight hours of wiring and not one of them in the film. The coupling fits. Mostly. Like me, in a new hut.", "Day 10: the relay road"),
    ("log_11", "log", "The Weld", "Ugly. Mine. A sleeve and a pipe and a moment of 'good enough' I am trying to talk myself out of.", "Day 10: the lander road"),
    ("item_sketch", "item", "Camp sketch", "A drawing of the camp: a lander with a crooked back, a hut with one window lit, a dish on a stick, a stick figure in a very large coat.", "Day 1: ask about the camp"),
    ("item_bar", "item", "The classified bar", "Dark chocolate with orange. Saved for something that needs it. Still saved.", "Day 2: ask about the chocolate"),
    ("item_plaque", "item", "Sparrow plaque", "Hand-lettered, taped to the bench: KEEP THE DISH POINTED.", "Day 3: leave the robot, read the bench"),
    ("item_bit_lamp", "item", "Bit's cracked lamp", "A crack across the lamp makes the light come out in jagged stars. Bit seems to prefer it.", "Day 5: Bit goes out in the storm"),
    ("item_seal", "item", "Spare seal", "A grey rubber seal from Kestrel's kit, now stuck on a lamp cover with the neatest tape on Orrin.", "Day 5: mend Bit's lamp"),
    ("item_rubbing", "item", "Wall rubbing", "A pencil rubbing of 'Sparrow forgives', and below it, in newer scratches, 'Harbour was here. Typed.'", "Day 7: add a line to the wall"),
    ("item_photo", "item", "A blurry Sparrow", "Out of focus, off-centre, the core room's one green light. Best photo of the trip.", "Day 10: the relay road, after the hum"),
    ("item_boat", "item", "Paper boat", "A tiny boat folded from a sugar wrapper, now the dish's mascot.", "Day 9, waiting: tidy the camp"),
    ("item_ridge", "item", "Ridge snapshot", "The ring over the ridge, taken through a visor that would not stop fogging. Perfect.", "Day 10, waiting: the ridge"),
    ("item_cell", "item", "Survey cell", "A power cell left in the wall by an earlier crew, labelled 'for whoever's next'.", "Day 9: the relay road, the wall cell"),
    ("rec_01", "rec", "Goodnight to the walls", "Walls. It's Ines. Sleep well. Stop creaking. That means you, lander.", "Day 2: leave the walls a goodnight"),
    ("rec_02", "rec", "The amber light", "I turned off the light. I wrote 'nominal'. That is all.", "Day 4: ask which light, and thank her"),
    ("rec_03", "rec", "Counted", "Pieces of messages. 'Still here. Still here. Still.' It was like being counted. Nobody has done that for me since training.", "Day 5: keep talking into the static"),
    ("rec_04", "rec", "Toaster", "Section four: browning dial. Section five: crumb tray. Harbour, I have never been so moved by a crumb tray.", "Day 6: read her something else"),
    ("rec_05", "rec", "To Pavel", "Pavel. You were right and I'm furious. The dish is pointed. See you soon, loser. Love, Inny.", "Day 6: open the message and reply together"),
    ("rec_06", "rec", "Eleven names", "Teo and Ama. Ruiz. Oyelaran. Kaito. And someone who wrote 'back soon'.", "Day 7: the names on the wall"),
    ("rec_07", "rec", "Word game", "LANTERN beats HARBOUR by two letters. I have counted. Rematch tomorrow.", "Day 9, waiting: play the word game to win"),
    ("rec_08", "rec", "For whoever's lonely", "Hello. If you're hearing this, you're having a day. Nudge the dish in the morning. The chocolate is real. The robot is nicer than it looks.", "Day 10, waiting: a message for whoever comes next"),
]
COLLECT_BY_ID = {c[0]: c for c in COLLECT}
COLLECT_IDS = [c[0] for c in COLLECT]
