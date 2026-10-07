"""shared/achievement-share.js (planning/TODO.md Z-27) in headless Chromium: the share line, the live
percentage (omitted while suppressed or under-sampled), the copy button and its fallback, and the
automatic buttons on earned rows. The stats endpoint is mocked; nothing touches the live backend."""

import pytest

from conftest import page_html

DATA = {"game_id": "tide", "suppressed": False, "save_count": 40, "achievements": {
    "first_reduction": {"earned_pct": 12.5, "earned_count": 5},
    "tiny": {"earned_pct": 0.25, "earned_count": 3},
    "all": {"earned_pct": 100, "earned_count": 40},
}}

CLIPBOARD_OK = ("window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                "value: {writeText: (t) => { window.__copied = t; return Promise.resolve(); }}});")
CLIPBOARD_BLOCKED = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                     "value: {writeText: () => Promise.reject(new Error('denied'))}}); document.execCommand = () => false;")

PANEL = ('<div id="achievements-panel">'
         '<div class="achievement-card achievement-card--earned" data-achievement-id="first_reduction"><p class="achievement-card-label">\U0001F3C6 Cleanup Crew</p><p class="achievement-card-description">Invest in reduction.</p></div>'
         '<div class="achievement-card" data-achievement-id="tiny"><p class="achievement-card-label">Tiny</p></div>'
         '<div class="achievement-card achievement-card--earned" data-achievement-id="unseen"><p class="achievement-card-label">Unseen</p></div>'
         '</div>')


def make(harness, data=DATA, status=200, scripts="stats+share", init=(), panel=PANEL, tag_attrs='data-game-id="tide" data-game-name="Tide"', **kw):
    h = harness(init_scripts=list(init), **kw)
    h.api_responses[("GET", "/stats/games/tide")] = (status, data)
    tags = ""
    if "stats" in scripts:
        tags += '<script src="/shared/achievement-stats.js" data-game-id="tide"></script>'
    tags += f'<script src="/shared/achievement-share.js" {tag_attrs}></script>'
    h.pages["/t.html"] = page_html('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
                                   'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>',
                                   f'<div id="slot"></div>{panel}{tags}')
    h.goto()
    return h


def txt(h, opts):
    return h.page.evaluate("o => NoyvjAchievementShare.text(o)", opts)


URL = "http://harness.test/games/tide/"


def test_text_with_a_percentage(harness):
    h = make(harness)
    assert txt(h, {"label": "Cleanup Crew", "gameName": "Tide", "game": "tide", "earnedPct": 12.5}) \
        == f"I earned Cleanup Crew in Tide, 12.5% of players have it\n{URL}"


@pytest.mark.parametrize("pct", [None, "12", float("nan"), -1, 101])
def test_percentage_is_left_out_when_unknown_or_suppressed(harness, pct):
    h = make(harness)
    assert txt(h, {"label": "Cleanup Crew", "gameName": "Tide", "game": "tide", "earnedPct": pct}) == f"I earned Cleanup Crew in Tide\n{URL}"


def test_text_defaults_and_flattening(harness):
    h = make(harness)
    assert txt(h, {"label": "A\n  B", "game": "trade-empire", "earnedPct": 3, "url": "https://x.test/g/"}) \
        == "I earned A B in Trade Empire, 3% of players have it\nhttps://x.test/g/"
    assert txt(h, {"game": "tide"}).startswith("I earned an achievement in Tide")
    assert txt(h, {"label": "X", "gameName": "G", "game": "tide", "earnedPct": 0.256}).startswith("I earned X in G, 0.26% of players")
    assert "100% of players" in txt(h, {"label": "X", "gameName": "G", "game": "tide", "earnedPct": 100})


def share(h, **extra):
    opts = {"game": "tide", "gameName": "Tide", "achievementId": "first_reduction", "label": "Cleanup Crew", **extra}
    return h.page.evaluate("o => NoyvjAchievementShare.share(o)", opts)


def test_share_uses_the_live_percentage(harness):
    h = make(harness, init=[CLIPBOARD_OK])
    h.page.evaluate("NoyvjAchievementStats.getStats('tide')")
    h.page.wait_for_function("NoyvjAchievementStats.peek('tide') !== undefined")
    out = share(h)
    assert out == {"ok": True, "text": f"I earned Cleanup Crew in Tide, 12.5% of players have it\n{URL}"}
    assert h.page.evaluate("window.__copied") == out["text"]


def test_share_waits_briefly_for_stats_not_yet_loaded(harness):
    h = make(harness, init=[CLIPBOARD_OK])
    assert "12.5% of players" in share(h)["text"]
    assert [c for c in h.api_calls if c[1] == "/stats/games/tide"]


@pytest.mark.parametrize("data,status,aid", [
    ({"suppressed": True, "achievements": {"first_reduction": {"earned_pct": 12.5}}}, 200, "first_reduction"),
    (DATA, 200, "unseen"),
    (DATA, 500, "first_reduction"),
    ({}, 200, "first_reduction"),
])
def test_percentage_omitted_when_suppressed_undersampled_or_unavailable(harness, data, status, aid):
    h = make(harness, init=[CLIPBOARD_OK], data=data, status=status)
    out = share(h, achievementId=aid)
    assert out["ok"] and out["text"] == f"I earned Cleanup Crew in Tide\n{URL}"


def test_share_works_without_achievement_stats_loaded(harness):
    h = make(harness, init=[CLIPBOARD_OK], scripts="share")
    assert h.page.evaluate("typeof window.NoyvjAchievementStats") == "undefined"
    assert "12.5% of players" in share(h)["text"]
    h2 = make(harness, init=[CLIPBOARD_OK], scripts="share", data={"suppressed": True})
    assert "players" not in share(h2)["text"]


def test_share_reports_a_refused_clipboard(harness):
    h = make(harness, init=[CLIPBOARD_BLOCKED])
    out = share(h)
    assert out["ok"] is False and "Cleanup Crew" in out["text"]


def test_mount_button_copies_and_announces(harness):
    h = make(harness, init=[CLIPBOARD_OK], tag_attrs="")
    h.page.evaluate("NoyvjAchievementShare.mountButton('#slot', {game: 'tide', gameName: 'Tide', achievementId: 'first_reduction', label: 'Cleanup Crew'})")
    assert h.page.get_attribute("#slot .noyvj-as-btn", "aria-label") == "Share: Cleanup Crew"
    h.page.wait_for_function("NoyvjAchievementStats.peek('tide') !== undefined")
    h.page.click("#slot .noyvj-as-btn")
    h.page.wait_for_function("window.__copied !== null")
    assert h.page.evaluate("window.__copied") == f"I earned Cleanup Crew in Tide, 12.5% of players have it\n{URL}"
    assert "Copied" in h.page.inner_text("#slot .noyvj-as-status")
    assert h.page.get_attribute("#slot .noyvj-as-status", "aria-live") == "polite"


def test_mount_button_text_box_fallback(harness):
    h = make(harness, init=[CLIPBOARD_BLOCKED], tag_attrs="")
    h.page.evaluate("NoyvjAchievementShare.mountButton('#slot', {game: 'tide', gameName: 'Tide', achievementId: 'first_reduction', label: 'Cleanup Crew'})")
    h.page.click("#slot .noyvj-as-btn")
    h.page.wait_for_selector("#slot .noyvj-as-box")
    assert "Cleanup Crew in Tide" in h.page.input_value("#slot .noyvj-as-box")
    assert "Ctrl+C" in h.page.inner_text("#slot .noyvj-as-status")


def test_mount_button_needs_game_and_id(harness):
    h = make(harness, tag_attrs="")
    assert h.page.evaluate("() => { try { NoyvjAchievementShare.mountButton('#slot', {game: 'tide'}); return 'no error'; } catch (e) { return e.message; } }") \
        .startswith("NoyvjAchievementShare.mountButton needs")
    assert h.page.evaluate("NoyvjAchievementShare.mountButton('#missing', {game: 'tide', achievementId: 'x'})") is None


def test_buttons_appear_only_on_earned_rows_and_survive_a_rebuild(harness):
    h = make(harness, init=[CLIPBOARD_OK])
    h.page.wait_for_selector("[data-achievement-id=first_reduction] .noyvj-as")
    assert h.page.evaluate("[...document.querySelectorAll('[data-achievement-id]')].map(r => [r.dataset.achievementId, r.querySelectorAll('.noyvj-as').length])") \
        == [["first_reduction", 1], ["tiny", 0], ["unseen", 1]]
    assert h.page.get_attribute("[data-achievement-id=first_reduction] .noyvj-as-btn", "aria-label") == "Share: Cleanup Crew"   # trophy stripped
    h.page.evaluate("""() => { const p = document.getElementById('achievements-panel'); const html = p.innerHTML; p.innerHTML = ''; p.innerHTML = html.replace(/<div class="noyvj-as">.*?<\\/div>/g, ''); }""")
    h.page.wait_for_function("document.querySelectorAll('[data-achievement-id=first_reduction] .noyvj-as').length === 1")
    h.page.evaluate("document.querySelector('[data-achievement-id=tiny]').classList.add('achievement-card--earned')")
    h.page.wait_for_selector("[data-achievement-id=tiny] .noyvj-as")
    h.page.wait_for_timeout(1300)
    assert h.page.evaluate("document.querySelectorAll('.noyvj-as').length") == 3        # no duplicates
    h.page.click("[data-achievement-id=first_reduction] .noyvj-as-btn")
    h.page.wait_for_function("window.__copied && window.__copied.includes('Cleanup Crew')")
    assert not h.errors


def test_nothing_attached_without_a_game_id_and_only_the_stats_endpoint_is_called(harness):
    h = make(harness, tag_attrs="")
    h.page.wait_for_timeout(1300)
    assert h.page.evaluate("document.querySelectorAll('.noyvj-as').length") == 0
    assert h.api_calls == []


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
def test_button_size_overflow_and_contrast(harness, theme, size):
    import re
    h = make(harness, size=size, touch=size[0] < 500)
    h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    h.page.wait_for_selector("[data-achievement-id=first_reduction] .noyvj-as-btn")
    assert h.page.evaluate("document.querySelector('.noyvj-as-btn').getBoundingClientRect().height") >= 44
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    colors = h.page.evaluate("(() => { const s = getComputedStyle(document.querySelector('.noyvj-as-btn')); return [s.color, s.backgroundColor, s.opacity]; })()")

    def lum(css):
        r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
        f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.03928 else c / 255 / 12.92  # noqa: E731
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    a, b = lum(colors[0]), lum(colors[1])
    assert (max(a, b) + 0.05) / (min(a, b) + 0.05) >= 4.5 and colors[2] == "1"
