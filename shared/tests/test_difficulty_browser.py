"""shared/difficulty.js + difficulty.css in headless Chromium (planning/TODO.md AN-17): one start-of-game choice, Easy / Normal /
Hard, Normal by default, remembered per browser per game, validated on read, listeners and a guard a game can use to lock the
choice, an accessible radio group (labelled, 44 px, never colour alone, a note that Normal is the intended game), themes,
360 px, blocked storage, no timers and no network. The component never decides a rule: it only stores and announces a level."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import page_html  # noqa: E402

STYLE = ('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
         'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>')
PAGE = page_html(STYLE + '<link rel="stylesheet" href="/shared/difficulty.css">',
                 '<h1>Game</h1><div id="slot"></div><div id="slot2"></div>'
                 '<script src="/shared/difficulty.js"></script>')
PAGE_NO_LINK = page_html(STYLE, '<div id="slot"></div><script src="/shared/difficulty.js"></script>')

DESC = {"easy": "Hints open faster.", "normal": "The game as designed.", "hard": "No answer step."}
BLOCK_STORAGE = "Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked'); }});"


def open_page(harness, page=PAGE, init=(), size=(1440, 900), theme=None):
    h = harness(size=size, init_scripts=list(init))
    h.pages["/t.html"] = page
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    return h


def mount(h, slug="logic-gates", **opts):
    h.page.evaluate("""([slug, opts]) => {
      window.__events = []; window.__docEvents = [];
      NoyvjDifficulty.onChange((d) => __events.push(d));
      document.addEventListener('noyvj-difficulty-change', (e) => __docEvents.push(e.detail));
      window.__ui = NoyvjDifficulty.mount('#slot', Object.assign({game: slug, descriptions: %s}, opts));
    }""" % __import__("json").dumps(DESC), [slug, opts])
    return h


def checked(h):
    return h.page.evaluate("(document.querySelector('.noyvj-diff-input:checked') || {}).value || null")


def stored(h, slug="logic-gates"):
    return h.page.evaluate("s => localStorage.getItem('difficulty:' + s)", slug)


# --------------------------------------------------------------------------------------------
def test_default_is_normal_and_nothing_is_stored(harness):
    h = open_page(harness)
    assert h.page.evaluate("NoyvjDifficulty.get('logic-gates')") == "normal"
    assert h.page.evaluate("NoyvjDifficulty.has('logic-gates')") is False
    assert h.page.evaluate("NoyvjDifficulty.DEFAULT") == "normal"
    assert h.page.evaluate("NoyvjDifficulty.LEVELS") == ["easy", "normal", "hard"]
    assert stored(h) is None
    assert h.errors == []


def test_mount_builds_a_labelled_radio_group_with_three_levels(harness):
    h = mount(open_page(harness))
    assert h.page.inner_text(".noyvj-diff-legend") == "Difficulty"
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-diff-input')].map(i => i.type + ':' + i.value)") == [
        "radio:easy", "radio:normal", "radio:hard"]
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-diff-name')].map(n => n.textContent)") == [
        "Easy", "Normal (recommended)", "Hard"]
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-diff-desc')].map(n => n.textContent)") == [
        DESC["easy"], DESC["normal"], DESC["hard"]]
    assert checked(h) == "normal"
    assert h.page.evaluate("document.querySelector('fieldset').tagName") == "FIELDSET"
    note = h.page.inner_text(".noyvj-diff-note")
    assert "Normal" in note and "nothing is locked" in note and "achievement" in note
    described = h.page.get_attribute("fieldset", "aria-describedby")
    assert h.page.evaluate("id => document.getElementById(id).className", described) == "noyvj-diff-note"
    assert h.page.is_hidden(".noyvj-diff-lock")


def test_choosing_a_level_stores_it_and_announces_it(harness):
    h = mount(open_page(harness))
    h.page.click('label[data-level="hard"]')
    assert checked(h) == "hard"
    assert stored(h) == "hard"
    assert h.page.evaluate("NoyvjDifficulty.get('logic-gates')") == "hard"
    assert h.page.evaluate("NoyvjDifficulty.has('logic-gates')") is True
    assert h.page.evaluate("__events") == [{"game": "logic-gates", "level": "hard", "previous": "normal", "source": "set"}]
    assert h.page.evaluate("__docEvents") == h.page.evaluate("__events")
    assert h.page.inner_text(".noyvj-diff-sr") == "Difficulty set to Hard."
    h.page.click('label[data-level="easy"]')
    assert stored(h) == "easy"
    assert h.page.evaluate("__events.length") == 2


def test_choice_survives_a_reload_and_is_per_game(harness):
    h = mount(open_page(harness))
    h.page.click('label[data-level="easy"]')
    h.page.reload()
    assert h.page.evaluate("NoyvjDifficulty.get('logic-gates')") == "easy"
    assert h.page.evaluate("NoyvjDifficulty.get('robot-script')") == "normal"
    h.page.evaluate("NoyvjDifficulty.set('robot-script', 'hard')")
    assert h.page.evaluate("[NoyvjDifficulty.get('logic-gates'), NoyvjDifficulty.get('robot-script')]") == ["easy", "hard"]


def test_choosing_normal_is_remembered_as_a_choice(harness):
    h = mount(open_page(harness))
    h.page.click('label[data-level="normal"]')
    assert stored(h) == "normal"
    assert h.page.evaluate("NoyvjDifficulty.has('logic-gates')") is True
    assert h.page.evaluate("__events") == []                      # nothing changed level, so no change event


def test_a_bad_stored_value_means_normal(harness):
    for bad in ["EASY", " hard", "hard ", "", "{}", "null", "easy,hard", "2", "<b>hard</b>"]:
        h = open_page(harness)
        h.page.evaluate("v => localStorage.setItem('difficulty:logic-gates', v)", bad)
        assert h.page.evaluate("NoyvjDifficulty.get('logic-gates')") == "normal", bad
        assert h.page.evaluate("NoyvjDifficulty.has('logic-gates')") is False, bad
    h = mount(open_page(harness))
    h.page.evaluate("localStorage.setItem('difficulty:logic-gates', 'nonsense')")
    h.page.evaluate("__ui.refresh()")
    assert checked(h) == "normal"


def test_bad_arguments_are_refused(harness):
    h = open_page(harness)
    results = h.page.evaluate("""() => [
      NoyvjDifficulty.set('logic-gates', 'extreme'), NoyvjDifficulty.set('logic-gates', ''), NoyvjDifficulty.set('logic-gates', null),
      NoyvjDifficulty.set('Bad Slug', 'hard'), NoyvjDifficulty.set('', 'hard'), NoyvjDifficulty.set(5, 'hard'),
      NoyvjDifficulty.set('a/b', 'hard'), NoyvjDifficulty.get('../x'), NoyvjDifficulty.get(undefined),
      NoyvjDifficulty.mount('#nowhere', {game: 'logic-gates'}), NoyvjDifficulty.mount('#slot', {game: 'Bad Slug'}),
      NoyvjDifficulty.mount('#slot', {})]""")
    assert results == [False, False, False, False, False, False, False, "normal", "normal", None, None, None]
    assert h.page.evaluate("Object.keys(localStorage)") == []
    assert h.page.query_selector(".noyvj-diff") is None


def test_listeners_can_unsubscribe_and_one_that_throws_does_not_break_the_rest(harness):
    h = open_page(harness)
    h.page.evaluate("""() => {
      window.__a = []; window.__b = [];
      NoyvjDifficulty.onChange(() => { throw new Error('boom'); });
      window.__offA = NoyvjDifficulty.onChange((d) => __a.push(d.level));
      NoyvjDifficulty.onChange((d) => __b.push(d.level));
      NoyvjDifficulty.onChange('not a function')();
    }""")
    h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'hard')")
    h.page.evaluate("__offA()")
    h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'easy')")
    assert h.page.evaluate("[__a, __b]") == [["hard"], ["hard", "easy"]]
    assert [e for e in h.errors if "boom" not in e] == []


def test_clear_forgets_the_choice(harness):
    h = mount(open_page(harness))
    h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'hard')")
    assert h.page.evaluate("NoyvjDifficulty.clear('logic-gates')") is True
    assert stored(h) is None
    assert h.page.evaluate("[NoyvjDifficulty.get('logic-gates'), NoyvjDifficulty.has('logic-gates')]") == ["normal", False]
    assert checked(h) == "normal"
    assert h.page.evaluate("__events.map(e => e.source)") == ["set", "clear"]


def test_a_guard_can_lock_the_choice_and_says_why(harness):
    h = mount(open_page(harness))
    h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'easy')")
    h.page.evaluate("NoyvjDifficulty.setGuard('logic-gates', () => ({allowed: false, reason: 'Finish this run first.'}))")
    assert h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'hard')") is False
    assert h.page.evaluate("NoyvjDifficulty.get('logic-gates')") == "easy"
    assert h.page.is_visible(".noyvj-diff-lock")
    assert h.page.inner_text(".noyvj-diff-lock") == "Finish this run first."
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-diff-input')].every(i => i.disabled)")
    assert checked(h) == "easy"
    assert h.page.evaluate("NoyvjDifficulty.canChange('logic-gates', 'hard')") == {"allowed": False, "reason": "Finish this run first."}
    # setting the level it already has is not a change, and a forced change (the game's own reset) goes through
    assert h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'easy')") is True
    assert h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'normal', {force: true})") is True
    assert checked(h) == "normal"
    h.page.evaluate("NoyvjDifficulty.setGuard('logic-gates', null)")
    assert h.page.is_hidden(".noyvj-diff-lock")
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-diff-input')].every(i => !i.disabled)")
    assert h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'hard')") is True


def test_a_guard_given_to_mount_works_and_a_broken_guard_never_traps_the_player(harness):
    h = open_page(harness)
    h.page.evaluate("window.__open = false; NoyvjDifficulty.mount('#slot', {game: 'logic-gates', canChange: () => __open})")
    assert h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'hard')") is False
    assert h.page.inner_text(".noyvj-diff-lock") == "The difficulty cannot be changed right now."
    h.page.evaluate("NoyvjDifficulty.setGuard('logic-gates', () => { throw new Error('guard bug'); })")
    assert h.page.evaluate("NoyvjDifficulty.set('logic-gates', 'hard')") is True
    assert h.page.evaluate("NoyvjDifficulty.canChange('robot-script')") == {"allowed": True, "reason": ""}


def test_a_refused_click_puts_the_group_back(harness):
    h = mount(open_page(harness))
    h.page.evaluate("NoyvjDifficulty.setGuard('logic-gates', (next) => next !== 'hard')")
    h.page.evaluate("document.querySelector('.noyvj-diff-input[value=hard]').click()")
    assert h.page.evaluate("NoyvjDifficulty.get('logic-gates')") == "normal"
    assert checked(h) == "normal"
    assert stored(h) is None


def test_collapsible_is_open_until_a_choice_exists(harness):
    h = mount(open_page(harness), collapsible=True)
    assert h.page.evaluate("document.querySelector('.noyvj-diff-details').open") is True
    assert h.page.inner_text(".noyvj-diff-summary") == "Difficulty: Normal"
    h.page.click('label[data-level="hard"]')
    assert h.page.inner_text(".noyvj-diff-summary") == "Difficulty: Hard"
    h.page.reload()
    mount(h, collapsible=True)
    assert h.page.evaluate("document.querySelector('.noyvj-diff-details').open") is False
    assert h.page.inner_text(".noyvj-diff-summary") == "Difficulty: Hard"
    assert checked(h) == "hard"


def test_two_mounts_stay_in_step(harness):
    h = mount(open_page(harness))
    h.page.evaluate("window.__ui2 = NoyvjDifficulty.mount('#slot2', {game: 'logic-gates'})")
    h.page.evaluate("document.querySelectorAll('.noyvj-diff-input[value=easy]')[1].click()")
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-diff-input:checked')].map(i => i.value)") == ["easy", "easy"]
    h.page.evaluate("__ui2.destroy()")
    assert h.page.evaluate("document.querySelectorAll('.noyvj-diff').length") == 1


def test_a_change_in_another_tab_arrives_as_a_storage_event(harness):
    h = mount(open_page(harness))
    h.page.evaluate("""() => {
      localStorage.setItem('difficulty:logic-gates', 'hard');
      window.dispatchEvent(new StorageEvent('storage', {key: 'difficulty:logic-gates', oldValue: null, newValue: 'hard'}));
    }""")
    assert checked(h) == "hard"
    assert h.page.evaluate("__events") == [{"game": "logic-gates", "level": "hard", "previous": "normal", "source": "storage"}]
    h.page.evaluate("window.dispatchEvent(new StorageEvent('storage', {key: 'something-else', newValue: 'easy'}))")
    assert h.page.evaluate("__events.length") == 1


def test_blocked_storage_keeps_the_choice_in_memory(harness):
    h = mount(open_page(harness, init=[BLOCK_STORAGE]))
    h.page.click('label[data-level="easy"]')
    assert h.page.evaluate("NoyvjDifficulty.get('logic-gates')") == "easy"
    assert h.page.evaluate("NoyvjDifficulty.has('logic-gates')") is True
    assert checked(h) == "easy"
    assert h.errors == []


def test_keyboard_arrows_move_between_levels(harness):
    h = mount(open_page(harness))
    h.page.focus('.noyvj-diff-input[value=normal]')
    h.page.keyboard.press("ArrowRight")
    assert checked(h) == "hard"
    assert h.page.evaluate("NoyvjDifficulty.get('logic-gates')") == "hard"
    h.page.keyboard.press("ArrowLeft")
    h.page.keyboard.press("ArrowLeft")
    assert checked(h) == "easy"
    assert stored(h) == "easy"


def test_every_option_is_at_least_44px_tall_and_the_group_fits_360px(harness):
    h = mount(open_page(harness, size=(360, 740)))
    heights = h.page.evaluate("[...document.querySelectorAll('.noyvj-diff-opt')].map(o => o.getBoundingClientRect().height)")
    assert all(x >= 44 for x in heights), heights
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    box = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-diff').getBoundingClientRect(); return [r.left, r.right]; })()")
    assert box[0] >= 0 and box[1] <= 360


def test_the_chosen_level_is_not_colour_only(harness):
    h = mount(open_page(harness))
    h.page.click('label[data-level="hard"]')
    look = h.page.evaluate("""() => {
      const chosen = document.querySelector('.noyvj-diff-opt[data-level=hard]');
      const other = document.querySelector('.noyvj-diff-opt[data-level=easy]');
      return {chosenBorder: getComputedStyle(chosen).borderTopWidth, otherBorder: getComputedStyle(other).borderTopWidth,
              chosenMark: getComputedStyle(chosen.querySelector('.noyvj-diff-name'), '::before').content,
              otherMark: getComputedStyle(other.querySelector('.noyvj-diff-name'), '::before').content,
              checked: chosen.querySelector('input').checked};
    }""")
    assert look["chosenBorder"] == "4px" and look["otherBorder"] == "2px"
    assert look["chosenMark"] != look["otherMark"]
    assert look["checked"] is True


def test_light_and_dark_themes_both_set_readable_tokens(harness):
    def contrast(h):
        return h.page.evaluate("""() => {
          const lum = (c) => { const m = c.match(/[\\d.]+/g).map(Number).slice(0, 3).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]; };
          const box = document.querySelector('.noyvj-diff');
          const bg = getComputedStyle(document.body).backgroundColor;
          const out = {};
          for (const sel of ['.noyvj-diff-name', '.noyvj-diff-desc', '.noyvj-diff-note']) {
            const fg = getComputedStyle(document.querySelector(sel)).color;
            const a = lum(fg), b = lum(bg);
            out[sel] = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
          }
          return out;
        }""")
    for theme in ("dark", "light"):
        h = mount(open_page(harness, theme=theme))
        for sel, ratio in contrast(h).items():
            assert ratio >= 4.5, (theme, sel, ratio)


def test_text_is_never_parsed_as_html_and_the_stylesheet_links_itself(harness):
    h = open_page(harness, page=PAGE_NO_LINK)
    h.page.evaluate("""NoyvjDifficulty.mount('#slot', {game: 'logic-gates', descriptions: {easy: '<img src=x onerror=alert(1)>', normal: '<b>bold</b>'}})""")
    assert h.page.query_selector(".noyvj-diff img") is None and h.page.query_selector(".noyvj-diff-desc b") is None
    assert "<b>bold</b>" in h.page.inner_text(".noyvj-diff")
    assert h.page.evaluate("!!document.querySelector('link[href*=\"difficulty.css\"]')")
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-diff-opt')).borderTopWidth") == "2px"
    assert h.page.evaluate("document.querySelector('.noyvj-diff-desc').textContent") == "<img src=x onerror=alert(1)>"


def test_missing_descriptions_fall_back_to_plain_words(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjDifficulty.mount('#slot', {game: 'logic-gates'})")
    descs = h.page.evaluate("[...document.querySelectorAll('.noyvj-diff-desc')].map(n => n.textContent)")
    assert len(descs) == 3 and all(descs)


def test_no_network_and_no_timers(harness):
    h = mount(open_page(harness))
    source = (Path(__file__).resolve().parents[1] / "difficulty.js").read_text(encoding="utf-8")
    for banned in ("setTimeout", "setInterval", "requestAnimationFrame", "fetch(", "XMLHttpRequest", "innerHTML", "Math.random", "Date.now"):
        assert banned not in source, banned
    h.page.click('label[data-level="hard"]')
    assert h.api_calls == []
    assert h.errors == []
