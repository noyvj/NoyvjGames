"""Evidence Hunt -- the vocabulary: six pieces of evidence (each read with one piece of equipment), twelve invented spirit kinds
(three evidence and two behaviours each), six room features that fool a reading, and eight keepsakes. Everything here is
fiction: the kinds, the rules and the houses are made up, and nothing is ever harmed.

Evidence and equipment share one index (0-5): the thermometer reads cold, the EMF reader reads charge, and so on."""

# id, name, equipment name, equipment letter, positive reading, clear reading
EVIDENCE = (
    ("cold", "Cold spot", "Thermometer", "T", "The thermometer drops well below the rest of the house.", "The thermometer sits steady."),
    ("charge", "Stray charge", "EMF reader", "E", "The needle on the EMF reader jumps and trembles.", "The needle lies flat."),
    ("script", "Writing", "Notebook", "N", "New lines have appeared on the page you left open.", "The page you left open stays blank."),
    ("lights", "Faint lights", "Camera", "C", "A pale smear of light hangs in the photograph.", "The photograph is plain and dark."),
    ("prints", "Prints", "Fine dust", "D", "Small prints show in the dust.", "The dust lies smooth."),
    ("glow", "Glow marks", "Violet lamp", "L", "The violet lamp lifts pale smudges off the wall.", "The violet lamp shows only plain paint."),
)
EV_IDS = tuple(e[0] for e in EVIDENCE)
EV_INDEX = {e[0]: i for i, e in enumerate(EVIDENCE)}
EV_NAME = tuple(e[1] for e in EVIDENCE)
GEAR_NAME = tuple(e[2] for e in EVIDENCE)
GEAR_LETTER = tuple(e[3] for e in EVIDENCE)
POSITIVE = tuple(e[4] for e in EVIDENCE)
CLEAR = tuple(e[5] for e in EVIDENCE)
GEAR_HOW = (
    "Left in the room to see how cold it gets.", "Held up in the room to see if the needle stirs.",
    "Left open on a table to see if anything is written.", "Used to take a photograph of the room.",
    "Dusted over a surface to see what crosses it.", "Shone along the walls to find marks.",
)

# id, name, the client's line, what it means for the rules
BEHAVIOURS = (
    ("tidy", "Tidy", "Things are always put back in order.", "Straightens and squares things."),
    ("mover", "Mover", "Things get moved about when no one is looking.", "Moves small objects about."),
    ("shy", "Shy", "It slips away whenever someone is in the room.", "Slips away from people."),
    ("curious", "Curious", "It follows visitors from room to room.", "Follows visitors about."),
    ("fond", "Fond of one room", "It keeps to one room only.", "Keeps to exactly one room."),
    ("roamer", "Roams", "It wanders between rooms.", "Is restless in two or more rooms."),
)
BH_IDS = tuple(b[0] for b in BEHAVIOURS)
BH_NAME = {b[0]: b[1] for b in BEHAVIOURS}
BH_LINE = {b[0]: b[2] for b in BEHAVIOURS}
BH_RULE = {b[0]: b[3] for b in BEHAVIOURS}
# what a keepsake shows about a behaviour when you look at it
BH_KEEPSAKE = {
    "tidy": "It is squared exactly to the edge of the shelf, as if someone straightens it every day.",
    "mover": "The family say it turns up somewhere new every morning.",
    "shy": "It is tucked well back, out of the light, as though it prefers not to be seen.",
    "curious": "It always faces the door, as if waiting to see who comes in.",
}

# id, name, evidence (three), behaviours (two), emblem (sides, hue), who they were
KINDS = (
    ("hearthkeeper", "Hearthkeeper", ("cold", "charge", "script"), ("tidy", "fond"), (6, 28),
     "Kept the fire in for half the street. Still checks that the hearth is swept, and is only ever cold because they are looking after the cold."),
    ("glimmer", "Glimmer", ("lights", "prints", "glow"), ("curious", "roamer"), (5, 190),
     "A lamp-lighter who walked every room each evening. The lights follow visitors because they never could leave anyone in the dark."),
    ("draughtling", "Draughtling", ("cold", "charge", "prints"), ("mover", "shy"), (7, 205),
     "A small, shy presence that loves a window left ajar. It moves things only to make room for the breeze."),
    ("scrivener", "Scrivener", ("script", "lights", "glow"), ("tidy", "curious"), (8, 48),
     "A letter-writer who answered every note ever left on the mat, and cannot stop being helpful with the tidy filing."),
    ("candlewick", "Candlewick", ("cold", "script", "lights"), ("shy", "fond"), (5, 38),
     "Read by one candle in one chair for forty winters. It never goes far, and it only wants the page to stay lit."),
    ("pacer", "Pacer", ("charge", "prints", "glow"), ("mover", "roamer"), (6, 140),
     "A night worker who walked the floors to settle a baby, and then to settle the house. The footsteps are only company."),
    ("lullwisp", "Lullwisp", ("cold", "script", "prints"), ("tidy", "roamer"), (7, 270),
     "Tucked in every bed on every floor. The cold is the draught from the window it always leaves open a crack, for air."),
    ("tangle", "Tangle", ("charge", "lights", "glow"), ("mover", "curious"), (5, 320),
     "A knitter whose wool is always in the wrong room. It follows visitors to hand them the end of the thread."),
    ("mothlight", "Mothlight", ("cold", "lights", "prints"), ("shy", "roamer"), (8, 170),
     "Drawn to every lit window in the house and a little embarrassed about it. It is gone the moment anyone looks."),
    ("ledger", "Ledger", ("charge", "script", "glow"), ("tidy", "mover"), (6, 62),
     "A shopkeeper who kept the books in perfect order and the stock always one shelf out. Both habits are a kind of care."),
    ("hushling", "Hushling", ("cold", "prints", "glow"), ("shy", "curious"), (7, 245),
     "A child who loved hide and seek. It follows you, then hides when you turn round, and wants you to find it."),
    ("spindle", "Spindle", ("charge", "script", "lights"), ("fond", "mover"), (5, 10),
     "A seamstress who loved one room by its window. It moves the thread and the buttons only to find the good light."),
)
KIND_IDS = tuple(k[0] for k in KINDS)
KIND_INDEX = {k[0]: i for i, k in enumerate(KINDS)}
KIND_NAME = {k[0]: k[1] for k in KINDS}
KIND_EVIDENCE = {k[0]: frozenset(EV_INDEX[e] for e in k[2]) for k in KINDS}
KIND_BEHAVIOURS = {k[0]: frozenset(k[3]) for k in KINDS}
KIND_EMBLEM = {k[0]: k[4] for k in KINDS}
KIND_NOTE = {k[0]: k[5] for k in KINDS}

# id, name, the evidence it fools, what the room shows
FEATURES = (
    ("draught", "Draughty window", 0, "A draughty window leaks cold air into this room."),
    ("wiring", "Old wiring", 1, "Old wiring hums in the walls of this room."),
    ("desk", "Writing desk", 2, "A writing desk here is covered in someone else's old notes."),
    ("streetlamp", "Street-lit window", 3, "A street lamp flickers through the glass in this room."),
    ("damp", "Damp floor", 4, "The floor here is damp and smears any dust."),
    ("paint", "Glow paint", 5, "Old luminous paint speckles the walls of this room."),
)
FT_IDS = tuple(f[0] for f in FEATURES)
FT_INDEX = {f[0]: i for i, f in enumerate(FEATURES)}
FT_NAME = {f[0]: f[1] for f in FEATURES}
FT_FOOLS = {f[0]: f[2] for f in FEATURES}
FT_TEXT = {f[0]: f[3] for f in FEATURES}

# id, name, what it is, what returning it says
KEEPSAKES = (
    ("musicbox", "Music box", "a small brass music box", "You set the music box where the afternoon sun reaches it. The lid is open a little, and the room feels like a held breath let go."),
    ("handmirror", "Hand mirror", "a silver hand mirror", "You prop the hand mirror on the dresser facing the window. The room looks back brighter than before."),
    ("brasskey", "Brass key", "a worn brass key", "You hang the brass key on the empty hook by the door. It swings once and is still, as though it fits."),
    ("teacup", "Teacup", "a chipped blue teacup", "You set the teacup on its saucer by the kettle. A faint warmth settles on the table."),
    ("thimble", "Thimble", "a dented silver thimble", "You leave the thimble beside the sewing basket. The thread beside it straightens itself, politely."),
    ("paperweight", "Paperweight", "a glass paperweight", "You set the paperweight on the open letters. The pages stay put, for the first time in years."),
    ("buttontin", "Button tin", "an old biscuit tin of buttons", "You put the button tin back on the lowest shelf. Every button is sorted by colour by morning."),
    ("woolbasket", "Wool basket", "a basket of grey wool", "You tuck the wool basket beside the chair. The needles click once, contentedly, and stop."),
)
KS_IDS = tuple(k[0] for k in KEEPSAKES)
KS_NAME = {k[0]: k[1] for k in KEEPSAKES}
KS_WHAT = {k[0]: k[2] for k in KEEPSAKES}
KS_RETURN = {k[0]: k[3] for k in KEEPSAKES}

# room type -> (default name, what you see on entering). Floors are set by the layout.
ROOM_TYPES = {
    "hall": ("Hall", "Coats hang on pegs and the boards are worn pale down the middle."),
    "kitchen": ("Kitchen", "A kettle stands cold on the stove and the tiles shine faintly."),
    "parlour": ("Parlour", "Two armchairs face a cold fireplace and a mantel with nothing on it."),
    "dining": ("Dining room", "A long table is laid for a meal that was never served."),
    "study": ("Study", "Shelves reach the ceiling and a green lamp leans over the desk."),
    "library": ("Library", "Ladders on rails, and a smell of paper and polish."),
    "bedroom": ("Bedroom", "The bed is made so tightly it looks drawn on."),
    "nursery": ("Nursery", "A cot, a rocking horse and wallpaper of small boats."),
    "bathroom": ("Bathroom", "A clawfoot bath and a mirror misted at the edges."),
    "pantry": ("Pantry", "Jars in rows, each with a hand-lettered label."),
    "cellar": ("Cellar", "Cool brick, a coal chute and a faint smell of apples."),
    "attic": ("Attic", "Slanted beams, a dressmaker's dummy and old trunks."),
    "landing": ("Landing", "A narrow window at the turn of the stairs looks out on the dark garden."),
    "conservatory": ("Conservatory", "Glass walls, ferns in pots and a view of the night sky."),
    "workshop": ("Workshop", "A bench of small tools, each hung on its own nail."),
    "boiler": ("Boiler room", "A squat iron boiler ticks as it cools."),
    "chapel": ("Chapel", "Four plain pews and a window of coloured glass."),
    "ballroom": ("Ballroom", "A polished floor, tall mirrors and chairs along the wall."),
    "porch": ("Porch", "A boot scraper, a row of umbrellas and a lamp on a hook."),
    "gallery": ("Gallery", "Portraits of people nobody can name look out in the half dark."),
    "scullery": ("Scullery", "A deep stone sink and a drying rack of cloths."),
    "store": ("Storeroom", "Crates, string and a ledger on a nail."),
    "shop": ("Shop floor", "Glass counters, a brass till and shelves in careful order."),
    "classroom": ("Classroom", "Desks in rows, a globe and a blackboard wiped clean."),
    "cloaks": ("Cloakroom", "A row of small hooks, each with a name above it."),
    "loft": ("Loft", "A sloping roof, a tall mirror and boxes tied with string."),
    "den": ("Den", "A low sofa, a map on the wall and a worn rug."),
    "music": ("Music room", "A piano with its lid closed and a stool turned a little aside."),
    "sewing": ("Sewing room", "A treadle machine, a basket of cotton and a window full of light."),
    "stairs": ("Stairwell", "A long stair with a polished rail and a runner of faded red."),
    "hallway": ("Back hall", "A narrow passage with a flagstone floor and a door to the garden."),
    "dairy": ("Dairy", "Cold slate shelves and wide shallow pans."),
    "smoking": ("Smoking room", "Leather chairs, a low table and a faint smell of cedar."),
    "laundry": ("Laundry", "Copper tubs, a mangle and washing lines strung overhead."),
    "tower": ("Tower room", "A round room at the top of the house with windows on every side."),
}
