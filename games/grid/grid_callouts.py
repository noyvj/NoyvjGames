"""One-time callouts and per-plant helpers: the 50%-renewable callout, retire/maintain callouts, disruption toast,
arrow-key commands for the plant rows and the mix hover text.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import grid_runstate as runstate
from grid_rules import EMISSIONS_FACTOR, GENERATION_TYPES, PLANT_CAPACITY, PLANT_LABEL, PLANT_TYPES
from grid_achievements import renewable_capacity_share
from grid_messages import disruption_reason, event_message


def _pulse_emissions_meter():
    """C24: a brief pulse on the emissions meter the instant renewables
    cross 50% of capacity. Pure CSS class, removed by timer."""
    meter = document.getElementById("emissions-bar")
    meter.classList.add("meter-pulse")

    def _clear(*args):
        meter.classList.remove("meter-pulse")
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 1600)


def _check_renewable_milestone():
    """Called after every action that could change capacity composition
    (build/retire/advance round) -- not from render() itself, so a loaded
    save doesn't flash the callout purely from being rendered once."""
    if not runstate.state.renewable_50_reached and renewable_capacity_share() >= 0.5:
        runstate.state.renewable_50_reached = True
        runstate.renewable_milestone_visible = True
        _pulse_emissions_meter()


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm, allow_skip=True):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    every other optional-JS-hook call in this hub (e.g. continuum's
    `_notify_visual_layer()`, champ-de-mots' `_dispatch_report()`). The
    pytest fake-DOM harness's `js` module only ever fakes `document`/
    `setTimeout` (see tests/conftest.py), never `window`, so `from js
    import window` raises ImportError there and this falls straight
    through to calling on_confirm() synchronously -- which is exactly
    what every existing test that drives a retire click already expects."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    options = {} if allow_skip else {"allowSkip": False}
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
        **options,
    )


def _play_demolition_puff():
    """GC-4: replays the little smoke puff on the eulogy line (CSS only; off under reduced motion)."""
    line = document.getElementById("eulogy-display")
    line.classList.remove("eulogy-puff")

    def _start(*args):
        line.classList.add("eulogy-puff")
        proxy.destroy()

    proxy = create_proxy(_start)
    setTimeout(proxy, 30)


# C-4 -- plant-mix hover/focus readout: one plant type's share of capacity, of the round's revenue and of
# its emissions, plus a highlight on its row. Pure display; no new state.
def mix_hover_text(plant_type):
    share = runstate.state.capacity_share(plant_type)
    total_capacity = runstate.state.total_capacity()
    if total_capacity <= 0:
        return f"{PLANT_LABEL[plant_type]}: no generation on the grid yet, so no share of capacity, revenue or emissions."
    paid_units = min(total_capacity, runstate.state.demand)
    revenue = share * paid_units * runstate.state.revenue_per_unit
    revenue_total = paid_units * runstate.state.revenue_per_unit
    emissions = runstate.state.plant_counts[plant_type] * PLANT_CAPACITY[plant_type] * EMISSIONS_FACTOR[plant_type]
    emissions_total = sum(
        runstate.state.plant_counts[t] * PLANT_CAPACITY[t] * EMISSIONS_FACTOR[t] for t in GENERATION_TYPES
    )
    emissions_part = (
        f"{emissions / emissions_total * 100:.0f}% of emissions ({emissions:.0f} of {emissions_total:.0f} per round)"
        if emissions_total > 0
        else "0% of emissions (the grid emits nothing)"
    )
    return (
        f"{PLANT_LABEL[plant_type]}: {share * 100:.0f}% of capacity, "
        f"about {share * 100:.0f}% of revenue ({revenue:.0f} of {revenue_total:.0f} funds per round, "
        f"every unit of output sold earns the same), {emissions_part}."
    )


# ---- C-5 arrow keys on the plant rows --------------------------------------------------------------------------------
# With focus anywhere inside a plant row (its Build, Retire or Maintain button, or the row itself): Right arrow builds one
# unit, Left arrow retires one (through exactly the same handlers as the buttons, so a last-unit warning, the refund and
# the spoken result are the same), and Up/Down move focus to the plant above or below, keeping the same kind of control.
# The row's own Auto-maintain select keeps its native arrow keys, any key with Ctrl, Alt or Meta is left alone, and a held
# (auto-repeating) key builds or retires only once.
PLANT_KEY_ACTIONS = {"ArrowRight": "build", "ArrowLeft": "retire"}
PLANT_KEY_MOVES = {"ArrowUp": -1, "ArrowDown": 1}
PLANT_KEY_HINT = (
    "Keyboard: with focus on a plant, Right arrow builds one, Left arrow retires one, "
    "Up and Down arrows move between plants."
)


def plant_key_command(key, plant_type, target_id="", tag="", ctrl=False, alt=False, meta=False):
    """What a key press on a plant row means: ("build" | "retire", plant) or ("move", plant) or None (not ours)."""
    if ctrl or alt or meta or str(tag).upper() in ("SELECT", "INPUT", "TEXTAREA"):
        return None
    if key in PLANT_KEY_ACTIONS:
        return (PLANT_KEY_ACTIONS[key], plant_type)
    if key in PLANT_KEY_MOVES:
        order = list(PLANT_TYPES)
        neighbour = order.index(plant_type) + PLANT_KEY_MOVES[key]
        if 0 <= neighbour < len(order):
            return ("move", order[neighbour])
        return ("move", plant_type)  # at the top or bottom: stay put
    return None


def _control_kind(target_id):
    for kind in ("build", "retire", "maintain"):
        if str(target_id).endswith(f"-{kind}-button"):
            return kind
    return "build"


def _make_mix_hover_handler(plant_type, entering):
    def handler(event=None):
        readout = document.getElementById("mix-hover-readout")
        row = document.getElementById(f"{plant_type}-row")
        mix_row = document.getElementById(f"{plant_type}-mix-row")
        if entering:
            readout.innerText = mix_hover_text(plant_type)
            row.classList.add("plant-row--highlight")
            mix_row.classList.add("mix-row--active")
        else:
            readout.innerText = MIX_HOVER_HINT
            row.classList.remove("plant-row--highlight")
            mix_row.classList.remove("mix-row--active")
    return handler


MIX_HOVER_HINT = "Hover or focus a bar to see that plant type's share of capacity, revenue and emissions."


DISRUPTION_TOAST_SEVERITY_CLASSES = ("disruption-toast--warning", "disruption-toast--danger")


def _display_disruption_toast(message, severity_class):
    """C12: a visible toast/banner for a disruption or aging-breakdown
    event, on top of the persistent #event-display/#aging-event-display
    status lines -- those require scrolling to notice; this surfaces the
    same information immediately regardless of scroll position. Same
    show-then-auto-hide shape as the achievement-unlock toast, styled by
    severity rather than always the same color."""
    toast = document.getElementById("disruption-toast")
    text = document.getElementById("disruption-toast-text")
    text.innerText = message
    for cls in DISRUPTION_TOAST_SEVERITY_CLASSES:
        toast.classList.remove(cls)
    toast.classList.add(severity_class)
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 5000)


def _check_disruption_toast():
    """Called only from on_advance_round(), right after a round resolves:
    a disruption event takes priority over an aging breakdown when both
    land the same round, matching render()'s own priority (a "damage"
    disruption event already implies a plant went offline this round, the
    more urgent read)."""
    if runstate.state.last_event is not None:
        severity_class = (
            "disruption-toast--danger" if runstate.state.last_event["type"] == "damage" else "disruption-toast--warning"
        )
        _display_disruption_toast(
            f"{event_message(runstate.state.last_event)} {disruption_reason(runstate.state.last_event)}", severity_class
        )
    elif runstate.state.last_aging_event is not None:
        plant_name = PLANT_LABEL[runstate.state.last_aging_event["plant"]]
        cost = runstate.state.last_aging_event["repair_cost"]
        _display_disruption_toast(
            f"Aging breakdown! A {plant_name} plant failed from wear (repair cost {cost:.0f}).",
            "disruption-toast--danger",
        )
