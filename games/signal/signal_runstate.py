"""The live state of the running engine: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`S = _fresh_state()`, `_cur = {...}`) lives only here, and every other
module reads and writes it as `runstate.<name>` (each module starts with `import signal_runstate as runstate`). Never
`from signal_runstate import S`: that copies the value once and goes stale at the next change. Dicts and lists that are
only changed in place (`_BOARDS`, `_PUZZLE_CACHE`) can stay in the module that owns them.

`_clock`, `_rand` and `S` start from a function or a class defined in a feature module, so they have a plain default here
and signal_rules / signal_puzzle / signal_records set them when they are imported.

LIVE_NAMES at the bottom lists every such variable. game.py forwards `game.<name>` reads and writes to this module for
exactly those names (the tests use game._cur and game.S). Add a new rebound variable here AND to LIVE_NAMES."""


_cur = None  # runtime: {"type", "date", "mode", "puzzle"}
_last_today = None

_clock = None  # signal_rules sets it (the real UTC clock) when it is imported

_rand = None  # signal_puzzle sets it (an OS-seeded random.Random) when it is imported

S = None  # signal_records sets it (a brand-new player) when it is imported


# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "_clock",
    "_rand",
    "S",
    "_cur",
    "_last_today",
)
