"""Routing convoys, balance bonus, ice-age tier, sparklines, announcements, rate breakdown, highlights, share result, temperature unit and the session note."""

import json

from js import document

import thaw_runstate as runstate
from thaw_bridge import _escape, _read_local_storage_item, _write_local_storage_item
from thaw_graphs import _melt_status_label
from thaw_mechanics import CRATE_EVERY, crates_ready
from thaw_model import deg, escalation_event_name, region, region_b, region_c, warming_scale
from thaw_presets import best_region_message, hard_mode_reveal_lines
from thaw_rules import (
    DAMPENING_PER_MONITOR_UNIT, DAMPENING_PER_PRESERVE_UNIT, FEEDBACK_RATE_PER_DEGREE_OVER, ICE_AGE_TIERS,
    LONG_GAME_WARMING_SCALE, MELT_THRESHOLD, TEMP_UNITS, TEMP_UNIT_STORAGE_KEY,
)
from thaw_sciencelog import _log_action, pinned_highlight_lines, science_log


# ===========================================================================
# GG-5: resource routing. A convoy moves a fixed parcel of funds from one
# managed region (A, B or C) to another, minus a transport tax, so the player
# triages between rescuing a stricken region and feeding a healthy one. Region
# D never takes part (it is the untouched baseline). The tax is the whole
# price: nothing is random and nothing is hidden. The visible stat is the
# convoy count and the funds the tax has swallowed.
# ===========================================================================
ROUTING_CONVOY_FUNDS = 50.0
ROUTING_TAX = 0.2
ROUTING_KEYS = ("a", "b", "c")


def _routing_region(key):
    return {"a": region, "b": region_b, "c": region_c}[key]


def can_route_funds(src_key, dst_key):
    return (
        src_key in ROUTING_KEYS
        and dst_key in ROUTING_KEYS
        and src_key != dst_key
        and _routing_region(src_key).funds >= ROUTING_CONVOY_FUNDS
    )


def route_funds(src_key, dst_key):
    """Sends one convoy. Returns True if it happened."""
    if not can_route_funds(src_key, dst_key):
        return False
    tax = ROUTING_CONVOY_FUNDS * ROUTING_TAX
    _routing_region(src_key).funds -= ROUTING_CONVOY_FUNDS
    _routing_region(dst_key).funds += ROUTING_CONVOY_FUNDS - tax
    runstate.convoys_sent += 1
    runstate.convoy_tax_lost += tax
    _log_action(
        dst_key.upper(),
        f"a convoy from Region {src_key.upper()} delivered {ROUTING_CONVOY_FUNDS - tax:.0f} funds "
        f"({tax:.0f} lost to the transport tax).",
    )
    return True


def _routing_selection():
    src = document.getElementById("routing-source").value
    dst = document.getElementById("routing-dest").value
    return (src if src in ROUTING_KEYS else "a", dst if dst in ROUTING_KEYS else "b")


def routing_preview_text(src_key, dst_key):
    if src_key == dst_key:
        return "Pick two different regions."
    received = ROUTING_CONVOY_FUNDS * (1 - ROUTING_TAX)
    text = (
        f"A convoy takes {ROUTING_CONVOY_FUNDS:.0f} funds from Region {src_key.upper()} and delivers "
        f"{received:.0f} to Region {dst_key.upper()} ({ROUTING_TAX * 100:.0f}% transport tax)."
    )
    if _routing_region(src_key).funds < ROUTING_CONVOY_FUNDS:
        text += f" Region {src_key.upper()} has only {_routing_region(src_key).funds:.0f} funds."
    return text


def render_routing():
    src, dst = _routing_selection()
    document.getElementById("routing-send-button").disabled = not can_route_funds(src, dst)
    document.getElementById("routing-send-button").innerText = (
        f"Send convoy: {src.upper()} → {dst.upper()}"
    )
    document.getElementById("routing-preview").innerText = routing_preview_text(src, dst)
    document.getElementById("routing-display").innerText = (
        f"Convoys sent: {runstate.convoys_sent}. Funds lost to the transport tax: {runstate.convoy_tax_lost:.0f}."
    )


# ===========================================================================
# GG-27: the perfect-balance bonus. When all three managed regions are
# melting and end a round within BALANCE_TOLERANCE degrees of each other, each
# gets BALANCE_BONUS_FUNDS and the comparison card pulses. It is only offered
# once every region is melting, because before melt all three regions climb at
# the same background rate whatever you do (so "balance" would be free).
# ===========================================================================
BALANCE_TOLERANCE = 1.0
BALANCE_BONUS_FUNDS = 20.0


def regions_balanced():
    managed = (region, region_b, region_c)
    if not all(r.is_melting() for r in managed):
        return False
    temps = [r.temperature for r in managed]
    return max(temps) - min(temps) <= BALANCE_TOLERANCE


def apply_balance_bonus():
    """Called once per Advance Round after every region has advanced."""
    if not regions_balanced():
        return False
    for r in (region, region_b, region_c):
        r.funds += BALANCE_BONUS_FUNDS
    runstate.balance_bonuses += 1
    runstate.just_balanced = True
    science_log.append({
        "region": "ABC",
        "round": region.round_number - 1,
        "text": (
            f"all three regions finished within {deg(BALANCE_TOLERANCE)} of each other: "
            f"a perfect-balance bonus of +{BALANCE_BONUS_FUNDS:.0f} funds each."
        ),
    })
    return True


def render_balance():
    document.getElementById("balance-display").innerText = (
        f"Perfect-balance bonuses: {runstate.balance_bonuses}. When all three regions are melting and end a "
        f"round within {deg(BALANCE_TOLERANCE, 0)} of each other, each gets +{BALANCE_BONUS_FUNDS:.0f} funds."
    )
    callout = document.getElementById("balance-callout")
    card = document.getElementById("region-comparison")
    if runstate.just_balanced:
        callout.innerText = (
            f"Perfect balance: all three regions finished within {deg(BALANCE_TOLERANCE, 0)} of each "
            f"other. +{BALANCE_BONUS_FUNDS:.0f} funds each."
        )
        callout.hidden = False
        card.className = "section region-comparison balance-pulse"
        runstate.just_balanced = False
    else:
        callout.hidden = True
        card.className = "section region-comparison"


# ===========================================================================
# GG-13: the Ice Age streak medal for Region A: rounds without a tipping
# event, grown into a frostier medal at 5, 10 and 15.
# ===========================================================================
def ice_age_tier(streak):
    """The (needed, name, icon) of the highest tier `streak` reaches, or None."""
    earned = None
    for tier in ICE_AGE_TIERS:
        if streak >= tier[0]:
            earned = tier
    return earned


def ice_age_text(r):
    streak = r.rounds_since_tipping_event
    best = r.best_stable_streak
    tier = ice_age_tier(streak)
    best_tier = ice_age_tier(best)
    nxt = next((t for t in ICE_AGE_TIERS if streak < t[0]), None)
    if tier is not None:
        head = f"{tier[2]} {tier[1]} medal: {streak} rounds without a tipping event."
    elif best_tier is not None:
        head = f"No medal right now ({streak} rounds since a tipping event). Best so far: {best_tier[2]} {best_tier[1]}."
    else:
        head = f"No medal yet: {streak} rounds without a tipping event."
    if nxt is not None:
        head += f" Next: {nxt[2]} {nxt[1]} at {nxt[0]}."
    else:
        head += " The top medal."
    if best > streak and tier is not None:
        head += f" Best run: {best}."
    return head


# ===========================================================================
# G-24: acceleration sparkline, and G-10: summary sentences for the graphs.
# ===========================================================================
SPARK_WIDTH = 100
SPARK_HEIGHT = 20


def accel_sparkline_text(history):
    if len(history) < 2:
        return "Acceleration history appears after the second round."
    first, last = history[0], history[-1]
    if last > first + 0.05:
        direction = "rising"
    elif last < first - 0.05:
        direction = "falling"
    else:
        direction = "steady"
    return (
        f"Acceleration over the last {len(history)} rounds: from {first:.1f}x to {last:.1f}x, "
        f"{direction}; peak {max(history):.1f}x."
    )


def accel_sparkline_svg(history):
    if len(history) < 2:
        return ""
    lo, hi = min(1.0, min(history)), max(history)
    span = max(hi - lo, 0.25)
    n = len(history)
    ys = [SPARK_HEIGHT - ((v - lo) / span) * (SPARK_HEIGHT - 2) - 1 for v in history]
    xs = [i * (SPARK_WIDTH / (n - 1)) for i in range(n)]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    base_y = SPARK_HEIGHT - ((1.0 - lo) / span) * (SPARK_HEIGHT - 2) - 1
    label = accel_sparkline_text(history)
    return (
        f'<svg viewBox="0 0 {SPARK_WIDTH} {SPARK_HEIGHT}" preserveAspectRatio="none" class="accel-sparkline-svg" role="img" '
        f'aria-label="{label}"><title>{label}</title>'
        f'<line x1="0" y1="{base_y:.1f}" x2="{SPARK_WIDTH}" y2="{base_y:.1f}" class="accel-sparkline-base" />'
        f'<polyline points="{points}" class="accel-sparkline-line" />'
        f"</svg>"
    )


def round_announcement():
    """G-10: the sentence an aria-live region reads after each Advance Round."""
    parts = [f"Round {region.round_number}."]
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        parts.append(f"Region {label} +{r.temperature:.1f} degrees, {_melt_status_label(r)}.")
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        if "melt" in r.round_events:
            parts.append(f"Region {label} started melting.")
        if "critical" in r.round_events:
            parts.append(f"Region {label} went critical.")
    if runstate.just_balanced:
        parts.append("Perfect balance bonus earned.")
    if crates_ready() > 0 and region.round_number > 1 and (region.round_number - 1) % CRATE_EVERY == 0:
        parts.append("A supply crate arrived.")
    if runstate.just_escalated and runstate.hold_the_line:
        parts.append(f"Escalation: {escalation_event_name(runstate.just_escalated)}.")
    if runstate.run_over:
        parts.append(f"The run is over after {runstate.run_result['survived']} rounds held.")
    return " ".join(parts)


# ===========================================================================
# G-4: "explain this number". A breakdown of one region's current warming rate
# into the background rise, the raw methane feedback, and what each lever takes
# off it.
# ===========================================================================
def rate_breakdown(r):
    """Returns a dict: base, raw_feedback, preserve/monitor/stance/rescue (each
    the part of raw_feedback that lever removes), net_feedback and total. The
    investment dampening is split between its sources in proportion to their
    uncapped contributions (the 85% cap is applied to the total)."""
    base = r.base_rise()
    excess = max(0.0, r.temperature - MELT_THRESHOLD)
    raw = excess * FEEDBACK_RATE_PER_DEGREE_OVER * warming_scale()
    invest_fraction = r.feedback_dampening_fraction()
    uncapped = {
        "preserve": r.capacity["preserve"] * DAMPENING_PER_PRESERVE_UNIT,
        "monitor": r.capacity["monitor"] * DAMPENING_PER_MONITOR_UNIT,
        "stance": r.policy_dampening,
    }
    total_uncapped = sum(uncapped.values())
    removed = {}
    for key, value in uncapped.items():
        share = (value / total_uncapped) if total_uncapped > 0 else 0.0
        removed[key] = raw * invest_fraction * share
    removed["rescue"] = raw * (r.effective_dampening_fraction() - invest_fraction)
    net = raw - sum(removed.values())
    return {
        "base": base, "raw_feedback": raw, "net_feedback": net,
        "preserve": removed["preserve"], "monitor": removed["monitor"],
        "stance": removed["stance"], "rescue": removed["rescue"],
        "total": base + net, "acceleration": (base + net) / base,
    }


def rate_breakdown_rows(b):
    rows = [
        ("Background rise (fixed)", b["base"], ""),
        ("Methane feedback before any lever", b["raw_feedback"], "+"),
    ]
    for key, label in (
        ("preserve", "Permafrost Preservation takes off"),
        ("monitor", "Monitoring & Response takes off"),
        ("stance", "Policy stance takes off"),
        ("rescue", "Emergency rescue takes off"),
    ):
        if b[key] > 0.0005:
            rows.append((label, b[key], "-"))
    rows.append(("Warming rate this round", b["total"], "="))
    return rows


def rate_breakdown_svg(b):
    """A stacked bar: background (solid), feedback that still lands, and the
    feedback the levers removed (outlined). Numbers in the list carry the
    meaning; the bar is only a shape cue."""
    whole = b["base"] + b["raw_feedback"]
    if whole <= 0:
        return ""
    base_w = 100 * b["base"] / whole
    net_w = 100 * b["net_feedback"] / whole
    cut_w = max(0.0, 100 - base_w - net_w)
    label = (
        f"Of {whole:.2f} degrees a round before any lever, {b['base']:.2f} is the fixed background, "
        f"{b['net_feedback']:.2f} is feedback that still lands and {whole - b['base'] - b['net_feedback']:.2f} "
        f"was removed by your levers."
    )
    return (
        f'<svg viewBox="0 0 100 8" class="rate-breakdown-svg" role="img" aria-label="{label}"><title>{label}</title>'
        f'<rect x="0" y="0" width="{base_w:.1f}" height="8" class="rate-seg-base" />'
        f'<rect x="{base_w:.1f}" y="0" width="{net_w:.1f}" height="8" class="rate-seg-net" />'
        f'<rect x="{base_w + net_w:.1f}" y="0.5" width="{max(cut_w - 0.5, 0):.1f}" height="7" class="rate-seg-cut" />'
        f"</svg>"
    )


def _inspector_region():
    key = document.getElementById("rate-inspector-region").value
    return {"a": region, "b": region_b, "c": region_c}.get(key, region), (key if key in ("a", "b", "c") else "a")


def render_rate_inspector():
    r, key = _inspector_region()
    b = rate_breakdown(r)
    rows = "".join(
        f'<li class="rate-row rate-row--{sign or "base"}"><span>{label}</span>'
        f"<span>{sign} {deg(value, 2)}</span></li>"
        for label, value, sign in rate_breakdown_rows(b)
    )
    document.getElementById("rate-inspector-body").innerHTML = (
        f"{rate_breakdown_svg(b)}<ul class=\"rate-rows\">{rows}</ul>"
        f'<p class="comparison-message">Region {key.upper()}: acceleration is this rate divided by the '
        f'background rise ({deg(b["base"], 2)}), so {b["total"]:.2f} / {b["base"]:.2f} = '
        f'{b["acceleration"]:.2f}x.</p>'
    )


# ===========================================================================
# GG-28: a three-line highlights recap, built from the regions' own records
# (when each tipped, what recovered, what the levers saved) so it stays right
# after the 40-entry scientist's log has scrolled.
# ===========================================================================
def highlights_lines():
    managed = (("A", region), ("B", region_b), ("C", region_c))
    tipped = [f"Region {label} tipped in round {r.melt_started_round}" for label, r in managed
              if r.melt_started_round is not None]
    line1 = ("; ".join(tipped) + ".") if tipped else "No region has tipped into melt yet."
    restored = [(label, r) for label, r in managed if r.restored_total > 0]
    rescued = [label for label, r in managed if r.rescue_used]
    if restored:
        total = sum(r.restored_total for _label, r in restored)
        names = ", ".join(label for label, _r in restored)
        line2 = f"Recovery: restoration pulled back {deg(total)} of melt-driven warming in Region {names}."
    elif rescued:
        line2 = f"Recovery: Region {', '.join(rescued)} used its one emergency rescue."
    else:
        line2 = "Recovery: no region has needed (or earned) one yet."
    saved = ", ".join(f"{label} {deg(r.temperature_saved())}" for label, r in managed)
    line3 = (
        f"Degrees saved versus no action: {saved}. {best_region_message()}"
    )
    return [line1, line2, line3]


def highlights_text():
    return f"Thaw highlights (round {region.round_number}): " + " ".join(
        highlights_lines() + pinned_highlight_lines() + hard_mode_reveal_lines()
    )


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (the page calls this by name through window.pyodide). Rounds played, regions that
    tipped into melt and the degrees all three regions saved against no action."""
    managed = (region, region_b, region_c)
    tipped = sum(1 for r in managed if r.melt_started_round is not None)
    saved = sum(r.temperature_saved() for r in managed)
    played = max(0, region.round_number - 1)
    return json.dumps({
        "game": "Thaw",
        "score": f"{played} round{'' if played == 1 else 's'}",
        "stats": [
            {"n": tipped, "one": "region tipped", "many": "regions tipped"},
            f"{deg(max(0.0, saved))} saved vs no action",
        ],
    })


def render_highlights():
    items = "".join(f"<li>{line}</li>" for line in highlights_lines())
    # G-19: pinned log entries ride along under the three recap lines.
    items += "".join(f'<li class="log-entry--pinned">{_escape(line)}</li>' for line in pinned_highlight_lines())
    # GG-23: hard mode's reveal of how close the forecasts were.
    items += "".join(f'<li class="hard-mode-reveal">{_escape(line)}</li>' for line in hard_mode_reveal_lines())
    document.getElementById("highlights-list").innerHTML = items


# ===========================================================================
# G-13: temperature unit (Celsius, Fahrenheit, Kelvin) for every displayed rise. A per-browser
# preference kept in localStorage, never part of the save.
# ===========================================================================
def load_temp_unit():
    raw = _read_local_storage_item(TEMP_UNIT_STORAGE_KEY)
    return raw if raw in TEMP_UNITS else "c"


def set_temp_unit(unit):
    if unit not in TEMP_UNITS:
        return False
    runstate.temp_unit = unit
    _write_local_storage_item(TEMP_UNIT_STORAGE_KEY, unit)
    return True


def render_temp_unit():
    document.getElementById("temp-unit-select").value = runstate.temp_unit


runstate.temp_unit = load_temp_unit()


# ===========================================================================
# G-22: a round-counter note with a rough session length and a gentle "good moment to save" nudge.
# ===========================================================================
SESSION_TARGET_ROUNDS = 20  # about 20 minutes (the page says "about 20 minutes"); the long game takes 2.5x
SESSION_MINUTES_PER_ROUND = 1
SAVE_NUDGE_EVERY = 5


def session_target_rounds():
    return round(SESSION_TARGET_ROUNDS / LONG_GAME_WARMING_SCALE) if runstate.long_game else SESSION_TARGET_ROUNDS


def session_note_text():
    """The line under the round counter. Rounds are counted as rounds played so far."""
    played = max(0, region.round_number - 1)
    if runstate.run_over:
        return f"The run is over after {runstate.run_result['survived'] if runstate.run_result else played} rounds. Nothing is lost: start a new game any time."
    target = session_target_rounds()
    if runstate.hold_the_line:
        text = (
            f"Round {region.round_number}. A Hold the Line run usually lasts 15 to 35 rounds, "
            f"about a minute each."
        )
    elif played >= target:
        text = (
            f"Round {region.round_number}: past a typical session of about {target} rounds. "
            f"A fine place to stop; your progress is kept if you save."
        )
    else:
        left = target - played
        minutes = left * SESSION_MINUTES_PER_ROUND
        text = (
            f"Round {region.round_number} of a typical {target}-round session: about {left} "
            f"round{'s' if left != 1 else ''} (around {minutes} minute{'s' if minutes != 1 else ''}) to go."
        )
    if played > 0 and played % SAVE_NUDGE_EVERY == 0:
        text += " Good moment to save: use the Save button if you want to stop here."
    return text
