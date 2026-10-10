"""shared/sfx.js + sfx.css (planning/TODO.md AU-1): generated sound with no audio files. The pure tone tables and
envelope math are checked through the page (no clipping: bounded summed peak, bounded master gain, short cues, calm
pitches), and the audio itself is checked with a stubbed AudioContext that records what would have played: nothing
is created while sound is off or before the first tap, the hidden tab is muted, "reduce sounds" is quieter and
shorter, the mounted control and the hub Settings page write the three localStorage keys, and nothing here touches
the network. Skipped when Playwright or Chromium is not installed (see conftest.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import page_html  # noqa: E402

STUB = """
(function () {
  const A = window.__audio = { contexts: 0, oscillators: [], gains: [], filters: [], comps: [], suspends: 0, resumes: 0, last: null };
  class Param {
    constructor(v) { this.value = v || 0; this.events = []; }
    setValueAtTime(v, t) { this.value = v; this.events.push(["set", v, t]); }
    linearRampToValueAtTime(v, t) { this.events.push(["lin", v, t]); }
    exponentialRampToValueAtTime(v, t) { this.events.push(["exp", v, t]); }
    cancelScheduledValues() {}
  }
  class Node { connect(n) { this.out = n; return n; } disconnect() {} }
  class Gain extends Node { constructor() { super(); this.gain = new Param(1); } }
  class Osc extends Node {
    constructor() { super(); this.frequency = new Param(440); this.type = "sine"; this.startAt = null; this.stopAt = null; }
    connect(n) { this.gainNode = n; return super.connect(n); }
    start(t) { this.startAt = t; }
    stop(t) { this.stopAt = t; }
  }
  class Filter extends Node { constructor() { super(); this.frequency = new Param(350); this.Q = new Param(1); this.type = "lowpass"; } }
  class Comp extends Node {
    constructor() { super(); this.threshold = new Param(-24); this.knee = new Param(30); this.ratio = new Param(12); this.attack = new Param(0.003); this.release = new Param(0.25); }
  }
  window.AudioContext = class {
    constructor() { A.contexts += 1; this.state = "suspended"; this.currentTime = 0; this.destination = new Node(); A.last = this; }
    createGain() { const g = new Gain(); A.gains.push(g); return g; }
    createOscillator() { const o = new Osc(); A.oscillators.push(o); return o; }
    createBiquadFilter() { const f = new Filter(); A.filters.push(f); return f; }
    createDynamicsCompressor() { const c = new Comp(); A.comps.push(c); return c; }
    resume() { this.state = "running"; A.resumes += 1; return Promise.resolve(); }
    suspend() { this.state = "suspended"; A.suspends += 1; return Promise.resolve(); }
  };
})();
"""
SOUND_ON = "localStorage.setItem('sfx_enabled','true')"
PAGE = page_html('<link rel="stylesheet" href="/shared/sfx.css">', '<h1>Game</h1><button id="btn">Press</button><div id="slot"></div>'
                 '<script src="/shared/sfx.js"></script>')
TONE_CUES = ["tap", "confirm", "soft_error", "success", "level_complete", "unlock", "bell", "click_low", "click_high"]


def load(harness, init=(), **kw):
    h = harness(init_scripts=[STUB] + list(init), **kw)
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjSfx")
    return h, page


def audio(page):
    return page.evaluate("""() => ({ contexts: __audio.contexts, oscillators: __audio.oscillators.length, suspends: __audio.suspends,
        resumes: __audio.resumes, state: __audio.last && __audio.last.state })""")


def voices(page, since=0):
    """The voices scheduled after the first `since` oscillators: peak gain, frequency, start and stop times."""
    return page.evaluate("""(since) => __audio.oscillators.slice(since).map(o => {
        const lin = (o.gainNode && o.gainNode.gain.events || []).filter(e => e[0] === 'lin');
        return { freq: o.frequency.events[0] ? o.frequency.events[0][1] : o.frequency.value, type: o.type,
                 peak: lin.length ? lin[0][1] : null, start: o.startAt, stop: o.stopAt };
    })""", since)


def wait_gap(page):
    page.wait_for_timeout(70)           # the same cue twice inside 45 ms is dropped on purpose


# ---------- pure tables and envelope math ----------

def test_every_named_cue_exists_and_the_tone_cues_are_calm_and_bounded(harness):
    h, page = load(harness)
    names = page.evaluate("NoyvjSfx.cueNames()")
    for needed in TONE_CUES + ["hum_start", "hum_stop"]:
        assert needed in names
    t = "NoyvjSfx._testing"
    assert page.evaluate(f"{t}.MAX_MASTER") <= 0.5
    for name in TONE_CUES:
        plan = page.evaluate(f"{t}.planCue({name!r}, {{}})")
        assert plan, name
        assert page.evaluate(f"{t}.peakSum({t}.planCue({name!r}, {{}}))") <= page.evaluate(f"{t}.MAX_PEAK_SUM"), name
        duration = page.evaluate(f"{t}.cueDuration({t}.planCue({name!r}, {{}}))")
        assert 0.03 <= duration <= 2.0, (name, duration)
        for v in plan:
            assert v["wave"] in ("sine", "triangle"), name                  # no harsh square or saw waves
            assert 100 <= v["freq"] <= 1500 and (not v.get("glide") or 100 <= v["glide"] <= 1500), name
            assert 0 < v["peak"] <= 0.4 and v["attack"] >= 0.002, name
    assert h.errors == []


def test_master_gain_is_low_monotonic_and_zero_at_zero(harness):
    h, page = load(harness)
    t = "NoyvjSfx._testing"
    gains = [page.evaluate(f"{t}.masterGain({v / 20})") for v in range(21)]
    assert gains[0] == 0 and gains == sorted(gains) and gains[-1] <= 0.5
    assert 0 < page.evaluate(f"{t}.masterGain(0.5)") < 0.2                      # the default volume is already quiet
    assert page.evaluate(f"{t}.masterGain(5)") == gains[-1] and page.evaluate(f"{t}.masterGain(-1)") == 0
    # even the loudest cue at the loudest setting stays far below full scale before the limiter
    worst = max(page.evaluate(f"{t}.peakSum({t}.planCue({n!r}, {{}}))") for n in TONE_CUES)
    assert worst * gains[-1] < 0.5


def test_envelope_math_attack_decay_and_silence_outside_the_voice(harness):
    h, page = load(harness)
    voice = {"dur": 0.4, "attack": 0.01, "peak": 0.3}
    env = lambda t: page.evaluate("([v, t]) => NoyvjSfx._testing.envelope(v, t)", [voice, t])  # noqa: E731
    assert env(-0.1) == 0 and env(0) == 0 and env(0.4) == 0 and env(1) == 0
    assert env(0.005) == pytest.approx(0.15)                                       # halfway up the attack
    assert env(0.01) == pytest.approx(0.3)
    samples = [env(0.01 + i * 0.039) for i in range(10)]
    assert samples == sorted(samples, reverse=True) and samples[-1] < 0.3 * 0.01   # decays towards the -60 dB floor
    assert max(env(i / 1000) for i in range(0, 400)) <= 0.3


def test_reduce_makes_every_cue_quieter_shorter_and_at_most_two_voices(harness):
    h, page = load(harness)
    t = "NoyvjSfx._testing"
    for name in TONE_CUES:
        full = page.evaluate(f"{t}.planCue({name!r}, {{}})")
        small = page.evaluate(f"{t}.planCue({name!r}, {{reduce: true}})")
        assert len(small) <= 2 and len(small) <= len(full), name
        assert page.evaluate(f"{t}.peakSum({t}.planCue({name!r}, {{reduce: true}}))") < page.evaluate(f"{t}.peakSum({t}.planCue({name!r}, {{}}))"), name
        assert page.evaluate(f"{t}.cueDuration({t}.planCue({name!r}, {{reduce: true}}))") < page.evaluate(f"{t}.cueDuration({t}.planCue({name!r}, {{}}))"), name
    assert page.evaluate(f"{t}.planCue('hum_start', {{}})") is None                 # the hum is not a one-shot cue


def test_pitch_and_gain_options_are_clamped(harness):
    h, page = load(harness)
    t = "NoyvjSfx._testing"
    base = page.evaluate(f"{t}.planCue('tap', {{}})")[0]
    up = page.evaluate(f"{t}.planCue('tap', {{pitch: 12}})")[0]
    wild = page.evaluate(f"{t}.planCue('tap', {{pitch: 99, gain: 7}})")[0]
    assert up["freq"] == pytest.approx(base["freq"] * 2) and wild["freq"] == pytest.approx(up["freq"])
    assert wild["peak"] == pytest.approx(base["peak"])                              # gain never raises a cue above its table


# ---------- the audio itself, with a stubbed AudioContext ----------

def test_nothing_is_created_on_load_and_nothing_plays_while_sound_is_off(harness):
    h, page = load(harness)
    assert page.evaluate("NoyvjSfx.enabled()") is False and page.evaluate("NoyvjSfx.volume()") == 0.5 and page.evaluate("NoyvjSfx.reduce()") is False
    assert audio(page)["contexts"] == 0
    page.click("#btn")
    page.keyboard.press("a")
    for name in TONE_CUES + ["hum_start"]:
        assert page.evaluate(f"NoyvjSfx.play({name!r})") is False
    assert audio(page) == {"contexts": 0, "oscillators": 0, "suspends": 0, "resumes": 0, "state": None}
    assert page.evaluate("NoyvjSfx._testing.status().humRunning") is False
    assert h.api_calls == [] and h.errors == []


def test_the_context_is_created_only_after_a_gesture_even_when_sound_is_on(harness):
    h, page = load(harness, init=[SOUND_ON])
    assert page.evaluate("NoyvjSfx.enabled()") is True
    assert audio(page)["contexts"] == 0
    assert page.evaluate("NoyvjSfx.play('tap')") is False                          # no tap yet: silent
    assert audio(page)["contexts"] == 0 and page.evaluate("NoyvjSfx._testing.status().gestureSeen") is False
    page.click("#btn")
    assert audio(page)["contexts"] == 1 and audio(page)["state"] == "running"       # created and resumed by the tap
    assert page.evaluate("NoyvjSfx.play('tap')") is True
    assert audio(page)["contexts"] == 1 and audio(page)["oscillators"] == 1
    # one limiter in the chain, and a low-pass filter
    assert page.evaluate("__audio.comps.length") == 1 and page.evaluate("__audio.comps[0].ratio.value") >= 10
    assert page.evaluate("__audio.filters[0].type") == "lowpass"


def test_a_key_press_is_also_a_gesture(harness):
    h, page = load(harness, init=[SOUND_ON])
    page.keyboard.press("Space")
    assert audio(page)["contexts"] == 1


def test_master_gain_follows_the_volume_setting(harness):
    h, page = load(harness, init=[SOUND_ON, "localStorage.setItem('sfx_volume','0.8')"])
    page.click("#btn")
    page.evaluate("NoyvjSfx.play('confirm')")
    master = page.evaluate("__audio.gains[0].gain.value")
    assert master == pytest.approx(page.evaluate("NoyvjSfx._testing.masterGain(0.8)"))
    page.evaluate("NoyvjSfx.setVolume(0.2)")
    wait_gap(page)
    page.evaluate("NoyvjSfx.play('confirm')")
    assert page.evaluate("__audio.gains[0].gain.value") == pytest.approx(page.evaluate("NoyvjSfx._testing.masterGain(0.2)"))
    page.evaluate("NoyvjSfx.setEnabled(false)")
    assert page.evaluate("__audio.gains[0].gain.value") == 0                       # turning it off silences the chain at once
    assert page.evaluate("NoyvjSfx.play('confirm')") is False


def test_every_cue_schedules_its_planned_voices_with_the_planned_peaks(harness):
    h, page = load(harness, init=[SOUND_ON])
    page.click("#btn")
    for name in TONE_CUES:
        before = audio(page)["oscillators"]
        assert page.evaluate(f"NoyvjSfx.play({name!r})") is True, name
        got = voices(page, before)
        plan = page.evaluate(f"NoyvjSfx._testing.planCue({name!r}, {{}})")
        assert len(got) == len(plan), name
        assert [round(v["peak"], 4) for v in got] == [round(v["peak"], 4) for v in plan], name
        assert all(v["stop"] > v["start"] >= 0 for v in got), name
        wait_gap(page)
        page.evaluate("__audio.last.currentTime += 5")                              # let the finished voices end
    assert h.errors == []


def test_too_many_overlapping_voices_are_dropped(harness):
    h, page = load(harness, init=[SOUND_ON])
    page.click("#btn")
    results = []
    for name in ("bell", "success", "level_complete", "unlock"):
        results.append(page.evaluate(f"NoyvjSfx.play({name!r})"))
    assert results[:2] == [True, True] and False in results                       # the stub clock stands still, so voices pile up
    assert audio(page)["oscillators"] <= page.evaluate("NoyvjSfx._testing.MAX_LIVE_VOICES")


def test_the_same_cue_twice_in_a_blink_plays_once(harness):
    h, page = load(harness, init=[SOUND_ON])
    page.click("#btn")
    assert page.evaluate("[NoyvjSfx.play('click_low'), NoyvjSfx.play('click_low')]") == [True, False]
    assert audio(page)["oscillators"] == 1


def test_a_hidden_tab_is_muted_and_wakes_up_again(harness):
    h, page = load(harness, init=[SOUND_ON])
    page.click("#btn")
    assert page.evaluate("NoyvjSfx.play('tap')") is True
    page.evaluate("""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
                              document.dispatchEvent(new Event('visibilitychange')); }""")
    assert audio(page)["suspends"] >= 1 and audio(page)["state"] == "suspended"
    before = audio(page)["oscillators"]
    wait_gap(page)
    assert page.evaluate("NoyvjSfx.play('tap')") is False and audio(page)["oscillators"] == before
    page.evaluate("""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
                              document.dispatchEvent(new Event('visibilitychange')); }""")
    assert audio(page)["state"] == "running"
    assert page.evaluate("NoyvjSfx.play('tap')") is True


def test_a_context_is_never_created_while_the_tab_is_hidden(harness):
    h, page = load(harness, init=[SOUND_ON, "Object.defineProperty(document, 'hidden', { configurable: true, get: () => true })"])
    page.click("#btn")
    assert audio(page)["contexts"] == 0 and page.evaluate("NoyvjSfx.play('tap')") is False


def test_reduce_mode_schedules_fewer_quieter_shorter_voices(harness):
    h, page = load(harness, init=[SOUND_ON])
    page.click("#btn")
    page.evaluate("NoyvjSfx.play('bell')")
    full = voices(page, 0)
    page.evaluate("NoyvjSfx.setReduce(true)")
    wait_gap(page)
    page.evaluate("NoyvjSfx.play('bell')")
    small = voices(page, len(full))
    assert 0 < len(small) <= 2 < len(full)
    assert sum(v["peak"] for v in small) < sum(v["peak"] for v in full) / 2
    assert max(v["stop"] - v["start"] for v in small) < max(v["stop"] - v["start"] for v in full)


def test_the_ambient_hum_waits_for_a_tap_stops_on_hide_reduce_and_off(harness):
    h, page = load(harness, init=[SOUND_ON])
    status = lambda: page.evaluate("NoyvjSfx._testing.status()")  # noqa: E731
    assert page.evaluate("NoyvjSfx.play('hum_start')") is False                    # no gesture yet: remembered, not started
    assert status()["humWanted"] is True and status()["humRunning"] is False and audio(page)["contexts"] == 0
    page.click("#btn")                                                              # the first tap starts the wished-for hum
    assert status()["humRunning"] is True
    hum_voices = audio(page)["oscillators"]
    assert hum_voices >= 4
    page.evaluate("NoyvjSfx.play('hum_start')")                                     # starting twice never doubles it
    assert audio(page)["oscillators"] == hum_voices
    page.evaluate("NoyvjSfx.setReduce(true)")
    assert status()["humRunning"] is False                                          # reduce mode has no hum
    page.evaluate("NoyvjSfx.setReduce(false)")
    assert status()["humRunning"] is True                                           # and it comes back when reduce goes off
    page.evaluate("NoyvjSfx.play('hum_stop')")
    assert status()["humRunning"] is False and status()["humWanted"] is False
    page.evaluate("NoyvjSfx.play('hum_start')")
    page.evaluate("NoyvjSfx.setEnabled(false)")
    assert status()["humRunning"] is False
    assert h.errors == []


def test_hum_never_starts_while_sound_is_off(harness):
    h, page = load(harness)
    page.click("#btn")
    page.evaluate("NoyvjSfx.play('hum_start')")
    assert audio(page)["contexts"] == 0 and page.evaluate("NoyvjSfx._testing.status().humRunning") is False
    page.evaluate("NoyvjSfx.setEnabled(true)")                                      # turning it on afterwards starts the remembered hum
    assert page.evaluate("NoyvjSfx._testing.status().humRunning") is True


def test_no_audio_support_means_silence_without_errors(harness):
    h, page = load(harness, init=[SOUND_ON, "delete window.AudioContext; delete window.webkitAudioContext"])
    page.click("#btn")
    assert page.evaluate("NoyvjSfx.supported()") is False
    assert page.evaluate("NoyvjSfx.play('tap')") is False and page.evaluate("NoyvjSfx.play('hum_start')") is False
    assert h.errors == []


def test_blocked_storage_does_not_break_the_page(harness):
    h, page = load(harness, init=["Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } })"])
    assert page.evaluate("NoyvjSfx.enabled()") is False
    page.evaluate("NoyvjSfx.setEnabled(true)")
    assert page.evaluate("NoyvjSfx.enabled()") is True                              # kept in memory for this page
    assert h.errors == []


# ---------- the control a game mounts in its Settings panel ----------

def test_the_control_is_labelled_off_by_default_and_writes_the_three_keys(harness):
    h, page = load(harness)
    page.evaluate("document.getElementById('slot').appendChild(NoyvjSfx.control())")
    assert page.evaluate("document.querySelector('link[href*=\"sfx.css\"]') !== null")
    on = page.get_by_label("Sound effects made in code (off by default)")
    vol = page.get_by_label("Volume")
    red = page.get_by_label("Reduce sounds (quieter, shorter, no ambient hum)")
    assert not on.is_checked() and vol.is_disabled() and red.is_disabled()          # nothing to adjust while it is off
    assert "Sound is off" in page.inner_text(".noyvj-sfx-note")
    on.check()
    assert page.evaluate("localStorage.getItem('sfx_enabled')") == "true" and audio(page)["contexts"] == 1
    assert vol.is_enabled() and "Sound is on at 50%" in page.inner_text(".noyvj-sfx-note")
    vol.fill("80")
    assert page.evaluate("localStorage.getItem('sfx_volume')") == "0.8"
    assert page.inner_text(".noyvj-sfx-out") == "80%"
    red.check()
    assert page.evaluate("localStorage.getItem('sfx_reduce')") == "true" and "Reduced" in page.inner_text(".noyvj-sfx-note")
    red.uncheck()
    assert page.evaluate("localStorage.getItem('sfx_reduce')") is None
    on.uncheck()
    assert page.evaluate("localStorage.getItem('sfx_enabled')") is None and page.evaluate("NoyvjSfx.enabled()") is False
    assert h.errors == []


def test_the_control_works_from_the_keyboard_and_the_sample_button_needs_sound_on(harness):
    h, page = load(harness)
    page.evaluate("document.getElementById('slot').appendChild(NoyvjSfx.control())")
    page.focus("[data-testid=sfx-enabled]")
    page.keyboard.press("Space")
    assert page.evaluate("NoyvjSfx.enabled()") is True
    before = audio(page)["oscillators"]
    wait_gap(page)
    page.click("[data-testid=sfx-test]")
    assert audio(page)["oscillators"] > before
    page.evaluate("NoyvjSfx.setEnabled(false)")
    after = audio(page)["oscillators"]
    page.click("[data-testid=sfx-test]")
    assert audio(page)["oscillators"] == after and "Turn sound on first" in page.inner_text(".noyvj-sfx-note")


def test_two_controls_stay_in_step_and_have_unique_ids(harness):
    h, page = load(harness)
    page.evaluate("document.getElementById('slot').append(NoyvjSfx.control(), NoyvjSfx.control())")
    ids = page.evaluate("[...document.querySelectorAll('.noyvj-sfx-control [id]')].map(e => e.id)")
    assert len(ids) == len(set(ids)) == 10
    page.locator("[data-testid=sfx-enabled]").first.check()
    assert page.locator("[data-testid=sfx-enabled]").nth(1).is_checked()


def test_the_control_fits_a_phone_without_sideways_scroll(harness):
    h, page = load(harness, size=(360, 740), touch=True)
    page.evaluate("document.getElementById('slot').appendChild(NoyvjSfx.control())")
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert page.locator("[data-testid=sfx-test]").bounding_box()["height"] >= 40


# ---------- the hub Settings page ----------

def test_the_hub_settings_page_writes_the_keys_and_reset_clears_them(harness):
    h = harness(init_scripts=[STUB])
    page = h.goto("/settings.html")
    page.wait_for_selector("#settings-sfx")
    assert page.input_value("#settings-sfx") == "off" and page.is_disabled("#settings-sfx-volume") and page.is_disabled("#settings-sfx-reduce")
    assert page.is_visible("text=Sound effects made in code") and "Defaults for every game" in page.inner_text("#settings-games-h")
    page.select_option("#settings-sfx", "on")
    assert page.evaluate("localStorage.getItem('sfx_enabled')") == "true"
    page.fill("#settings-sfx-volume", "30")
    assert page.evaluate("localStorage.getItem('sfx_volume')") == "0.3" and page.inner_text("#settings-sfx-volume-out") == "30%"
    page.check("#settings-sfx-reduce")
    assert page.evaluate("localStorage.getItem('sfx_reduce')") == "true"
    # the page itself never makes a sound
    assert audio(page)["contexts"] == 0
    # a reload shows the same state
    page.reload()
    page.wait_for_selector("#settings-sfx")
    assert page.input_value("#settings-sfx") == "on" and page.input_value("#settings-sfx-volume") == "30" and page.is_checked("#settings-sfx-reduce")
    page.click("#settings-clear-prefs")
    page.click("#settings-confirm-yes")
    assert page.evaluate("['sfx_enabled','sfx_volume','sfx_reduce'].map(k => localStorage.getItem(k))") == [None, None, None]
    assert page.input_value("#settings-sfx") == "off" and page.input_value("#settings-sfx-volume") == "50"
    page.select_option("#settings-sfx", "on")
    page.select_option("#settings-sfx", "off")
    assert page.evaluate("localStorage.getItem('sfx_enabled')") is None                  # off removes the key, like the other settings
    assert h.errors == []


def test_a_game_reads_what_the_hub_settings_page_wrote(harness):
    h = harness(init_scripts=[STUB])
    page = h.goto("/settings.html")
    page.wait_for_selector("#settings-sfx")
    page.select_option("#settings-sfx", "on")
    page.fill("#settings-sfx-volume", "70")
    h.pages["/t.html"] = PAGE
    page.goto("http://harness.test/t.html")
    page.wait_for_function("window.NoyvjSfx")
    assert page.evaluate("[NoyvjSfx.enabled(), NoyvjSfx.volume(), NoyvjSfx.reduce()]") == [True, 0.7, False]
