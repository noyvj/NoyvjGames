"""AN-14: overlay-mockups.html shows one sample window as a side drawer, a centred pop-up and a full-screen menu
so the owner can pick the Desktop style. Esc closes, Tab stays inside, focus returns, the choice is remembered
locally and nothing leaves the browser."""

import pytest


def open_page(harness, size=(1280, 800)):
    h = harness(size=size)
    h.goto("/overlay-mockups.html")
    return h


@pytest.mark.parametrize("kind", ["drawer", "popup", "full"])
def test_each_style_opens_closes_with_escape_and_returns_focus(harness, kind):
    h = open_page(harness)
    h.page.click(f'[data-open="{kind}"]')
    assert h.page.is_visible("#win") and h.page.evaluate("document.getElementById('win').className") == f"win {kind}"
    assert h.page.evaluate("document.activeElement.id") == "win-close"
    assert h.page.get_attribute("#main", "aria-hidden") == "true"
    h.page.keyboard.press("Escape")
    assert h.page.is_hidden("#layer")
    assert h.page.evaluate("document.activeElement.getAttribute('data-open')") == kind
    assert h.page.get_attribute("#main", "aria-hidden") is None


def test_tab_stays_inside_the_window_both_ways(harness):
    h = open_page(harness)
    h.page.click('[data-open="popup"]')
    for _ in range(12):
        h.page.keyboard.press("Tab")
        assert h.page.evaluate("document.getElementById('win').contains(document.activeElement)")
    for _ in range(12):
        h.page.keyboard.press("Shift+Tab")
        assert h.page.evaluate("document.getElementById('win').contains(document.activeElement)")


def test_geometry_of_the_three_styles(harness):
    h = open_page(harness)
    h.page.click('[data-open="drawer"]')
    h.page.wait_for_timeout(350)                 # the slide-in animation is 180 ms
    box = h.page.evaluate("(() => { const r = document.getElementById('win').getBoundingClientRect(); return [r.left, r.top, r.width, r.height, innerWidth, innerHeight]; })()")
    assert box[3] == box[5] and abs(box[0] + box[2] - box[4]) < 1 and box[2] <= 420
    h.page.keyboard.press("Escape")
    h.page.click('[data-open="full"]')
    box = h.page.evaluate("(() => { const r = document.getElementById('win').getBoundingClientRect(); return [r.width, r.height, innerWidth, innerHeight]; })()")
    assert box[0] == box[2] and box[1] == box[3]
    h.page.keyboard.press("Escape")
    h.page.click('[data-open="popup"]')
    h.page.wait_for_timeout(350)
    box = h.page.evaluate("(() => { const r = document.getElementById('win').getBoundingClientRect(); return [r.left, r.width, innerWidth]; })()")
    assert abs((box[0] + box[1] / 2) - box[2] / 2) < 1 and box[1] < box[2]


def test_clicking_the_dimmed_area_closes_and_the_choice_is_remembered(harness):
    h = open_page(harness)
    h.page.click('[data-open="drawer"]')
    h.page.mouse.click(20, 20)
    assert h.page.is_hidden("#layer")
    h.page.click('[data-prefer="popup"]')
    assert "Centred pop-up" in h.page.inner_text("#choice-line")
    assert h.page.get_attribute('[data-prefer="popup"]', "aria-pressed") == "true"
    h.page.reload()
    assert "Centred pop-up" in h.page.inner_text("#choice-line")
    assert h.api_calls == []


def test_fits_a_phone_and_targets_are_44px(harness):
    h = open_page(harness, size=(360, 740))
    assert h.page.evaluate("document.documentElement.scrollWidth <= 360")
    h.page.click('[data-open="popup"]')
    assert h.page.evaluate("[...document.querySelectorAll('#win button, #win select, #win input[type=text]')].every(e => e.getBoundingClientRect().height >= 44)")
    assert h.page.evaluate("document.getElementById('win').getBoundingClientRect().right <= 360")
