"""The What's New changelog panel, the info page, the personal best and learning readouts and the sourced real-world note."""

import json

import info_page
from js import document

import drift_runstate as runstate
from drift_model_region import region
from drift_rules import LEARNING_INTEGRATION_BONUS, LEARNING_STORAGE_KEY, STRAIN_LEVEL_THRESHOLDS


# ===========================================================================
# Changelog panel (site-wide goal, planning/TODO.md, origin K16: "Per-game
# in-game changelog panel, for every game"). A quick highlights view, not a
# full duplicate of CLAUDE.md/BCM114-DEV-LOG.md -- same loading contract as
# ACHIEVEMENTS above: the boot script fetches changelog.json and hands it to
# Python as a window global before this file runs, with a filesystem
# fallback for the pytest harness (no real `js.CHANGELOG_JSON` there).
# Unlike ACHIEVEMENTS, this is a flat list (no wrapping key) -- see
# changelog.json itself.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as `_read_achievements_json()` above."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to an empty list rather than crashing this module's whole
# import -- the changelog panel is purely informational, not core to
# Drift's gameplay.
try:
    CHANGELOG = json.loads(_read_changelog_json())
except (ValueError, OSError, NameError):
    CHANGELOG = []


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if runstate.changelog_open else "📋 What's New"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    # Newest first -- entries are authored newest-first in changelog.json
    # already, but sort defensively so a future out-of-order edit can't
    # silently invert the panel.
    for entry in sorted(CHANGELOG, key=lambda e: e["date"], reverse=True):
        card = document.createElement("div")
        card.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-date"
        date.innerText = entry["date"]
        card.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-text"
        text.innerText = entry["entry"]
        card.appendChild(text)

        panel.appendChild(card)


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
# Kept institutional/systems-level per this game's sensitivity note in
# CLAUDE.md's Tech notes section
# — about regional capacity, not individual migrant stories.
INFO_PAGE = {
    "framing": (
        "Climate-driven displacement is already happening at scale, and "
        "how well it goes depends far more on a receiving region's "
        "institutional preparedness than on the number of people "
        "arriving — real projections vary by tens of millions depending "
        "on how much the world invests in resilience now. Drift's "
        "capacity-vs-pressure system is modeled on that same "
        "institutional framing, deliberately kept impersonal rather than "
        "told through individual stories."
    ),
    "mechanic_tie_in": (
        "Drift's long-horizon coda is grounded in real evidence that "
        "early institutional investment in integration converts "
        "displacement pressure into a net-positive contribution over "
        "time, not just crisis management."
    ),
    "sources": [
        {
            "label": "UNHCR — Climate change and displacement",
            "url": "https://www.unhcr.org/us/what-we-do/build-better-futures/climate-change-and-displacement",
            "note": "The authoritative agency perspective, framing displacement institutionally — consistent with Drift's own framing.",
        },
        {
            "label": "Migration Policy Institute — Climate Migration 101: An Explainer",
            "url": "https://www.migrationpolicy.org/journal/feature/climate-migration-101-explainer",
            "note": "Real projections (44-216 million internal migrants by 2050) that echo Drift's \"preparedness changes the outcome\" hope angle.",
        },
        {
            "label": "Migration Policy Institute — Who Counts as a Climate Migrant?",
            "url": "https://www.migrationpolicy.org/article/who-is-a-climate-migrant",
            "note": "Explains the legal/definitional gap behind why Drift frames this as a systems/capacity problem, not a legal one.",
        },
        {
            "label": "Brookings — The climate crisis, migration, and refugees",
            "url": "https://www.brookings.edu/articles/the-climate-crisis-migration-and-refugees/",
            "note": "Policy-level analysis of the institutional response gap, grounding Drift's receiving-region capacity mechanic.",
        },
        {
            "label": "Migration Policy Institute — How Are Refugees Faring? Integration at U.S. and State Levels",
            "url": "https://www.migrationpolicy.org/publication/how-are-refugees-faring-integration-us-and-state-levels",
            "note": "Source for the in-game real-world resettlement-outcome benchmark (89% employment among recently-resettled working-age refugees, 2023).",
        },
    ],
}


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, runstate.info_page_open)


# I10: a per-browser "best run" stat -- the highest wellbeing_score() any
# session on this device has ever reached, persisted via localStorage.
# Same distinguishing rationale as Thaw's G19/Canopy's B14/Tide's D13:
# this tracks the best this *browser* has ever seen across every
# session/save on this device, not one save's snapshot, so it's
# deliberately NOT part of get_state()/the save-code system.
PERSONAL_BEST_STORAGE_KEY = "drift_personal_best_v1"


def _read_local_storage_item(key):
    """Lazy `import js` (same convention as _read_achievements_json()) so
    this file stays importable outside a real browser. Broad except on
    the actual read/write below is deliberate: a real browser can refuse
    localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly -- this feature is a nice-to-have, not core gameplay,
    so it degrades to "no personal best recorded" rather than crashing
    the module import."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 -- see docstring above
        return None


def _write_local_storage_item(key, value):
    try:
        import js  # noqa: PLC0415
    except ImportError:
        return
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return
    try:
        storage.setItem(key, value)
    except Exception:  # noqa: BLE001 -- see _read_local_storage_item's docstring
        pass


def load_personal_best():
    """Reads the stored best wellbeing_score(), defaulting to 0.0 if
    nothing is stored yet, storage is unavailable, or the stored value is
    malformed (e.g. hand-edited or from a future incompatible format)."""
    raw = _read_local_storage_item(PERSONAL_BEST_STORAGE_KEY)
    if not raw:
        return {"wellbeing_score": 0.0}
    try:
        data = json.loads(raw)
        return {"wellbeing_score": float(data.get("wellbeing_score", 0.0))}
    except (ValueError, TypeError, AttributeError):
        return {"wellbeing_score": 0.0}


personal_best = load_personal_best()


def _maybe_update_personal_best():
    """Called every render(); bumps + persists personal_best whenever the
    live session exceeds it."""
    if runstate.assisted_run:  # I-3: an assisted run never moves a personal best
        return
    score = region.wellbeing_score()
    if score > personal_best["wellbeing_score"]:
        personal_best["wellbeing_score"] = score
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))


def _maybe_record_learning():
    """I29: once any region has reached Thriving, remember it for every
    region that begins afterwards."""
    if runstate.cross_region_learning or region.thriving_round is None:
        return
    runstate.cross_region_learning = True
    _write_local_storage_item(LEARNING_STORAGE_KEY, "1")


def render_learning():
    element = document.getElementById("learning-display")
    if element is None:
        return
    if region.learning_active:
        element.innerText = (
            f"Lessons from an earlier thriving region: +{LEARNING_INTEGRATION_BONUS * 100:.0f}% faster integration here."
        )
    elif runstate.cross_region_learning:
        element.innerText = (
            f"Thriving reached: every region you start from now on begins with "
            f"+{LEARNING_INTEGRATION_BONUS * 100:.0f}% faster integration."
        )
    else:
        element.innerText = (
            f"Bring any region to Thriving once and every future region starts with "
            f"+{LEARNING_INTEGRATION_BONUS * 100:.0f}% faster integration."
        )


def render_personal_best():
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.innerText = f"Personal best wellbeing: {personal_best['wellbeing_score']:.0f}"


# ===========================================================================
# W2-drift -- "In the real world": a collapsible note that pairs the region's
# current situation with one real, sourced example of institutions handling
# the same thing. Every figure below was read from the linked page on
# 2026-09-27 (nothing recalled from memory); where a page gave no number, none
# is quoted. Kept institutional and neutral, in line with this game's
# sensitivity note: programmes, laws and documented figures, never individual
# stories or advocacy. The choice is a pure function of run state, with no RNG:
#   * a warned or active second wave -> the 2022 EU temporary-protection surge,
#   * else any strain above "stable" -> Jordan's services under pressure,
#   * else the funded policies (language access, credentialing, sponsorship)
#     rotate by round, one example per funded policy,
#   * else all examples rotate by round.
# It never changes any number in a run.
# ===========================================================================
REAL_WORLD_READ_DATE = "2026-09-27"
REAL_WORLD_ORDER = ["settlement", "language_access", "credentialing", "sponsorship", "surge", "services_strain"]
REAL_WORLD_POLICY_TOPICS = ["language_access", "credentialing", "sponsorship"]  # POLICIES keys that have an example
REAL_WORLD_EXAMPLES = {
    "settlement": {
        "title": "Uganda's settlement approach",
        "text": "Uganda's 2006 Refugee Act granted freedom of movement, the right to work and access to public services, and households in settlements were allotted a uniform plot of 30 by 30 metres. The page also records that implementation gaps remained, and reports about 1.95 million refugees in the country by October 2025.",
        "source": "Wikipedia, Refugees in Uganda", "url": "https://en.wikipedia.org/wiki/Refugees_in_Uganda",
    },
    "language_access": {
        "title": "Germany's integration courses",
        "text": "Germany introduced state-funded integration courses in 2005: 600 hours of language instruction plus 100 hours of orientation (as of 2016). About 94,020 people started one in 2012 and 142,439 in 2014; the page notes one evaluation found a 53% pass rate in 2012.",
        "source": "Wikipedia, Integration course", "url": "https://en.wikipedia.org/wiki/Integration_course",
    },
    "credentialing": {
        "title": "Recognising qualifications gained abroad (Germany)",
        "text": "Germany's federal migration office describes a recognition process in which qualifications obtained abroad are compared with German requirements. Nationality is not decisive and no residence permit is needed, and as a rule the process should not take longer than three months if all documents are complete.",
        "source": "BAMF (German Federal Office for Migration and Refugees), Recognition of foreign professional qualifications", "url": "https://www.bamf.de/EN/Themen/Integration/ZugewanderteTeilnehmende/AnerkennungBerufsabschluesse/anerkennungberufsabschluesse-node.html",
    },
    "sponsorship": {
        "title": "Canada's Private Sponsorship of Refugees Program",
        "text": "Established in 1978, the programme lets groups of citizens and organisations provide social, emotional, residential and financial support for one year or until a refugee becomes self-sufficient. The page counts nearly 300,000 refugees resettled through it since 1979 (as of January 2020).",
        "source": "Wikipedia, Private Sponsorship of Refugees Program", "url": "https://en.wikipedia.org/wiki/Private_Sponsorship_of_Refugees_Program",
    },
    "surge": {
        "title": "The EU's temporary protection for Ukraine (2022)",
        "text": "The EU invoked its Temporary Protection Directive on 3 March 2022: people covered can get a residence permit without the complicated bureaucracy normally associated with asylum, may work and access social welfare, and children can attend school as EU residents do. Protection can last up to three years.",
        "source": "Wikipedia, Temporary Protection Directive", "url": "https://en.wikipedia.org/wiki/Temporary_Protection_Directive",
    },
    "services_strain": {
        "title": "Jordan's public services under pressure",
        "text": "By November 2015, 630,776 Syrian refugees were registered in Jordan according to UNHCR data cited by the page, which describes the added pressure on Jordan's infrastructure, specifically water supplies, sanitation, housing and energy.",
        "source": "Wikipedia, Syrian refugees in Jordan", "url": "https://en.wikipedia.org/wiki/Syrian_refugees_in_Jordan",
    },
}


def real_world_topic():
    """Which example the note shows right now (pure function of run state)."""
    if region.second_wave_status in ("warned", "active"):
        return "surge"
    if region.strain_level() != STRAIN_LEVEL_THRESHOLDS[0][1]:
        return "services_strain"
    funded = [p for p in REAL_WORLD_POLICY_TOPICS if region.policy_level.get(p, 0) > 0]
    if funded:
        return funded[region.round_number % len(funded)]
    return REAL_WORLD_ORDER[region.round_number % len(REAL_WORLD_ORDER)]


def render_real_world():
    box = document.getElementById("real-world-note")
    if box is None:
        return
    example = REAL_WORLD_EXAMPLES[real_world_topic()]
    box.hidden = False
    document.getElementById("real-world-text").innerText = f"{example['title']}. {example['text']}"
    link = document.getElementById("real-world-source")
    link.innerText = f"Source: {example['source']} (read {REAL_WORLD_READ_DATE})"
    link.href = example["url"]
