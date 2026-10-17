"""The settlement archive, comparison table, export and shareable card, Found a New Settlement, the post-mortem and the Civilization Summary panel (they call each other, so they live together)."""

import json
import time

from js import document
from pyodide.ffi import create_proxy

import archive
import banners
import beyond
import consulting
import dataexport
import dynasty
import founding
import minutes
import par
import postmortem
import sim
import statlog
import summary
import sustainability

import continuum_runstate as runstate
from continuum_achievements import ACHIEVEMENTS, _seed_achievement_toast_baseline, achievement_ids_earned
from continuum_base import SEASON_SECONDS, _bank_current, _citizens_on, _js_window, _resting, _rewind_clear
from continuum_founders import play_seconds, settlement_name, sync_name_input

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# ===========================================================================
# K5 (planning/TODO.md): the civilization summary report. An on-demand
# panel, not a forced end screen -- see summary.py's own module docstring
# for why (Continuum has no forced end state to hook, the same "no hard
# fail/win state" shape Grid's own Run Summary panel documents). Same
# hidden-until-opened idiom as the achievements/changelog panels above,
# and (unlike them) purely a this-session display preference -- never
# persisted to the save, matching changelog_open/achievements_open.
# ===========================================================================


# ===========================================================================
# K18 settlement archive + K20 shareable infographic card. Records live in
# the browser's localStorage (a per-device keepsake, not part of the save
# code), validated through archive.py on every read. The thumbnail and the
# card image come from the 3D canvas via window.ContinuumVisual.capture and
# window.ContinuumCard.download (plain JS); both are absent in the 2D
# fallback and under the test harness, and everything degrades to no image.
# ===========================================================================
_archive_proxies = []


def archive_load():
    window = _js_window()
    if window is None:
        return []
    try:
        raw = window.localStorage.getItem(archive.STORAGE_KEY)
    except Exception:
        return []
    return archive.clean_records(raw) if isinstance(raw, str) else []


def archive_store(records):
    window = _js_window()
    if window is None or runstate.sandbox_active:  # Z-18
        return False
    try:
        window.localStorage.setItem(archive.STORAGE_KEY, archive.serialize(records))
        return True
    except Exception:
        return False


def _capture_image(width, quality):
    """A JPEG data URL of the live 3D scene, or '' when there is none."""
    window = _js_window()
    visual_layer = getattr(window, "ContinuumVisual", None) if window is not None else None
    capture = getattr(visual_layer, "capture", None)
    if capture is None:
        return ""
    try:
        result = capture(width, quality)
    except Exception:
        return ""
    return result if isinstance(result, str) else ""


def _today():
    return time.strftime("%Y-%m-%d")


def current_record(thumbnail=""):
    return archive.make_record(
        runstate.campaign,
        len(achievement_ids_earned()),
        _today(),
        thumbnail,
        name=settlement_name(),
        researched=None if runstate.campaign.revisiting else len(runstate.tree.researched),
        minutes=int(play_seconds() // 60),
        cosmetics=_cosmetic_choice(),
        dynasty_info=_dynasty_record_info(),
        beyond_best=beyond.get(runstate.campaign.ui)["best"],
    )


def _cosmetic_choice():
    """K-20: the banner and flourish to show (anything no longer unlocked falls back to plain)."""
    return banners.effective(
        runstate.campaign.ui, set(achievement_ids_earned()), dynasty.rank_index(dynasty.get(runstate.campaign.ui)["earned"])
    )


def _dynasty_record_info():
    """K-2: the Dynasty rank and the perks that applied to this settlement, for the archive."""
    record = dynasty.get(runstate.campaign.ui)
    return {"rank": dynasty.rank_index(record["earned"]), "perks": dynasty.active_perk_ids(runstate.campaign.ui, _resting())}


def on_archive_current(event=None):
    runstate._archive_confirm_clear = False
    del _compare_picks[:]
    record = current_record(archive.clean_thumbnail(_capture_image(320, 0.7)))
    if record is not None:
        archive_store(archive.add_record(archive_load(), record))
    update_summary_panel()


def _make_archive_delete_handler(index):
    def handler(event=None):
        del _compare_picks[:]  # indexes shift after a delete
        archive_store(archive.remove_record(archive_load(), index))
        update_summary_panel()
    return handler


def on_archive_clear(event=None):
    if not runstate._archive_confirm_clear:
        runstate._archive_confirm_clear = True
    else:
        runstate._archive_confirm_clear = False
        del _compare_picks[:]
        archive_store([])
    update_summary_panel()


# --- K-19: compare two archived settlements ---------------------------------
# Session-only: the archive indexes picked for comparison, in pick order (A then B).
_compare_picks = []


def _make_compare_handler(index):
    def handler(event=None):
        if index in _compare_picks:
            _compare_picks.remove(index)
        else:
            if len(_compare_picks) >= 2:
                del _compare_picks[0]  # a third pick replaces the oldest
            _compare_picks.append(index)
        update_summary_panel()
    return handler


def on_compare_clear(event=None):
    del _compare_picks[:]
    update_summary_panel()


def _compare_cell(parent, tag, text, css=None):
    cell = document.createElement(tag)
    if css:
        cell.className = css
    cell.innerText = text
    parent.appendChild(cell)
    return cell


def _render_compare_table(panel, records):
    """The side-by-side table for the two picked entries (nothing when fewer than two)."""
    picks = [i for i in _compare_picks if 0 <= i < len(records)]
    if len(picks) != 2:
        return
    a, b = records[picks[0]], records[picks[1]]
    rows = archive.compare(a, b)
    if not rows:
        return
    box = document.createElement("div")
    box.className = "archive-compare"
    box.id = "archive-compare-box"
    heading = document.createElement("h3")
    heading.className = "summary-eras-heading"
    heading.innerText = "Comparing two settlements"
    box.appendChild(heading)
    note = document.createElement("p")
    note.className = "row-blurb"
    note.innerText = "The difference column is B minus A. The settlement ahead on each row is in bold and underlined."
    box.appendChild(note)
    for letter, record, index in (("A", a, picks[0]), ("B", b, picks[1])):
        who = document.createElement("p")
        who.className = "row-blurb compare-who"
        who.innerText = f"{letter}: {archive.record_label(record, index)}"
        box.appendChild(who)
    table = document.createElement("table")
    table.className = "compare-table"
    head = document.createElement("tr")
    _compare_cell(head, "th", "")
    _compare_cell(head, "th", "A")
    _compare_cell(head, "th", "B")
    _compare_cell(head, "th", "Difference (B \u2212 A)")
    table.appendChild(head)
    for row in rows:
        line = document.createElement("tr")
        line.className = "compare-row compare-row--differs" if row["delta"] not in ("\u25AC same", "same", "no comparison") else "compare-row"
        _compare_cell(line, "th", row["label"])
        _compare_cell(line, "td", row["a"], "compare-cell compare-cell--lead" if row["lead"] == "a" else "compare-cell")
        _compare_cell(line, "td", row["b"], "compare-cell compare-cell--lead" if row["lead"] == "b" else "compare-cell")
        _compare_cell(line, "td", row["delta"], "compare-delta")
        table.appendChild(line)
    box.appendChild(table)
    actions = document.createElement("div")
    actions.className = "archive-actions"
    _archive_button(actions, "archive-compare-clear-button", "Stop comparing", on_compare_clear)
    box.appendChild(actions)
    panel.appendChild(box)


# --- K-18: export the run as CSV / JSON -------------------------------------


def _download_text(text, filename, mime):
    window = _js_window()
    card = getattr(window, "ContinuumCard", None) if window is not None else None
    download = getattr(card, "downloadText", None)
    if download is None:
        return False
    try:
        download(json.dumps({"text": text, "filename": filename, "mime": mime}))
    except Exception:
        return False
    return True


def export_text(kind):
    """(text, filename, mime) for one export kind, or None when there is nothing to export.

    kinds: "stats" (per-season stats CSV), "minutes" (Council Minutes CSV),
    "run" (both, with the settlement's name, as JSON).
    """
    history = statlog.rows(runstate.campaign.ui)
    entries = minutes.entries(runstate.campaign.ui)
    name = settlement_name()
    today = _today()
    if kind == "stats":
        if not history:
            return None
        return dataexport.stats_csv(history), dataexport.filename("stats", name, today), dataexport.CSV_MIME
    if kind == "minutes":
        if not entries:
            return None
        return dataexport.minutes_csv(entries), dataexport.filename("minutes", name, today), dataexport.CSV_MIME
    if kind == "run":
        if not history and not entries:
            return None
        text = dataexport.run_json(name, runstate.state.scenario, runstate.state.hard_mode, history, entries)
        return text, dataexport.filename("run", name, today), dataexport.JSON_MIME
    return None


def _make_export_handler(kind):
    def handler(event=None):
        result = export_text(kind)
        if result is None:
            runstate._export_status = "Nothing to export yet: play a season (or make a decision) first."
        elif _download_text(*result):
            runstate._export_status = f"Downloaded {result[1]}."
        else:
            runstate._export_status = "The download could not start in this browser."
        update_summary_panel()
    return handler


def _download_card(record, thumbnail):
    window = _js_window()
    card = getattr(window, "ContinuumCard", None) if window is not None else None
    download = getattr(card, "download", None)
    if download is None:
        return False
    payload = {
        "title": archive.title_of(record),
        "lines": archive.card_lines(record),
        "thumb": thumbnail,
        "filename": f"continuum-card-{record['era']}-{record['saved_on']}.png",
    }
    payload.update(banners.card_payload({"banner": record.get("banner"), "flourish": record.get("flourish")}))
    try:
        download(json.dumps(payload))
    except Exception:
        return False
    return True


def on_card_current(event=None):
    _download_card(current_record(), _capture_image(720, 0.85))


def _make_card_handler(index):
    def handler(event=None):
        records = archive_load()
        if 0 <= index < len(records):
            _download_card(records[index], records[index]["thumb"])
    return handler


def _archive_button(parent, button_id, text, handler):
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.innerText = text
    proxy = create_proxy(handler)
    _archive_proxies.append(proxy)
    button.addEventListener("click", proxy)
    parent.appendChild(button)
    return button


def _found_button(parent, button_id):
    """O-6: a "Found a new settlement" button, the archive as a jumping-off
    point. Same confirm-gated action as the scenario panel's own button."""
    button = _archive_button(parent, button_id, "Found a new settlement", on_found_new_settlement)
    button.disabled = runstate.campaign.revisiting is not None
    button.setAttribute("aria-label", "Found a new settlement (files the current settlement in the archive first)")
    return button


def _render_export_section(panel):
    """K-18: the three download buttons and their status line."""
    heading = document.createElement("h3")
    heading.className = "summary-eras-heading"
    heading.innerText = "Export your data"
    panel.appendChild(heading)
    note = document.createElement("p")
    note.className = "row-blurb"
    note.innerText = (
        "Download this settlement's numbers: one row per season (CSV), the Council Minutes (CSV), "
        "or both with the settlement's name (JSON). Kept on your device; nothing is sent anywhere."
    )
    panel.appendChild(note)
    actions = document.createElement("div")
    actions.className = "archive-actions"
    _archive_button(actions, "export-stats-button", "Per-season stats (CSV)", _make_export_handler("stats"))
    _archive_button(actions, "export-minutes-button", "Council Minutes (CSV)", _make_export_handler("minutes"))
    _archive_button(actions, "export-run-button", "Everything (JSON)", _make_export_handler("run"))
    panel.appendChild(actions)
    status = document.createElement("p")
    status.id = "export-status"
    status.className = "row-blurb export-status"
    status.setAttribute("role", "status")
    status.setAttribute("aria-live", "polite")
    status.innerText = runstate._export_status
    panel.appendChild(status)


def _render_archive_section(panel):
    """Appends the archive gallery + card buttons to the summary panel."""
    for proxy in _archive_proxies:
        proxy.destroy()
    del _archive_proxies[:]
    records = archive_load()

    heading = document.createElement("h3")
    heading.className = "summary-eras-heading"
    heading.innerText = f"Settlement archive ({len(records)} of {archive.MAX_RECORDS})"
    panel.appendChild(heading)
    note = document.createElement("p")
    note.className = "row-blurb"
    note.innerText = (
        "File this settlement's stats and a picture of its 3D view in a gallery kept on this device only. "
        "The oldest entry is dropped once the archive is full."
    )
    panel.appendChild(note)
    actions = document.createElement("div")
    actions.className = "archive-actions"
    _archive_button(actions, "archive-add-button", "Add this settlement to the archive", on_archive_current)
    _archive_button(actions, "archive-card-current-button", "Download a shareable card", on_card_current)
    _found_button(actions, "archive-found-button")
    panel.appendChild(actions)
    _render_export_section(panel)
    if len(records) >= 2:
        hint = document.createElement("p")
        hint.className = "row-blurb"
        hint.innerText = "Pick two filed settlements with their Compare buttons to see them side by side."
        panel.appendChild(hint)
    _render_compare_table(panel, records)

    gallery = document.createElement("div")
    gallery.className = "archive-gallery"
    for index in range(len(records) - 1, -1, -1):
        record = records[index]
        card = document.createElement("div")
        card.className = "archive-entry"
        if record["thumb"]:
            image = document.createElement("img")
            image.className = "archive-thumb"
            image.src = record["thumb"]
            image.alt = f"{sim.ERA_LABEL[record['era']]} era settlement"
            card.appendChild(image)
        text = document.createElement("div")
        text.className = "archive-text"
        if record.get("name"):
            name_row = document.createElement("p")
            name_row.className = "archive-line archive-line--name"
            name_row.innerText = record["name"]
            text.appendChild(name_row)
        for i, line in enumerate(archive.card_lines(record)):
            row = document.createElement("p")
            row.className = "archive-line archive-line--head" if i == 0 else "archive-line"
            row.innerText = line
            text.appendChild(row)
        stamp = document.createElement("p")
        stamp.className = "archive-line archive-date"
        stamp.innerText = f"Filed {record['saved_on']}"
        text.appendChild(stamp)
        if record.get("banner") or record.get("flourish"):
            # K-20: the cosmetic banner and flourish, drawn from the catalogue and named in words.
            flair = document.createElement("div")
            flair.className = "archive-flair"
            picture = document.createElement("span")
            picture.className = "archive-flair-picture"
            picture.innerHTML = (
                banners.banner_svg(record["banner"], 36) if record.get("banner") else ""
            ) + (banners.flourish_svg(record["flourish"], 120) if record.get("flourish") else "")
            flair.appendChild(picture)
            names = [banners.label_of(record["banner"])] if record.get("banner") else []
            if record.get("flourish"):
                names.append(banners.flourish_label_of(record["flourish"]))
            caption = document.createElement("span")
            caption.className = "archive-line"
            caption.innerText = " · ".join(names)
            flair.appendChild(caption)
            text.appendChild(flair)
        card.appendChild(text)
        buttons = document.createElement("div")
        buttons.className = "archive-actions"
        _archive_button(buttons, f"archive-card-{index}-button", "Card", _make_card_handler(index))
        picked = index in _compare_picks
        compare_label = "Compare"
        if picked:
            compare_label = "Comparing as " + ("A" if _compare_picks.index(index) == 0 else "B")
        compare_button = _archive_button(buttons, f"archive-compare-{index}-button", compare_label, _make_compare_handler(index))
        compare_button.setAttribute("aria-pressed", "true" if picked else "false")
        compare_button.setAttribute("aria-label", f"{compare_label}: {archive.record_label(record, index)}")
        _archive_button(buttons, f"archive-delete-{index}-button", "Delete", _make_archive_delete_handler(index))
        _found_button(buttons, f"archive-found-{index}-button")
        card.appendChild(buttons)
        gallery.appendChild(card)
    panel.appendChild(gallery)
    if records:
        clear_wrap = document.createElement("div")
        clear_wrap.className = "archive-actions"
        _archive_button(
            clear_wrap,
            "archive-clear-button",
            "Really clear the whole archive?" if runstate._archive_confirm_clear else "Clear archive",
            on_archive_clear,
        )
        panel.appendChild(clear_wrap)


# ===========================================================================
# O-5/O-6/O-7: "Found a New Settlement". The front door back to the scenario
# picker (K12), hard mode (K18) and consulting mode (K22): a confirm-gated
# action that FIRST files the current settlement in the archive (unless it is
# already filed, or has nothing in it), and only then resets the campaign in
# place (founding.found_new). If the archive write fails the whole thing is
# refused, so a settlement that has not been archived is never thrown away.
# The new settlement inherits one small founder's legacy (founding.py), from
# the settlement just filed, and nothing else.
# ===========================================================================


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    """Same helper shape as SOL's: the shared ConfirmDialog when present, else
    (pytest's fake `js`, or a page without confirm-dialog.js) confirm at once."""
    window = _js_window()
    confirm_dialog = getattr(window, "ConfirmDialog", None) if window is not None else None
    if confirm_dialog is None:
        on_confirm()
        return
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        allowSkip=False,
        onConfirm=create_proxy(on_confirm),
    )


def _departing_is_inherited_only():
    """True when the settlement being left is an unplayed-beyond-its-start
    consulting case: its era was handed over, not reached, so it earns no
    legacy (the same fairness rule the era achievements follow)."""
    case = consulting.get(runstate.campaign.ui)
    if case is None:
        return False
    return sim.era_index(runstate.campaign.furthest_era) <= sim.era_index(consulting.CASES[case["case"]]["era"])


def pending_legacy():
    """The legacy entry the NEXT settlement would inherit, or None: from the
    current settlement (which founding archives first), or, when there is
    nothing worth archiving, from the newest archived settlement."""
    if founding.is_pristine(runstate.campaign):
        records = archive_load()
        record = records[-1] if records else None
    elif _departing_is_inherited_only():
        record = None
    else:
        record = current_record()
    return founding.make_legacy(record)


def _archive_departing():
    """Files the current settlement unless it is empty or already filed.
    True only when it is safe to leave it behind."""
    if founding.is_pristine(runstate.campaign):
        return True
    record = current_record(archive.clean_thumbnail(_capture_image(320, 0.7)))
    if record is None:
        return False
    records = archive_load()
    if records and archive.same_settlement(records[-1], record):
        return True
    return archive_store(archive.add_record(records, record))


def found_new_settlement():
    """Archive, then reset. Returns True when a new settlement was founded."""
    if runstate.sandbox_active:  # Z-18: nothing is filed or founded from the sandbox
        runstate.found_status = "Founding a settlement is switched off in the sandbox."
        render()
        return False
    if runstate.campaign.revisiting is not None:
        runstate.found_status = "Return to the present before founding a new settlement."
        render()
        return False
    legacy_entry = pending_legacy()
    if not _archive_departing():
        runstate.found_status = (
            "The current settlement could not be filed in the archive (browser storage is "
            "unavailable), so nothing was changed."
        )
        render()
        return False
    earned = achievement_ids_earned()
    # K-2: the departing settlement's Legacy is banked first (by the difference), then the
    # player-level records (Dynasty, tokens used, banner, citizens switch) follow into the next one.
    banked, _info = _bank_current()
    carry = {key: runstate.campaign.ui[key] for key in founding.CARRY_KEYS if key in runstate.campaign.ui and key != "citizens"}
    if not _citizens_on():
        carry["citizens"] = {"off": True}
    if not founding.found_new(runstate.campaign, runstate.chronicle, legacy_entry, earned, carry):
        runstate.found_status = "A new settlement could not be founded, so nothing was changed."
        render()
        return False
    _rewind_clear()
    runstate.sim_speed = 0
    runstate.season_progress = 0.0
    runstate._last_tick = time.time()
    runstate._archive_confirm_clear = False
    del _compare_picks[:]
    sync_name_input()
    runstate.found_status = (
        "A new settlement is founded. The old one is filed in the archive. Pick a starting "
        "scenario, Hard Mode or a consulting case, then press 1x to begin."
    )
    if banked["gained"]:
        runstate.found_status += f" Its Legacy is banked: +{banked['gained']} points."
    render()
    _seed_achievement_toast_baseline()
    return True


def _found_confirm_message():
    parts = [
        "Found a new settlement? The current one is filed in your archive first, then a brand-new "
        "Tribal-era settlement begins, paused, with the scenario picker, Hard Mode and consulting "
        "cases open again."
    ]
    entry = pending_legacy()
    if entry is not None:
        legacy = founding.LEGACIES[entry["id"]]
        parts.append(
            f"It inherits one founder's legacy: {legacy['label']} ({founding.bonus_text(entry)}), "
            f"from a {sim.ERA_LABEL[entry['from_era']]}-era settlement."
        )
    else:
        parts.append("There is no founder's legacy to inherit yet.")
    return " ".join(parts)


def on_found_new_settlement(event=None):
    if runstate.campaign.revisiting is not None:
        runstate.found_status = "Return to the present before founding a new settlement."
        update_found_display()
        return
    _confirm_dialog_ask(
        "continuum-found-settlement",
        _found_confirm_message(),
        "Found a new settlement",
        found_new_settlement,
    )


def update_found_display():
    button = document.getElementById("found-settlement-button")
    button.disabled = runstate.campaign.revisiting is not None or runstate.sandbox_active
    document.getElementById("found-settlement-status").innerText = runstate.found_status
    legacy_line = document.getElementById("legacy-display")
    text = founding.status_text(
        founding.get_legacy(runstate.campaign.ui), consulting.get(runstate.campaign.ui) is not None
    )
    legacy_line.innerText = text
    legacy_line.hidden = not text


# --- K-14 post-mortem ---------------------------------------------------
_postmortem_proxies = []       # the panel's own Close button
_postmortem_open_proxies = []  # the Open/Close button inside the Civilization Summary


def on_toggle_postmortem(event=None):
    runstate.postmortem_open = not runstate.postmortem_open
    update_postmortem_panel()
    update_summary_panel()  # its button's label follows


def _postmortem_button(parent, button_id, text, proxies):
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.innerText = text
    proxy = create_proxy(on_toggle_postmortem)
    proxies.append(proxy)
    button.addEventListener("click", proxy)
    parent.appendChild(button)
    return button


def _pm_text(parent, tag, css, text):
    element = document.createElement(tag)
    element.className = css
    element.innerText = text
    parent.appendChild(element)
    return element


def update_postmortem_panel():
    panel = document.getElementById("postmortem-panel")
    panel.hidden = not runstate.postmortem_open
    if not runstate.postmortem_open:
        return
    for proxy in _postmortem_proxies:
        proxy.destroy()
    del _postmortem_proxies[:]
    panel.innerHTML = ""
    report = postmortem.build(runstate.campaign)
    _pm_text(panel, "h2", "section-heading", "Post-mortem")
    _pm_text(
        panel, "p", "row-blurb",
        "A look back at this settlement in the style of an engineering post-mortem, written from the "
        "livability record, the per-season stats and your Council Minutes. The prompts are things to "
        "think about, not verdicts.",
    )
    if not report["ready"]:
        for note in report["notes"]:
            _pm_text(panel, "p", "status-line pm-line", note)
    else:
        for title, key, empty in (
            ("What went well", "went_well", "Nothing stood out yet."),
            ("What went wrong", "went_wrong", "Nothing went badly wrong."),
        ):
            _pm_text(panel, "h3", "summary-eras-heading", title)
            for line in report[key] or [empty]:
                _pm_text(panel, "p", "status-line pm-line", line)
        _pm_text(panel, "h3", "summary-eras-heading", "Root cause of the biggest livability drop")
        block = report["root_cause"]
        _pm_text(panel, "p", "status-line pm-line pm-line--head", block["headline"])
        for line in block["lines"]:
            _pm_text(panel, "p", "status-line pm-line", line)
        _pm_text(panel, "h3", "summary-eras-heading", "Three decisions to redo")
        if report["redo"]:
            for item in report["redo"]:
                row = document.createElement("div")
                row.className = "pm-decision"
                _pm_text(row, "p", "status-line pm-line pm-line--head", item["decision"])
                _pm_text(row, "p", "row-blurb pm-line", f"{item['when']}. {item['hint']}")
                panel.appendChild(row)
        else:
            _pm_text(panel, "p", "status-line pm-line", "None to show.")
        for note in report["notes"]:
            _pm_text(panel, "p", "row-blurb pm-line", note)
    actions = document.createElement("div")
    actions.className = "archive-actions"
    _postmortem_button(actions, "postmortem-close-button", "Close post-mortem", _postmortem_proxies)
    panel.appendChild(actions)


def on_toggle_summary_panel(event=None):
    runstate.summary_panel_open = not runstate.summary_panel_open
    update_summary_panel()


def _summary_stat_row(container, text):
    row = document.createElement("p")
    row.className = "status-line summary-line"
    row.innerText = text
    container.appendChild(row)


def _detach_copy_result_holder(panel):
    """Z-20: empties the summary panel but keeps the shared "Copy result" button's container (and so
    its listener and its "Copied" message) alive, returning it with whether it held keyboard focus."""
    holder = document.getElementById("summary-copy-result")
    focused = False
    try:
        focused = holder is not None and bool(holder.contains(document.activeElement))
    except Exception:  # noqa: BLE001 -- no focus API (tests)
        pass
    panel.innerHTML = ""
    return holder, focused


def _reattach_copy_result_holder(panel, held):
    holder, focused = held
    if holder is None:
        return
    panel.appendChild(holder)
    if focused:
        try:
            holder.querySelector("button").focus()
        except Exception:  # noqa: BLE001
            pass


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (it calls this by name through window.pyodide): the furthest era, seasons played, peak
    population and the peak sustainability score, from the same summary the panel shows."""
    data = summary.summary(runstate.campaign)
    stats = [
        data["furthest_era_label"] + " reached",
        {"n": data["total_seasons"], "one": "season", "many": "seasons"},
        f"peak population {data['peak_population']}",
    ]
    if data["peak_score"] is not None:
        stats.append(f"peak sustainability {data['peak_score']:.0f}/100")
    return json.dumps({"game": "Continuum", "score": f"{data['eras_completed']} of {data['eras_total']} eras", "stats": stats})


def update_summary_panel():
    toggle = document.getElementById("summary-toggle-button")
    panel = document.getElementById("summary-panel")
    toggle.innerText = "Hide Civilization Summary" if runstate.summary_panel_open else "📜 Civilization Summary"
    panel.hidden = not runstate.summary_panel_open
    if not runstate.summary_panel_open:
        return

    holder = _detach_copy_result_holder(panel)
    data = summary.summary(runstate.campaign)

    # K7: in-character stakeholder-report framing, K17: efficiency rank.
    statement = document.createElement("p")
    statement.className = "row-blurb summary-statement"
    statement.innerText = summary.stakeholder_statement(data, data["rank"], settlement_name())
    panel.appendChild(statement)
    if data["rank"]:
        _summary_stat_row(panel, f"Efficiency rank: {data['rank']} city.")
    # K-14: the post-mortem opens from here (its own proxy list, since the archive
    # section below destroys every proxy in `_archive_proxies` each time it rebuilds).
    for proxy in _postmortem_open_proxies:
        proxy.destroy()
    del _postmortem_open_proxies[:]
    pm_actions = document.createElement("div")
    pm_actions.className = "archive-actions"
    _postmortem_button(
        pm_actions, "postmortem-open-button",
        "Close the post-mortem report" if runstate.postmortem_open else "Open a post-mortem report",
        _postmortem_open_proxies,
    )
    panel.appendChild(pm_actions)
    _summary_stat_row(
        panel,
        f"Furthest era reached: {data['furthest_era_label']} "
        f"({data['eras_completed']} of {data['eras_total']} eras completed).",
    )
    _summary_stat_row(panel, f"Total seasons played: {data['total_seasons']}.")
    _summary_stat_row(panel, f"Peak population ever reached: {data['peak_population']}.")
    if data["peak_score"] is not None:
        # Labeled against the settlement's *current* hard-mode setting --
        # score_history is just raw numbers with no per-entry hard-mode
        # flag of its own, so "what band was this historically" isn't a
        # question this data can answer; using the live setting is what
        # keeps this line consistent with every other score_label() call
        # on this same render (the sustainability panel, the era-by-era
        # rows below).
        _summary_stat_row(
            panel,
            f"Peak sustainability score: {data['peak_score']:.0f} / 100 "
            f"({sustainability.score_label(data['peak_score'], sustainability.is_hard_mode(runstate.state))}).",
        )
    if data["journey_complete"]:
        _summary_stat_row(panel, f"This settlement has carried its story all the way to the {sim.ERA_LABEL[sim.ERA_ORDER[-1]]}.")
    if consulting.get(runstate.campaign.ui) is None:
        for line in par.lines(runstate.state.scenario, SEASON_SECONDS, par.get(runstate.campaign.ui), data["total_seasons"], play_seconds()):
            _summary_stat_row(panel, line)
    if data["has_revisited"]:
        _summary_stat_row(panel, "You've looked back at least once during this playthrough.")
    _summary_stat_row(panel, f"Achievements earned: {len(achievement_ids_earned())} of {len(ACHIEVEMENTS)}.")
    _reattach_copy_result_holder(panel, holder)

    heading = document.createElement("h3")
    heading.className = "summary-eras-heading"
    heading.innerText = "Era by era"
    panel.appendChild(heading)

    for row in data["eras"]:
        entry = document.createElement("div")
        entry.className = "summary-era-row" if row["completed"] else "summary-era-row summary-era-row--current"

        name = document.createElement("p")
        name.className = "summary-era-name"
        status_word = "completed" if row["completed"] else "in progress"
        name.innerText = f"{row['label']} — {status_word}"
        entry.appendChild(name)

        detail = document.createElement("p")
        detail.className = "summary-era-detail"
        score_text = f"{row['score']:.0f}/100 ({row['score_label']})" if row["score"] is not None else "—"
        detail.innerText = (
            f"Season {row['season_reached']} · Population {row['population']} · "
            f"Sustainability {score_text}"
        )
        entry.appendChild(detail)

        panel.appendChild(entry)

    _render_archive_section(panel)
