"""shared/run-code.js in headless Chromium (planning/TODO.md FY-7). The decisive test: the JavaScript
encoder, decoder and describe() agree with shared/run_code.py exactly, on many inputs (valid, mangled,
foreign and forged). Then the "Copy run code" and "Paste a run code" UIs: accessible, 44 px, themed,
reduced-motion safe, nothing executed, nothing sent anywhere. No network."""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_code as rc  # noqa: E402
import seed as sd  # noqa: E402
from conftest import page_html  # noqa: E402

PAGE = page_html('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
                 'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>',
                 '<h1>Game</h1><div id="slot"></div><script src="/shared/run-code.js"></script>')

CLIPBOARD_OK = ("window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                "value: {writeText: (t) => { window.__copied = t; return Promise.resolve(); }}});")
CLIPBOARD_BLOCKED = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                     "value: {writeText: () => Promise.reject(new Error('denied'))}}); "
                     "document.execCommand = () => false;")

FULL = {"game": "tide", "seed": "TIDE-K7F2Q", "mode": "hard", "score": 4210, "stats": [3, 12]}
FULL_CODE = "RUN-TIDE-7G0F4-1JE0H-M62WK-4Y8G0-630-EPX"
DESCRIBE = {"unit": "pts", "stats": [{"one": "storm", "many": "storms"}, "calm days"], "modes": {"hard": "Hard"}}


def open_page(harness, init=(), size=(1440, 900), theme=None, **kw):
    h = harness(size=size, init_scripts=list(init), **kw)
    h.pages["/t.html"] = PAGE
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    return h


JS_DECODED_TO_PY = {"hasResult": "has_result"}


def py_shape(d):
    """A run_code.decode() result with JS-style key names, for comparing with run-code.js."""
    return {({v: k for k, v in JS_DECODED_TO_PY.items()}).get(k, k): v for k, v in d.items()}


# --------------------------------------------------------------------------------------------
# Python and JavaScript agree
# --------------------------------------------------------------------------------------------
def encode_corpus():
    r = sd.Rng("run-code-identity")
    games = ["tide", "signal", "trade-empire", "champ-de-mots", "sol", "canopy", "a-very-long-game-slug"]
    modes = ["", "hard", "easy", "daily", "a", "12345678", "z9", "HARD"]
    out = []
    for _ in range(300):
        game = r.choice(games)
        f = {"game": game}
        if r.chance(0.8):
            f["seed"] = r.choice([sd.new_seed(game, entropy=r), sd.new_seed(game, entropy=r).lower(), sd.new_seed(game, entropy=r)[-5:]])
        if r.chance(0.7):
            f["mode"] = r.choice(modes)
        if r.chance(0.8):
            f["score"] = r.choice([0, 1, 127, 128, 16383, 16384, 4210, r.below(10 ** 9), r.below(rc.MAX_VALUE + 1), rc.MAX_VALUE])
            f["stats"] = [r.choice([0, 1, 3, 200, r.below(10 ** 6), rc.MAX_VALUE]) for _ in range(r.below(3))]
        out.append(f)
    out += [
        {}, {"game": 5}, {"game": "x"}, {"game": "tide", "seed": "TIDE-K0F2Q"}, {"game": "tide", "seed": 12345},
        {"game": "tide", "seed": "SIGNAL-K7F2Q"}, {"game": "tide", "mode": "Hard Mode"}, {"game": "tide", "mode": "waytoolongmode"},
        {"game": "tide", "mode": 3}, {"game": "tide", "score": -1}, {"game": "tide", "score": 1.5}, {"game": "tide", "score": True},
        {"game": "tide", "score": "9"}, {"game": "tide", "score": rc.MAX_VALUE + 1}, {"game": "tide", "score": 10 ** 30},
        {"game": "tide", "stats": [1]}, {"game": "tide", "score": 1, "stats": [1, 2, 3]}, {"game": "tide", "score": 1, "stats": [-1]},
        {"game": "tide", "score": 1, "stats": "ab"}, {"game": "tide", "seed": "", "mode": None, "score": None, "stats": None},
    ]
    return out


JS_ENCODE = """(list) => list.map((f) => {
  try { return {code: NoyvjRunCode.encode(f)}; }
  catch (e) { return {reason: e.reason, message: e.message, isRange: e instanceof RangeError}; }
})"""


def py_encode(f):
    try:
        return {"code": rc.encode(f)}
    except rc.RunCodeError as e:
        return {"reason": e.reason, "message": str(e), "isRange": True}


def test_python_and_javascript_encode_identically(harness):
    h = open_page(harness)
    corpus = encode_corpus()
    js = h.page.evaluate(JS_ENCODE, corpus)
    assert len(js) == len(corpus) > 300
    for fields, got in zip(corpus, js):
        assert got == py_encode(fields), fields
    assert sum("code" in g for g in js) > 280
    assert not h.errors


def test_pinned_codes_match_the_python_pins(harness):
    h = open_page(harness)
    assert h.page.evaluate("f => NoyvjRunCode.encode(f)", FULL) == FULL_CODE
    assert h.page.evaluate("NoyvjRunCode.encode({game: 'trade-empire'})") == "RUN-TRADEEMPIRE-4000-NH6"
    d = h.page.evaluate("c => NoyvjRunCode.decode(c, 'tide')", FULL_CODE)
    assert d == py_shape(rc.decode(FULL_CODE, "tide"))
    assert d["verified"] is False


def decode_corpus():
    r = sd.Rng("run-code-decode")
    codes = [rc.encode(f) for f in encode_corpus()[:60] if "game" in f and rc.is_valid(rc.encode(f))]
    inputs = list(codes)
    for c in codes[:30]:
        inputs += [c.lower(), " " + c.replace("-", " ") + " ", c.replace("-", ""), c.replace("-", "–"), c.replace("-", "_"),
                   c.replace("0", "O"), c.replace("1", "L"), c[:-1], c[:-3], c + "A", c.replace("RUN", "RAN"), "x" + c]
        for _ in range(6):                                   # one-character slips at random positions
            i = r.below(len(c))
            if c[i] != "-":
                inputs.append(c[:i] + r.choice(rc.B32) + c[i + 1:])
    r2 = sd.Rng("forged")
    for _ in range(40):                                      # random bodies with a CORRECT checksum: format/version paths
        data = [r2.below(256) for _ in range(r2.randint(1, 14))]
        body = rc._to_b32(data)
        inputs.append("RUN-TIDE-%s-%s" % (rc._group(body), rc._checksum("TIDE", body)))
    inputs += ["", "   ", "\n", "RUN", "RUN-", "RUN-TIDE", "RUN-TIDE-", "RUN-TIDE-AB-C", "RUN-T-ABCDE-FGH", "run run run", "hello world",
               "RUN-TIDE-" + "A" * 90, "x" * 401, "x" * 400, "ß", "﻿", "\x1f", "日本語", "ＲＵＮ-TIDE", "RUN-TIDE-UUUUU-UUUUU-UUU",
               "RUN-" + "ZZ" * 6 + "-ABCDEFGH-ABC", None, 12345, 0, True, [], {}]
    return inputs


def test_python_and_javascript_decode_identically(harness):
    h = open_page(harness)
    inputs = decode_corpus()
    games = [None, "tide", "signal", "trade-empire"]
    cases = [[t, g] for t in inputs for g in games]
    js = h.page.evaluate("""(cases) => cases.map(([t, g]) => {
        const d = NoyvjRunCode.decode(t, g === null ? undefined : g);
        return [d, NoyvjRunCode.validate(t, g === null ? undefined : g), NoyvjRunCode.normalize(t, g === null ? undefined : g),
                NoyvjRunCode.isValid(t, g === null ? undefined : g)]; })""", cases)
    assert len(js) == len(cases) > 1500
    ok = 0
    for (text, game), (d, v, n, valid) in zip(cases, js):
        want = rc.decode(text, game)
        assert d == py_shape(want), (text, game)
        assert v == rc.validate(text, game), (text, game)
        assert n == rc.normalize(text, game) and valid == rc.is_valid(text, game), (text, game)
        ok += want["ok"]
    assert ok > 150                                            # plenty of accepted codes, not only refusals
    assert not h.errors


def test_describe_agrees(harness):
    h = open_page(harness)
    codes = [rc.encode(f) for f in encode_corpus() if "code" in py_encode(f)]
    optionsets = [None, DESCRIBE, {"prefix": "Ghost", "unit": "points"}, {"stats": ["a", None], "modes": {"easy": "Easy"}},
                  {"stats": [{"one": "x"}, {"many": "ys"}], "prefix": ""}]
    cases = [[c, o] for c in codes for o in optionsets] + [["nope", None]]
    js = h.page.evaluate("""(cases) => cases.map(([c, o]) => NoyvjRunCode.describe(NoyvjRunCode.decode(c), o || undefined))""", cases)
    assert len(js) > 1000
    for (code, options), got in zip(cases, js):
        assert got == rc.describe(rc.decode(code), options), (code, options)
    assert h.page.evaluate("[NoyvjRunCode.describe(null), NoyvjRunCode.describe({ok: false})]") == ["", ""]


def test_javascript_never_throws_on_decode(harness):
    h = open_page(harness)
    got = h.page.evaluate("""() => [undefined, null, NaN, {}, [], () => 1, Symbol.iterator.toString(), "RUN-\\u0000-\\u0000"]
        .map((x) => { try { return NoyvjRunCode.decode(x).ok; } catch (e) { return "threw " + e.message; } })""")
    assert got == [False] * 8


# --------------------------------------------------------------------------------------------
# Copy run code
# --------------------------------------------------------------------------------------------
def mount_copy(h, run="FULL", extra=""):
    h.page.evaluate("""([run, extra]) => {
      window.__run = run;
      window.__copyBox = NoyvjRunCode.mountCopy('#slot', Object.assign({game: 'tide', getRun: () => window.__run,
        describe: %s, onCopy: (c) => (window.__onCopy = c)}, extra));
    }""" % json.dumps(DESCRIBE), [{"seed": "TIDE-K7F2Q", "mode": "hard", "score": 4210, "stats": [3, 12]} if run == "FULL" else run, {}])


def test_copy_shows_the_code_and_a_preview_of_what_a_friend_sees(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    mount_copy(h)
    assert h.page.inner_text(".noyvj-rc-code") == FULL_CODE
    assert h.page.inner_text(".noyvj-rc-preview") == "A friend will see: Their run: 4,210 pts, 3 storms, 12 calm days, Hard mode"
    hint = h.page.inner_text(".noyvj-rc-hint")
    assert "not checked against a server" in hint and "not proof" in hint     # scores are client-trusted, said out loud
    assert h.page.get_attribute(".noyvj-rc-copy", "role") == "group"
    assert h.page.get_attribute(".noyvj-rc-copy", "aria-labelledby")
    assert not h.errors


def test_copy_button_copies_announces_and_reads_the_run_at_click_time(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    mount_copy(h)
    h.page.evaluate("window.__run = {seed: 'TIDE-K7F2Q', score: 99}")           # the run changed since mount
    h.page.click(".noyvj-rc-copy button")
    h.page.wait_for_function("window.__copied !== null")
    copied = h.page.evaluate("window.__copied")
    assert copied == rc.encode({"game": "tide", "seed": "TIDE-K7F2Q", "score": 99})
    assert h.page.evaluate("window.__onCopy") == copied
    assert "✓ Copied" in h.page.inner_text(".noyvj-rc-status")
    assert h.page.get_attribute(".noyvj-rc-status", "aria-live") == "polite"
    assert h.page.get_attribute(".noyvj-rc-status", "role") == "status"
    assert h.page.inner_text(".noyvj-rc-code") == copied                         # the visible code follows


def test_copy_falls_back_to_a_selected_box(harness):
    h = open_page(harness, init=[CLIPBOARD_BLOCKED])
    mount_copy(h)
    h.page.click(".noyvj-rc-copy button")
    h.page.wait_for_selector(".noyvj-rc-fallback")
    assert h.page.input_value(".noyvj-rc-fallback") == FULL_CODE
    assert h.page.evaluate("document.activeElement.classList.contains('noyvj-rc-fallback')")
    assert h.page.evaluate("document.activeElement.selectionEnd - document.activeElement.selectionStart") == len(FULL_CODE)
    assert "Ctrl+C" in h.page.inner_text(".noyvj-rc-status")


def test_copy_with_nothing_to_share_or_a_bad_run_is_disabled_and_explains(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    mount_copy(h, run={"score": -5})
    assert h.page.is_disabled(".noyvj-rc-copy button")
    assert h.page.inner_text(".noyvj-rc-code") == "none yet"
    assert h.page.inner_text(".noyvj-rc-status").startswith("! Could not make a run code:")
    assert h.page.is_hidden(".noyvj-rc-preview")
    h.page.evaluate("__copyBox.update({score: 5})")
    assert not h.page.is_disabled(".noyvj-rc-copy button")
    assert h.page.inner_text(".noyvj-rc-status") == ""
    assert h.page.inner_text(".noyvj-rc-code") == rc.encode({"game": "tide", "score": 5})


def test_copy_requires_a_game(harness):
    h = open_page(harness)
    assert h.page.evaluate("try { NoyvjRunCode.mountCopy('#slot', {}); 'no error' } catch (e) { e.message }") == "NoyvjRunCode.mountCopy needs a game slug"
    assert h.page.evaluate("NoyvjRunCode.mountCopy('#missing', {game: 'tide'})") is None


# --------------------------------------------------------------------------------------------
# Paste a run code
# --------------------------------------------------------------------------------------------
def mount_paste(h, extra="{}"):
    h.page.evaluate("""() => { window.__viewed = []; window.__played = [];
      window.__paste = NoyvjRunCode.mountPaste('#slot', Object.assign({game: 'tide', describe: %s,
        onView: (d) => __viewed.push(d.code)}, %s)); }""" % (json.dumps(DESCRIBE), extra))


def test_paste_shows_a_ghost_summary_and_only_displays_it(harness):
    h = open_page(harness)
    mount_paste(h)
    h.page.fill(".noyvj-rc-input", "  " + FULL_CODE.lower().replace("-", " ") + " ")
    h.page.click(".noyvj-rc-paste button[type=submit]")
    ghost = h.page.inner_text(".noyvj-rc-ghost")
    assert "Their run: 4,210 pts, 3 storms, 12 calm days, Hard mode" in ghost
    assert "Seed TIDE-K7F2Q" in ghost
    assert "Not verified" in ghost and "anyone can write one" in ghost
    assert h.page.input_value(".noyvj-rc-input") == FULL_CODE                    # tidied to the canonical spelling
    assert h.page.evaluate("__viewed") == [FULL_CODE]
    assert h.page.get_attribute(".noyvj-rc-result", "role") == "status"
    assert h.page.get_attribute(".noyvj-rc-result", "aria-live") == "polite"
    assert h.page.is_hidden(".noyvj-rc-error")
    assert h.page.locator("text=Play this seed").count() == 0                    # only when the game offers it
    assert h.page.evaluate("typeof NoyvjSeed") == "undefined"                    # the codec stands alone
    assert not h.errors


def test_paste_rejects_bad_input_with_text_a_dashed_border_and_focus(harness):
    h = open_page(harness)
    mount_paste(h)
    samples = {
        "": "Paste a run code first.",
        "hello": "does not look like a run code",
        FULL_CODE[:-1] + "Z": "typing mistake",
        rc.encode({"game": "signal", "score": 5}): "is for SIGNAL, not this game",
        "RUN-TIDE-" + "A" * 90: "too long",
    }
    for text, expect in samples.items():
        h.page.fill(".noyvj-rc-input", text)
        h.page.press(".noyvj-rc-input", "Enter")
        err = h.page.inner_text(".noyvj-rc-error")
        assert err.startswith("! ") and expect in err, (text, err)
        assert h.page.get_attribute(".noyvj-rc-input", "aria-invalid") == "true"
        assert h.page.get_attribute(".noyvj-rc-error", "role") == "alert"
        assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-rc-input')).borderTopStyle") == "dashed"
        assert h.page.evaluate("document.activeElement.classList.contains('noyvj-rc-input')")
        assert h.page.locator(".noyvj-rc-ghost").count() == 0
    assert h.page.evaluate("__viewed.length") == 0
    h.page.fill(".noyvj-rc-input", "RUN")
    assert h.page.is_hidden(".noyvj-rc-error") and h.page.get_attribute(".noyvj-rc-input", "aria-invalid") is None   # typing clears it


def test_paste_play_seed_button_only_with_a_seed_and_a_handler(harness):
    h = open_page(harness)
    mount_paste(h, "{onPlaySeed: (s, d) => __played.push([s, d.mode, d.score])}")
    h.page.fill(".noyvj-rc-input", FULL_CODE)
    h.page.press(".noyvj-rc-input", "Enter")
    h.page.click("text=Play this seed")
    assert h.page.evaluate("__played") == [["TIDE-K7F2Q", "hard", 4210]]
    # a code with no seed has nothing to play, even with a handler
    h.page.fill(".noyvj-rc-input", rc.encode({"game": "tide", "score": 7}))
    h.page.press(".noyvj-rc-input", "Enter")
    assert h.page.locator("text=Play this seed").count() == 0
    assert "Their run: 7" in h.page.inner_text(".noyvj-rc-ghost")


def test_paste_clear_resets_and_returns_focus(harness):
    h = open_page(harness)
    mount_paste(h)
    h.page.fill(".noyvj-rc-input", FULL_CODE)
    h.page.press(".noyvj-rc-input", "Enter")
    h.page.click(".noyvj-rc-ghost >> text=Clear")
    assert h.page.locator(".noyvj-rc-ghost").count() == 0 and h.page.input_value(".noyvj-rc-input") == ""
    assert h.page.evaluate("document.activeElement.classList.contains('noyvj-rc-input')")


def test_paste_field_is_labelled_and_described(harness):
    h = open_page(harness)
    mount_paste(h)
    assert h.page.inner_text("label.noyvj-rc-label") == "Paste a run code"
    input_id = h.page.get_attribute(".noyvj-rc-input", "id")
    assert h.page.get_attribute("label.noyvj-rc-label", "for") == input_id
    assert len(h.page.get_attribute(".noyvj-rc-input", "aria-describedby").split()) == 2
    assert h.page.get_attribute(".noyvj-rc-input", "placeholder") == "RUN-TIDE-..."
    assert h.page.evaluate("try { NoyvjRunCode.mountPaste('#slot', {}); 'no error' } catch (e) { e.message }") == "NoyvjRunCode.mountPaste needs a game slug"


def test_nothing_in_a_pasted_code_can_become_markup_or_script(harness):
    h = open_page(harness)
    mount_paste(h)
    evil = '<img src=x onerror="window.__pwned=1"><script>window.__pwned=2</script>'
    h.page.fill(".noyvj-rc-input", evil)
    h.page.press(".noyvj-rc-input", "Enter")
    assert h.page.evaluate("window.__pwned") is None
    assert h.page.locator("#slot img, #slot script").count() == 0
    assert "typing mistake" not in h.page.inner_text(".noyvj-rc-error")
    # and a valid code's text is inserted as text: no element appears inside the ghost besides the card's own
    h.page.fill(".noyvj-rc-input", FULL_CODE)
    h.page.press(".noyvj-rc-input", "Enter")
    tags = h.page.evaluate("[...document.querySelectorAll('.noyvj-rc-ghost *')].map(e => e.tagName)")
    assert set(tags) <= {"P", "DIV", "BUTTON"}


def test_nothing_touches_the_network_or_storage(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    mount_copy(h)
    h.page.click(".noyvj-rc-copy button")
    h.page.evaluate("__copyBox.destroy()")
    mount_paste(h)
    h.page.fill(".noyvj-rc-input", FULL_CODE)
    h.page.press(".noyvj-rc-input", "Enter")
    assert h.api_calls == []
    assert h.page.evaluate("localStorage.length + sessionStorage.length") == 0
    assert h.page.evaluate("document.cookie") == ""


# --------------------------------------------------------------------------------------------
# Look: sizes, themes, reduced motion, phone width
# --------------------------------------------------------------------------------------------
MOUNT_ALL = """() => { const slot = document.getElementById('slot');
  for (const id of ['a', 'b']) { const d = document.createElement('div'); d.id = id; slot.appendChild(d); }
  NoyvjRunCode.mountCopy('#a', {game: 'trade-empire', run: {seed: 'TRADEEMPIRE-K7F2Q', mode: 'hard', score: 123456789, stats: [4, 5]}});
  const p = NoyvjRunCode.mountPaste('#b', {game: 'trade-empire', onPlaySeed: () => {}});
  p.setValue(NoyvjRunCode.encode({game: 'trade-empire', seed: 'TRADEEMPIRE-K7F2Q', mode: 'hard', score: 123456789, stats: [4, 5]}));
  p.element.requestSubmit(); }"""


@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_controls_are_44px_and_nothing_overflows(harness, size, theme):
    h = open_page(harness, size=size, touch=size[0] < 500, theme=theme)
    h.page.evaluate(MOUNT_ALL)
    heights = h.page.evaluate("[...document.querySelectorAll('.noyvj-rc button, .noyvj-rc input')].map(e => e.getBoundingClientRect().height)")
    assert len(heights) >= 5 and min(heights) >= 44
    widths = h.page.evaluate("[...document.querySelectorAll('.noyvj-rc button')].map(e => e.getBoundingClientRect().width)")
    assert min(widths) >= 44
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-rc')].every(e => e.getBoundingClientRect().right <= window.innerWidth + 0.5)")


def lum(css):
    r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
    f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.03928 else c / 255 / 12.92  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def test_light_and_dark_tokens_differ_and_text_is_legible(harness):
    seen = {}
    for theme in ("dark", "light"):
        h = open_page(harness, theme=theme)
        h.page.evaluate(MOUNT_ALL)
        seen[theme] = h.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.noyvj-rc'));
          const hint = getComputedStyle(document.querySelector('.noyvj-rc-hint'));
          return [s.backgroundColor, s.color, hint.color]; }""")
    assert seen["dark"] != seen["light"]
    for theme, (bg, fg, muted) in seen.items():
        page_bg = 0.01 if theme == "dark" else 0.85
        lb = lum(bg) * 0.78 + page_bg * 0.22 if "rgba" in bg else lum(bg)
        for colour in (fg, muted):
            lf = lum(colour)
            assert (max(lb, lf) + 0.05) / (min(lb, lf) + 0.05) >= 4.5, (theme, colour)


def test_reduced_motion_removes_transitions(harness):
    h = open_page(harness)
    h.page.evaluate(MOUNT_ALL)
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-rc-btn')).transitionDuration") != "0s"
    h.page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-rc-btn')).transitionDuration") == "0s"
    os_reduced = harness(media={"reduced_motion": "reduce"})
    os_reduced.pages["/t.html"] = PAGE
    os_reduced.goto()
    os_reduced.page.evaluate(MOUNT_ALL)
    assert os_reduced.page.evaluate("getComputedStyle(document.querySelector('.noyvj-rc-btn')).transitionDuration") == "0s"


def test_disabled_state_is_not_colour_alone(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjRunCode.mountCopy('#slot', {game: 'tide', run: {score: -1}})")
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-rc-btn')).borderTopStyle") == "dashed"
    assert "none yet" in h.page.inner_text(".noyvj-rc-code")
