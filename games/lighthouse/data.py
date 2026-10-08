"""Lighthouse -- the fixed rules and tables. Every number a rule uses lives here so tests and the balance bots
read the same values the engine does. One tick is ten in-game minutes; a night is 36 to 56 ticks."""

TICK_MINUTES = 10
NIGHTS_PER_SEASON = 10
NIGHTS_PER_YEAR = 40
SEASONS = ("Spring", "Summer", "Autumn", "Winter")
NIGHT_LEN = (42, 36, 48, 56)                 # ticks in a night, by season (winter nights are the longest)
NIGHT_START_MIN = (1200, 1290, 1170, 1080)   # clock minute at tick 0 (20:00, 21:30, 19:30, 18:00)
FESTIVAL_NIGHT = 20                          # night of the year when every boat stays in harbour for the supper

# ---- the lamp ------------------------------------------------------------------------------------------
LEVELS = ("dim", "standard", "bright", "storm")
LEVEL_LABELS = ("Dim", "Standard", "Bright", "Storm")
LEVEL_REACH = (3, 5, 7, 9)                   # how far the beam carries on a clear night
LEVEL_BURN = (0.6, 1.0, 1.6, 2.6)            # oil burnt per tick
BLOCKS = ("Dusk", "Deep night", "Dawn")      # a night plan sets one lamp level for each third of the night

CLOCK_BASE = 24                              # ticks one winding lasts
CLOCK_WEIGHTS = 36                           # with the winding weights upgrade
FIXED_CONE_DIVISOR = 2                       # a stopped beam is a fixed cone, half as useful

# ---- weather -------------------------------------------------------------------------------------------
CONDS = ("clear", "haze", "fog", "squall", "storm")
COND_LABELS = ("Clear", "Haze", "Fog", "Squall", "Storm")
COND_ICONS = ("☀", "≈", "☁", "☂", "⚡")   # sun, haze, cloud, umbrella, bolt (never colour alone)
COND_PENALTY = (0, 1, 2, 2, 3)               # reach lost to the weather
SEVERITY_LABELS = ("Calm", "Unsettled", "Rough", "Dangerous")
SEVERITY_WEIGHTS = (                         # calm, unsettled, rough, dangerous by season
    (3.0, 4.0, 2.0, 1.0),
    (5.0, 3.0, 1.0, 0.5),
    (2.0, 4.0, 3.0, 2.0),
    (1.0, 3.0, 3.0, 4.0),
)
SQUALL_DAMAGE_CHANCE = 0.04                  # per part per tick
STORM_DAMAGE_CHANCE = 0.16

# ---- the station ---------------------------------------------------------------------------------------
PARTS = ("tower", "lantern", "rail", "dock", "cistern")
PART_LABELS = {"tower": "Tower", "lantern": "Lantern glass", "rail": "Gallery rail", "dock": "Dock", "cistern": "Cistern"}
PART_ICONS = {"tower": "♖", "lantern": "◇", "rail": "≡", "dock": "⚓", "cistern": "◯"}
START_STRUCTURE = {"tower": 80, "lantern": 70, "rail": 60, "dock": 65, "cistern": 75}
SUPPLIES = ("food", "tar", "glass", "timber")
SUPPLY_LABELS = {"food": "Food", "tar": "Tar", "glass": "Glass", "timber": "Timber"}
SUPPLY_CAP = 24
OIL_CAP = 200
OIL_CAP_BIG = 280
DAY_REPAIR = {   # what a day repair costs, and heals 35
    "tower": {"timber": 1, "tar": 1}, "lantern": {"glass": 2}, "rail": {"timber": 1},
    "dock": {"timber": 2}, "cistern": {"tar": 2},
}
NIGHT_PATCH = {  # what patching in the dark costs, and heals 10 (8 when the keeper's task does it)
    "tower": {"timber": 1}, "lantern": {"glass": 1}, "rail": {"timber": 1}, "dock": {"timber": 1}, "cistern": {"tar": 1},
}
DAY_REPAIR_HEAL = 35
NIGHT_PATCH_HEAL = 10
AUTO_PATCH_HEAL = 8
DAY_SLOTS = 5

START_OIL = 150
START_SUPPLIES = {"food": 6, "tar": 3, "glass": 2, "timber": 3}
EMERGENCY_OIL = 25                           # the reserve flask the station always keeps; costs a point of reputation
ENERGY_MAX = 100
TIRED = 20                                   # below this the keeper works at half strength (the light is never blocked)

# ---- ships ---------------------------------------------------------------------------------------------
# need: the effective reach the ship needs to pick the light out. window: ticks it spends near the rock.
SHIP_KINDS = {
    "fisher": {"label": "Fishing boat", "icon": "△", "need": 5, "window": 6, "rep": 1, "salvage": 1},
    "ferry": {"label": "Ferry", "icon": "□", "need": 4, "window": 5, "rep": 1, "salvage": 1},
    "cargo": {"label": "Cargo ship", "icon": "▬", "need": 4, "window": 7, "rep": 1, "salvage": 2},
    "yacht": {"label": "Yacht", "icon": "◇", "need": 5, "window": 5, "rep": 1, "salvage": 2},
    "mail": {"label": "Mail boat", "icon": "✉", "need": 5, "window": 6, "rep": 1, "salvage": 1},
}
SHIP_ORDER = ("fisher", "ferry", "cargo", "yacht")
SHIP_WEIGHTS = (     # by season: fisher, ferry, cargo, yacht
    (3.5, 3.5, 2.0, 1.0),
    (2.5, 4.5, 1.0, 3.5),
    (3.5, 3.5, 3.0, 0.5),
    (2.0, 2.0, 5.0, 0.0),
)
SHIPS_PER_NIGHT = ((1, 3), (2, 3), (2, 4), (2, 3))   # by severity, inclusive range
MAIL_NAME = "Gannet"
FIRST_MAIL_NIGHT = 3
DOCK_MIN = 30                                 # the mail boat will not tie up at a broken dock
MAIL_WIND_MAX = 3                             # nor in a gale

# ---- supplies by boat ------------------------------------------------------------------------------------
BOAT_CRATES = 12
CRATE_UNITS = {"oil": 40, "food": 3, "timber": 2, "tar": 2, "glass": 1}
CRATE_KINDS = ("oil", "food", "timber", "tar", "glass")
DEFAULT_ORDER = {"oil": 5, "food": 2, "timber": 2, "tar": 1, "glass": 2}

# ---- reputation ("The Light") -----------------------------------------------------------------------------
REP_TITLES = ((0, "Unknown"), (10, "Noted"), (30, "Trusted"), (60, "Known"), (100, "Beloved"))
REP_CAP = 999

# ---- upgrades (spent with salvage) -------------------------------------------------------------------------
UPGRADES = (
    {"id": "lens", "name": "Better lens", "cost": 8, "text": "The beam reaches one step further in every weather."},
    {"id": "wick", "name": "Oil-saver wick", "cost": 6, "text": "The lamp burns a fifth less oil at every level."},
    {"id": "weights", "name": "Winding weights", "cost": 6, "text": "One winding lasts 36 ticks instead of 24."},
    {"id": "cistern", "name": "Bigger cistern", "cost": 10, "text": "A cool vault for 80 more litres of oil, and the keeper rests a little better."},
    {"id": "bell", "name": "Fog bell", "cost": 12, "text": "In fog the bell, rung on its own pulse, cuts the fog's cost to the beam by one."},
    {"id": "shutters", "name": "Storm shutters", "cost": 10, "text": "The lantern glass and the rail take half the storm damage."},
    {"id": "boat", "name": "Small boat", "cost": 8, "text": "Helping a damaged ship costs one supply instead of two."},
    {"id": "greenhouse", "name": "Greenhouse box", "cost": 8, "text": "Unlocks the day task tend the box: +2 food."},
    {"id": "vane", "name": "Wind vane", "cost": 6, "text": "The barometer is right more often, and its band narrows."},
)
UPGRADE_IDS = tuple(u["id"] for u in UPGRADES)
RARE_UPGRADE_COST = 10                        # an upgrade at least this dear asks for confirmation

# ---- incidents -------------------------------------------------------------------------------------------
INCIDENT_CHANCE = 0.025
INCIDENT_KINDS = ("smoke", "shutter", "sticks")
INCIDENT_TEXT = {
    "smoke": "The wick smokes and the glass is clouding.",
    "shutter": "A shutter works loose and starts to bang.",
    "sticks": "The clockwork sticks and begins to labour.",
}
INCIDENT_FIX = {
    "smoke": "You trim the wick and wipe the glass.",
    "shutter": "You latch the shutter back.",
    "sticks": "You free the clockwork with a drop of oil.",
}
INCIDENT_LIFE = {"smoke": 6, "shutter": 4, "sticks": 8}

# ---- keeper -------------------------------------------------------------------------------------------------
ENERGY_WIND = 2
ENERGY_TEND = 2
ENERGY_PATCH = 4
WATCH_DRAIN = 0.25
REST_GAIN = 0.35
DAY_REPAIR_ENERGY = 8
DAY_REST_GAIN = 30
HUNGRY_COST = 15
COMFORT_MAX = 10

START_ENERGY = 100
LOG_KEEP = 120
