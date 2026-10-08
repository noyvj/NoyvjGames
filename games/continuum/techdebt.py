"""Continuum -- K-4: technical debt (Digital Age and later).

From the Digital Age on, the Build panel offers "Quick builds": every
building costs a quarter less, but each one is thrown up with shortcuts and
adds hidden **technical debt** to the settlement. Debt is a 0..1 stock that
never decays on its own. While it is above zero it does two things:

* **Upkeep**: every season the settlement pays materials to keep the old
  shortcuts working, `debt x buildings x UPKEEP_PER_BUILDING`.
* **Outages**: a share of the settlement's materials, tool and knowledge
  output is lost, `min(OUTAGE_CAP, debt x OUTAGE_PER_DEBT)`. The simulation has
  no random events (see `sim.py`), so the "failure odds" are an expected loss
  applied to every season rather than a dice roll: the same city, the same
  debt, the same result.

The way out is a **refactor season**: the player schedules one, and the next
season runs with output cut to `REFACTOR_OUTPUT` (the crews are rewriting
things, not producing) while the debt falls by `REFACTOR_PAYDOWN`. Nothing
else pays debt down, and slow, full-price builds never add any.

It is the same trade the real world knows: cheap-now code or buildings that
cost more every season they stay. The cost is the player's choice to make, not
a hidden penalty, and the City Views dashboard and the civic map's hazard
tint (see `views.py`) show where it stands.

How it reaches the simulation. Debt rides in `campaign.ui["tech_debt"]`
(plain JSON, validated on every read by `clean()`, so there is NO save-schema
change and an older save simply has none). It reaches the season loop through
the one research seam, the effects dict (`apply_effects`), plus a separate
upkeep payment after each season (`after_season`). With no debt the effects are
returned unchanged and nothing is paid, so a game that never uses Quick builds
plays exactly as it did before.

Pure functions only: no DOM, no storage. `game.py` owns the controls.
"""

import math

import sim

KEY = "tech_debt"
ACTIVE_ERA = "digital"

QUICK_DISCOUNT = 0.25          # share of a building's cost refunded by a quick build
DEBT_PER_QUICK_BUILD = 0.05    # debt added by each quick build
UPKEEP_PER_BUILDING = 0.25     # materials per building per season at 100% debt
OUTAGE_PER_DEBT = 0.4          # share of output lost per unit of debt
OUTAGE_CAP = 0.30
REFACTOR_OUTPUT = 0.6          # output multiplier during the refactor season
REFACTOR_PAYDOWN = 0.30        # debt removed by one refactor season
WARN_AT = 0.5                  # one log line when debt first reaches this

LOW, HIGH = 0.2, 0.5           # label bands (also the civic map's tint bands)

# The effects keys that reliability and refactoring scale (all multiplicative).
OUTPUT_KEYS = ("materials_yield_mult", "tool_yield_mult", "knowledge_mult")


def active(era):
    """True from the Digital Age on (the era the mechanic belongs to)."""
    return era in sim.ERA_ORDER and sim.era_index(era) >= sim.era_index(ACTIVE_ERA)


def fresh():
    return {"debt": 0.0, "quick": False, "refactor": False, "refactors": 0, "quick_builds": 0, "warned": False}


def _num(value, low, high, default):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    if not math.isfinite(value):
        return default
    return max(low, min(high, value))


def _count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return min(value, 10**6)


def clean(raw):
    """A validated record from whatever a save handed back (may be junk)."""
    out = fresh()
    if not isinstance(raw, dict):
        return out
    out["debt"] = round(_num(raw.get("debt"), 0.0, 1.0, 0.0), 4)
    out["quick"] = raw.get("quick") is True
    out["refactor"] = raw.get("refactor") is True
    out["refactors"] = _count(raw.get("refactors"))
    out["quick_builds"] = _count(raw.get("quick_builds"))
    out["warned"] = raw.get("warned") is True
    return out


def get(ui):
    """The record in `campaign.ui` (a fresh one when absent or junk)."""
    return clean(ui.get(KEY)) if isinstance(ui, dict) else fresh()


def put(ui, record):
    ui[KEY] = clean(record)
    return ui[KEY]


def has_any(ui):
    """True once the player has ever used the mechanic (for hiding empty rows)."""
    record = get(ui)
    return record["quick_builds"] > 0 or record["debt"] > 0 or record["refactors"] > 0


# --- the numbers ----------------------------------------------------------
def total_buildings(state):
    total = 0
    for count in state.buildings.values():
        if isinstance(count, int) and not isinstance(count, bool) and count > 0:
            total += count
    return total


def outage_share(record):
    """Share of materials/tool/knowledge output lost to outages (0..OUTAGE_CAP)."""
    return min(OUTAGE_CAP, record["debt"] * OUTAGE_PER_DEBT)


def output_multiplier(record):
    """The factor applied to the three output keys this coming season."""
    factor = 1.0 - outage_share(record)
    if record["refactor"]:
        factor *= REFACTOR_OUTPUT
    return factor


def upkeep(state, record):
    """Materials the settlement pays after the coming season."""
    return round(record["debt"] * total_buildings(state) * UPKEEP_PER_BUILDING, 2)


def label(debt):
    if debt >= HIGH:
        return "high"
    if debt >= LOW:
        return "building up"
    if debt > 0:
        return "low"
    return "none"


def hazard_level(debt):
    """0 none, 1 caution, 2 danger: the civic map's tint band."""
    if debt >= HIGH:
        return 2
    if debt >= LOW:
        return 1
    return 0


def apply_effects(effects, ui, era=None):
    """`effects` with debt and a scheduled refactor applied (a copy).

    Unchanged (same values) when there is no debt and no refactor scheduled, or
    before the Digital Age.
    """
    record = get(ui)
    if era is not None and not active(era):
        return effects
    factor = output_multiplier(record)
    if factor == 1.0:
        return effects
    merged = dict(effects)
    for key in OUTPUT_KEYS:
        merged[key] = merged.get(key, 1.0) * factor
    return merged


# --- actions ---------------------------------------------------------------
def set_quick(ui, on):
    record = get(ui)
    record["quick"] = bool(on)
    return put(ui, record)


def schedule_refactor(ui, on=True):
    record = get(ui)
    record["refactor"] = bool(on)
    return put(ui, record)


def quick_build(ui, cost):
    """Books a quick build: returns the materials refunded (the discount).

    Call it AFTER the build itself succeeded at full cost. Refuses (0.0) when
    quick builds are off.
    """
    record = get(ui)
    if not record["quick"]:
        return 0.0
    record["debt"] = min(1.0, round(record["debt"] + DEBT_PER_QUICK_BUILD, 4))
    record["quick_builds"] += 1
    put(ui, record)
    return round(float(cost) * QUICK_DISCOUNT, 2)


def after_season(ui, state, report=None):
    """Settles one season: pays upkeep, finishes a refactor, flags a warning.

    `state` is mutated (materials paid, never below zero). Returns a dict:
    `upkeep` (materials actually paid), `refactored` (bool), `eased` (debt
    removed), `before`/`after` (debt), `warn` (True once, when debt first
    reaches WARN_AT).
    """
    record = get(ui)
    before = record["debt"]
    paid = 0.0
    if active(state.era):
        owed = upkeep(state, record)
        paid = min(owed, max(0.0, state.resources["materials"]))
        state.resources["materials"] -= paid
    refactored = False
    if record["refactor"]:
        refactored = True
        record["debt"] = round(max(0.0, record["debt"] - REFACTOR_PAYDOWN), 4)
        record["refactor"] = False
        record["refactors"] += 1
    warn = False
    if record["debt"] >= WARN_AT and not record["warned"]:
        record["warned"] = True
        warn = True
    if record["debt"] < LOW:
        record["warned"] = False
    put(ui, record)
    return {
        "upkeep": round(paid, 2),
        "refactored": refactored,
        "eased": round(before - record["debt"], 4) if refactored else 0.0,
        "before": before,
        "after": record["debt"],
        "warn": warn,
    }


# --- text ------------------------------------------------------------------
def build_note(record, cost):
    """The line under the Quick builds toggle."""
    saves = cost * QUICK_DISCOUNT
    return (
        f"Quick builds cost {QUICK_DISCOUNT * 100:.0f}% less (about {saves:.0f} materials back on a "
        f"{cost:.0f}-material building) but add {DEBT_PER_QUICK_BUILD * 100:.0f}% technical debt each."
    )


def status_lines(state, record):
    """Plain sentences for the Build panel / dashboard, never colour alone."""
    pct = record["debt"] * 100
    out = [f"Technical debt: {pct:.0f}% ({label(record['debt'])})."]
    if record["debt"] > 0:
        out.append(
            f"Upkeep {upkeep(state, record):.1f} materials a season; {outage_share(record) * 100:.0f}% of "
            "materials, tool and knowledge output lost to outages."
        )
    if record["refactor"]:
        out.append(
            f"A refactor season is scheduled: next season's output is cut to {REFACTOR_OUTPUT * 100:.0f}% "
            f"and the debt falls by {REFACTOR_PAYDOWN * 100:.0f} points."
        )
    return out


def dashboard_rows(state, record):
    """Rows for the City Views 'Era pressures' section."""
    rows = [("Technical debt", f"{record['debt'] * 100:.0f}% ({label(record['debt'])})")]
    rows.append(("Debt upkeep", f"{upkeep(state, record):.1f} materials a season"))
    rows.append(("Output lost to outages", f"{outage_share(record) * 100:.0f}%"))
    rows.append(("Refactor season", "scheduled for next season" if record["refactor"] else "not scheduled"))
    return rows
