"""The shell side of milestones 6 and 7: the new panels, keyboard use, non-colour cues, light theme, reduced motion, tutorial,
Info page, the owner's review page and the docs. (JS is not unit tested; these check what the files promise, and the page
itself is verified live.)"""

import json
import re
from pathlib import Path

from .test_accessibility import APP, CSS, DARK, HTML, LIGHT, ratio

GAME_DIR = Path(__file__).resolve().parent.parent
REVIEW_PAGE = (GAME_DIR / "review.html").read_text(encoding="utf-8")
CLAUDE = (GAME_DIR / "CLAUDE.md").read_text(encoding="utf-8")


def ids():
    return set(re.findall(r'\bid="([^"]+)"', HTML))


# ---- the page ---------------------------------------------------------------------------------------------------------

def test_six_modes_are_a_tablist_whose_panels_all_exist():
    for mode, panel in (("account", "account-panel"), ("decision", "decision-panel"), ("review", "review-panel")):
        m = re.search(r'<button id="mode-%s-button"[^>]*>' % mode, HTML)
        assert m and 'role="tab"' in m.group(0) and "aria-selected=" in m.group(0) and 'aria-controls="%s"' % panel in m.group(0)
        assert panel in ids()
    assert len(re.findall(r'role="tab"', HTML)) == 6


def test_the_new_panels_have_labelled_regions_live_messages_and_named_buttons():
    for needle in ('id="account-message"', 'id="decision-message"', 'id="review-message"', 'aria-labelledby="account-heading"',
                   'aria-labelledby="decision-heading"', 'aria-labelledby="review-heading"',
                   'aria-label="Passages, each a short summary of one source"', 'aria-label="Questions about the passage marked with a diamond"'):
        assert needle in HTML, needle
    assert HTML.count('role="status" aria-live="polite"') >= 7
    for m in re.finditer(r"<button([^>]*)>(.*?)</button>", HTML, re.S):
        assert re.sub(r"<[^>]+>", "", m.group(2)).strip() or "aria-label" in m.group(1)


def test_the_modes_are_reached_by_click_arrow_keys_and_single_keys():
    assert 'MODE_KEYS = { t: "timeline", w: "web", m: "myth", a: "account", d: "decision", r: "review" }' in APP
    assert "var tabs = MODE_IDS" in APP and "ArrowRight" in APP and "Home" in APP
    for panel in ("account", "decision", "review"):
        assert '$("%s-panel").hidden = mode !== "%s"' % (panel, panel) in APP


def test_questions_options_and_review_answers_work_from_the_keyboard():
    assert '/^[1-5]$/.test(ev.key)' in APP and "answerAccount(" in APP and "pickDecision(" in APP and "answerReview(" in APP
    assert '/^[1-4]$/.test(ev.key)' in APP
    assert 'li.setAttribute("tabindex", "0")' in APP and 'btn.type = "button"' in APP and "b.type = \"button\"" in APP
    assert "n.focus()" in APP                          # after a review answer the Next button gets the focus
    assert "Press 1 to " in APP


def test_the_skip_link_follows_every_mode():
    for text in ("Skip to whose account", "Skip to decision points", "Skip to review"):
        assert text in APP


def test_the_tutorial_teaches_the_new_modes_and_points_at_real_elements():
    for sel in ("mode-account-button", "mode-decision-button", "mode-review-button"):
        assert 'selector: "#%s"' % sel in APP and sel in ids()
    for sel in re.findall(r'selector: "#([a-z\-]+)"', APP):
        assert sel in ids(), sel
    for title in ("Whose account?", "Decision points", "Review"):
        assert 'title: "%s"' % title in APP


def test_the_new_engine_modules_are_loaded_and_the_page_fetches_the_new_set_files():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    for name in ("account.py", "decision.py", "review.py"):
        assert '"%s"' % name in block
    optional = re.findall(r'"([a-z]+)"', APP.split("OPTIONAL_SET_FILES = [")[1].split("]")[0])
    assert optional == ["chapters", "accounts", "decisions"] and "optResp.ok" in APP


def test_every_id_the_new_code_uses_exists_in_the_page():
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used <= ids(), sorted(used - ids())


def test_the_cached_view_without_a_result_cannot_crash_the_new_boards():
    assert "finished && a.result" in APP and "r.feedback" in APP and "d.decided && r" in APP


def test_nothing_new_posts_anywhere():
    assert not re.search(r'method:\s*["\']POST', APP)
    for url in re.findall(r"fetch\(([^)]*)\)", APP):
        assert "http" not in url


# ---- non-colour cues, light theme, reduced motion ---------------------------------------------------------------------

def test_the_focus_passage_and_answer_states_are_marked_by_borders_symbols_and_words():
    assert re.search(r"\.passage\.focus\s*\{[^}]*double", CSS) and "◆ the questions are about this one" in APP
    assert re.search(r"\.acct-q\.right\s*\{[^}]*double", CSS) and re.search(r"\.acct-q\.wrong\s*\{[^}]*dashed", CSS)
    for state in ("✔ Right answer (locked)", "✖ Not this one yet", "Not answered yet", "Chosen, not checked"):
        assert state in APP
    assert re.search(r'\.opt-btn\[aria-pressed="true"\]::before\s*\{[^}]*content', CSS)


def test_a_decision_marks_what_you_chose_and_what_they_chose_in_words_not_colour():
    assert "◆ You chose this" in APP and "★ " in APP and "labelled as what they chose, not as the best choice" in APP


def test_review_is_written_in_words_and_has_no_animation_or_timer():
    for text in ("coming back later", "at the longest gap", "ready now", "Let a day pass"):
        assert text in APP or text in HTML
    assert "setInterval" not in APP and "requestAnimationFrame" not in APP


def test_new_rules_use_only_theme_variables_so_the_light_theme_follows():
    stripped = re.sub(r":root\s*\{[^}]*\}", "", CSS)
    stripped = re.sub(r'html\[data-(theme="light"|high-contrast="true")\][^{]*\{[^}]*\}', "", stripped)
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", stripped)


def test_the_text_on_the_new_surfaces_is_readable_in_both_themes():
    for theme in (DARK, LIGHT):
        for fg, bg in (("text", "surface"), ("accent-ink", "surface"), ("muted", "surface"), ("on-primary", "btn-primary"), ("text", "btn")):
            assert ratio(theme[fg], theme[bg]) >= 4.5, (fg, bg)


def test_the_phone_layout_stacks_the_options():
    block = CSS.split("@media (max-width: 640px)")[1].split("@media (max-width: 420px)")[0]
    assert ".opt-row { flex-direction: column; }" in block and ".opt-btn { width: 100%; }" in block


# ---- the Info page, the archive and the owner's review page ------------------------------------------------------------

def test_the_info_page_explains_the_three_new_modes_honestly():
    for needle in ("Whose account?", "a summary written for this game in original words", "never against the whole source", "Decision points",
                   "only where the sources document the options", "never presents an alternative as what would have happened",
                   "Let a day pass", "nothing that runs out while you are away", "never taken away"):
        assert needle in HTML, needle
    for needle in ("Accounts you have weighed", "Decision points you have made", "found_accounts", "found_decisions", "i.counts.passages"):
        assert needle in APP, needle


def test_the_archive_can_open_a_judged_source_and_a_choice():
    for needle in ('e.kind === "account"', 'e.kind === "decision"', "account:", "decision:"):
        assert needle in APP, needle


def test_every_new_claim_block_still_has_the_report_button():
    assert "claimBlock(pt.claim)" in APP and "claimBlock(r.choice_claim)" in APP and "claimBlock(f.claim)" in APP and "claimBlock(d.situation)" in APP
    assert "Report a problem" in APP


def test_the_review_page_lists_every_passage_and_decision_for_the_owner():
    for needle in ("rv-accounts", "rv-decisions", "accounts.json", "decisions.json", "Whose account?", "Decision points (", "ORIGINAL summary",
                   "Leaves out", "Mentions", "Account fact: ", "(too few)"):
        assert needle in REVIEW_PAGE, needle
    assert 'name="robots" content="noindex' in REVIEW_PAGE


def test_the_changelog_announces_the_three_new_modes():
    log = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    text = next(e["entry"] for e in log if "whose account?" in e["entry"].lower()).lower()   # not always the newest entry
    assert "whose account?" in text and "decision points" in text and "review" in text and "day" in text
    assert [e["date"] for e in log] == sorted((e["date"] for e in log), reverse=True)


def test_claude_md_marks_milestones_six_and_seven_done_and_describes_the_new_files():
    for n in ("6", "7"):
        row = re.search(r"^\| %s \|.*$" % n, CLAUDE, re.M).group(0)
        assert "DONE" in row, row
    for needle in ("accounts.json", "decisions.json", "account.py", "decision.py", "review.py", "E_ACCOUNT", "E_DECISION", "schema: 3",
                   "Let a day pass", "27 achievements"):
        assert needle in CLAUDE, needle
