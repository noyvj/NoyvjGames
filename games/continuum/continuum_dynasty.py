"""Dynasty (banked legacy points, banners), era doctrines and the K-17 rewind token."""

import json
import time

from js import document
from pyodide.ffi import create_proxy

import banners
import challengerun
import consulting
import doctrines
import dynasty
import rewind
import sim

import continuum_runstate as runstate
from continuum_achievements import (
    ACHIEVEMENTS, _display_toast, _seed_achievement_toast_baseline, achievement_ids_earned,
)
from continuum_base import (
    DYNASTY_STORAGE_KEY, _bank_current, _dynasty_local_store, _inherited_era, _js_window, _resting,
)
from continuum_clock import set_speed
from continuum_founders import add_founders_note, sync_name_input, update_founders_panel

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# ===========================================================================
# Round 3, third batch: K-2 Dynasty (and K-20 banners), K-6 era doctrines, K-17 the
# rewind token, K-15/K-28 notable citizens and the citizen of the season, and K-7
# computer-controlled neighbouring settlements. The rules live in dynasty.py, banners.py,
# doctrines.py, rewind.py, citizens.py and neighbours.py; this is the DOM half.
# ===========================================================================
_dynasty_proxies = []

_banner_proxies = []
_doctrine_proxies = []
_citizens_proxies = []
_neighbour_proxies = []


def _rest_reason():
    if challengerun.get(runstate.campaign.ui) is not None:
        return "a challenge run is the active run, so its score stays comparable."
    if consulting.get(runstate.campaign.ui) is not None:
        return "a consulting case is the active run, so its goal stays comparable."
    return ""


def _seed_hint():
    return int(time.time()) % 2147483647 or 1


# --- per-browser copy of the Dynasty (so a reload or an older save never takes progress away) --------------
def _dynasty_local_load():
    window = _js_window()
    if window is None:
        return None
    try:
        raw = window.localStorage.getItem(DYNASTY_STORAGE_KEY)
        return json.loads(raw) if isinstance(raw, str) else None
    except Exception:
        return None


def _adopt_local_dynasty():
    """Merges this browser's Dynasty with the one in the live save (neither loses progress)."""
    local = _dynasty_local_load()
    if local is None:
        return
    merged = dynasty.merge(runstate.campaign.ui.get(dynasty.KEY), local)
    if merged != dynasty.get(runstate.campaign.ui):
        dynasty.put(runstate.campaign.ui, merged)


# --- K-2 Dynasty ----------------------------------------------------------------------------------------
def _rank_names():
    return [name for _need, name in dynasty.RANKS]


def _banked_text(result):
    if result["points"] <= 0:
        return (
            f"A settlement is only worth banking once it has lived {dynasty.MIN_SEASONS_TO_BANK} seasons; "
            "this one has not yet."
        )
    if result["gained"] <= 0:
        return f"Already banked: this settlement is worth {result['points']} Legacy points and all of them are in."
    return f"Banked {result['gained']} Legacy points ({result['total']} earned in all)."


def on_toggle_dynasty(event=None):
    runstate.dynasty_open = not runstate.dynasty_open
    update_dynasty_panel()


def on_dynasty_bank(event=None):
    if runstate.sandbox_active:  # Z-18: no Legacy points come out of a practice settlement
        runstate._dynasty_status = "Banking Legacy is switched off in the sandbox."
    elif runstate.campaign.revisiting is not None:
        runstate._dynasty_status = "Return to the present before banking."
    else:
        result, _info = _bank_current()
        runstate._dynasty_status = _banked_text(result)
    render()


def on_dynasty_off(event=None):
    record = dynasty.get(runstate.campaign.ui)
    dynasty.set_off(runstate.campaign.ui, not record["off"])
    _dynasty_local_store()
    render()


def _dynasty_buy(node_id):
    result = dynasty.buy(runstate.campaign.ui, node_id)
    if result["ok"]:
        _dynasty_local_store()
        render()
    return result


def _dynasty_refund(node_id):
    result = dynasty.refund(runstate.campaign.ui, node_id)
    if result["ok"]:
        _dynasty_local_store()
        render()
    return result


def _dynasty_refund_all():
    result = dynasty.refund_all(runstate.campaign.ui)
    _dynasty_local_store()
    render()
    return result


def _to_js(value):
    try:
        from js import Object  # noqa: PLC0415
        from pyodide.ffi import to_js  # noqa: PLC0415
    except ImportError:
        return None
    return to_js(value, dict_converter=Object.fromEntries)


def _render_dynasty_tree():
    window = _js_window()
    skill_view = getattr(window, "NoyvjSkillTree", None) if window is not None else None
    container = document.getElementById("dynasty-tree")
    if skill_view is None:
        return
    record = dynasty.get(runstate.campaign.ui)
    if runstate._dynasty_view is None:
        if not _dynasty_proxies:
            _dynasty_proxies.extend([
                create_proxy(lambda node_id, node=None: _dynasty_buy(str(node_id))),
                create_proxy(lambda node_id, node=None: _dynasty_refund(str(node_id))),
                create_proxy(lambda: _dynasty_refund_all()),
            ])
        buy, refund, refund_all = _dynasty_proxies
        options = _to_js({
            "tree": dynasty.DYNASTY_TREE, "owned": list(record["owned"]), "earned": record["earned"],
            "refundNodes": True, "onBuy": buy, "onRefund": refund, "onRefundAll": refund_all,
        })
        if options is not None:
            runstate._dynasty_view = skill_view.render(container, options)
        return
    update = _to_js({"owned": list(record["owned"]), "earned": record["earned"]})
    if update is not None:
        runstate._dynasty_view.update(update)


def _make_banner_handler(kind, item_id):
    def handler(event=None):
        banner_id = item_id if kind == "banner" else None
        flourish_id = item_id if kind == "flourish" else None
        ok, _reason = banners.choose(
            runstate.campaign.ui, banner_id, flourish_id, set(achievement_ids_earned()),
            dynasty.rank_index(dynasty.get(runstate.campaign.ui)["earned"]),
        )
        if ok:
            render()
    return handler


def _achievement_names():
    return {entry["id"]: entry["label"] for entry in ACHIEVEMENTS}


def _render_banner_picker():
    for proxy in _banner_proxies:
        proxy.destroy()
    del _banner_proxies[:]
    holder = document.getElementById("banner-list")
    holder.innerHTML = ""
    earned = set(achievement_ids_earned())
    rank_index = dynasty.rank_index(dynasty.get(runstate.campaign.ui)["earned"])
    choice = banners.effective(runstate.campaign.ui, earned, rank_index)
    names = _achievement_names()
    for heading, kind, catalog, current in (
        ("Banners", "banner", banners.BANNERS, choice["banner"]),
        ("Skyline flourishes", "flourish", banners.FLOURISHES, choice["flourish"]),
    ):
        title = document.createElement("h4")
        title.className = "banner-heading"
        title.innerText = heading
        holder.appendChild(title)
        row = document.createElement("div")
        row.className = "banner-row"
        for item in catalog:
            unlocked = banners.is_unlocked(item, earned, rank_index)
            card = document.createElement("div")
            card.className = "banner-card" + (" banner-card--locked" if not unlocked else "")
            picture = document.createElement("span")
            picture.className = "banner-picture"
            picture.innerHTML = (
                banners.banner_svg(item["id"], 44) if kind == "banner" else banners.flourish_svg(item["id"], 120)
            ) if unlocked else ""
            card.appendChild(picture)
            button = document.createElement("button")
            button.id = f"{kind}-{item['id']}-button"
            button.className = "secondary banner-button"
            button.type = "button"
            selected = item["id"] == current
            button.innerText = ("✓ " if selected else ("" if unlocked else "🔒 ")) + item["label"]
            button.disabled = not unlocked
            button.setAttribute("aria-pressed", "true" if selected else "false")
            if not unlocked:
                button.title = banners.unlock_text(item, names, _rank_names())
                button.setAttribute("aria-label", f"{item['label']}, locked. {button.title}")
            proxy = create_proxy(_make_banner_handler(kind, item["id"]))
            _banner_proxies.append(proxy)
            button.addEventListener("click", proxy)
            card.appendChild(button)
            if not unlocked:
                hint = document.createElement("span")
                hint.className = "banner-hint"
                hint.innerText = banners.unlock_text(item, names, _rank_names())
                card.appendChild(hint)
            row.appendChild(card)
        holder.appendChild(row)


def update_dynasty_panel():
    record = dynasty.get(runstate.campaign.ui)
    toggle = document.getElementById("dynasty-toggle-button")
    free = dynasty.points_free(record)
    toggle.innerText = "Hide Dynasty" if runstate.dynasty_open else (f"🏰 Dynasty ({free} pts)" if free else "🏰 Dynasty")
    panel = document.getElementById("dynasty-panel")
    panel.hidden = not runstate.dynasty_open
    if not runstate.dynasty_open:
        return
    resting = _resting()
    lines = dynasty.status_lines(runstate.campaign.ui, resting, _rest_reason())
    info = dynasty.run_info(runstate.campaign, _inherited_era())
    run = dynasty.get_run(runstate.campaign.ui)
    lines.append(
        f"This settlement is worth {info['points']} Legacy points so far ({run['banked']} banked). "
        "Points are banked when you found a new settlement or when it collapses, or any time with the button below."
    )
    document.getElementById("dynasty-summary").innerText = " ".join(lines)
    off = document.getElementById("dynasty-off-button")
    off.innerText = f"Dynasty perks: {'OFF' if record['off'] else 'ON'}"
    off.setAttribute("aria-pressed", "false" if record["off"] else "true")
    bank_button = document.getElementById("dynasty-bank-button")
    bank_button.disabled = runstate.campaign.revisiting is not None
    document.getElementById("dynasty-bank-status").innerText = runstate._dynasty_status
    _render_dynasty_tree()
    _render_banner_picker()


def _dynasty_start_message(bonuses):
    return f"Dynasty heritage arrives with the first season: {dynasty.start_text(bonuses)}."


# --- K-6 doctrines ----------------------------------------------------------------------------------------
def on_toggle_doctrines(event=None):
    runstate.doctrines_open = not runstate.doctrines_open
    update_doctrines_panel()


def _make_doctrine_handler(doctrine_id):
    def handler(event=None):
        if runstate.campaign.revisiting is not None:
            return
        era = runstate.state.era
        ok, _reason = doctrines.choose(runstate.campaign.ui, era, doctrine_id)
        if ok:
            line = doctrines.log_line(era, doctrine_id)
            add_founders_note(line)
            runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, line)
            update_founders_panel()
            render()
    return handler


def update_doctrines_panel():
    open_now = runstate.campaign.revisiting is None and doctrines.is_open(runstate.campaign.ui, runstate.state.era)
    toggle = document.getElementById("doctrines-toggle-button")
    toggle.innerText = "Hide Doctrines" if runstate.doctrines_open else ("⚖️ Doctrines (choose)" if open_now else "⚖️ Doctrines")
    panel = document.getElementById("doctrines-panel")
    panel.hidden = not runstate.doctrines_open
    if not runstate.doctrines_open:
        return
    for proxy in _doctrine_proxies:
        proxy.destroy()
    del _doctrine_proxies[:]
    edge = dynasty.doctrine_edge(runstate.campaign.ui, _resting())
    chosen = doctrines.chosen_for(runstate.campaign.ui, runstate.state.era)
    if runstate.state.era == sim.FIRST_ERA:
        status = "Doctrines begin with your first era transition. Enter the Agrarian era to adopt one."
    elif chosen:
        status = f"The {sim.ERA_LABEL[runstate.state.era]} era follows the {doctrines.DOCTRINES[chosen]['label']} doctrine."
    elif runstate.campaign.revisiting is not None:
        status = "Return to the present to adopt a doctrine."
    else:
        status = f"Choose a doctrine for the {sim.ERA_LABEL[runstate.state.era]} era. The choice is final for this era."
    if edge:
        status += f" Schools of Thought makes each doctrine's main discount {edge} points deeper."
    document.getElementById("doctrines-status").innerText = status
    holder = document.getElementById("doctrines-list")
    holder.innerHTML = ""
    counts = doctrines.counts(runstate.campaign.ui)
    for doctrine_id, info in doctrines.DOCTRINES.items():
        card = document.createElement("div")
        card.className = "doctrine-card"
        for css, tag, text in (
            ("doctrine-name", "h3", info["label"] + (" (entrenched)" if counts.get(doctrine_id, 0) >= 2 else "")),
            ("row-blurb", "p", info["blurb"]),
            ("status-line", "p", doctrines.discount_text(doctrine_id) + "; " + doctrines.effect_text(doctrine_id) + "."),
        ):
            node = document.createElement(tag)
            node.className = css
            node.innerText = text
            card.appendChild(node)
        button = document.createElement("button")
        button.id = f"doctrine-{doctrine_id}-button"
        button.className = "secondary"
        button.type = "button"
        button.innerText = "✓ Adopted for this era" if chosen == doctrine_id else f"Adopt the {info['label']} doctrine"
        button.disabled = not open_now
        proxy = create_proxy(_make_doctrine_handler(doctrine_id))
        _doctrine_proxies.append(proxy)
        button.addEventListener("click", proxy)
        card.appendChild(button)
        holder.appendChild(card)
    history = document.getElementById("doctrines-history")
    history.innerHTML = ""
    rows = doctrines.history(runstate.campaign.ui)
    if not rows:
        node = document.createElement("p")
        node.className = "row-blurb"
        node.innerText = "No doctrine adopted yet."
        history.appendChild(node)
    for era, doctrine_id in rows:
        node = document.createElement("p")
        node.className = "status-line"
        node.innerText = f"{sim.ERA_LABEL[era]} era: {doctrines.DOCTRINES[doctrine_id]['label']}"
        history.appendChild(node)


# --- K-17 rewind ------------------------------------------------------------------------------------------
def _rewind_tokens():
    return rewind.tokens_left(
        runstate.campaign.ui, len(achievement_ids_earned()), dynasty.rewind_perk_tokens(runstate.campaign.ui)
    )


def on_rewind(event=None):
    reason = rewind.refusal(runstate._rewind_snapshot, runstate.campaign, _rewind_tokens(), _resting())
    if reason:
        _display_toast(reason)
        return
    ok, cost = rewind.apply(runstate.campaign, runstate._rewind_snapshot)
    runstate._rewind_snapshot = None
    if not ok:
        _display_toast("The season could not be unwound.")
        return
    set_speed(0)
    runstate.chronicle.log_challenge(
        runstate.state.season, runstate.state.era,
        f"A season was unwound. It cost a rewind token and {cost:.1f} knowledge; time is held until you choose a speed.",
    )
    sync_name_input()
    _dynasty_local_store()
    render()
    _seed_achievement_toast_baseline()
    _display_toast(f"Season unwound. {cost:.1f} knowledge spent, {_rewind_tokens()} rewind tokens left.")


def update_rewind_button():
    button = document.getElementById("rewind-button")
    tokens = _rewind_tokens()
    button.innerText = f"↶ Rewind ({tokens})"
    reason = rewind.refusal(runstate._rewind_snapshot, runstate.campaign, tokens, _resting())
    text = rewind.preview(runstate._rewind_snapshot, runstate.campaign, tokens, _resting())
    button.disabled = bool(reason)
    button.title = text
    button.setAttribute("aria-label", f"Rewind one season, {tokens} tokens. {text}")
