"""Stakeholder requests (trigger, message, counter-offer plan), stakeholder faces and friendship, request history and the stakeholder panel render."""

from js import document

import canopy_runstate as runstate
from canopy_helpers import _el, _svg_text, plot_coordinate_label
from canopy_rules import (
    ACCRUING_STATES, BARE, REPLANT_GRANT_INCOME_BONUS, REPLANT_GRANT_RELATIONS_DELTA,
    STAKEHOLDER_DECLINE_RELATIONS_DELTA, STAKEHOLDER_EVENT_INTERVAL_TICKS,
    STAKEHOLDER_GRANT_RELATIONS_DELTA, STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA,
    STAKEHOLDER_INCENTIVE_INCOME_BONUS, STAKEHOLDER_INCENTIVE_REASONS, STAKEHOLDER_INCENTIVE_REASON_TEXT,
    STAKEHOLDER_KIND_CLEAR, STAKEHOLDER_KIND_INCENTIVE, STAKEHOLDER_KIND_REPLANT_GRANT, STAKEHOLDER_REASONS,
    STAKEHOLDER_REASON_TEXT, STAKEHOLDER_REQUEST_CYCLE_LENGTH, lab,
)
from canopy_weather import _note_season_relations
from canopy_worldvars import REQUEST_HISTORY_MAX, REQUEST_PACE_FACTOR, request_history


def _most_established_plot_index():
    """The standing plot with the highest accrued value — the one a
    stakeholder request targets, since it's the one with the most at
    stake for both sides of the decision."""
    candidates = [p for p in runstate.plots if p.state in ACCRUING_STATES and p.value > 0 and p.index != runstate.heart_tree_index]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.value).index


def _replant_grant_target_index():
    """B25: the bare plot a replant grant would restore -- the one with the
    healthiest soil (most worth restoring), lowest index on ties."""
    bare = [p for p in runstate.plots if p.state == BARE and not p.blocked]
    if not bare:
        return None
    return max(bare, key=lambda p: (p.productivity_multiplier(), -p.index)).index


def maybe_trigger_stakeholder_request():
    if runstate.pending_stakeholder_request is not None:
        return
    runstate._ticks_since_last_request += 1
    if runstate._ticks_since_last_request < current_request_interval():  # B-6
        return
    target = _most_established_plot_index()
    if target is None:
        return  # try again next tick once something's actually established
    grant_target = _replant_grant_target_index()
    incentive_slot = runstate._stakeholder_request_count % STAKEHOLDER_REQUEST_CYCLE_LENGTH >= len(STAKEHOLDER_REASONS)
    if (
        incentive_slot
        and grant_target is not None
        and (runstate._stakeholder_request_count // STAKEHOLDER_REQUEST_CYCLE_LENGTH) % 2 == 1
    ):
        runstate.pending_stakeholder_request = {
            "plot_index": grant_target,
            "reason": "replant_fund",
            "kind": STAKEHOLDER_KIND_REPLANT_GRANT,
        }
        runstate._stakeholder_request_count += 1
        runstate._ticks_since_last_request = 0
        return
    # B11: a full pass through STAKEHOLDER_REASONS (3 requests) plays out
    # exactly as before, then the 4th request in the cycle is a positive
    # incentive offer instead -- see the constants' own comment above.
    cycle_position = runstate._stakeholder_request_count % STAKEHOLDER_REQUEST_CYCLE_LENGTH
    if cycle_position < len(STAKEHOLDER_REASONS):
        kind = STAKEHOLDER_KIND_CLEAR
        reason = STAKEHOLDER_REASONS[cycle_position]
    else:
        kind = STAKEHOLDER_KIND_INCENTIVE
        incentive_turn = runstate._stakeholder_request_count // STAKEHOLDER_REQUEST_CYCLE_LENGTH
        reason = STAKEHOLDER_INCENTIVE_REASONS[incentive_turn % len(STAKEHOLDER_INCENTIVE_REASONS)]
    runstate.pending_stakeholder_request = {"plot_index": target, "reason": reason, "kind": kind}
    runstate._stakeholder_request_count += 1
    runstate._ticks_since_last_request = 0


def stakeholder_request_message():
    if runstate.pending_stakeholder_request is None:
        return ""
    idx = runstate.pending_stakeholder_request["plot_index"]
    reason = runstate.pending_stakeholder_request["reason"]
    label = plot_coordinate_label(idx)
    # .get(), not bare indexing: a request built before B11 (or a manually
    # constructed test fixture) simply lacks "kind" and means "clear", the
    # only kind that existed before.
    kind = runstate.pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    if kind == STAKEHOLDER_KIND_REPLANT_GRANT:
        return (
            f"Plot {label} is bare, and a community restoration fund is offering a {REPLANT_GRANT_INCOME_BONUS:.0f} "
            "grant specifically to replant it. Accept to start replanting it now, or decline?"
        )
    if kind == STAKEHOLDER_KIND_INCENTIVE:
        return (
            f"Plot {label} is thriving, and {STAKEHOLDER_INCENTIVE_REASON_TEXT[reason]}. "
            "Accept for a relations boost and a funding bonus, or decline and keep your options open?"
        )
    return f"Plot {label} is thriving, but {STAKEHOLDER_REASON_TEXT[reason]}. Grant the request, or decline and keep it standing?"


def _stakeholder_target_is_still_standing():
    """A pending request names its target plot by index, but nothing stops
    the player from selecting that same plot and clicking Clear directly,
    bypassing Grant/Decline entirely. Guards both handlers below against a
    stale request: without this, Grant would hand out its relations bonus
    for free (clear() on an already-BARE plot is a no-op, no real payout),
    and Decline would penalize relations for a plot that isn't standing
    anymore."""
    plot = runstate.plots[runstate.pending_stakeholder_request["plot_index"]]
    if runstate.pending_stakeholder_request.get("kind") == STAKEHOLDER_KIND_REPLANT_GRANT:
        return plot.state == BARE  # B25: the offer is for a plot that must still be bare
    return plot.state in ACCRUING_STATES


def _note_community_relations_change():
    """Tracks the running minimum community_relations has ever reached —
    achievements' `rebuilt_trust` needs to know relations genuinely dropped
    low at some point, not just where they sit right now."""
    runstate.community_relations_min_ever = min(runstate.community_relations_min_ever, runstate.community_relations)
    _note_season_relations()  # GB-30


# B-25 (2026-10-09): a third answer to a clear-request, the Counter-offer. Deterministic, previewed with its numbers:
# with bare plots available you offer to replant up to two of them (the nearest to the requested plot) instead;
# with none you harvest half of the requested plot's value and keep the rest standing (its soil is not degraded).
COUNTER_RELATIONS_TWO_PLOTS = 5
COUNTER_RELATIONS_ONE_PLOT = 3
COUNTER_RELATIONS_HALF = 5
COUNTER_HALF_FRACTION = 0.5


def counter_offer_plan():
    """The counter-offer for the pending clear request, or None (no request, or not a clear request)."""
    if runstate.pending_stakeholder_request is None:
        return None
    if runstate.pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR) != STAKEHOLDER_KIND_CLEAR:
        return None
    target = runstate.pending_stakeholder_request["plot_index"]
    if not 0 <= target < len(runstate.plots):
        return None
    target_row, target_col = divmod(target, runstate.GRID_COLS)
    bare = sorted(
        (p for p in runstate.plots if p.state == BARE and p.index != target and not p.blocked),
        key=lambda p: (abs(divmod(p.index, runstate.GRID_COLS)[0] - target_row) + abs(divmod(p.index, runstate.GRID_COLS)[1] - target_col), p.index),
    )[:2]
    if bare:
        delta = COUNTER_RELATIONS_TWO_PLOTS if len(bare) == 2 else COUNTER_RELATIONS_ONE_PLOT
        labels = " and ".join(plot_coordinate_label(p.index) for p in bare)
        return {
            "kind": "replant", "target": target, "plots": [p.index for p in bare], "relations": delta, "income": 0.0,
            "preview": f"Counter-offer: replant {labels} instead. Community relations +{delta}; "
                       f"{plot_coordinate_label(target)} stays standing and unharmed.",
        }
    value = runstate.plots[target].value
    payout = round(value * COUNTER_HALF_FRACTION, 2)
    return {
        "kind": "half", "target": target, "plots": [], "relations": COUNTER_RELATIONS_HALF, "income": payout,
        "preview": f"Counter-offer: harvest half of {plot_coordinate_label(target)} ({payout:.1f} income). "
                   f"It keeps {value - payout:.1f} value and its soil. Community relations +{COUNTER_RELATIONS_HALF}.",
    }


# GB-25 (2026-10-09): stakeholder faces. Each kind of request comes from a recurring named character with a mood and a
# small portrait drawn in code. Trust grows when you engage (grant +1, counter-offer +2, accept an offer +2) and is never
# lost; a decline just leaves them disappointed for their next request. Allies (trust 5) and champions (trust 8) stretch
# the gap between requests: +10% and +20% each, at most +50% in all. Kept per forest, saved only once someone has been met.
FACES = {
    "mayor": {"name": "Mayor Odalys", "role": "the mayor", "skin": "#e0b48a", "accent": "#6b7fd7", "hat": "sash"},
    "farmer": {"name": "Farmer Brennan", "role": "a local farmer", "skin": "#d9a679", "accent": "#a8873c", "hat": "brim"},
    "foreman": {"name": "Foreman Garrick", "role": "the timber foreman", "skin": "#c98f66", "accent": "#c4743a", "hat": "helmet"},
    "broker": {"name": "Broker Tessaly", "role": "the carbon broker", "skin": "#f0c8a0", "accent": "#3d9aa6", "hat": "tie"},
    "ranger": {"name": "Ranger Ines", "role": "the restoration ranger", "skin": "#b8805a", "accent": "#2f7d4a", "hat": "cap"},
}
REASON_FACE = {"housing": "mayor", "farming": "farmer", "resources": "foreman", "ecotourism": "broker",
               "carbon_credit": "broker", "conservation_grant": "ranger"}
FACE_TRUST_MAX = 10
FACE_ALLY_TRUST, FACE_CHAMPION_TRUST = 5, 8
FACE_INTERVAL_BONUS = {"ally": 0.10, "champion": 0.20}
FACE_INTERVAL_BONUS_CAP = 0.5
FACE_TRUST_GAIN = {"granted": 1, "countered": 2, "accepted": 2, "declined": 0}
FACE_TONES = {
    "reserved": "keeps it formal and brief.",
    "disappointed": "sounds disappointed, but says they understand.",
    "pleased": "is pleased you listened last time.",
    "friendly": "greets you like a neighbour.",
    "ally": "speaks as an ally of the forest now.",
    "champion": "treats you as a champion of the valley.",
}
stakeholder_faces = {}  # face id -> {"trust": int, "last": str, "met": int}


def face_for_request(request):
    if request is None:
        return None
    if request.get("kind") == STAKEHOLDER_KIND_REPLANT_GRANT:
        return "ranger"
    return REASON_FACE.get(request.get("reason"))


def face_tier(trust):
    if trust >= FACE_CHAMPION_TRUST:
        return "champion"
    if trust >= FACE_ALLY_TRUST:
        return "ally"
    return "friendly" if trust >= 3 else "none"


def face_mood(face_id):
    state = stakeholder_faces.get(face_id)
    if not state or not state["met"]:
        return "reserved"
    if state["last"] == "declined":
        return "disappointed"
    tier = face_tier(state["trust"])
    if tier != "none":
        return tier
    return "pleased" if state["last"] in ("granted", "countered", "accepted") else "reserved"


def face_tone_text(face_id):
    return f"{FACES[face_id]['name']} {FACE_TONES[face_mood(face_id)]}"


def note_face_choice(choice, request, kind):
    """Records one answered request against its character (called from the request history hook)."""
    face_id = face_for_request(request)
    if face_id is None:
        return
    state = stakeholder_faces.setdefault(face_id, {"trust": 0, "last": "", "met": 0})
    label = "accepted" if choice == "granted" and kind in (STAKEHOLDER_KIND_INCENTIVE, STAKEHOLDER_KIND_REPLANT_GRANT) else choice
    state["trust"] = min(FACE_TRUST_MAX, state["trust"] + FACE_TRUST_GAIN.get(label, 0))
    state["last"] = label
    state["met"] += 1


def friendship_interval_factor():
    bonus = sum(FACE_INTERVAL_BONUS.get(face_tier(s["trust"]), 0.0) for s in stakeholder_faces.values())
    return 1.0 + min(FACE_INTERVAL_BONUS_CAP, bonus)


def face_portrait_svg(face_id):
    face = FACES[face_id]
    mood = face_mood(face_id)
    mouth = {"pleased": "M17 32 Q24 39 31 32", "friendly": "M17 32 Q24 39 31 32", "ally": "M17 31 Q24 40 31 31",
             "champion": "M17 31 Q24 41 31 31", "disappointed": "M18 35 Q24 30 30 35"}.get(mood, "M19 33 L29 33")
    hats = {
        "sash": f'<path d="M13 22 L35 22 L33 16 Q24 10 15 16 Z" fill="{face["accent"]}"/>',
        "brim": '<path d="M9 21 L39 21 L35 20 Q24 9 13 20 Z" fill="#8a6a3f"/>',
        "helmet": '<path d="M12 22 Q24 6 36 22 Z" fill="#e8c14c"/>',
        "tie": f'<path d="M22 40 L26 40 L27 47 L24 45 L21 47 Z" fill="{face["accent"]}"/>',
        "cap": f'<path d="M12 21 Q24 8 36 21 L38 22 L12 22 Z" fill="{face["accent"]}"/>',
    }
    brows = '<path d="M16 21 L21 23 M32 21 L27 23" stroke="#222" stroke-width="1.4" fill="none"/>' if mood == "disappointed" else ""
    return (
        f'<svg viewBox="0 0 48 48" width="48" height="48" class="face-portrait" role="img" aria-label="{_svg_text(face["name"])}, {mood}">'
        f'<circle cx="24" cy="24" r="23" fill="{face["accent"]}" opacity="0.35"/>'
        f'<circle cx="24" cy="27" r="13" fill="{face["skin"]}"/>{hats[face["hat"]]}{brows}'
        '<circle cx="19" cy="25" r="1.7" fill="#222"/><circle cx="29" cy="25" r="1.7" fill="#222"/>'
        f'<path d="{mouth}" stroke="#222" stroke-width="1.6" fill="none" stroke-linecap="round"/></svg>'
    )


def faces_rows():
    """Lines for the Session Summary: everyone met so far, with trust, mood and any perk."""
    rows = []
    for face_id, face in FACES.items():
        state = stakeholder_faces.get(face_id)
        if not state or not state["met"]:
            continue
        tier = face_tier(state["trust"])
        perk = {"ally": " Perk: requests come about 10% less often.", "champion": " Perk: requests come about 20% less often."}.get(tier, "")
        rows.append(f"{face['name']} ({face['role']}): trust {state['trust']}/{FACE_TRUST_MAX}, {face_mood(face_id)}, asked {state['met']} time{'s' if state['met'] != 1 else ''}.{perk}")
    return rows


def render_faces():
    element = _el("faces-list")
    if element is not None:
        rows = faces_rows()
        element.innerText = "\n".join(rows) if rows else "Nobody met yet: answer a community request to meet the people asking."
    face_el, speaker_el, tone_el = _el("stakeholder-face"), _el("stakeholder-speaker"), _el("stakeholder-tone")
    face_id = face_for_request(runstate.pending_stakeholder_request)
    if face_el is not None:
        face_el.innerHTML = face_portrait_svg(face_id) if face_id else ""
    if speaker_el is not None:
        speaker_el.innerText = f"{FACES[face_id]['name']}, {FACES[face_id]['role']}" if face_id else ""
    if tone_el is not None:
        tone_el.innerText = face_tone_text(face_id) if face_id else ""


def _record_request_choice(choice, snapshot):
    note_face_choice(choice, runstate.pending_stakeholder_request, snapshot.get("kind"))  # GB-25
    request_history.append({**snapshot, "choice": choice})
    del request_history[:-REQUEST_HISTORY_MAX]


REQUEST_KIND_LABELS = {
    STAKEHOLDER_KIND_CLEAR: "Clear request",
    STAKEHOLDER_KIND_INCENTIVE: "Incentive offer",
    STAKEHOLDER_KIND_REPLANT_GRANT: "Replanting grant",
}


def request_history_rows(sort="newest", kind="all"):
    """B-14: rows for the 'did I choose well' table. `delta` is that plot's standing value now minus its value
    when the request was answered, so a declined clear that kept growing reads positive and a granted clear
    reads negative until the plot is replanted and regrows."""
    rows = []
    for entry in request_history:
        if kind != "all" and entry["kind"] != kind:
            continue
        idx = entry["plot"]
        now = runstate.plots[idx].value if 0 <= idx < len(runstate.plots) else 0.0
        rows.append({
            "tick": entry["tick"],
            "plot": plot_coordinate_label(idx) if 0 <= idx < len(runstate.plots) else "?",
            "kind": REQUEST_KIND_LABELS.get(entry["kind"], entry["kind"]),
            "kind_id": entry["kind"],
            "choice": entry["choice"],
            "value_then": entry["value_then"],
            "delta": round(now - entry["value_then"], 2),
        })
    keys = {
        "newest": lambda r: -r["tick"],
        "oldest": lambda r: r["tick"],
        "delta-high": lambda r: -r["delta"],
        "delta-low": lambda r: r["delta"],
        "plot": lambda r: r["plot"],
    }
    rows.sort(key=keys.get(sort, keys["newest"]))
    return rows


def render_request_history():
    element = _el("request-history-table")
    if element is None:
        return
    sort_el, kind_el = _el("request-history-sort"), _el("request-history-kind")
    rows = request_history_rows(
        getattr(sort_el, "value", "newest") or "newest", getattr(kind_el, "value", "all") or "all"
    )
    if not rows:
        element.innerText = "No answered requests yet: grant or decline one to start the table."
        return
    header = "Plot | Request | Your choice | Value then | Change since\n"
    body = "\n".join(
        f"{r['plot']} | {r['kind']} | {r['choice']} | {r['value_then']:.1f} | {r['delta']:+.1f}" for r in rows
    )
    element.innerText = header + body


INCENTIVE_MESSAGE_TOOLTIP = (
    "This is a genuinely positive offer: it never asks you to clear anything. "
    "Accepting keeps the plot standing and adds funding and community trust."
)
INCENTIVE_ACCEPT_TOOLTIP = (
    f"Accept: the plot stays standing, +{STAKEHOLDER_INCENTIVE_INCOME_BONUS:.0f} funding, "
    f"+{STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA} community relations."
)
REPLANT_GRANT_ACCEPT_TOOLTIP = (
    f"Accept: replants the bare plot now, +{REPLANT_GRANT_INCOME_BONUS:.0f} funding, "
    f"+{REPLANT_GRANT_RELATIONS_DELTA} community relations."
)
INCENTIVE_DECLINE_TOOLTIP = "Decline: no cost and no relations penalty, the offer just passes."
CLEAR_GRANT_TOOLTIP = (
    f"Grant: clears the plot and banks its value, +{STAKEHOLDER_GRANT_RELATIONS_DELTA} community relations."
)
CLEAR_DECLINE_TOOLTIP = (
    f"Decline: the plot stays standing, {STAKEHOLDER_DECLINE_RELATIONS_DELTA} community relations."
)


def render_stakeholder_panel():
    panel_el = document.getElementById("stakeholder-panel")
    message_el = document.getElementById("stakeholder-message")
    grant_button = document.getElementById("stakeholder-grant-button")
    decline_button = document.getElementById("stakeholder-decline-button")

    if runstate.pending_stakeholder_request is None:
        panel_el.hidden = True
        return
    panel_el.hidden = False
    render_faces()  # GB-25: portrait, name and tone for whoever is asking
    message_el.innerText = stakeholder_request_message()
    # B11: "Accept" reads more naturally than "Grant" for a positive-
    # trade-off offer, where the player isn't granting the community
    # anything -- the community is offering *them* something.
    kind = runstate.pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    is_replant_grant = kind == STAKEHOLDER_KIND_REPLANT_GRANT
    grant_button.innerText = "Accept" if (kind == STAKEHOLDER_KIND_INCENTIVE or is_replant_grant) else "Grant"
    # B8: an incentive is a gift, not an ask -- say so on hover before the
    # player commits (and on the floating badge, before the panel is even
    # scrolled into view).
    is_incentive = kind == STAKEHOLDER_KIND_INCENTIVE or is_replant_grant
    grant_button.title = (
        REPLANT_GRANT_ACCEPT_TOOLTIP if is_replant_grant
        else INCENTIVE_ACCEPT_TOOLTIP if is_incentive else CLEAR_GRANT_TOOLTIP
    )
    decline_button.title = INCENTIVE_DECLINE_TOOLTIP if is_incentive else CLEAR_DECLINE_TOOLTIP
    counter_button = _el("stakeholder-counter-button")  # B-25
    if counter_button is not None:
        plan = counter_offer_plan()
        counter_button.hidden = plan is None
        counter_button.disabled = plan is None
        if plan is not None:
            counter_button.title = plan["preview"]
            counter_button.setAttribute("aria-label", plan["preview"])
    message_el.title = INCENTIVE_MESSAGE_TOOLTIP if is_incentive else ""
    badge = document.getElementById("stakeholder-badge")
    if badge is not None:
        badge.innerText = "\U0001F381 Incentive offer" if is_incentive else "\U0001F3D8\ufe0f Pending request"
        badge.title = INCENTIVE_MESSAGE_TOOLTIP if is_incentive else "A community request is waiting for your decision."
    grant_button.disabled = False
    decline_button.disabled = False


def current_request_interval():
    """Ticks between community requests: the Pass 3 interval scaled by the chosen pace."""
    factor = REQUEST_PACE_FACTOR.get(runstate.current_pace, 1.0)
    return max(5, int(round(STAKEHOLDER_EVENT_INTERVAL_TICKS * factor * friendship_interval_factor() / lab["requests"])))  # B-5, GB-25
