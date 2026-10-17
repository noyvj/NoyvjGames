"""Faux Amis: reading the false-friends list from the live page, caching it, and the game built on it.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import re

from pyodide.ffi import create_proxy

import champ_minigames_runstate as runstate
from champ_minigames_core import DIFFICULTY_LABELS, _build_answer_area, _check, _record, context_line
from champ_minigames_arcade import _Arcade


# render() is defined in champ_minigames_registry, which comes later in the module list; that module puts it here when
# it loads (see the end of champ_minigames_registry.py). Calls below find it at run time.
render = None


# ---------------------------------------------------------------------------
# Faux Amis: false friends, read live from a reputable list (TODO L-15, L-16)
# ---------------------------------------------------------------------------
# The list is the French Wiktionary's "Annexe:Faux-amis anglais-français"
# (CC BY-SA), read from the live page and named on screen. Nothing from it is
# bundled: the parsed entries are cached in this browser (never in the save
# code) so the farm badges (L-16) can show before the page is read again, and
# the game itself always asks for a fresh read when it is opened.
#
# Not plot-linked: the words come from the list, not from the player's farm, so
# the game says "Does not grow plots", and its answers feed the practice ledger
# (mode "amis"). Where a plot's French word is on the list, that plot carries a
# small "false friend" badge and tooltip instead (game.py asks amis_for_plot).
AMIS_PAGE_TITLE = "Annexe:Faux-amis anglais-français"
AMIS_PAGE_URL = "https://fr.wiktionary.org/wiki/Annexe:Faux-amis_anglais-fran%C3%A7ais"
AMIS_API_URL = (
    "https://fr.wiktionary.org/w/api.php?action=query&prop=revisions&rvprop=content&rvslots=main"
    "&format=json&formatversion=2&origin=*&titles=Annexe%3AFaux-amis%20anglais-fran%C3%A7ais"
)
AMIS_SOURCE_NAME = "French Wiktionary, “Annexe:Faux-amis anglais-français” (CC BY-SA)"
AMIS_CACHE_KEY = "champ-amis-cache"
AMIS_CACHE_DAYS = 7
AMIS_QUESTIONS = 10
AMIS_MIN_ENTRIES = 12
AMIS_DIFFICULTY = {
    "slower": {"seconds": 30, "lives": 6},
    "normal": {"seconds": 18, "lives": 3},
    "faster": {"seconds": 10, "lives": 2},
}
AMIS_WORD_RE = re.compile(r"^[a-zà-ÿœ'’-]{3,16}$")
_AMIS_ARTICLE_RE = re.compile(r"^(?:(?:le|la|les|un|une|des|du|de la)\s+|l'|de l')")


_amis_plot_cache = {}
on_amis_loaded = None  # game.py sets this to its render()


def parse_amis(text):
    """Entries from the page's wikitext: each "* ''english''" headline followed
    by "** fr : word (n m) : ''meaning''" lines. Keeps single-word pairs with a
    short plain meaning, drops anything that reads as commentary."""
    entries = []
    head, partial = None, False
    for line in str(text).splitlines():
        match = re.match(r"^\* ''([^'\n]+)''(.*)$", line)
        if match:
            head = match.group(1).strip().lower()
            partial = "fa p" in match.group(2)
            continue
        if head is None:
            continue
        match = re.match(r"^\*\* fr : (.+)$", line)
        if not match:
            continue
        body = match.group(1)
        if " : " not in body:
            continue
        before, tail = body.split(" : ", 1)
        before = re.sub(r"\([^)]*\)", " ", before).strip().lower()
        before = _AMIS_ARTICLE_RE.sub("", before).strip()
        if " " in before or not AMIS_WORD_RE.match(before) or not AMIS_WORD_RE.match(head):
            continue
        tail = tail.split(" mais ")[0]
        means = [m.strip() for m in re.findall(r"''([^'\n]+)''", tail)]
        means = [m for m in means if 2 <= len(m) <= 24 and "(" not in m and m.lower() != head]
        if not means:
            continue
        entries.append({"en": head, "fr": before, "means": means[:3], "partial": partial})
    return entries


def _amis_pack(entries):
    return [[e["en"], e["fr"], e["means"], 1 if e["partial"] else 0] for e in entries]


def _amis_unpack(rows):
    entries = []
    for row in rows if isinstance(rows, list) else []:
        if (
            isinstance(row, list) and len(row) == 4 and isinstance(row[0], str) and isinstance(row[1], str)
            and isinstance(row[2], list) and row[2] and all(isinstance(m, str) for m in row[2])
        ):
            entries.append({"en": row[0], "fr": row[1], "means": row[2][:3], "partial": bool(row[3])})
    return entries


def _amis_today():
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return ""
    hook = getattr(window, "studyToday", None)
    value = hook() if hook is not None else ""
    return value if isinstance(value, str) else ""


def _amis_days_between(older, newer):
    """Whole days between two YYYY-MM-DD strings (no datetime: see game.py)."""
    import calendar  # noqa: PLC0415

    def stamp(value):
        year, month, day = (int(part) for part in value.split("-"))
        return calendar.timegm((year, month, day, 0, 0, 0))

    try:
        return (stamp(newer) - stamp(older)) // 86400
    except (ValueError, TypeError):
        return 10 ** 6


def _amis_set(entries, date, cached):
    runstate.amis_entries = list(entries)
    runstate.amis_read_date = date
    runstate.amis_from_cache = cached
    runstate.amis_status = "ready" if len(runstate.amis_entries) >= AMIS_MIN_ENTRIES else "failed"
    runstate._amis_by_word = {}
    for entry in runstate.amis_entries:
        runstate._amis_by_word.setdefault(entry["fr"], entry)
    _amis_plot_cache.clear()
    AMIS.reset_pool()


def load_amis_cache():
    """Show what the last read found, until (or instead of) a fresh read."""
    if runstate._pref_get is None:
        return False
    raw = runstate._pref_get(AMIS_CACHE_KEY)
    if not raw:
        return False
    try:
        import json  # noqa: PLC0415
        data = json.loads(raw)
    except (TypeError, ValueError):
        return False
    entries = _amis_unpack(data.get("entries") if isinstance(data, dict) else None)
    date = data.get("date") if isinstance(data, dict) and isinstance(data.get("date"), str) else ""
    if len(entries) < AMIS_MIN_ENTRIES:
        return False
    _amis_set(entries, date, True)
    return True


def amis_cache_is_stale():
    today = _amis_today()
    if not runstate.amis_read_date or not today:
        return True
    return _amis_days_between(runstate.amis_read_date, today) >= AMIS_CACHE_DAYS


def fetch_amis(force=False):
    """Ask the page (window.championFetchText, see index.html) for the live
    list. Returns True when a request was started."""
    if runstate.amis_status == "loading":
        return False
    try:
        from js import window  # noqa: PLC0415
    except ImportError:
        return False
    hook = getattr(window, "championFetchText", None)
    if hook is None:
        return False
    runstate.amis_status = "loading" if not runstate.amis_entries else runstate.amis_status
    runstate.amis_error = ""

    def on_text(text):
        try:
            import json  # noqa: PLC0415
            content = json.loads(str(text))["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
            entries = parse_amis(content)
        except (KeyError, IndexError, TypeError, ValueError):
            entries = []
        if len(entries) < AMIS_MIN_ENTRIES:
            on_error("The list could not be read.")
            return
        date = _amis_today()
        _amis_set(entries, date, False)
        if runstate._pref_set is not None:
            import json  # noqa: PLC0415
            runstate._pref_set(AMIS_CACHE_KEY, json.dumps({"date": date, "entries": _amis_pack(entries)}))
        _amis_changed()

    def on_error(reason=None):
        runstate.amis_error = str(reason) if isinstance(reason, str) else "The list could not be reached."
        if not runstate.amis_entries:
            runstate.amis_status = "failed"
        _amis_changed()

    try:
        promise = hook(AMIS_API_URL)
        promise.then(create_proxy(on_text), create_proxy(on_error))
    except Exception:  # noqa: BLE001 -- a broken fetch hook must never break the page
        on_error("The list could not be reached.")
        return False
    return True


def _amis_changed():
    if on_amis_loaded is not None:
        on_amis_loaded()
    else:
        render()


def amis_source_line():
    """The line under the game's title: what it reads, from where, and when."""
    if runstate.amis_status == "loading":
        return f"Reading {AMIS_SOURCE_NAME} now..."
    if runstate.amis_status == "ready":
        if runstate.amis_from_cache:
            when = f"on {runstate.amis_read_date}" if runstate.amis_read_date else "earlier"
            extra = f" A fresh read failed ({runstate.amis_error})" if runstate.amis_error else ""
            return f"Source: {AMIS_SOURCE_NAME}. Showing the copy read {when}.{extra}"
        return f"Source: {AMIS_SOURCE_NAME}, read live on {runstate.amis_read_date or 'today'}."
    if runstate.amis_status == "failed":
        return f"Source: {AMIS_SOURCE_NAME}. It could not be read just now ({runstate.amis_error or 'no connection'}); try again later."
    return f"Source: {AMIS_SOURCE_NAME}, read live when this panel opens."


def amis_for_word(word):
    return runstate._amis_by_word.get(str(word).strip().lower())


def _amis_plot_words(fr_text):
    words = []
    for piece in re.split(r"\s*/\s*", re.sub(r"\([^)]*\)", "", str(fr_text))):
        piece = _AMIS_ARTICLE_RE.sub("", piece.strip().lower()).strip(" .!?")
        if piece and " " not in piece:
            words.append(piece)
    return words


def amis_for_plot(plot):
    """The list entry for a plot's French word, or None (cached per plot)."""
    if not runstate._amis_by_word or plot is None:
        return None
    key = plot.plot_id
    if key not in _amis_plot_cache:
        found = None
        for item in plot.items:
            for word in _amis_plot_words(item.get("fr", "")):
                entry = runstate._amis_by_word.get(word)
                if entry is not None and not entry["partial"] and word != entry["means"][0].lower():
                    # the farm's own English already says the look-alike (a "chef" that is a chef):
                    # then there is nothing to warn about for this plot
                    english = " " + re.sub(r"[^a-z' ]", " ", str(item.get("en", "")).lower()) + " "
                    if f" {entry['en']} " in english:
                        continue
                    found = entry
                    break
            if found:
                break
        _amis_plot_cache[key] = found
    return _amis_plot_cache[key]


def amis_plot_note(plot):
    entry = amis_for_plot(plot)
    if entry is None:
        return ""
    means = " or ".join(entry["means"][:2])
    return f"false friend: “{entry['fr']}” looks like English “{entry['en']}” but means {means}"


def _amis_similarity(entry):
    import difflib  # noqa: PLC0415
    return difflib.SequenceMatcher(None, entry["fr"], entry["en"]).ratio()


class _AmisGame(_Arcade):
    key = "amis"
    open_label = "\U0001F575 Faux Amis"
    close_label = "Close Faux Amis"
    start_label = "Start Faux Amis"
    again_label = "Play again"
    difficulty_table = AMIS_DIFFICULTY
    asked = 0
    run = ()

    def describe(self, level):
        p = self.difficulty_table[level]
        return f"{DIFFICULTY_LABELS[level]}: {p['seconds']} seconds for each of {AMIS_QUESTIONS} questions, {p['lives']} lives."

    def reset_pool(self):
        self._pool = None

    def build_pool(self):
        return [e for e in runstate.amis_entries if not e["partial"] and e["en"] not in [m.lower() for m in e["means"]]]

    def available(self):
        return True

    def lock_reason(self):
        if runstate.amis_status == "ready":
            return None
        if runstate.amis_status == "loading":
            return "Reading the list now. This takes a moment."
        return "The list could not be read just now, so there is nothing to ask. Close this panel and open it again later."

    def toggle(self, event=None):
        opening = not self.open
        super().toggle(event)
        if opening:
            fetch_amis()

    def open_panel(self):
        super().open_panel()
        fetch_amis()

    def start(self, event=None):
        if runstate.amis_status != "ready" or len(self.pool()) < AMIS_MIN_ENTRIES:
            return None
        return super().start(event)

    def begin(self):
        entries = self.pool()
        picked = self.rng.sample(entries, min(AMIS_QUESTIONS, len(entries)))
        # increasingly sneaky: the pairs that look least alike first, the near-twins last
        picked.sort(key=_amis_similarity)
        self.run = picked
        self.asked = 0
        self.question_seconds = self.params()["seconds"]
        self.time_remaining = self.question_seconds

    def _distractors(self, entry, count):
        pool = self.pool()
        banned = {entry["en"].lower()} | {m.lower() for m in entry["means"]}
        options = []
        for other in self.rng.sample(pool, min(len(pool), 40)):
            meaning = other["means"][0]
            if meaning.lower() not in banned and meaning.lower() not in {o.lower() for o in options}:
                options.append(meaning)
            if len(options) == count:
                break
        return options

    def new_round(self):
        entry = self.run[self.asked]
        true_meaning = entry["means"][0]
        choices = [true_meaning, entry["en"]] + self._distractors(entry, 2)
        self.rng.shuffle(choices)
        self.round = {
            "mode": "choice",
            "plot_id": None,
            "variant": "amis",
            "context": f"Looks like the English “{entry['en']}”",
            "instruction": "What does this French word really mean?",
            "prompt": entry["fr"],
            "choices": choices,
            "answer": true_meaning,
            "entry": entry,
        }
        self.asked += 1
        self.time_remaining = self.question_seconds

    def waters_labels(self):
        return []

    def stats(self):
        values = super().stats()
        values["combo"] = f"Question {min(self.asked, AMIS_QUESTIONS)} of {len(self.run) or AMIS_QUESTIONS}"
        return values

    def on_time_up(self):
        if self.round is not None:
            self.settle(False, timed_out=True)

    def settle(self, correct, timed_out=False):
        question = self.round
        entry = question["entry"]
        _record(self.key, correct)
        said = f"“{entry['fr']}” means {question['answer']}, not “{entry['en']}”."
        if correct:
            self.note = "Yes: " + said
            self.combo += 1
            self.score += self.award()
        else:
            self.note = ("Time ran out. " if timed_out else "Not quite. ") + said
            self.combo = 0
            self.lives -= 1
        if self.lives <= 0:
            self.end("lives")
        elif self.asked >= len(self.run):
            self.end("cleared")
        else:
            self.new_round()

    def submit(self, given):
        if not self.active or self.round is None:
            return None
        correct = _check(self.round, given)
        self.settle(correct)
        render()
        return correct

    def cleared_text(self):
        return f"All {len(self.run)} asked! Score: {self.score} (best this session: {self.best})."

    def clear_round_ui(self):
        self.el("choices").innerHTML = ""
        self.el("context").innerText = ""
        self.el("prompt").innerText = ""

    def draw_round(self):
        self.el("context").innerText = context_line(self.round)
        self.el("prompt").innerText = self.round["prompt"]
        _build_answer_area(self.key, self.round, self.el("choices"), self.proxies, self.submit)

    def render(self):
        super().render()
        self.el("source").innerText = amis_source_line()


AMIS = _AmisGame()
