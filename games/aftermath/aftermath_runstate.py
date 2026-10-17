"""The module variables that get REPLACED while the game runs (the run, the skill tree, saved records, panel-open flags, filters, status texts).

Other modules read and write them as `runstate.x`, never as a copied name."""


community_resilience = None  # the community mean, or None while unknown

memory_just_formed = None  # E29: the category remembered by the run that just completed, for one callout

curriculum_just_completed = None  # E19: the lesson the run that just completed finished, for one callout


achievements_open = False


# Unlock toast + hub-dashboard link (TODO.md "roll achievements out
# everywhere" — required on top of the base per-game rollout, per
# ACHIEVEMENTS-SYSTEM-DESIGN.md's site-wide goal). Same pattern as SOL's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()

event_badges = []

info_page_open = False

past_runs_open = False

mentor_enabled = False

past_runs_sort = "newest"
past_runs_filter = "all"  # "all", "standard", "extended" or "scenario:<key>"
past_runs_show_archived = False
past_runs_compare = []  # up to two run numbers, oldest pick first

changelog_open = False


last_knowledge_preview = None

callout_message = ""


codex_open = False


stats_open = False

skill_search_text = ""
skill_filter_status = "all"
skill_filter_group = "any"

preset_selected = ""
preset_status_text = ""

save_health_announced = ""


challenge_status_text = ""

builder_status_text = ""


skill_move_message = ""

skill_map_selected = None
skill_map_reveal = None  # GE-16: {"skill": id, "children": [ids]} until the next map action

_skill_map_built = False

skill_ranks_just_gained = []  # [(skill_id, new_rank)] from the run that just paid out, for one callout

founding_message_text = ""


_timer_chain_pending = False

_achievement_strip_signature = None


chronicle_open = False

meta = None  # aftermath_persist loads the saved meta record here when it is imported (load_meta())

skill_tree = None  # aftermath_skilltree loads the skill tree here when it is imported

run_history = None  # aftermath_skilltree loads the run history here when it is imported

legacy_events = None  # aftermath_skilltree loads the legacy events here when it is imported

curriculum_progress = None  # aftermath_skilltree loads the curriculum progress here when it is imported

legacy_event_counts = None  # aftermath_skilltree loads the legacy event counts here when it is imported

highest_awarded_run = None  # aftermath_skilltree loads the highest awarded run here when it is imported

run = None  # aftermath_model_run creates the first RunState here when it is imported

achievement_progress = None  # aftermath_achievements loads the saved progress here when it is imported

invest_step = None  # aftermath_codex loads the saved step size here when it is imported


# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "meta",
    "community_resilience",
    "skill_tree",
    "run_history",
    "legacy_events",
    "memory_just_formed",
    "curriculum_progress",
    "curriculum_just_completed",
    "legacy_event_counts",
    "highest_awarded_run",
    "run",
    "achievement_progress",
    "achievements_open",
    "_achievements_seen_ids",
    "event_badges",
    "info_page_open",
    "past_runs_open",
    "mentor_enabled",
    "past_runs_sort",
    "past_runs_filter",
    "past_runs_show_archived",
    "past_runs_compare",
    "changelog_open",
    "last_knowledge_preview",
    "callout_message",
    "invest_step",
    "codex_open",
    "stats_open",
    "skill_search_text",
    "skill_filter_status",
    "skill_filter_group",
    "preset_selected",
    "preset_status_text",
    "save_health_announced",
    "challenge_status_text",
    "builder_status_text",
    "skill_move_message",
    "skill_map_selected",
    "skill_map_reveal",
    "_skill_map_built",
    "skill_ranks_just_gained",
    "founding_message_text",
    "_timer_chain_pending",
    "_achievement_strip_signature",
    "chronicle_open",
)
