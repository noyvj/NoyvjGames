"""SOL -- pure helpers for the Scarcity Run (A-11), its seed words (A-12) and the Ghost Run recordings (A-29).

Nothing here reads the clock, the DOM or the game: the view hands in "today" as a UTC YYYY-MM-DD string and
every function is a pure function of its arguments, so the tests can pin dates exactly. game.py owns the
simulation; this module owns the date maths, the word lists, the daily's rules and the validators for what
gets saved.

A Scarcity Run is one fixed challenge per UTC date, the same for everybody, derived from the date text ALONE:
  * a world set (Earth, the Moon and Mars, after the Near Bodies research), and which of them must reach a
    terraform target;
  * the ecology decay factor, what machines cost, a yield factor per world (the day's "resource mix": one pile
    is scarce, one rich) and a starting loadout per world (stock, Auto-Machines, Recyclers, starting ecology);
  * terraforming runs TERRAFORM_SPEED times faster than in the campaign, so a day is decided by how fast you
    can stabilise ecology and not by waiting;
  * a short pronounceable seed such as ``amber-orbit-7`` (word lists below, collision-free for 12,800
    consecutive days).

Nothing is a streak. A result is kept per date (best time in ticks, tries); a missed day costs nothing and any
date from the epoch on stays open. The leaderboard is NOT built: `leaderboard_entry` shapes the record a future
backend board would take and nothing sends it anywhere.
"""

from datetime import date as _date, timedelta

import seed

GENERATOR_VERSION = "v1"
EPOCH = "2026-10-01"          # the first playable date; every day since then is open
LAST_DATE = "2099-12-31"
MAX_DAYS_SAVED = 4000
MAX_TICKS_SAVED = 10 ** 8     # a stored completion time above this is junk

WORLDS = ("Earth", "Moon", "Mars")
TERRAFORM_SPEED = 4.0                          # terraform rate multiplier inside a Scarcity Run
TARGET_CHOICES = (30, 40, 50, 60)              # terraform percent the target worlds must reach
DECAY_CHOICES = (1.5, 2.0, 2.5, 3.0)            # ecology decay factor
COST_CHOICES = (2.0, 3.0, 4.0)                  # what Auto-Machines and Recyclers cost, times the usual
YIELD_CHOICES = (0.4, 0.6, 0.8, 1.0, 1.25)     # one yield factor per world (the resource mix)
STOCK_CHOICES = (0, 0, 30, 60, 100)             # starting stock per world
ECOLOGY_CHOICES = (20, 35, 50, 65, 80)         # starting ecology per world
MAX_ATTEMPTS = 24

# Word lists as data: 40 adjectives x 40 nouns x 8 digits = 12,800 seeds, each date gets its own for 12,800 days.
ADJECTIVES = (
    "amber", "azure", "bold", "brisk", "calm", "cosy", "dusky", "eager", "early", "faint",
    "frosty", "gentle", "golden", "hazy", "humble", "icy", "ivory", "jade", "jolly", "keen",
    "kind", "lively", "lunar", "mellow", "misty", "nimble", "noble", "olive", "opal", "placid",
    "quiet", "rustic", "silver", "tidy", "umber", "vivid", "windy", "wise", "woolly", "zesty",
)
NOUNS = (
    "anchor", "aurora", "basalt", "beacon", "canyon", "cedar", "comet", "delta", "dune", "ember",
    "falcon", "fjord", "glacier", "harbor", "haven", "island", "juniper", "kestrel", "lagoon", "maple",
    "meadow", "nebula", "orbit", "otter", "prairie", "quartz", "quasar", "ridge", "river", "saffron",
    "summit", "thistle", "tundra", "upland", "valley", "vector", "willow", "wren", "yarrow", "zenith",
)
DIGITS = (2, 3, 4, 5, 6, 7, 8, 9)
SEED_SPACE = len(ADJECTIVES) * len(NOUNS) * len(DIGITS)

_order = []


# --- dates (strict, and never the clock) ---------------------------------------------------------------
def parse_date(text):
    """A datetime.date for a strict YYYY-MM-DD string, else None."""
    if not isinstance(text, str) or len(text) != 10 or text[4] != "-" or text[7] != "-" or not text.isascii():
        return None
    try:
        return _date.fromisoformat(text)
    except ValueError:
        return None


def valid_date(text):
    return parse_date(text) is not None


def day_number(text):
    """Day 1 is the epoch."""
    return (parse_date(text) - parse_date(EPOCH)).days + 1


def playable(text, today):
    """A date may be played when it is a real date between the epoch and `today`, both included."""
    d, t = parse_date(text), parse_date(today)
    return d is not None and t is not None and parse_date(EPOCH) <= d <= t


def add_days(text, n):
    return (parse_date(text) + timedelta(days=n)).isoformat()


def month_of(text):
    """(year, month) of a date text."""
    d = parse_date(text)
    return (d.year, d.month)


def shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return (index // 12, index % 12 + 1)


def month_weeks(year, month):
    """The month as weeks of seven cells, Monday first; a cell is a YYYY-MM-DD text or None outside the month."""
    first = _date(year, month, 1)
    cells = [None] * first.weekday()
    day = first
    while day.month == month:
        cells.append(day.isoformat())
        day += timedelta(days=1)
    while len(cells) % 7:
        cells.append(None)
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


# --- A-12: the seed words ---------------------------------------------------------------------------------
def _seed_order():
    """A fixed shuffle of 0..SEED_SPACE-1, so consecutive days look unrelated yet never repeat within a cycle."""
    if not _order:
        _order.extend(seed.Rng("sol-scarcity-words-%s" % GENERATOR_VERSION).shuffled(range(SEED_SPACE)))
    return _order


def seed_words(date_text):
    """The day's pronounceable seed, e.g. "amber-orbit-7". Two dates less than SEED_SPACE days apart never share one."""
    d = parse_date(date_text)
    if d is None:
        raise ValueError("seed_words needs a YYYY-MM-DD date")
    index = _seed_order()[d.toordinal() % SEED_SPACE]
    return "%s-%s-%d" % (ADJECTIVES[index % len(ADJECTIVES)], NOUNS[(index // len(ADJECTIVES)) % len(NOUNS)],
                         DIGITS[index // (len(ADJECTIVES) * len(NOUNS))])


def is_seed_words(text):
    """True for a well-formed seed triple made from the word lists."""
    if not isinstance(text, str):
        return False
    parts = text.split("-")
    return (len(parts) == 3 and parts[0] in ADJECTIVES and parts[1] in NOUNS
            and parts[2].isdigit() and int(parts[2]) in DIGITS)


# --- the daily's rules ----------------------------------------------------------------------------------------
def make_spec(date_text, attempt=0):
    """The challenge for a date (attempt 0 is the first try; the game asks for the next attempt only if the Governor
    bar fails, which the tests show never happens for the shipped ranges). Pure data:
    {"date", "words", "attempt", "targets", "target_pct", "decay", "cost", "yields", "loadout"}."""
    if parse_date(date_text) is None:
        raise ValueError("make_spec needs a YYYY-MM-DD date")
    r = seed.Rng("sol-scarcity-%s|%s|%d" % (GENERATOR_VERSION, date_text, attempt))
    if r.chance(0.34):
        targets = list(WORLDS)
    else:
        targets = sorted(r.sample(WORLDS, 2), key=WORLDS.index)
    target_pct = r.choice(TARGET_CHOICES)
    decay = r.choice(DECAY_CHOICES)
    cost = r.choice(COST_CHOICES)
    yields = {w: r.choice(YIELD_CHOICES) for w in WORLDS}
    # The day's scarcity: at least one pile is thin and at least one is not.
    if all(v >= 1.0 for v in yields.values()):
        yields[r.choice(WORLDS)] = 0.4
    if all(v < 1.0 for v in yields.values()):
        yields[r.choice(WORLDS)] = 1.25
    loadout = {}
    for w in WORLDS:
        loadout[w] = {
            "stock": r.choice(STOCK_CHOICES),
            "generators": r.randint(0, 3) if w == "Earth" else r.randint(0, 2),
            "recyclers": r.randint(0, 1),
            "ecology": r.choice(ECOLOGY_CHOICES),
        }
        # Every world starts with a way to earn: one machine at least.
        if loadout[w]["generators"] + loadout[w]["recyclers"] == 0:
            loadout[w]["generators"] = 1
    return {"date": date_text, "words": seed_words(date_text), "attempt": attempt, "targets": targets,
            "target_pct": target_pct, "decay": decay, "cost": cost, "yields": yields, "loadout": loadout}


def goal_text(spec):
    names = [("Earth", "Earth"), ("Moon", "the Moon"), ("Mars", "Mars")]
    picked = [label for key, label in names if key in spec["targets"]]
    if len(picked) == 1:
        who = picked[0]
    elif len(picked) == 2:
        who = " and ".join(picked)
    else:
        who = ", ".join(picked[:-1]) + " and " + picked[-1]
    return "Terraform %s to %d%%." % (who, spec["target_pct"])


# --- results ----------------------------------------------------------------------------------------------
def merge_record(old, ticks, par):
    """The saved record for a date after another finished run: the best time, tries + 1, and whether any run
    beat the par (the Governor alone)."""
    old = old if isinstance(old, dict) else {}
    best = ticks if not isinstance(old.get("ticks"), int) else min(old["ticks"], ticks)
    record = {"ticks": int(best), "tries": min(999, int(old.get("tries", 0)) + 1)}
    if (old.get("under_par") is True) or (isinstance(par, int) and ticks < par):
        record["under_par"] = True
    return record


def clean_days(raw):
    """Validated copy of the saved {date: {"ticks", "tries", "under_par"?}} map. Junk entries are dropped one by one."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for text, rec in raw.items():
        d = parse_date(text) if isinstance(text, str) else None
        if d is None or not (parse_date(EPOCH) <= d <= parse_date(LAST_DATE)) or not isinstance(rec, dict):
            continue
        ticks, tries = rec.get("ticks"), rec.get("tries")
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (ticks, tries)):
            continue
        if not 1 <= ticks <= MAX_TICKS_SAVED:
            continue
        clean = {"ticks": ticks, "tries": max(1, min(999, tries))}
        if rec.get("under_par") is True:
            clean["under_par"] = True
        out[text] = clean
        if len(out) >= MAX_DAYS_SAVED:
            break
    return out


def tally(days, today):
    """How many of the open days have been played and how many of those beat the Governor. No streaks, ever."""
    t = parse_date(today)
    open_days = day_number(today) if t is not None and t >= parse_date(EPOCH) else 0
    played = [d for d in days if playable(d, today)]
    return {"open": open_days, "played": len(played), "under_par": sum(1 for d in played if days[d].get("under_par"))}


def leaderboard_entry(date_text, record):
    """HOOK for a future daily board (a separate backend job, NOT built in this pass): the entry a board would take
    for one date. Pure; nothing calls a server with it."""
    return {"board": "sol-scarcity-daily", "date": date_text, "words": seed_words(date_text),
            "score": int(record.get("ticks", 0)), "unit": "ticks"}


# --- A-29: ghost recordings ---------------------------------------------------------------------------------
GHOST_STEP = 25                 # ticks between two samples (2.5 s of game time)
GHOST_MAX_SAMPLES = 20000       # about 140 minutes of game time
GHOST_TRACK_ROWS = 12           # how many of the latest checkpoints the split track shows


def clean_recording(raw):
    """A validated recording {"ticks": int, "pct": [int tenths of a percent, 0..1000]} or None.
    Anything wrong with it (wrong type, out of range, too long or too short) drops the whole recording."""
    if not isinstance(raw, dict):
        return None
    ticks, pct = raw.get("ticks"), raw.get("pct")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 1 <= ticks <= MAX_TICKS_SAVED:
        return None
    if not isinstance(pct, list) or not 2 <= len(pct) <= GHOST_MAX_SAMPLES:
        return None
    for value in pct:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
            return None
    return {"ticks": ticks, "pct": list(pct)}


def ghost_value(recording, index):
    """The ghost's terraform percent (a float) at sample `index`; it holds its last value once it has finished."""
    pct = recording["pct"]
    return pct[min(index, len(pct) - 1)] / 10.0


def lead_text(mine, ghost):
    """Signed text for how far ahead (+) or behind (-) you are, in terraform points: '+0.4 points ahead'."""
    diff = round(mine - ghost, 1)
    if abs(diff) < 0.05:
        return "level (+0.0)"
    return ("%+.1f points ahead" % diff) if diff > 0 else ("%+.1f points behind" % diff)


def split_rows(mine, recording, rows=GHOST_TRACK_ROWS):
    """The latest `rows` checkpoints of the split track: [{"tick", "mine", "ghost", "diff", "text"}], where `mine`
    is the list of your samples (tenths of a percent) so far."""
    out = []
    first = max(0, len(mine) - rows)
    for index in range(first, len(mine)):
        m = mine[index] / 10.0
        g = ghost_value(recording, index)
        diff = round(m - g, 1)
        out.append({"tick": index * GHOST_STEP, "mine": m, "ghost": g, "diff": diff,
                    "text": "%s%.1f" % ("+" if diff >= 0 else "-", abs(diff))})
    return out


def ghost_summary(mine, recording):
    """(ahead, behind, level) checkpoint counts over the whole run so far."""
    ahead = behind = level = 0
    for index, value in enumerate(mine):
        diff = value - recording["pct"][min(index, len(recording["pct"]) - 1)]
        if diff > 0:
            ahead += 1
        elif diff < 0:
            behind += 1
        else:
            level += 1
    return ahead, behind, level
