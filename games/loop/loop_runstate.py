"""The live state of the running game: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`chain = ChainState()`, `info_page_open = not info_page_open`)
lives only here, and every other module reads and writes it as `runstate.<name>` (each module starts with
`import loop_runstate as runstate`). Never `from loop_runstate import chain`: that copies the name once and goes
stale the moment the chain is replaced. Lists, dicts and sets that are only changed in place (past_chains,
career_counts, plan, narrator_history, ...) can stay in the module that owns them.

LIVE_NAMES at the bottom lists every such variable. game.py forwards `game.<name>` reads and writes to this module
for exactly those names (tests use game.chain, game.buy_multiple = 5 and so on). Add a new rebound variable here AND
to LIVE_NAMES.
"""

from loop_model import ChainState
from loop_rules import ALL_GOODS, DEFAULT_GOODS_CATEGORY, GOODS_CATEGORIES

chain = ChainState()  # the chain in play: Start New Chain and load_state() replace it

# Module-level state that deliberately survives a "Start New Chain" reset
# (H7) -- these two counters exist specifically to measure something
# *across* resets/chains, so resetting `chain` must never touch them.
# Both ride get_state()/load_state() as top-level (not chain-scoped) keys.
chains_completed_count = 0
goods_categories_tried = {DEFAULT_GOODS_CATEGORY}
# H28: one-time Regional Partner hint; survives reset like the counters
# above (a player who has seen the explanation does not need it again).
regional_hint_seen = False
# H20: per-session random offset for which vignette variant a bucket
# starts on. 0 (deterministic) outside a real browser -- setup() sets it.
vignette_session_offset = 0

ghost = None  # GH-28 / H-7: a loaded friend's run (see load_ghost), session and browser only, never in a save

ledger_sort = "newest"

info_page_open = False

achievements_open = False

# Unlock toast (site-wide "roll achievements out everywhere" requirement,
# on top of the base per-game rollout). A snapshot of which ids were
# already earned as of the last seed point, so a fresh load or a loaded
# save doesn't flood the player with toasts for achievements it already
# satisfies.
_achievements_seen_ids = set()

changelog_open = False

# H-14: the x1 / x5 / x10 chips (a browser-session choice, not saved).
buy_multiple = 1

planner_horizon = 3  # how many cycles ahead the preview looks (3, 4 or 5)
planner_slot = 0  # which cycle the "add" buttons put a purchase into

planner_message = ""

# Every variable above that gets reassigned. game.py forwards game.<name> to these.
LIVE_NAMES = (
    "chain",
    "chains_completed_count",
    "goods_categories_tried",
    "regional_hint_seen",
    "vignette_session_offset",
    "ghost",
    "ledger_sort",
    "info_page_open",
    "achievements_open",
    "_achievements_seen_ids",
    "changelog_open",
    "buy_multiple",
    "planner_horizon",
    "planner_slot",
    "planner_message",
)


def current_goods_label():
    spec = ALL_GOODS.get(chain.goods_category, GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY])
    return spec["label"]


def current_vignette_item():
    spec = ALL_GOODS.get(chain.goods_category, GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY])
    return spec["vignette_item"]
