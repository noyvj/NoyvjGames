"""shared/achievement-stats.js in headless Chromium: the existing '% of players' line stays exactly as
it was, plus Z-15 rarity labels (Bronze/Silver/Gold from the live earned_pct, one threshold table,
text + shape + border, hidden while suppressed) and hidden achievements ('???' until earned).
The stats endpoint is mocked; nothing touches the live backend."""

import re

import pytest

from conftest import page_html

DATA = {"game_id": "tide", "suppressed": False, "save_count": 40, "achievements": {
    "rare": {"earned_pct": 4.5, "earned_count": 3},
    "edge_gold": {"earned_pct": 10, "earned_count": 4},
    "middle": {"earned_pct": 20, "earned_count": 8},
    "edge_silver": {"earned_pct": 35, "earned_count": 14},
    "common": {"earned_pct": 80, "earned_count": 32},
}}


def row(aid, label, desc, earned=False, extra=""):
    cls = "achievement-card achievement-card--earned" if earned else "achievement-card"
    return (f'<div class="{cls}" data-achievement-id="{aid}" {extra}><p class="achievement-card-label">{label}</p>'
            f'<p class="achievement-card-description">{desc}</p></div>')


ROWS = "".join([
    row("rare", "Rare One", "Do the rare thing.", True),
    row("edge_gold", "Edge Gold", "Exactly ten percent.", True),
    row("middle", "Middle", "Mid thing.", False),
    row("edge_silver", "Edge Silver", "Exactly thirty five.", False),
    row("common", "Common", "Easy thing.", True),
    row("unseen", "Unseen", "Nobody has this yet.", False),
])


def make(harness, rows=ROWS, data=DATA, status=200, head="", size=(1440, 900), theme=None, apply=True, **kw):
    h = harness(size=size, **kw)
    h.api_responses[("GET", "/stats/games/tide")] = (status, data)
    h.pages["/t.html"] = page_html(
        '<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
        'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>' + head,
        f'<div id="achievements-panel">{rows}</div><script src="/shared/achievement-stats.js" data-game-id="tide"></script>')
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    if apply:
        h.page.evaluate("window.applyAchievementStats()")
        h.page.wait_for_function("document.querySelectorAll('.achievement-earn-rate').length > 0 || window.__never", timeout=3000) if data and not data.get("suppressed") and status == 200 else None
    return h


def rarity(h, aid):
    return h.page.evaluate("""(id) => { const el = document.querySelector(`[data-achievement-id="${id}"] .achievement-rarity`);
      return el ? [el.dataset.rarity, el.textContent, getComputedStyle(el).borderTopStyle] : null; }""", aid)


def test_percent_line_is_unchanged(harness):
    h = make(harness)
    lines = h.page.evaluate("[...document.querySelectorAll('[data-achievement-id]')].map(r => [r.dataset.achievementId, r.querySelector('.achievement-earn-rate').textContent])")
    assert dict(lines) == {"rare": "Earned by 4.5% of players.", "edge_gold": "Earned by 10% of players.",
                           "middle": "Earned by 20% of players.", "edge_silver": "Earned by 35% of players.",
                           "common": "Earned by 80% of players.", "unseen": "Not enough data yet on this achievement."}
    assert h.api_calls == [("GET", "/stats/games/tide", None)]


def test_rarity_labels_follow_the_thresholds(harness):
    h = make(harness)
    assert rarity(h, "rare")[0] == "gold" and "Gold" in rarity(h, "rare")[1] and "★" in rarity(h, "rare")[1]
    assert rarity(h, "edge_gold")[0] == "gold"                         # 10 is inclusive
    assert rarity(h, "middle")[0] == "silver" and "◆" in rarity(h, "middle")[1]
    assert rarity(h, "edge_silver")[0] == "silver"                     # 35 is inclusive
    assert rarity(h, "common")[0] == "bronze" and "●" in rarity(h, "common")[1]
    assert rarity(h, "unseen") is None                                 # under-sampled: no label, no guess


def test_each_tier_differs_by_shape_word_and_border_not_only_colour(harness):
    h = make(harness)
    seen = {k: rarity(h, a) for k, a in (("gold", "rare"), ("silver", "middle"), ("bronze", "common"))}
    assert len({v[1] for v in seen.values()}) == 3                     # text (glyph + word) differs
    assert len({v[2] for v in seen.values()}) == 3                     # border style differs: double / dashed / dotted
    assert [seen[k][2] for k in ("gold", "silver", "bronze")] == ["double", "dashed", "dotted"]
    assert h.page.evaluate("document.querySelector('.achievement-rarity span').getAttribute('aria-hidden')") == "true"


def test_rarity_for_and_threshold_table_in_one_place(harness):
    h = make(harness, apply=False)
    r = h.page.evaluate("""() => { const s = NoyvjAchievementStats;
      return [s.RARITY_THRESHOLDS, [0, 10, 10.01, 35, 35.01, 100].map(s.rarityFor),
              [null, undefined, NaN, -1, 101, '5', Infinity].map(s.rarityFor)]; }""")
    assert r[0] == {"gold": 10, "silver": 35}
    assert r[1] == ["gold", "gold", "silver", "silver", "bronze", "bronze"]
    assert r[2] == [None] * 7
    changed = h.page.evaluate("""() => { const s = NoyvjAchievementStats;
      const bad = [s.setRarityThresholds({gold: 20, silver: 10}), s.setRarityThresholds({gold: 0, silver: 5}), s.setRarityThresholds(null), s.setRarityThresholds({gold: 5, silver: 100})];
      const ok = s.setRarityThresholds({gold: 5, silver: 50});
      return [bad, ok, s.rarityFor(10), s.rarityFor(50.5)]; }""")
    assert changed == [[False] * 4, True, "silver", "bronze"]


def test_suppressed_game_shows_nothing_at_all(harness):
    h = make(harness, data={"game_id": "tide", "suppressed": True, "achievements": {"rare": {"earned_pct": 4.5}}})
    h.page.wait_for_timeout(300)
    assert h.page.evaluate("document.querySelectorAll('.achievement-earn-rate, .achievement-rarity').length") == 0


def test_failed_or_missing_stats_leave_rows_untouched_without_errors(harness):
    for status in (404, 500):
        h = make(harness, status=status, apply=True)
        h.page.wait_for_timeout(300)
        assert h.page.evaluate("document.querySelectorAll('.achievement-earn-rate, .achievement-rarity').length") == 0
        assert not h.errors
    off = harness()
    off.pages["/t.html"] = page_html("", f'<div id="achievements-panel">{ROWS}</div><script src="/shared/achievement-stats.js" data-game-id="tide"></script>')
    off.goto()
    off.page.route("**/stats/**", lambda route: route.abort())
    off.page.evaluate("window.applyAchievementStats()")
    off.page.wait_for_timeout(300)
    assert off.page.evaluate("document.querySelectorAll('.achievement-rarity').length") == 0 and not off.errors


def test_the_stat_line_is_added_once_per_row_even_if_applied_twice(harness):
    h = make(harness)
    h.page.evaluate("window.applyAchievementStats()")
    h.page.wait_for_timeout(200)
    assert h.page.evaluate("document.querySelectorAll('[data-achievement-id=\"rare\"] .achievement-rarity').length") == 1
    assert h.page.evaluate("document.querySelectorAll('[data-achievement-id=\"rare\"] .achievement-earn-rate').length") == 1


def test_no_panel_or_no_rows_is_harmless(harness):
    h = harness()
    h.pages["/t.html"] = page_html("", '<script src="/shared/achievement-stats.js" data-game-id="tide"></script>')
    h.goto()
    h.page.evaluate("window.applyAchievementStats()")
    assert not h.errors and h.api_calls == []


def test_missing_game_id_logs_one_error_like_before(harness):
    h = harness()
    h.pages["/t.html"] = page_html("", '<div id="achievements-panel"></div><script src="/shared/achievement-stats.js"></script>')
    h.goto()
    h.page.evaluate("window.applyAchievementStats()")
    assert any("missing required data-game-id" in text for kind, text in h.console if kind == "error")


# ---- hidden achievements -----------------------------------------------------------------------------
HIDDEN_ROWS = "".join([
    row("secret_a", "Secret A", "The real description A.", False, 'data-achievement-hidden="true"'),
    row("secret_b", "Secret B", "The real description B.", True, 'data-achievement-hidden="true"'),
    row("plain", "Plain", "A normal description.", False),
    row("secret_c", "Secret C", "From the catalog.", False),
])


def descs(h):
    return h.page.evaluate("Object.fromEntries([...document.querySelectorAll('[data-achievement-id]')].map(r => [r.dataset.achievementId, r.querySelector('.achievement-card-description').textContent]))")


def test_hidden_unearned_description_is_masked_until_earned(harness):
    h = make(harness, rows=HIDDEN_ROWS, apply=False)
    h.page.evaluate("NoyvjAchievementStats.registerCatalog([{id: 'secret_c', hidden: true}, {id: 'plain'}])")
    h.page.evaluate("window.applyAchievementStats()")
    assert descs(h) == {"secret_a": "???", "secret_b": "The real description B.", "plain": "A normal description.", "secret_c": "???"}
    assert h.page.evaluate("document.querySelector('[data-achievement-id=secret_a]').dataset.achievementMasked") == "true"
    # the label is still visible, so the player knows something is there
    assert h.page.inner_text("[data-achievement-id=secret_a] .achievement-card-label") == "Secret A"


def test_masking_happens_synchronously_before_any_network_answer(harness):
    h = make(harness, rows=HIDDEN_ROWS, apply=False)
    assert h.page.evaluate("() => { window.applyAchievementStats(); return document.querySelector('[data-achievement-id=secret_a] .achievement-card-description').textContent; }") == "???"


def test_earning_a_hidden_achievement_reveals_it_on_the_next_pass(harness):
    h = make(harness, rows=HIDDEN_ROWS, apply=False)
    h.page.evaluate("window.applyAchievementStats()")
    assert descs(h)["secret_a"] == "???"
    h.page.evaluate("document.querySelector('[data-achievement-id=secret_a]').classList.add('achievement-card--earned'); NoyvjAchievementStats.maskHidden()")
    assert descs(h)["secret_a"] == "The real description A."
    assert h.page.evaluate("document.querySelector('[data-achievement-id=secret_a]').dataset.achievementMasked") is None


def test_earned_flag_variants_and_catalog_toggle(harness):
    rows = (row("x1", "X1", "d1", False, 'data-achievement-earned="true" data-achievement-hidden="true"') +
            '<div class="achievement-earned" data-achievement-id="x2" data-achievement-hidden="true"><p class="achievement-card-description">d2</p></div>')
    h = make(harness, rows=rows, apply=False)
    h.page.evaluate("window.applyAchievementStats()")
    assert descs(h) == {"x1": "d1", "x2": "d2"}
    h.page.evaluate("NoyvjAchievementStats.registerCatalog({achievements: [{id: 'x1', hidden: true}]}); NoyvjAchievementStats.registerCatalog([{id: 'x1', hidden: false}])")
    assert h.page.evaluate("NoyvjAchievementStats.isHiddenRow(document.querySelector('[data-achievement-id=x1]'))") is True   # attribute still wins
    h2 = make(harness, rows=row("y", "Y", "dy"), apply=False)
    h2.page.evaluate("NoyvjAchievementStats.registerCatalog([{id: 'y', hidden: true}]); NoyvjAchievementStats.registerCatalog([{id: 'y', hidden: false}])")
    h2.page.evaluate("window.applyAchievementStats()")
    assert descs(h2) == {"y": "dy"}


def test_hidden_masking_works_while_stats_are_suppressed(harness):
    h = make(harness, rows=HIDDEN_ROWS, data={"suppressed": True, "achievements": {}}, apply=False)
    h.page.evaluate("window.applyAchievementStats()")
    h.page.wait_for_timeout(200)
    assert descs(h)["secret_a"] == "???" and h.page.evaluate("document.querySelectorAll('.achievement-rarity').length") == 0


def test_rows_without_a_description_element_are_left_alone(harness):
    rows = '<div class="achievement-earned" data-achievement-id="champ" data-achievement-hidden="true"><span>Champ line</span></div>'
    h = make(harness, rows=rows, data={"suppressed": False, "achievements": {"champ": {"earned_pct": 3}}})
    assert h.page.inner_text("[data-achievement-id=champ] span") == "Champ line"
    assert rarity(h, "champ")[0] == "gold"


# ---- look ----------------------------------------------------------------------------------------------
def lum(css):
    r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
    f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.03928 else c / 255 / 12.92  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
def test_label_is_legible_and_fits_in_both_themes_and_sizes(harness, theme, size):
    h = make(harness, theme=theme, size=size)
    for aid in ("rare", "middle", "common"):
        c = h.page.evaluate("""(id) => { const s = getComputedStyle(document.querySelector(`[data-achievement-id="${id}"] .achievement-rarity`));
          return [s.color, s.backgroundColor, s.opacity]; }""", aid)
        a, b = lum(c[0]), lum(c[1])
        assert (max(a, b) + 0.05) / (min(a, b) + 0.05) >= 4.5, (theme, aid)
        assert c[2] == "1"
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
