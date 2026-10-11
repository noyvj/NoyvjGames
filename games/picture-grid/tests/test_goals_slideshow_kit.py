"""The three-goals queue, the slideshow note, the About and What's New data, and the standard kit's wiring on the page."""

import json
import re
from pathlib import Path

import game
import goals
import info
import pictures

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def not_done(queue):
    return [g for g in queue if not g["done"]]


# ---- goals ------------------------------------------------------------------------------------------------------------------------
def test_a_fresh_game_shows_three_goals_one_of_each_kind():
    q = goals.queue(set(), 0)
    top = not_done(q)[:3]
    assert [g["id"] for g in top] == ["open-small-machines", "cells-100", "finish-instruments"]
    assert top[0]["label"] == "Hang 6 pictures in Instruments" and top[0]["reward"] == "Opens Small Machines"
    assert all(g["current"] == 0 for g in top) and [g["target"] for g in top] == [6, 100, 10]


def test_goal_ids_are_unique_and_values_are_clamped_and_text_is_plain():
    solved = {p.id: 1 for p in pictures.ALL}
    q = goals.queue(solved, 10 ** 6)
    assert len({g["id"] for g in q}) == len(q)
    for g in q:
        assert 0 <= g["current"] <= g["target"] and g["label"].strip() and "!" not in g["label"]
        assert g["done"] is (g["current"] >= g["target"])


def test_a_finished_wall_has_every_goal_done_and_the_done_ones_stay_in_the_queue():
    q = goals.queue({p.id: 1 for p in pictures.ALL}, 10000)
    assert all(g["done"] for g in q) and len(q) == 5 + 6 + 3 + 6
    assert {"hung-60", "cells-10000", "finish-long-wall", "open-long-wall"} <= {g["id"] for g in q}


def test_goals_read_the_hung_set_and_the_fills_and_only_ever_move_forward():
    solved = {p.id: 1 for p in pictures.GALLERIES[0]["pictures"][:6]}
    q = {g["id"]: g for g in goals.queue(solved, 120)}
    assert q["open-small-machines"]["done"] and q["cells-100"]["done"] and not q["cells-500"]["done"]
    assert q["open-small-machines"]["current"] == 6 and q["finish-instruments"]["current"] == 6
    assert "open-robots" in q and q["open-robots"]["current"] == 0                  # the next gallery's unlock goal appears when this one opens
    assert "open-deep-sky" not in q                                                  # but only the next one: no crowd of locked targets
    more = {g["id"]: g for g in goals.queue(dict(solved, **{p.id: 1 for p in pictures.GALLERIES[0]["pictures"]}), 900)}
    assert all(more[i]["current"] >= q[i]["current"] for i in q if i in more)


def test_unfinished_goals_come_first_in_a_fixed_rhythm_then_the_done_ones():
    q = goals.queue({p.id: 1 for p in pictures.GALLERIES[0]["pictures"][:6]}, 120)
    flags = [g["done"] for g in q]
    assert flags == sorted(flags)                                                    # False (not done) first, then True
    assert goals.queue({p.id: 1 for p in pictures.GALLERIES[0]["pictures"][:6]}, 120) == q


def test_the_view_carries_the_queue_and_hint_filled_cells_do_not_count_toward_cells():
    fresh()
    v = call(action="open")
    assert v["goals"] == goals.queue({}, 0)
    call(action="hint"); call(action="hint"); v = call(action="hint", confirm=True)
    assert v["totals"]["cells"] == 0 and [g for g in v["goals"] if g["id"] == "cells-100"][0]["current"] == 0
    v = call(action="paint", cells=[[4, 0], [4, 1]], value=1)
    assert [g for g in v["goals"] if g["id"] == "cells-100"][0]["current"] == 2


def test_hanging_pictures_completes_the_unlock_goal_and_opens_the_next_gallery():
    fresh()
    for p in pictures.GALLERIES[0]["pictures"][:6]:
        call(action="pick", picture=p.id)
        call(action="paint", cells=[[r, c] for r in range(p.height) for c in range(p.width) if p.rows[r][c] == "#"], value=1)
    v = call(action="open")
    by = {g["id"]: g for g in v["goals"]}
    assert by["open-small-machines"]["done"] and v["galleries"][1]["open"]


# ---- slideshow ----------------------------------------------------------------------------------------------------------------------
def test_the_slideshow_is_a_noted_viewing_mode_that_changes_no_progress():
    fresh()
    assert call(action="open")["slideshow_seen"] is False and "slides" not in game.get_state()
    before = call(action="open")
    v = call(action="slideshow")
    assert v["slideshow_seen"] is True and game.get_state()["slides"] == 1
    assert {k: v[k] for k in ("totals", "tally", "grid", "goals")} == {k: before[k] for k in ("totals", "tally", "grid", "goals")}
    saved = game.get_state()
    fresh()
    game.load_state(saved)
    assert call(action="open")["slideshow_seen"] is True
    game.load_state(dict(saved, slides="yes"))
    assert call(action="open")["slideshow_seen"] is False
    call(action="slideshow")
    call(action="reset")
    assert call(action="open")["slideshow_seen"] is False


def test_the_page_has_a_slideshow_button_that_steps_by_hand_and_nothing_moves_on_a_timer():
    assert 'id="slideshow-button"' in HTML and "openSlideshow" in APP and "ArrowRight" in APP
    for banned in ("setInterval", "requestAnimationFrame"):
        assert banned not in APP


# ---- About, What's New, sources ---------------------------------------------------------------------------------------------------
def test_about_has_a_pledge_how_it_works_and_real_facts_with_a_named_source_and_read_date():
    v = info.view()
    assert v["pledge"] and v["how"] and v["facts"] and v["date_read"] == info.DATE_READ
    for fact in v["facts"]:
        assert fact["heading"] and fact["fact"] and fact["tie_in"]
        assert fact["source"]["title"] and fact["source"]["publisher"] and fact["source"]["url"].startswith("https://")
        assert fact["source"]["date_read"] == info.DATE_READ
    text = json.dumps(v)
    assert "Non Ishida" in text and "1987" in text and "Tetsuya Nishio" in text
    assert v["live"]["api"].startswith("https://en.wikipedia.org/api/rest_v1/page/summary/")
    assert call(action="open")["info"] == v


def test_about_makes_no_claim_the_game_cannot_keep():
    text = " ".join(info.PLEDGE).lower()
    assert "no luck" in text and "nothing is timed" in text and "60 pictures" in text


def test_the_page_reads_wikipedia_live_with_a_fallback_and_names_the_day_it_read():
    assert "loadLiveInfo" in APP and "rest_v1" not in APP            # the address lives in the engine's data
    assert "could not be reached" in APP and "Read live on" in APP and "CC BY-SA" in APP
    assert "textContent" in APP and "innerHTML" not in APP


def test_the_changelog_is_valid_dated_and_newest_entries_describe_this_milestone():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    assert len(data) >= 3
    for entry in data:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"]) and entry["entry"].strip()
    text = " ".join(e["entry"] for e in data)
    assert "opening screen" in text and "hint" in text.lower() and "Slideshow" in text


def test_sources_json_names_the_nonogram_article_with_a_read_date():
    data = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    assert data["game"] == "picture-grid"
    research = data["research"][0]
    assert research["url"] == "https://en.wikipedia.org/wiki/Nonogram" and research["read"] == info.DATE_READ
    assert data["inspiration"] and all(i["title"] and i["note"] for i in data["inspiration"])


# ---- the standard kit on the page ------------------------------------------------------------------------------------------------------
def test_the_page_includes_the_standard_kit_by_script_tag_and_in_a_sane_order():
    scripts = re.findall(r'<script src="([^"]+)"', HTML)
    for needed in ("../../shared/tutorial.js", "../../shared/opening-screen.js", "../../shared/confirm-dialog.js", "../../shared/difficulty.js",
                   "../../shared/goals-panel.js", "../../shared/keyboard-shortcuts.js", "../../shared/whats-new-banner.js",
                   "../../shared/announcer.js", "../../shared/info-footer.js", "../../shared/last-played.js", "../../shared/save-widget.js"):
        assert needed in scripts, needed
    assert scripts.index("../../shared/save-widget.js") < scripts.index("../../shared/opening-screen.js")
    assert scripts.index("app.js") < scripts.index("../../shared/whats-new-banner.js") < scripts.index("../../shared/keyboard-shortcuts.js")
    assert 'data-game-id="picture-grid"' in HTML and 'data-game-name="Picture Grid"' in HTML


def test_the_shared_files_the_page_names_exist():
    root = GAME_DIR.parent.parent
    for src in re.findall(r'(?:src|href)="(\.\./\.\./shared/[^"]+)"', HTML):
        assert (GAME_DIR / src).resolve().exists(), src
        assert str((GAME_DIR / src).resolve()).startswith(str(root / "shared"))


def test_every_panel_toggle_the_help_overlay_lists_exists_and_the_toolbar_is_complete():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    block = HTML.split("KeyboardShortcuts.init(")[1]
    for toggle, panel in re.findall(r'toggle: "([^"]+)", panel: "([^"]+)"', block):
        assert toggle in ids and panel in ids
    for needed in ("tutorial-restart-button", "info-page-toggle-button", "changelog-toggle-button", "settings-toggle-button", "gallery-toggle-button"):
        assert needed in ids


def test_clear_frame_and_reset_ask_first_and_the_fill_asks_on_normal():
    assert "picture-grid-clear-frame" in APP and "picture-grid-reset" in APP and "picture-grid-hint-fill" in APP
    assert "ConfirmDialog" in APP


def test_the_difficulty_picker_and_goals_panel_are_mounted_and_described():
    for needle in ("NoyvjDifficulty.mount", "NoyvjGoals.mount", "bindCheckbox", 'action: "difficulty"', "DIFF_TEXT"):
        assert needle in APP
    assert 'id="difficulty-slot"' in HTML and 'id="goals"' in HTML and 'id="goals-checkbox"' in HTML
    for level in ("easy:", "normal:", "hard:"):
        assert level in APP


def test_the_announcer_is_shared_when_present_and_text_is_never_the_only_signal():
    assert "NoyvjAnnounce" in APP
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    for rung in (1, 2, 3):                                           # each ladder rung has its own glyph and border style, not just a colour
        assert ".hint-rung-%d" % rung in css
    assert "b-hintline" in css and "stroke-dasharray" in css.split(".b-hintline")[1].split("}")[0]


def test_reduced_motion_and_touch_targets_are_covered():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert 'data-reduced-motion="true"' in css
    assert "touch-targets.css" in HTML and "a11y.css" in HTML
