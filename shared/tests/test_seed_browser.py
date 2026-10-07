"""shared/seed.js in headless Chromium (planning/TODO.md Z-1 and Z-5). The decisive test: the
JavaScript generator, seed codes, daily seeds and seed parsing agree with shared/seed.py exactly,
on many seeds. Then the Copy seed / Start from seed / Today's run helpers. No network."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import seed as sd  # noqa: E402
from conftest import page_html  # noqa: E402

PAGE = page_html('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
                 'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>',
                 '<h1>Game</h1><div id="slot"></div><script src="/shared/seed.js"></script>')

CLIPBOARD_OK = ("window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                "value: {writeText: (t) => { window.__copied = t; return Promise.resolve(); }}});")
CLIPBOARD_BLOCKED = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                     "value: {writeText: () => Promise.reject(new Error('denied'))}}); "
                     "document.execCommand = () => false;")


def open_page(harness, init=(), size=(1440, 900), theme=None, **kw):
    h = harness(size=size, init_scripts=list(init), **kw)
    h.pages["/t.html"] = PAGE
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    return h


# --------------------------------------------------------------------------------------------
# Python and JavaScript agree
# --------------------------------------------------------------------------------------------
def py_trace(seed):
    r = sd.Rng(seed)
    return {
        "raw": [str(r.next()) for _ in range(3)],
        "floats": [r.random() for _ in range(3)],
        "ints": [r.randint(-50, 50), r.randint(0, 10 ** 9), r.below(10 ** 12), r.below(1), r.below(2)],
        "uniform": r.uniform(1.5, 9.25),
        "choice": r.choice(["a", "b", "c", "d", "e"]),
        "shuffled": r.shuffled(list(range(12))),
        "sample": r.sample(list(range(30)), 5),
        "weighted": r.weighted_choice(["x", "y", "z"], [0.5, 2.25, 1]),
        "chance": [r.chance(0.3), r.chance(0.9)],
        "fork": str(r.fork("loot").next()),
        "state": r.get_state(),
    }


JS_TRACE = """(seeds) => seeds.map((seed) => {
  const r = new NoyvjSeed.Rng(seed);
  return {
    raw: [r.next(), r.next(), r.next()].map(String),
    floats: [r.random(), r.random(), r.random()],
    ints: [r.randint(-50, 50), r.randint(0, 1e9), r.below(1e12), r.below(1), r.below(2)],
    uniform: r.uniform(1.5, 9.25),
    choice: r.choice(["a", "b", "c", "d", "e"]),
    shuffled: r.shuffled([0,1,2,3,4,5,6,7,8,9,10,11]),
    sample: r.sample(Array.from({length: 30}, (_, i) => i), 5),
    weighted: r.weightedChoice(["x", "y", "z"], [0.5, 2.25, 1]),
    chance: [r.chance(0.3), r.chance(0.9)],
    fork: String(r.fork("loot").next()),
    state: r.getState(),
  };
})"""


def corpus_seeds():
    src = sd.Rng("corpus")
    games = ["tide", "signal", "trade-empire", "champ-de-mots", "sol", "canopy"]
    seeds = [sd.new_seed(games[i % len(games)], entropy=src) for i in range(240)]
    seeds += ["", "a", "TIDE-K7F2Q", "tést-ünï", "日本語", "emoji \U0001F30A seed", "x" * 500]
    return seeds


def test_python_and_javascript_generate_identical_runs(harness):
    h = open_page(harness)
    seeds = corpus_seeds()
    js = h.page.evaluate(JS_TRACE, seeds)
    assert len(js) == len(seeds) > 200
    for seed, got in zip(seeds, js):
        assert got == py_trace(seed), seed
    assert not h.errors


def test_pinned_values_match_the_python_pins(harness):
    h = open_page(harness)
    got = h.page.evaluate("""() => { const r = new NoyvjSeed.Rng("TIDE-K7F2Q");
      return [r.next(), r.next(), r.next()].map(String); }""")
    assert got == ["10252949485630092546", "9651280616414493402", "15263075260975997904"]
    assert h.page.evaluate("new NoyvjSeed.Rng('TIDE-K7F2Q').random()") == 0.555813505335214
    assert h.page.evaluate("NoyvjSeed.fnv1a64('a').toString()") == "12638187200555641996"


def test_daily_seeds_agree_for_every_day_of_two_years(harness):
    h = open_page(harness)
    from datetime import date, timedelta
    days = []
    d = date(2026, 1, 1)
    while d <= date(2027, 12, 31):
        days.append(d.isoformat())
        d += timedelta(days=1)
    days.append("2028-02-29")
    games = ["tide", "signal", "trade-empire", "champ-de-mots", "sol"]
    js = h.page.evaluate("([games, days]) => games.map(g => days.map(d => NoyvjSeed.dailySeed(g, d)))", [games, days])
    for g, row in zip(games, js):
        assert row == [sd.daily_seed(g, day) for day in days], g
    assert h.page.evaluate("NoyvjSeed.daily_seed('tide', new Date(Date.UTC(2026, 9, 8, 23, 59)))") == "TIDE-X54PB"


def test_new_seed_with_an_entropy_source_agrees(harness):
    h = open_page(harness)
    js = h.page.evaluate("""() => { const r = new NoyvjSeed.Rng("fixed");
      return [NoyvjSeed.newSeed("tide", r), NoyvjSeed.new_seed("trade-empire", r), NoyvjSeed.newSeed("sol", () => 0)]; }""")
    r = sd.Rng("fixed")
    assert js == [sd.new_seed("tide", r), sd.new_seed("trade-empire", r), "SOL-22222"]


def test_random_new_seeds_are_valid_and_vary(harness):
    h = open_page(harness)
    seeds = h.page.evaluate("Array.from({length: 60}, () => NoyvjSeed.newSeed('champ-de-mots'))")
    assert len(set(seeds)) > 55
    assert all(sd.validate(s, "champ-de-mots")["ok"] for s in seeds)


def test_normalize_and_validate_agree_on_many_inputs(harness):
    h = open_page(harness)
    base = [sd.new_seed(g, entropy=sd.Rng(g)) for g in ("tide", "signal", "trade-empire")]
    inputs = []
    for s in base:
        inputs += [s, s.lower(), " " + s.replace("-", " ") + " ", s.replace("-", "–"), s.replace("-", ""),
                   s.split("-")[1], s[:-1], s + "Q", s.replace("-", "_"), s.upper().replace("A", "0"), s.replace("-", "--")]
    inputs += ["", "   ", "-", "--", "ab", "TIDE-", "-K7F2Q", "TIDE-K7F2Q-K7F2Q", "T-K7F2Q", "TOOLONGPREFIXX-K7F2Q",
               "TIDE-k7f2q\n", "ti de - k7 f2q", "ß-K7F2Q", None, 12345, 0, True]
    games = [None, "tide", "trade-empire", "signal"]
    cases = [[t, g] for t in inputs for g in games]
    js = h.page.evaluate("""(cases) => cases.map(([t, g]) =>
        [NoyvjSeed.normalize(t, g === null ? undefined : g), NoyvjSeed.validate(t, g === null ? undefined : g)])""", cases)
    assert len(js) == len(cases) > 150
    for (text, game), (norm, val) in zip(cases, js):
        assert norm == sd.normalize(text, game), (text, game)
        assert val == sd.validate(text, game), (text, game)


def test_javascript_errors_for_bad_arguments(harness):
    h = open_page(harness)
    result = h.page.evaluate("""() => {
      const bad = (f) => { try { f(); return "no error"; } catch (e) { return e.name; } };
      const r = NoyvjSeed.rng("TIDE-K7F2Q");
      return [bad(() => r.below(0)), bad(() => r.below(1.5)), bad(() => r.randint(5, 1)), bad(() => r.choice([])),
              bad(() => r.sample([1], 2)), bad(() => NoyvjSeed.dailySeed("tide", "2026-02-30")),
              bad(() => NoyvjSeed.dailySeed("tide", "nope")), bad(() => NoyvjSeed.prefixFor("x")),
              bad(() => r.setState("12abc")), bad(() => r.weightedChoice(["a"], [0]))]; }""")
    assert result == ["RangeError"] * 10


def test_state_save_and_resume(harness):
    h = open_page(harness)
    got = h.page.evaluate("""() => { const r = NoyvjSeed.rng("TIDE-STATE");
      for (let i = 0; i < 5; i++) r.next();
      const saved = r.getState(); const a = [r.random(), r.random()];
      const q = NoyvjSeed.rng("TIDE-STATE"); q.setState(saved); return [saved, a, [q.random(), q.random()]]; }""")
    assert got[1] == got[2]
    r = sd.Rng("TIDE-STATE")
    for _ in range(5):
        r.next()
    assert got[0] == r.get_state()


# --------------------------------------------------------------------------------------------
# current seed (shared/info-footer.js reads window.NoyvjSeed.current())
# --------------------------------------------------------------------------------------------
def test_current_seed_contract_for_the_info_footer(harness):
    h = open_page(harness)
    assert h.page.evaluate("NoyvjSeed.current()") == ""
    h.page.evaluate("""() => { window.__events = []; document.addEventListener('noyvj-seed-change', (e) => __events.push(e.detail.seed)); }""")
    h.page.evaluate("NoyvjSeed.set('TIDE-K7F2Q')")
    h.page.evaluate("NoyvjSeed.set('TIDE-K7F2Q')")
    assert h.page.evaluate("NoyvjSeed.current()") == "TIDE-K7F2Q"
    assert h.page.evaluate("__events") == ["TIDE-K7F2Q"]
    h.page.evaluate("NoyvjSeed.clear()")
    assert h.page.evaluate("[NoyvjSeed.current(), __events.length]") == ["", 2]


def test_info_footer_shows_the_seed_once_the_module_provides_it(harness):
    h = harness()
    h.pages["/t.html"] = page_html(
        "", '<div id="howto-panel"><p>How to play</p></div><script src="/shared/seed.js"></script>'
            '<script>NoyvjSeed.set("TIDE-K7F2Q")</script>'
            '<script src="/shared/info-footer.js" data-game-id="tide" data-game-name="Tide"></script>')
    h.goto()
    h.page.wait_for_selector("#howto-panel .noyvj-info-footer")
    assert "seed TIDE-K7F2Q" in h.page.inner_text("#howto-panel")


def test_from_url_reads_a_valid_seed_parameter(harness):
    h = harness()
    h.pages["/t.html"] = PAGE
    h.page.goto("http://harness.test/t.html?seed=tide-k7f2q")
    assert h.page.evaluate("[NoyvjSeed.fromUrl('tide'), NoyvjSeed.fromUrl('signal')]") == ["TIDE-K7F2Q", ""]


# --------------------------------------------------------------------------------------------
# Copy seed
# --------------------------------------------------------------------------------------------
def test_copy_seed_copies_and_announces(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    h.page.evaluate("NoyvjSeed.mountCopy('#slot', {seed: 'TIDE-K7F2Q'})")
    assert h.page.inner_text(".noyvj-seed-code") == "TIDE-K7F2Q"
    h.page.click(".noyvj-seed-copy button")
    h.page.wait_for_function("window.__copied === 'TIDE-K7F2Q'")
    assert "Copied TIDE-K7F2Q" in h.page.inner_text(".noyvj-seed-status")
    assert h.page.get_attribute(".noyvj-seed-status", "aria-live") == "polite"
    assert h.page.get_attribute(".noyvj-seed-copy", "role") == "group"
    assert not h.errors


def test_copy_seed_falls_back_to_a_selected_box(harness):
    h = open_page(harness, init=[CLIPBOARD_BLOCKED])
    h.page.evaluate("NoyvjSeed.mountCopy('#slot', {seed: 'TIDE-K7F2Q'})")
    h.page.click(".noyvj-seed-copy button")
    h.page.wait_for_selector(".noyvj-seed-fallback")
    assert h.page.input_value(".noyvj-seed-fallback") == "TIDE-K7F2Q"
    assert h.page.evaluate("document.activeElement.className.includes('noyvj-seed-fallback')")
    assert h.page.evaluate("document.activeElement.selectionEnd - document.activeElement.selectionStart") == 10
    assert "Ctrl+C" in h.page.inner_text(".noyvj-seed-status")


def test_copy_seed_defaults_to_the_current_seed_and_updates(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    h.page.evaluate("window.v = NoyvjSeed.mountCopy('#slot')")
    assert h.page.inner_text(".noyvj-seed-code") == "none yet"
    assert h.page.is_disabled(".noyvj-seed-copy button")
    h.page.evaluate("NoyvjSeed.set('SOL-22222'); v.update()")
    assert h.page.inner_text(".noyvj-seed-code") == "SOL-22222"
    assert not h.page.is_disabled(".noyvj-seed-copy button")


# --------------------------------------------------------------------------------------------
# Start from seed
# --------------------------------------------------------------------------------------------
def test_start_from_seed_rejects_bad_input_with_text_and_focus(harness):
    h = open_page(harness)
    h.page.evaluate("window.started = []; NoyvjSeed.mountStart('#slot', {game: 'tide', onStart: (s, i) => started.push([s, i])})")
    h.page.fill(".noyvj-seed-input", "TIDE-K0F2Q")
    h.page.press(".noyvj-seed-input", "Enter")
    err = h.page.inner_text(".noyvj-seed-error")
    assert err.startswith("! ") and "0, 1, I, L or O" in err
    assert h.page.get_attribute(".noyvj-seed-input", "aria-invalid") == "true"
    assert h.page.get_attribute(".noyvj-seed-error", "role") == "alert"
    assert h.page.evaluate("document.activeElement.classList.contains('noyvj-seed-input')")
    assert h.page.evaluate("started.length") == 0
    h.page.fill(".noyvj-seed-input", "SIGNAL-K7F2Q")
    h.page.press(".noyvj-seed-input", "Enter")
    assert "SIGNAL" in h.page.inner_text(".noyvj-seed-error") and h.page.evaluate("started.length") == 0
    h.page.fill(".noyvj-seed-input", "")
    h.page.click(".noyvj-seed-start button[type=submit]")
    assert "TIDE-K7F2Q" in h.page.inner_text(".noyvj-seed-error")


def test_start_from_seed_accepts_loose_input_and_sets_the_current_seed(harness):
    h = open_page(harness)
    h.page.evaluate("window.started = []; NoyvjSeed.mountStart('#slot', {game: 'tide', onStart: (s, i) => started.push([s, i])})")
    h.page.fill(".noyvj-seed-input", " k7f2q ")
    h.page.click(".noyvj-seed-start button[type=submit]")
    assert h.page.evaluate("started") == [["TIDE-K7F2Q", {"fromUser": True}]]
    assert h.page.evaluate("NoyvjSeed.current()") == "TIDE-K7F2Q"
    assert h.page.input_value(".noyvj-seed-input") == "TIDE-K7F2Q"
    assert h.page.is_hidden(".noyvj-seed-error")
    assert h.page.get_attribute(".noyvj-seed-input", "aria-invalid") is None


def test_random_seed_button_fills_a_valid_seed(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjSeed.mountStart('#slot', {game: 'trade-empire'})")
    h.page.click("text=Random seed")
    value = h.page.input_value(".noyvj-seed-input")
    assert sd.validate(value, "trade-empire")["ok"]
    off = open_page(harness)
    off.page.evaluate("NoyvjSeed.mountStart('#slot', {game: 'tide', random: false})")
    assert off.page.locator("text=Random seed").count() == 0


def test_start_field_is_labelled_and_described(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjSeed.mountStart('#slot', {game: 'tide'})")
    assert h.page.inner_text("label.noyvj-seed-label") == "Start from seed"
    input_id = h.page.get_attribute(".noyvj-seed-input", "id")
    assert h.page.get_attribute("label.noyvj-seed-label", "for") == input_id
    assert h.page.get_attribute(".noyvj-seed-input", "placeholder") == "TIDE-K7F2Q"
    assert len(h.page.get_attribute(".noyvj-seed-input", "aria-describedby").split()) == 2


# --------------------------------------------------------------------------------------------
# Today's run
# --------------------------------------------------------------------------------------------
NOW = "new Date(Date.UTC(2026, 9, 8, 12, 0))"


def test_mark_completed_stores_the_documented_shape(harness):
    h = open_page(harness)
    run = h.page.evaluate(f"NoyvjSeed.daily.markCompleted('tide', {{score: 4210, text: '4,210 pts'}}, {NOW})")
    assert run == {"seed": "TIDE-X54PB", "completed_at": "2026-10-08T12:00:00.000Z", "score": 4210, "text": "4,210 pts"}
    stored = json.loads(h.page.evaluate("localStorage.getItem('noyvj-daily-v1')"))
    assert stored == {"version": 1, "date": "2026-10-08", "runs": {"tide": run},
                      "streaks": {"tide": {"count": 1, "best": 1, "last": "2026-10-08"}}}
    assert h.page.evaluate(f"NoyvjSeed.daily.markCompleted('tide', null, {NOW})") is None   # once per day
    assert h.page.evaluate(f"NoyvjSeed.daily.completed('tide', {NOW})") is True
    assert h.page.evaluate(f"NoyvjSeed.daily.completed('signal', {NOW})") is False
    assert h.page.evaluate("NoyvjSeed.daily.key") == "noyvj-daily-v1"


def test_a_new_utc_day_clears_runs_but_keeps_streaks_without_punishment(harness):
    h = open_page(harness)
    d = lambda day: f"new Date(Date.UTC(2026, 9, {day}, 9, 0))"  # noqa: E731
    for day in (6, 7, 8):
        h.page.evaluate(f"NoyvjSeed.daily.markCompleted('tide', null, {d(day)})")
    assert h.page.evaluate(f"NoyvjSeed.daily.streak('tide', {d(8)})") == {"count": 3, "best": 3, "last": "2026-10-08", "doneToday": True}
    nxt = h.page.evaluate(f"[NoyvjSeed.daily.read({d(9)}), NoyvjSeed.daily.streak('tide', {d(9)})]")
    assert nxt[0]["runs"] == {} and nxt[0]["date"] == "2026-10-09"
    assert nxt[1] == {"count": 3, "best": 3, "last": "2026-10-08", "doneToday": False}      # still alive until the day ends
    lapsed = h.page.evaluate(f"NoyvjSeed.daily.streak('tide', {d(11)})")
    assert lapsed["count"] == 0 and lapsed["best"] == 3                                    # best is kept, nothing is "lost"
    h.page.evaluate(f"NoyvjSeed.daily.markCompleted('tide', null, {d(11)})")
    assert h.page.evaluate(f"NoyvjSeed.daily.streak('tide', {d(11)})") == {"count": 1, "best": 3, "last": "2026-10-11", "doneToday": True}


def test_daily_is_daily_helper(harness):
    h = open_page(harness)
    assert h.page.evaluate(f"[NoyvjSeed.daily.isDaily('tide', 'tide-x54pb', {NOW}), NoyvjSeed.daily.isDaily('tide', 'TIDE-AAAAA', {NOW})]") == [True, False]


def test_corrupt_or_blocked_storage_never_throws(harness):
    h = open_page(harness)
    for junk in ("not json", '{"version":2}', '{"version":1,"date":"2026-10-08","runs":{"BAD KEY":{"seed":"x"},"tide":{"seed":5}},"streaks":{"tide":{"count":"x","last":"nope"}}}'):
        h.page.evaluate("j => localStorage.setItem('noyvj-daily-v1', j)", junk)
        assert h.page.evaluate(f"NoyvjSeed.daily.read({NOW})") == {"version": 1, "date": "2026-10-08", "runs": {}, "streaks": {}}
    blocked = open_page(harness, init=["Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked'); }});"])
    assert blocked.page.evaluate(f"NoyvjSeed.daily.markCompleted('tide', null, {NOW})") is None
    assert blocked.page.evaluate(f"NoyvjSeed.daily.completed('tide', {NOW})") is False
    assert not blocked.errors


def test_todays_run_button_flow(harness):
    h = open_page(harness)
    h.page.evaluate(f"window.v = NoyvjSeed.daily.mountButton('#slot', {{game: 'tide', today: {NOW}, onStart: (s, i) => (window.started = [s, i])}})")
    root = ".noyvj-seed-daily"
    assert "Seed TIDE-X54PB (2026-10-08 UTC)" in h.page.inner_text(f"{root} .noyvj-seed-hint")
    assert "Play today's run" in h.page.inner_text(f"{root} button")
    assert "noyvj-seed--open" in h.page.get_attribute(root, "class")
    h.page.click(f"{root} button")
    assert h.page.evaluate("started") == ["TIDE-X54PB", {"daily": True, "date": "2026-10-08"}]
    assert h.page.evaluate("NoyvjSeed.current()") == "TIDE-X54PB"
    h.page.evaluate(f"NoyvjSeed.daily.markCompleted('tide', {{score: 10}}, {NOW})")      # fires noyvj-daily-change
    assert "✓ Today's run done" in h.page.inner_text(f"{root} .noyvj-seed-label")
    assert "play today's run again" in h.page.inner_text(f"{root} button").lower()
    assert "noyvj-seed--done" in h.page.get_attribute(root, "class")
    assert "1 day in a row" in h.page.inner_text(f"{root} .noyvj-seed-hint")


# --------------------------------------------------------------------------------------------
# Look: sizes, themes, reduced motion, phone width
# --------------------------------------------------------------------------------------------
MOUNT_ALL = """() => { const slot = document.getElementById('slot');
  for (const id of ['a', 'b', 'c']) { const d = document.createElement('div'); d.id = id; slot.appendChild(d); }
  NoyvjSeed.mountCopy('#a', {seed: 'TRADEEMPIRE-K7F2Q'});
  NoyvjSeed.mountStart('#b', {game: 'trade-empire'});
  NoyvjSeed.daily.mountButton('#c', {game: 'trade-empire', today: new Date(Date.UTC(2026, 9, 8))}); }"""


@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
def test_controls_are_44px_and_nothing_overflows(harness, size):
    h = open_page(harness, size=size, touch=size[0] < 500)
    h.page.evaluate(MOUNT_ALL)
    heights = h.page.evaluate("[...document.querySelectorAll('.noyvj-seed button, .noyvj-seed input')].map(e => e.getBoundingClientRect().height)")
    assert heights and min(heights) >= 44
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_light_and_dark_tokens_differ_and_text_is_legible(harness):
    seen = {}
    for theme in ("dark", "light"):
        h = open_page(harness, theme=theme)
        h.page.evaluate(MOUNT_ALL)
        seen[theme] = h.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.noyvj-seed'));
          return [s.backgroundColor, s.color]; }""")
    assert seen["dark"] != seen["light"]

    def lum(css):
        import re
        r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
        f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.03928 else c / 255 / 12.92  # noqa: E731
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    # text colour against its panel colour, composited on the page background, needs at least 4.5:1
    for theme, (bg, fg) in seen.items():
        page_bg = (0.01 if theme == "dark" else 0.85)
        lb = lum(bg) * 0.78 + page_bg * 0.22 if "rgba" in bg else lum(bg)
        lf = lum(fg)
        ratio = (max(lb, lf) + 0.05) / (min(lb, lf) + 0.05)
        assert ratio >= 4.5, (theme, ratio)


def test_reduced_motion_removes_transitions(harness):
    h = open_page(harness)
    h.page.evaluate(MOUNT_ALL)
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-seed-btn')).transitionDuration") != "0s"
    h.page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-seed-btn')).transitionDuration") == "0s"
    os_reduced = harness(media={"reduced_motion": "reduce"})
    os_reduced.pages["/t.html"] = PAGE
    os_reduced.goto()
    os_reduced.page.evaluate(MOUNT_ALL)
    assert os_reduced.page.evaluate("getComputedStyle(document.querySelector('.noyvj-seed-btn')).transitionDuration") == "0s"


def test_state_is_never_colour_alone(harness):
    h = open_page(harness)
    h.page.evaluate(MOUNT_ALL)
    open_style = h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-seed-daily')).borderTopStyle")
    h.page.evaluate("NoyvjSeed.daily.markCompleted('trade-empire', null, new Date(Date.UTC(2026, 9, 8)))")
    done_style = h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-seed-daily')).borderTopStyle")
    assert (open_style, done_style) == ("dashed", "solid")
    assert "✓" in h.page.inner_text(".noyvj-seed-daily .noyvj-seed-label")


def test_nothing_touches_the_network(harness):
    h = open_page(harness, init=[CLIPBOARD_OK])
    h.page.evaluate(MOUNT_ALL)
    h.page.click(".noyvj-seed-copy button")
    assert h.api_calls == []
