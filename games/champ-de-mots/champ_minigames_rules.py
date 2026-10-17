"""Tuning numbers for the five timed arcade games (durations, lives, base points, patience, combo steps). Pure data.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

BLITZ_DURATION_SECONDS = 60
BLITZ_STARTING_LIVES = 3
BLITZ_BASE_POINTS = 10
BLITZ_COMBO_STEP = 3  # every N correct-in-a-row raises the multiplier once
BLITZ_COMBO_BONUS_PER_STEP = 0.5
BLITZ_MAX_COMBO_STEPS = 4  # multiplier caps at 1 + 4*0.5 = 3.0x


RACER_TOTAL_STEPS = 10
RACER_RIVAL_TICKS_PER_STEP = 3  # the rival's fixed pace: 1 step every 3 real seconds


BOUTIQUE_TOTAL_CUSTOMERS = 15
BOUTIQUE_STARTING_PATIENCE = 12  # seconds for the first customer
BOUTIQUE_MIN_PATIENCE = 6  # the pace never speeds up past this floor
BOUTIQUE_PATIENCE_STEP = 1  # shaved off the patience clock per correct sale
BOUTIQUE_OPTION_COUNT = 4
BOUTIQUE_BASE_POINTS = 10


CAFE_TOTAL_CUSTOMERS = 15
CAFE_STARTING_PATIENCE = 12
CAFE_MIN_PATIENCE = 6
CAFE_PATIENCE_STEP = 1
CAFE_OPTION_COUNT = 4
CAFE_BASE_POINTS = 10
CAFE_TWIST_BONUS_POINTS = 5
CAFE_TWIST_INTERVAL = 3  # every Nth customer also gets the passé composé twist


CAFE_STAGE_PICK = "pick"
CAFE_STAGE_TWIST = "twist"


SPRINT_DURATION_SECONDS = 60
SPRINT_STARTING_LIVES = 3
SPRINT_BASE_POINTS = 10
SPRINT_COMBO_STEP = 3  # every N correct-in-a-row raises the multiplier once
SPRINT_COMBO_BONUS_PER_STEP = 0.5
SPRINT_MAX_COMBO_STEPS = 4  # multiplier caps at 1 + 4*0.5 = 3.0x
