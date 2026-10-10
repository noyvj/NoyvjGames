"""ideas.html "Game notes": a free place to write comments, thoughts, bugs, ideas and questions per game.
Quick add (button and Ctrl+Enter), edit in place, change kind, delete with a tombstone, per-game and
Everything views, counts in the nav, saved in the browser and PUT to the owner note "game-notes",
merged from the account by newest edit, a copy-as-markdown button, and no console errors."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TOKEN_INIT = "localStorage.setItem('hub_bearer_token', 'test-token');"


def open_notes(harness, remote_notes=None):
    h = harness(init_scripts=[TOKEN_INIT])
    h.api_responses[("GET", "/users/me")] = (200, {"username": "noyvj", "id": 1})
    h.api_responses[("GET", "/owner/notes/game-notes")] = (200, {"value": {"version": 1, "notes": remote_notes or {}}})
    h.api_responses[("PUT", "/owner/notes/game-notes")] = (200, {"ok": True})
    h.api_responses[("GET", "/owner/notes/ideas-answers")] = (200, {"value": {"version": 1, "answers": {}}})
    h.api_responses[("PUT", "/owner/notes/ideas-answers")] = (200, {"ok": True})
    page = h.goto("/ideas.html")
    page.wait_for_selector("#round-select")
    page.select_option("#round-select", "notes")
    page.wait_for_selector(".note-form")
    return h, page


def stored(page):
    return json.loads(page.evaluate("localStorage.getItem('ideas-game-notes-v1') || '{}'"))


def test_the_notes_round_lists_the_whole_site_and_every_game(harness):
    h, page = open_notes(harness)
    labels = page.eval_on_selector_all("#sections button", "els => els.map(e => e.firstChild.textContent)")
    assert labels[:2] == ["Everything", "Whole site"]
    assert "Canopy" in labels and "Le Champ de Mots" in labels and "SOL" in labels and "Tide" in labels
    assert len(labels) >= 27
    assert page.evaluate("document.body.dataset.mode") == "notes"
    assert page.is_hidden("#search")
    assert h.errors == []


def test_adding_a_note_for_a_game_saves_it_and_shows_it_and_counts_it(harness):
    h, page = open_notes(harness)
    page.click('#sections button[data-code="canopy"]')
    assert page.input_value("#note-game") == "canopy"
    page.fill("#note-text", "The sprites look great but the +link marks are noisy at the start.")
    page.select_option("#note-kind", "feedback")
    page.click("text=Add note")
    notes = stored(page)
    assert len(notes) == 1
    note = next(iter(notes.values()))
    assert note["g"] == "canopy" and note["k"] == "feedback" and "sprites" in note["m"] and note["c"] and note["u"]
    assert page.locator(".note").count() == 1
    assert page.input_value(".note textarea") == note["m"]
    assert page.input_value("#note-text") == ""  # the form is clear for the next one
    count = page.inner_text('#sections button[data-code="canopy"] .count')
    assert count == "1"


def test_ctrl_enter_adds_and_empty_notes_are_refused(harness):
    h, page = open_notes(harness)
    page.click('#sections button[data-code="tide"]')
    page.fill("#note-text", "   ")
    page.click("text=Add note")
    assert stored(page) == {}
    page.fill("#note-text", "Quiet seasons star frame is lovely.")
    page.press("#note-text", "Control+Enter")
    assert len(stored(page)) == 1


def test_everything_view_shows_all_games_newest_first_with_game_chips(harness):
    h, page = open_notes(harness)
    for slug, text in (("canopy", "first"), ("tide", "second"), ("site", "third")):
        page.click(f'#sections button[data-code="{slug}"]')
        page.fill("#note-text", text)
        page.click("text=Add note")
        page.wait_for_timeout(5)
    page.click('#sections button[data-code="*"]')
    texts = page.eval_on_selector_all(".note textarea", "els => els.map(e => e.value)")
    assert texts == ["third", "second", "first"]
    chips = page.eval_on_selector_all(".note .chip.kind", "els => els.map(e => e.textContent)")
    assert chips == ["Whole site", "Tide", "Canopy"]
    page.click('#sections button[data-code="tide"]')
    assert page.locator(".note").count() == 1


def test_editing_text_and_kind_updates_the_note_and_its_time(harness):
    h, page = open_notes(harness)
    page.click('#sections button[data-code="loop"]')
    page.fill("#note-text", "original")
    page.click("text=Add note")
    before = next(iter(stored(page).values()))
    page.wait_for_timeout(5)
    page.fill(".note textarea", "original, plus more")
    page.select_option(".note-head select", "bug")
    after = next(iter(stored(page).values()))
    assert after["m"] == "original, plus more" and after["k"] == "bug" and after["u"] > before["u"] and after["c"] == before["c"]


def test_deleting_leaves_a_tombstone_so_it_cannot_come_back(harness):
    h, page = open_notes(harness)
    page.click('#sections button[data-code="grid"]')
    page.fill("#note-text", "to delete")
    page.click("text=Add note")
    page.once("dialog", lambda d: d.accept())
    page.click(".note .link")
    assert page.locator(".note").count() == 0
    notes = stored(page)
    assert len(notes) == 1 and next(iter(notes.values()))["d"] == 1
    page.reload()
    page.wait_for_selector("#round-select")
    page.select_option("#round-select", "notes")
    assert page.locator(".note").count() == 0


def test_every_change_is_pushed_to_the_owner_note_with_the_whole_set(harness):
    h, page = open_notes(harness)
    page.click('#sections button[data-code="signal"]')
    page.fill("#note-text", "daily puzzle thought")
    page.click("text=Add note")
    page.wait_for_timeout(1700)
    puts = [c for c in h.api_calls if c[0] == "PUT" and c[1] == "/owner/notes/game-notes"]
    assert puts, h.api_calls
    body = json.loads(puts[-1][2])
    assert body["value"]["version"] == 1 and len(body["value"]["notes"]) == 1
    assert "Notes saved to your account" in page.inner_text("#sync-status")


def test_notes_from_the_account_are_merged_by_newest_edit(harness):
    remote = {
        "r1": {"g": "herd", "k": "idea", "m": "from another device", "c": 1000, "u": 2000},
        "r2": {"g": "herd", "k": "bug", "m": "old remote", "c": 1000, "u": 1500},
    }
    h = harness(init_scripts=[TOKEN_INIT, "localStorage.setItem('ideas-game-notes-v1', JSON.stringify({r2: {g: 'herd', k: 'bug', m: 'newer local', c: 1000, u: 3000}}));"])
    h.api_responses[("GET", "/users/me")] = (200, {"username": "noyvj", "id": 1})
    h.api_responses[("GET", "/owner/notes/game-notes")] = (200, {"value": {"version": 1, "notes": remote}})
    h.api_responses[("PUT", "/owner/notes/game-notes")] = (200, {"ok": True})
    h.api_responses[("GET", "/owner/notes/ideas-answers")] = (200, {"value": {"version": 1, "answers": {}}})
    h.api_responses[("PUT", "/owner/notes/ideas-answers")] = (200, {"ok": True})
    page = h.goto("/ideas.html")
    page.wait_for_selector("#round-select")
    page.select_option("#round-select", "notes")
    page.click('#sections button[data-code="herd"]')
    page.wait_for_function("document.querySelectorAll('.note').length === 2")
    texts = sorted(page.eval_on_selector_all(".note textarea", "els => els.map(e => e.value)"))
    assert texts == ["from another device", "newer local"]


def test_copy_notes_gives_markdown_grouped_by_game(harness):
    h, page = open_notes(harness)
    page.evaluate("window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: async (t) => { window.__copied = t; }}})")
    for slug, text in (("canopy", "alpha"), ("tide", "beta\nsecond line")):
        page.click(f'#sections button[data-code="{slug}"]')
        page.fill("#note-text", text)
        page.click("text=Add note")
    assert "Copy notes (2)" in page.inner_text("#export-btn")
    page.click("#export-btn")
    page.wait_for_function("window.__copied !== null")
    md = page.evaluate("window.__copied")
    assert md.startswith("# Game notes") and "## Canopy" in md and "## Tide" in md and "alpha" in md and "beta second line" in md


def test_a_note_with_markup_is_shown_as_text(harness):
    h, page = open_notes(harness)
    page.click('#sections button[data-code="lexis"]')
    page.fill("#note-text", "<img src=x onerror=window.__pwned=1> hello")
    page.click("text=Add note")
    assert page.evaluate("window.__pwned") is None
    assert "<img" in page.input_value(".note textarea")


def test_going_back_to_the_ideas_rounds_restores_the_normal_sheet(harness):
    h, page = open_notes(harness)
    page.select_option("#round-select", "all-open")
    page.wait_for_selector(".item")
    assert page.evaluate("document.body.dataset.mode") == "ideas"
    assert page.is_visible("#search") and "Copy answers" in page.inner_text("#export-btn")
    assert h.errors == []
