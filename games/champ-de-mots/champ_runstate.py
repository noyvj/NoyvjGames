"""The live state of the running game: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`current_question = None`, `combo_count += 1`) lives only here, and
every other module reads and writes it as `runstate.<name>` (each module starts with `import champ_runstate as runstate`).
Never `from champ_runstate import current_question`: that copies the name once and goes stale the moment the variable is
replaced. Lists, dicts and sets that are only changed in place can stay in the module that owns them.

LIVE_NAMES at the bottom lists every such variable. game.py forwards `game.<name>` reads and writes to this module for
exactly those names (tests use game.current_question and so on). Add a new rebound variable here AND to LIVE_NAMES.
"""

from champ_rules import PLANNER_DEFAULT_MINUTES, PRACTICE_MODES, _blank_practice_entry


# ---------------------------------------------------------------------------
# Progressive question format (2026-10-08)
# ---------------------------------------------------------------------------
# A plot that has never been watered always starts with multiple choice. As its
# comprehension grows (its growth stage first, then its correct streak and
# ease factor) typed answers appear more and more often, until a mastered plot
# is mostly typed. Deterministic: whether a given question is typed is decided
# by a fixed hash of the plot's own scheduling state against its typed share,
# so there is no new randomness (the variant is still picked with the caller's
# seeded generator, exactly as before). The "Always multiple choice" setting
# switches the whole thing off.
ALWAYS_MULTIPLE_CHOICE = False


error_pattern_counts = {}


# Module-level UI state.
current_question = None
current_result = None
current_submitted_answer = None
current_water_kind = None  # what the last correct farm answer did: WATER_FULL / WATER_NUDGE / None
practice_open = False
report_sent = False
pronunciation_report_sent = False


# Session combo count (consecutive correct answers, any plot) and the
# confidence tag on the currently-open question. Both are pure session
# state -- like ACCENT_SENSITIVE below -- and deliberately never reach
# get_state()/load_state(): a fresh page load always starts at zero/unset.
combo_count = 0
current_confidence = None  # None | "sure" | "unsure"


# §14.2's accent-sensitivity toggle: default ON (accents must be typed
# correctly) since spelling them right is an assessed skill. A session
# preference, not SRS state, so it deliberately stays out of get_state()/
# load_state() -- same call as `plot.last_variant` in Milestone 4.
ACCENT_SENSITIVE = True


# --- Milestone 11: Review tab state (design doc §14.4) ---------------------
#
# Opt-in, entirely separate from the daily watering loop: it never grows a
# plot's stage and never changes row-unlock state (only stage does that), so
# it can't be used to skip the pacing gate. All of it is session state, like
# `ACCENT_SENSITIVE` above — none of it belongs in get_state()/load_state().

review_controls_open = False
review_mode = None  # None | "word" | "grammar"
review_queue = []  # plot_ids, fixed for the session once start_review() rolls it
review_index = 0
review_question = None
review_result = None
review_score = {"correct": 0, "total": 0}


review_water_kind = None  # what the last correct Review answer did to its plot
review_listen_revealed = False  # listening water: the French text has been shown


# Milestone 26: the report buttons, extended here from the main practice
# panel only (see that milestone's build note -- requested directly after
# Milestone 11 had explicitly scoped them out). Same session-only posture as
# everything else in this block.
review_submitted_answer = None
review_report_sent = False
review_pronunciation_report_sent = False


proficiency_mode = False
proficiency_sequence = None
proficiency_questions = []  # [{"topic_id","topic_title","topic_type","question"}, ...]
proficiency_index = 0
proficiency_result = None
proficiency_score = {"correct": 0, "total": 0}
proficiency_topic_scores = {}  # topic_id -> {"title", "correct", "total"}


# Milestone 26: same report-button extension as Review, see that milestone's
# build note.
proficiency_submitted_answer = None
proficiency_report_sent = False
proficiency_pronunciation_report_sent = False


bonus_mode = False
bonus_sequence = None
bonus_queue = []  # this week's bonus_sentences, fixed for the session
bonus_index = 0  # which sentence in the queue
bonus_task = None  # None | "order" | "translate_tiles" | "translate_sentence"
bonus_tile_pool = []  # tiles not yet placed (task 1), shuffled
bonus_placed = []  # tiles placed so far, in the player's chosen order
bonus_order_correct = None  # None | True | False, set once the pool empties
bonus_tile_index = 0  # which tile (in correct order) is being translated (task 2)
bonus_tile_result = None  # None | True | False for the tile currently shown
bonus_tile_score = {"correct": 0, "total": 0}  # this sentence's task-2 tally
bonus_sentence_result = None  # None | True | False (task 3)
bonus_score = {"correct": 0, "total": 0}  # every checkable step, this session


bonus_tile_submitted_answer = None
bonus_tile_report_sent = False
bonus_tile_pronunciation_report_sent = False
bonus_sentence_submitted_answer = None
bonus_sentence_report_sent = False
bonus_sentence_pronunciation_report_sent = False


report_log = []
report_log_open = False


legend_open = False
_legend_drawn = False


# Improvement Ideas §4: optional, toggleable cultural/usage notes -- off the
# main screen by default so it adds depth without cluttering the core drill
# for anyone who just wants to water plots. Session-only, like the review
# controls above: no note ever grows a plant or affects unlocking.
cultural_notes_open = False


practice_ledger = {mode: _blank_practice_entry() for mode in PRACTICE_MODES}


study_buddy_enabled = False


leech_rests = 0  # how many times a stubborn plot has been rested (saved)


slip_used = False
_slip_snapshot = None
slip_note = ""


_last_download = None


dashboard_open = False


study_days = {}
calendar_open = False
calendar_view = None  # (year, month) being shown; None means today's month


phrasebook = []
phrasebook_open = False


deepdive_open = False


liaison_mode = False
liaison_questions = []
liaison_index = 0
liaison_result = None
liaison_score = {"correct": 0, "total": 0}
liaison_choice_proxies = []


achievements_open = False

# Tracks the earned-id set as of the last time it was checked, so a fresh
# unlock (one that wasn't in this set last time) can trigger a toast
# without re-toasting every already-earned achievement on every render.
# Session-only, same category as ACCENT_SENSITIVE -- a fresh page load or
# a save/load round-trip starts from an empty baseline rather than
# spamming toasts for achievements that were already satisfied before.
_achievement_ids_seen = set()


changelog_open = False


farm_filter = "all"
farm_sort = "syllabus"
_farm_order_cache = None  # (sort, tuple of row sequences, tuple of per-row plot-id tuples)


shop_open = False


_plot_by_fr_index = None


water_options_open = False
water_mode_arg = None  # the row number or topic key of the running chooser session
water_row_choice = 1
water_topic_choice = "vocab"


builder_active = False
builder_queue = []
builder_index = 0
builder_pool = []
builder_placed = []
builder_result = None
builder_score = {"correct": 0, "total": 0}


conversation_active = False
conversation = None
conversation_turn = 0
conversation_choices = []
conversation_result = None
conversation_picked = None
conversation_score = {"correct": 0, "total": 0}
conversation_last_id = None


listening_active = False
listening_available = True
listening_queue = []
listening_index = 0
listening_choices = []
listening_result = None
listening_score = {"correct": 0, "total": 0}


placement_through = 0  # saved: highest row ever placed through (0 = never)
placement_active = False
placement_phase = "intro"  # intro | testing | summary
placement_queue = []  # [{"band", "sequence", "topic_id", "topic_title", "question"}]
placement_bands_list = []  # [[sequence, ...], ...] for the current session
placement_index = 0
placement_result = None
placement_submitted_answer = None
placement_band_scores = {}  # band -> {"correct", "total"}
placement_plan_data = None
placement_applied = False


# ===========================================================================
# FS-17 to FS-22 -- exam formats: clock reading, true/false reading, sentence
# rewriting, answering with a pronoun, reciprocal pronouns and pair questions,
# the tutorial exercise formats that had no matching practice mode. The
# questions come from formats.py (pure data from a seeded random generator);
# this block is the thin panel around it. Each format has its own ledger
# entry (record_practice(<format>, ok)), so every answer counts toward the
# visible practice score. Nothing here is a plot: SRS state is never touched.
# ===========================================================================
formats_active = False
formats_format = None
formats_queue = []
formats_index = 0
formats_result = None
formats_given = None
formats_score = {"correct": 0, "total": 0}


exam_date = None  # "YYYY-MM-DD" or None
exam_minutes = PLANNER_DEFAULT_MINUTES
planner_open = False


# Every variable above that gets reassigned. game.py forwards game.<name> to this module for exactly these names.
LIVE_NAMES = (
    "ALWAYS_MULTIPLE_CHOICE",
    "error_pattern_counts",
    "current_question",
    "current_result",
    "current_submitted_answer",
    "current_water_kind",
    "practice_open",
    "report_sent",
    "pronunciation_report_sent",
    "combo_count",
    "current_confidence",
    "ACCENT_SENSITIVE",
    "review_controls_open",
    "review_mode",
    "review_queue",
    "review_index",
    "review_question",
    "review_result",
    "review_score",
    "review_water_kind",
    "review_listen_revealed",
    "review_submitted_answer",
    "review_report_sent",
    "review_pronunciation_report_sent",
    "proficiency_mode",
    "proficiency_sequence",
    "proficiency_questions",
    "proficiency_index",
    "proficiency_result",
    "proficiency_score",
    "proficiency_topic_scores",
    "proficiency_submitted_answer",
    "proficiency_report_sent",
    "proficiency_pronunciation_report_sent",
    "bonus_mode",
    "bonus_sequence",
    "bonus_queue",
    "bonus_index",
    "bonus_task",
    "bonus_tile_pool",
    "bonus_placed",
    "bonus_order_correct",
    "bonus_tile_index",
    "bonus_tile_result",
    "bonus_tile_score",
    "bonus_sentence_result",
    "bonus_score",
    "bonus_tile_submitted_answer",
    "bonus_tile_report_sent",
    "bonus_tile_pronunciation_report_sent",
    "bonus_sentence_submitted_answer",
    "bonus_sentence_report_sent",
    "bonus_sentence_pronunciation_report_sent",
    "report_log",
    "report_log_open",
    "legend_open",
    "_legend_drawn",
    "cultural_notes_open",
    "practice_ledger",
    "study_buddy_enabled",
    "leech_rests",
    "slip_used",
    "_slip_snapshot",
    "slip_note",
    "_last_download",
    "dashboard_open",
    "study_days",
    "calendar_open",
    "calendar_view",
    "phrasebook",
    "phrasebook_open",
    "deepdive_open",
    "liaison_mode",
    "liaison_questions",
    "liaison_index",
    "liaison_result",
    "liaison_score",
    "liaison_choice_proxies",
    "achievements_open",
    "_achievement_ids_seen",
    "changelog_open",
    "farm_filter",
    "farm_sort",
    "_farm_order_cache",
    "shop_open",
    "_plot_by_fr_index",
    "water_options_open",
    "water_mode_arg",
    "water_row_choice",
    "water_topic_choice",
    "builder_active",
    "builder_queue",
    "builder_index",
    "builder_pool",
    "builder_placed",
    "builder_result",
    "builder_score",
    "conversation_active",
    "conversation",
    "conversation_turn",
    "conversation_choices",
    "conversation_result",
    "conversation_picked",
    "conversation_score",
    "conversation_last_id",
    "listening_active",
    "listening_available",
    "listening_queue",
    "listening_index",
    "listening_choices",
    "listening_result",
    "listening_score",
    "placement_through",
    "placement_active",
    "placement_phase",
    "placement_queue",
    "placement_bands_list",
    "placement_index",
    "placement_result",
    "placement_submitted_answer",
    "placement_band_scores",
    "placement_plan_data",
    "placement_applied",
    "formats_active",
    "formats_format",
    "formats_queue",
    "formats_index",
    "formats_result",
    "formats_given",
    "formats_score",
    "exam_date",
    "exam_minutes",
    "planner_open",
)
