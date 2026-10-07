"""The shell side of milestones 4 and 5: the page, keyboard use, non-colour cues, light theme, reduced motion, the Info page
audit, the owner's review page and the docs. (JS is not unit tested; these check what the files promise, and the
page itself is verified live.)"""

import json
import re
from pathlib import Path

import setdata
from .test_accessibility import APP, CSS, DARK, HTML, LIGHT, ratio

GAME_DIR = Path(__file__).resolve().parent.parent
REVIEW = (GAME_DIR / "review.html").read_text(encoding="utf-8")


def ids():
    return set(re.findall(r'\bid="([^"]+)"', HTML))


# ---- the page --------------------------------------------------------------------------------------------------

def test_the_three_modes_are_a_tablist_whose_panels_all_exist():
    assert 'role="tablist"' in HTML and 'id="mode-tabs"' in HTML
    for mode, panel in (("timeline", "puzzle-panel"), ("web", "web-panel"), ("myth", "myth-panel")):
        m = re.search(r'<button id="mode-%s-button"[^>]*>' % mode, HTML)
        assert m and 'role="tab"' in m.group(0) and 'aria-selected=' in m.group(0) and 'aria-controls="%s"' % panel in m.group(0)
        assert panel in ids()


def test_both_new_panels_are_reachable_by_tab_click_arrow_keys_and_single_keys():
    assert '$("mode-" + id + "-button").addEventListener("click"' in APP
    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert key in APP
    assert "/^[twm]$/i" in APP and "switchMode" in APP
    assert "T, W or M" in HTML and "press T, W or M" in HTML
    assert 'currentMode() !== "web"' in APP and '$("web-panel").hidden = mode !== "web"' in APP and '$("myth-panel").hidden = mode !== "myth"' in APP


def test_the_new_panels_have_labelled_live_regions_and_named_buttons():
    for needle in ('id="web-message"', 'id="myth-message"', 'aria-labelledby="web-heading"', 'aria-labelledby="myth-heading"',
                   'aria-label="Moments on the board, earliest first"', 'aria-label="Statements to sort"', 'aria-label="The three bins"'):
        assert needle in HTML, needle
    assert HTML.count('role="status" aria-live="polite"') >= 4
    for m in re.finditer(r"<button([^>]*)>(.*?)</button>", HTML, re.S):
        assert re.sub(r"<[^>]+>", "", m.group(2)).strip() or "aria-label" in m.group(1)


def test_the_skip_link_follows_the_mode():
    assert 'id="skip-link"' in HTML and "Skip to the cause web" in APP and "Skip to myth or record" in APP


def test_the_tutorial_teaches_both_new_modes_and_points_at_real_elements():
    for title in ("Three ways to play", "Cause web", "Myth or record"):
        assert 'title: "%s"' % title in APP
    for sel in ("mode-tabs", "mode-web-button", "mode-myth-button"):
        assert 'selector: "#%s"' % sel in APP and sel in ids()


def test_the_keyboard_help_lists_the_new_keys():
    for needle in ("T, W or M", "Cause web: press a moment's number", "Myth or record: with a statement focused"):
        assert needle in HTML, needle


def test_the_page_fetches_the_optional_chapters_file_only_if_it_exists():
    assert re.findall(r'"([a-z]+)"', APP.split("OPTIONAL_SET_FILES = [")[1].split("]")[0]) == list(setdata.OPTIONAL_FILES)
    assert "optResp.ok" in APP


def test_the_new_engine_modules_are_loaded_and_have_no_dom():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    for name in ("web.py", "myth.py"):
        assert '"%s"' % name in block
        source = (GAME_DIR / name).read_text(encoding="utf-8")
        assert "document." not in source and "window." not in source
        assert not re.search(r"^\s*(import|from)\s+(random|time|datetime)\b", source, re.M)


def test_nothing_new_reaches_a_network():
    for name in ("web.py", "myth.py", "game.py"):
        source = (GAME_DIR / name).read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(urllib|http|requests|socket)", source, re.M), name


def test_the_cached_view_without_a_result_cannot_crash_the_boards():
    assert "finished && w.result" in APP and "finished && m.result" in APP
    assert "copy.web.result = null" in APP and "copy.myth.result = null" in APP


# ---- non-colour cues, light theme, reduced motion ---------------------------------------------------------------

def test_strength_is_a_symbol_words_a_border_and_a_line_style_not_colour():
    assert re.search(r"\.strength\.direct\s*\{[^}]*solid", CSS) and re.search(r"\.strength\.contributing\s*\{[^}]*dashed", CSS)
    assert re.search(r"\.arc\.direct\s*\{[^}]*stroke-width: 4", CSS) and re.search(r"\.arc\.contributing\s*\{[^}]*stroke-dasharray", CSS)
    py = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    assert '"Direct cause"' in py and '"Contributing cause"' in py and "\\u21d2" in py and "\\u21e2" in py


def test_the_three_bins_are_symbols_words_and_three_border_styles():
    assert re.search(r"\.bin-btn\.disputed\s*\{[^}]*dashed", CSS) and re.search(r"\.bin-btn\.traditional-but-doubtful\s*\{[^}]*dotted", CSS)
    assert re.search(r'\.bin-btn\[aria-pressed="true"\]::before\s*\{[^}]*content', CSS)
    assert "b.symbol + \" \" + b.label" in APP
    for state in ("✔ Right bin (locked)", "✖ Not this bin yet", "Not sorted yet"):
        assert state in APP
    assert re.search(r"\.myth-card\.right\s*\{[^}]*double", CSS) and re.search(r"\.myth-card\.wrong\s*\{[^}]*dashed", CSS)


def test_cause_web_cards_and_tabs_have_state_marks_beyond_colour():
    assert "▶ Cause picked up" in APP and re.search(r'\.web-card\[aria-pressed="true"\]\s*\{[^}]*border-width: 4px', CSS)
    assert re.search(r'\.mode-tabs button\[aria-selected="true"\]::before\s*\{[^}]*content', CSS)
    assert "✖ Not confirmed" in APP and "does not mean they are unrelated" in APP


def test_new_rules_use_only_theme_variables_so_the_light_theme_follows():
    stripped = re.sub(r":root\s*\{[^}]*\}", "", CSS)
    stripped = re.sub(r'html\[data-(theme="light"|high-contrast="true")\][^{]*\{[^}]*\}', "", stripped)
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", stripped), re.findall(r"#[0-9a-fA-F]{3,6}\b", stripped)


def test_the_diagram_ink_on_its_nodes_is_readable_in_both_themes():
    for theme in (DARK, LIGHT):                                 # .web-svg .mark-text fills with --bg on an --accent-ink circle
        assert ratio(theme["bg"], theme["accent-ink"]) >= 4.5


def test_the_new_animation_is_covered_by_the_reduced_motion_and_effects_switches():
    assert "@keyframes thread-in" in CSS and "animation: thread-in" in CSS
    assert re.search(r'html\[data-reduced-motion="true"\] \*[^{]*\{[^}]*animation: none !important', CSS)
    assert 'html[data-effects="off"] .web-svg .arc.fresh' in CSS


def test_the_phone_layout_stacks_the_new_boards():
    block = CSS.split("@media (max-width: 640px)")[1].split("@media (max-width: 420px)")[0]
    assert ".web-cards { grid-template-columns: minmax(0, 1fr); }" in block and ".bin-row { flex-direction: column; }" in block


# ---- the Info page audit -----------------------------------------------------------------------------------------

def test_the_info_page_states_the_legend_the_strengths_and_what_is_not_shown_yet():
    for needle in ("How sure are the sources?", "How strong is a cause link?", "i.coverage.note", "i.found_relations", "Cause links you have found"):
        assert needle in APP, needle
    for needle in ("Direct cause", "Contributing cause", "Causes are plural", "every claim links at least three reputable sources"):
        assert needle in HTML, needle


def test_every_claim_block_names_its_three_sources_and_their_publishers():
    assert 'claim.institutions' in APP and '"Sources (" + claim.sources.length + ")"' in APP
    assert "claimBlock(c)" in APP and "claimBlock(t.claim)" in APP and "threadBlock" in APP


def test_opening_every_source_list_at_once_does_not_count_as_reading_them():
    assert 'data-skip-view' in APP and 'Show every source list below' in APP


def test_every_claim_the_info_page_can_show_has_three_sources_and_a_label(p, sample):
    p.m.load_state({"sets": {"presidents-sample": {"learned": list(sample.events), "threads": sample.web_relation_ids()}}})
    info = p.call("info")["info"]
    shown = [c for f in info["found_claims"] for c in f["claims"]] + [t["claim"] for t in info["found_relations"]]
    assert len(shown) == info["coverage"]["shown"] == len(sample.claims)
    for c in shown:
        assert len(c["sources"]) >= 3 and c["symbol"] and c["confidence_label"] and c["institutions"]
    assert {l["id"] for l in info["legend"]} == {"documented", "disputed", "traditional-but-doubtful"}
    assert sum(info["counts"]["levels"].values()) == len(sample.claims)


# ---- the owner's review page and the docs --------------------------------------------------------------------------

def test_the_review_page_lists_every_cause_link_with_its_sources():
    for needle in ("rv-relations", "chapters.json", "Cause link:", "Cause links (", "(too few)", "Chapters (the cause web and myth or record)"):
        assert needle in REVIEW, needle
    assert 'name="robots" content="noindex' in REVIEW


def test_relation_claims_are_in_the_data_the_review_page_reads(sample):
    claims = json.loads((GAME_DIR / "sets" / "presidents-sample" / "claims.json").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in claims}
    for r in sample.relations:
        assert by_id[r["claim"]]["field"] == "relation" and len(by_id[r["claim"]]["sources"]) >= 3


def test_the_changelog_announces_both_mechanics():
    log = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    text = " ".join(e["entry"] for e in log).lower()
    assert "cause web" in text and "myth or record" in text


def test_the_claude_md_marks_milestones_four_and_five_done():
    text = (GAME_DIR / "CLAUDE.md").read_text(encoding="utf-8")
    for n in ("4", "5"):
        row = re.search(r"^\| %s \|.*$" % n, text, re.M).group(0)
        assert "DONE" in row, row
    for needle in ("chapters.json", "web.py", "myth.py", "E_CHAPTER", "E_RELATION_CLAIM"):
        assert needle in text, needle
