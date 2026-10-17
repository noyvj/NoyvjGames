"""Stubborn plots (leeches): detecting and resting them, the re-teach lines, the session highlights and the weak-items
CSV and Anki exports.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import csv
import io

import champ_runstate as runstate
from champ_rules import PRACTICE_COUNT_LIMIT
from champ_model import state
from champ_practice_base import close_practice


# --- L-18: stubborn weeds ---------------------------------------------------
# A plot answered wrong LEECH_THRESHOLD times in a row (a correct answer
# resets the run) turns into a stubborn weed: it shows a re-teach card before
# its next question (the answer, chunked into syllable-like pieces, and a
# prompt to make your own memory hook) and offers to rest for a week.
LEECH_THRESHOLD = 4
LEECH_REST_DAYS = 7
LEECH_FAIL_RUN_LIMIT = 1000


_VOWELS = "aeiouyàâäéèêëîïôöùûüœæ"


def _validated_fail_run(raw):
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return max(0, min(raw, LEECH_FAIL_RUN_LIMIT))


def _validated_last_watered(record, plot):
    """The saved day of a plot's last full watering (a save from before the
    2026-10-08 watering rule has no such key, which reads as never: on the day
    of the upgrade those plots can be watered once more, which is harmless)."""
    raw = record.get("last_watered")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        return None
    return raw


def _validated_leech_rests(raw):
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return max(0, min(raw, PRACTICE_COUNT_LIMIT))


def is_leech(plot):
    return plot.fail_run >= LEECH_THRESHOLD


def leech_plots():
    return [p for p in state.plots if is_leech(p)]


def chunk_word(word):
    """Split one French word into syllable-like chunks ("bonjour" -> ["bon",
    "jour"]) for the re-teach card. Mechanical: vowel groups are the cores, a
    single consonant between two cores starts the next chunk, and a cluster
    splits after its first consonant unless it ends in l or r after another
    consonant (pl, tr, ...)."""
    lower = word.lower()
    cores = []
    index = 0
    while index < len(lower):
        if lower[index] in _VOWELS:
            start = index
            while index < len(lower) and lower[index] in _VOWELS:
                index += 1
            cores.append((start, index))
        else:
            index += 1
    # A silent ending (-e, -es, -ent) is not a syllable of its own: "madame"
    # is ma-dame, not ma-da-me.
    if len(cores) >= 2:
        last_start, last_end = cores[-1]
        tail = lower[last_start:]
        if lower[last_start:last_end] == "e" and tail in ("e", "es", "ent"):
            cores = cores[:-1]
    if len(cores) < 2:
        return [word]
    cuts = []
    for (_, previous_end), (next_start, _) in zip(cores, cores[1:]):
        gap = next_start - previous_end
        if gap <= 0:
            continue
        if gap == 1:
            cuts.append(previous_end)
        elif lower[next_start - 1] in "lr" and gap >= 2 and lower[next_start - 2] not in "lr":
            cuts.append(next_start - 2)
        else:
            cuts.append(previous_end + 1)
    pieces = []
    last = 0
    for cut in cuts:
        pieces.append(word[last:cut])
        last = cut
    pieces.append(word[last:])
    return [piece for piece in pieces if piece]


def chunk_text(text):
    """Chunk every word of `text`, words separated by three spaces."""
    words = []
    for word in str(text).split():
        letters = word.strip(".,;:!?¡¿()\"«»")
        words.append(" · ".join(chunk_word(letters)) if letters else word)
    return "   ".join(words)


def leech_reteach_lines(plot):
    """The three lines of a stubborn plot's re-teach card."""
    item = plot.items[0]
    fr = item.get("fr") or item.get("prompt") or plot.label
    en = item.get("en") or item.get("answer") or ""
    if plot.topic_type == "grammar":
        head = f"{plot.topic_title}: {fr}" + (f" = {en}" if en else "")
    else:
        head = f"{fr} = {en}" if en else str(fr)
    return [
        f"Stubborn weed: missed {plot.fail_run} times in a row. Here it is once more: {head}",
        "In pieces: " + chunk_text(fr),
        "Make your own hook: picture it, rhyme it or link it to a word you already know, then say it out loud once.",
    ]


def rest_leech(event=None):
    """Put the open stubborn plot aside for LEECH_REST_DAYS and close it."""
    if runstate.current_question is None:
        return False
    plot = state.plots_by_id.get(runstate.current_question["plot_id"])
    if plot is None or not is_leech(plot):
        return False
    plot.next_due = state.current_day + LEECH_REST_DAYS
    plot.fail_run = 0
    runstate.leech_rests = min(runstate.leech_rests + 1, PRACTICE_COUNT_LIMIT)
    close_practice()
    return True


def leech_summary_text():
    now = len(leech_plots())
    return f"Stubborn weeds: {now} now, {runstate.leech_rests} rested so far"


# --- L-27: session highlights ----------------------------------------------
# What went well this sitting, shown on the Review and Proficiency results and
# in the dashboard. Session state, never saved. (A "quickest answer" is not
# tracked: this file deliberately has no clock.)
session_highlights = {"best_combo": 0, "toughest_label": None, "toughest_misses": 0}


def _note_highlights(plot, correct, prior_fail_run):
    if runstate.combo_count > session_highlights["best_combo"]:
        session_highlights["best_combo"] = runstate.combo_count
    if correct and prior_fail_run >= 1 and prior_fail_run > session_highlights["toughest_misses"]:
        session_highlights["toughest_label"] = plot.label
        session_highlights["toughest_misses"] = prior_fail_run


def session_highlights_text():
    parts = []
    if session_highlights["best_combo"] >= 2:
        parts.append(f"best combo {session_highlights['best_combo']} in a row")
    if session_highlights["toughest_label"]:
        misses = session_highlights["toughest_misses"]
        parts.append(
            f"toughest word beaten: {session_highlights['toughest_label']} "
            f"(missed {misses} time{'s' if misses != 1 else ''} in a row before)"
        )
    return "Highlights this session: " + "; ".join(parts) + "." if parts else ""


def _with_highlights(message):
    extra = session_highlights_text()
    return f"{message} {extra}" if extra else message


# --- L-29: weak-items export -----------------------------------------------
WEAK_EXPORT_HEADER = ["French", "English", "Topic", "Week", "Why it is here"]


def weak_items():
    """Every fact the farm has flagged: stubborn weeds, known mix-ups, plots
    whose last answer was wrong, and anything saved to the phrasebook."""
    rows = []
    for plot in state.plots:
        reasons = []
        if is_leech(plot):
            reasons.append("stubborn weed")
        if plot.in_weeds:
            reasons.append("known mix-up")
        if plot.last_reviewed is not None and plot.correct_streak == 0 and not is_leech(plot):
            reasons.append("missed last time")
        if plot.plot_id in runstate.phrasebook:
            reasons.append("in my phrasebook")
        if not reasons:
            continue
        for item in plot.items:
            fr = item.get("fr") or item.get("prompt") or ""
            en = item.get("en") or item.get("answer") or ""
            if not fr and not en:
                continue
            rows.append(
                {
                    "fr": str(fr),
                    "en": str(en),
                    "topic": plot.topic_title,
                    "week": f"{plot.course} wk {plot.week}",
                    "why": "; ".join(reasons),
                }
            )
    return rows


def weak_items_csv():
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(WEAK_EXPORT_HEADER)
    for row in weak_items():
        writer.writerow([row["fr"], row["en"], row["topic"], row["week"], row["why"]])
    return buffer.getvalue()


def weak_items_anki():
    """Tab-separated text Anki's importer reads (front, back, tags)."""
    lines = ["#separator:tab", "#html:false", "#tags column:3"]
    for row in weak_items():
        tags = " ".join(part.strip().replace(" ", "_") for part in row["why"].split(";"))
        front = row["fr"].replace("\t", " ").replace("\n", " ")
        back = row["en"].replace("\t", " ").replace("\n", " ")
        lines.append(f"{front}\t{back}\t{tags}")
    return "\n".join(lines) + "\n"


def _download_text(filename, text, mime):
    """Hands a file to the page's own downloader (index.html), the same
    Python-computes/JS-does-the-browser-thing split as the report sender.
    Remembers the last request so a test can read it."""
    runstate._last_download = {"filename": filename, "text": text, "mime": mime}
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    hook = getattr(window, "championDownload", None)
    if hook is None:
        return False
    hook(filename, text, mime)
    return True


def export_weak_items_csv(event=None):
    return _download_text("champ-de-mots-weak-items.csv", weak_items_csv(), "text/csv")


def export_weak_items_anki(event=None):
    return _download_text("champ-de-mots-weak-items-anki.txt", weak_items_anki(), "text/plain")
