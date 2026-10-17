"""The live state of the arcade minigames: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`blitz_active = True`, `blitz_score += 10`) lives only here, and
every other module reads and writes it as `runstate.<name>` (each module starts with `import champ_minigames_runstate as runstate`).
Never `from champ_minigames_runstate import blitz_active`: that copies the name once and goes stale the moment the variable is
replaced. Lists, dicts and sets that are only changed in place can stay in the module that owns them.

LIVE_NAMES at the bottom lists every such variable. minigames.py forwards `minigames.<name>` reads and writes to this module for
exactly those names (tests use minigames.blitz_active and so on). Add a new rebound variable here AND to LIVE_NAMES.
"""

from champ_minigames_rules import (
    BLITZ_DURATION_SECONDS, BLITZ_STARTING_LIVES, BOUTIQUE_STARTING_PATIENCE, CAFE_STAGE_PICK,
    CAFE_STARTING_PATIENCE, SPRINT_DURATION_SECONDS, SPRINT_STARTING_LIVES,
)


# --- wiring from game.py (avoids the circular import noted above) ----------

_farm = None
_generate_question = None
_variants_for = None
_record_practice = None
_credit_plot_id = None
_credit_item = None
_credit_reset = None
_credit_text = None
_plot_for_fr = None
_pref_get = None
_pref_set = None
_check_answer = None


blitz_open = False  # panel toggled open, independent of a live run
blitz_active = False  # a 60s run is currently in progress
blitz_score = 0
blitz_best_score = 0  # best across runs *this page load* -- session-only
blitz_lives = BLITZ_STARTING_LIVES
blitz_combo = 0
blitz_time_remaining = BLITZ_DURATION_SECONDS
blitz_question = None
blitz_end_reason = None  # None | BLITZ_END_TIME | BLITZ_END_LIVES


blitz_note = ""  # what the last answer did to its plot


_blitz_candidates_cache = None


_blitz_rendered_question = None  # identity tracker -- see the note below


racer_open = False
racer_active = False
racer_player_position = 0
racer_rival_position = 0
racer_tick_count = 0  # ticks since the rival's last step
racer_question = None
racer_result = None  # None | True | False -- last attempt, transient UI flash
racer_end_reason = None  # None | RACER_END_PLAYER | RACER_END_RIVAL


racer_note = ""  # what the last answer did to its plot


_racer_candidates_cache = None


_racer_rendered_question = None  # identity tracker, same fix Blitz needed


boutique_open = False
boutique_active = False
boutique_served = 0
boutique_missed = 0
boutique_score = 0
boutique_patience_max = BOUTIQUE_STARTING_PATIENCE
boutique_patience_remaining = BOUTIQUE_STARTING_PATIENCE
boutique_order = None  # {"order_en", "answer", "choices"} | None
boutique_last_result = None  # None | True | False -- last customer, transient UI flash


boutique_note = ""  # what the last sale did to its plots


_boutique_garments_cache = None
_boutique_colours_cache = None


_boutique_rendered_order = None  # identity tracker -- see Blitz's own build note on why


cafe_open = False
cafe_active = False
cafe_served = 0
cafe_missed = 0
cafe_score = 0
cafe_patience_max = CAFE_STARTING_PATIENCE
cafe_patience_remaining = CAFE_STARTING_PATIENCE
cafe_customer_index = 0  # 1-based count of customers seen this session so far
cafe_stage = CAFE_STAGE_PICK  # CAFE_STAGE_PICK | CAFE_STAGE_TWIST
cafe_is_twist_round = False
cafe_order = None  # {"order_en", "answer", "choices"} | None
cafe_twist_question = None  # generate_question() output | None
cafe_last_result = None  # None | True | False -- last customer, transient UI flash


cafe_note = ""  # what the last customer's order did to its plots


_cafe_food_cache = None
_cafe_twist_candidates_cache = None


_cafe_rendered_order = None  # identity tracker -- see Blitz's own build note on why
_cafe_rendered_twist = None


sprint_open = False  # panel toggled open, independent of a live run
sprint_active = False  # a 60s run is currently in progress
sprint_score = 0
sprint_best_score = 0  # best across runs *this page load* -- session-only
sprint_lives = SPRINT_STARTING_LIVES
sprint_combo = 0
sprint_time_remaining = SPRINT_DURATION_SECONDS
sprint_question = None
sprint_end_reason = None  # None | SPRINT_END_TIME | SPRINT_END_LIVES


sprint_note = ""  # what the last answer did to its plot


_sprint_candidates_cache = None


_sprint_rendered_question = None  # identity tracker -- see the note below


# ===========================================================================
# 2026-10-08 -- four new arcade games for the weeks the first five do not reach
# ===========================================================================
#
# Word Match (vocabulary and phrases, weeks 12-23), Grammar Gaps (fill the gap
# in the grammar of the weeks Blitz, Racer and the Sprint do not ask gaps
# about), Listening Pick (hear it, pick what it means; vocabulary, phrases and
# pronunciation items) and Word Order Race (put an example sentence's words in
# order). Each draws only on content already in the catalog, is row-unlock-
# gated like the others, waters real plots (the line under every question names
# them), feeds the practice ledger and has a Slower / Normal / Faster setting.
# The four share one small base class so each game is only its own rules.

_speak = None
_speech_ok = None


amis_entries = []  # [{"en", "fr", "means", "partial"}]
amis_status = "idle"  # idle, loading, ready, failed
amis_read_date = ""  # YYYY-MM-DD of the read the entries come from
amis_from_cache = False
amis_error = ""
_amis_by_word = {}


# Every variable above that gets reassigned. minigames.py forwards minigames.<name> to this module for exactly these names.
LIVE_NAMES = (
    "_farm",
    "_generate_question",
    "_variants_for",
    "_record_practice",
    "_credit_plot_id",
    "_credit_item",
    "_credit_reset",
    "_credit_text",
    "_plot_for_fr",
    "_pref_get",
    "_pref_set",
    "_check_answer",
    "blitz_open",
    "blitz_active",
    "blitz_score",
    "blitz_best_score",
    "blitz_lives",
    "blitz_combo",
    "blitz_time_remaining",
    "blitz_question",
    "blitz_end_reason",
    "blitz_note",
    "_blitz_candidates_cache",
    "_blitz_rendered_question",
    "racer_open",
    "racer_active",
    "racer_player_position",
    "racer_rival_position",
    "racer_tick_count",
    "racer_question",
    "racer_result",
    "racer_end_reason",
    "racer_note",
    "_racer_candidates_cache",
    "_racer_rendered_question",
    "boutique_open",
    "boutique_active",
    "boutique_served",
    "boutique_missed",
    "boutique_score",
    "boutique_patience_max",
    "boutique_patience_remaining",
    "boutique_order",
    "boutique_last_result",
    "boutique_note",
    "_boutique_garments_cache",
    "_boutique_colours_cache",
    "_boutique_rendered_order",
    "cafe_open",
    "cafe_active",
    "cafe_served",
    "cafe_missed",
    "cafe_score",
    "cafe_patience_max",
    "cafe_patience_remaining",
    "cafe_customer_index",
    "cafe_stage",
    "cafe_is_twist_round",
    "cafe_order",
    "cafe_twist_question",
    "cafe_last_result",
    "cafe_note",
    "_cafe_food_cache",
    "_cafe_twist_candidates_cache",
    "_cafe_rendered_order",
    "_cafe_rendered_twist",
    "sprint_open",
    "sprint_active",
    "sprint_score",
    "sprint_best_score",
    "sprint_lives",
    "sprint_combo",
    "sprint_time_remaining",
    "sprint_question",
    "sprint_end_reason",
    "sprint_note",
    "_sprint_candidates_cache",
    "_sprint_rendered_question",
    "_speak",
    "_speech_ok",
    "amis_entries",
    "amis_status",
    "amis_read_date",
    "amis_from_cache",
    "amis_error",
    "_amis_by_word",
)
