"""B-7: shared/announcer.js, the one screen-reader announcer. Live regions with the right roles, a burst in one
tick joined into one announcement, repeats still announced, assertive kept apart, adoption of an existing
element, textContent only, no timers and no network."""

from conftest import page_html

PAGE = page_html("", '<h1>Game</h1><div id="sr"></div><script src="/shared/announcer.js"></script>')


def open_page(harness):
    h = harness()
    h.pages["/t.html"] = PAGE
    h.goto()
    return h


def region(h, kind):
    return h.page.evaluate(f"(document.querySelector('[data-noyvj-announcer={kind}]') || {{}}).textContent || ''").replace("​", "")


def test_regions_are_made_on_first_use_with_the_right_roles(harness):
    h = open_page(harness)
    assert h.page.evaluate("document.querySelectorAll('[data-noyvj-announcer]').length") == 0
    h.page.evaluate("NoyvjAnnounce.say('Plot 3 cleared'); NoyvjAnnounce.say('Careful', {priority: 'assertive'}); 0")
    h.page.wait_for_function("document.querySelectorAll('[data-noyvj-announcer]').length === 2")
    polite = h.page.evaluate("(() => { const n = document.querySelector('[data-noyvj-announcer=polite]'); return [n.getAttribute('role'), n.getAttribute('aria-live'), n.getAttribute('aria-atomic')]; })()")
    assert polite == ["status", "polite", "true"]
    assertive = h.page.evaluate("(() => { const n = document.querySelector('[data-noyvj-announcer=assertive]'); return [n.getAttribute('role'), n.getAttribute('aria-live')]; })()")
    assert assertive == ["alert", "assertive"]
    assert region(h, "polite") == "Plot 3 cleared" and region(h, "assertive") == "Careful"


def test_a_burst_in_one_tick_is_one_announcement_and_exact_repeats_are_dropped(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjAnnounce.say('Flood hit, 42 damage'); NoyvjAnnounce.say('18 prevented.'); NoyvjAnnounce.say('18 prevented'); 0")
    h.page.wait_for_function("NoyvjAnnounce.history().length === 1")
    assert region(h, "polite") == "Flood hit, 42 damage. 18 prevented"
    assert h.page.evaluate("NoyvjAnnounce.history()") == [{"text": "Flood hit, 42 damage. 18 prevented", "priority": "polite"}]


def test_saying_the_same_thing_again_later_is_announced_again(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjAnnounce.say('Saved'); 0")
    h.page.wait_for_function("NoyvjAnnounce.history().length === 1")
    first = h.page.evaluate("document.querySelector('[data-noyvj-announcer=polite]').textContent")
    h.page.evaluate("NoyvjAnnounce.say('Saved'); 0")
    h.page.wait_for_function("NoyvjAnnounce.history().length === 2")
    second = h.page.evaluate("document.querySelector('[data-noyvj-announcer=polite]').textContent")
    assert first != second and first.replace("​", "") == second.replace("​", "") == "Saved"


def test_the_queue_is_capped_to_the_newest_messages(harness):
    h = open_page(harness)
    h.page.evaluate("for (let i = 0; i < 20; i++) NoyvjAnnounce.say('m' + i); 0")
    h.page.wait_for_function("NoyvjAnnounce.history().length === 1")
    said = region(h, "polite").split(". ")
    assert len(said) == h.page.evaluate("NoyvjAnnounce.MAX_QUEUED") and said[-1] == "m19" and said[0] == "m12"


def test_empty_and_junk_text_says_nothing_and_markup_stays_text(harness):
    h = open_page(harness)
    assert h.page.evaluate("[NoyvjAnnounce.say(''), NoyvjAnnounce.say(null), NoyvjAnnounce.say('   ')]") == [False, False, False]
    h.page.evaluate("NoyvjAnnounce.say('<img src=x onerror=window.__pwned=1> hi'); 0")
    h.page.wait_for_function("NoyvjAnnounce.history().length === 1")
    assert h.page.evaluate("window.__pwned") is None
    assert h.page.evaluate("document.querySelectorAll('[data-noyvj-announcer] img').length") == 0


def test_mount_adopts_an_existing_element_as_the_polite_region(harness):
    h = open_page(harness)
    assert h.page.evaluate("NoyvjAnnounce.mount('#sr') === document.getElementById('sr')")
    h.page.evaluate("NoyvjAnnounce.say('Season 7 begins'); 0")
    h.page.wait_for_function("NoyvjAnnounce.history().length === 1")
    assert h.page.evaluate("document.getElementById('sr').textContent.replace('\\u200b','')") == "Season 7 begins"
    assert h.page.get_attribute("#sr", "aria-live") == "polite"
    assert h.page.evaluate("document.querySelectorAll('[data-noyvj-announcer=polite]').length") == 0
    assert h.page.evaluate("NoyvjAnnounce.mount('#nope')") is None


def test_clear_empties_regions_and_drops_waiting_messages(harness):
    h = open_page(harness)
    h.page.evaluate("NoyvjAnnounce.say('one'); NoyvjAnnounce.clear(); 0")
    h.page.wait_for_timeout(50)
    assert h.page.evaluate("NoyvjAnnounce.history().length") == 0


def test_no_timers_no_network_no_errors(harness):
    h = open_page(harness)
    h.page.evaluate("window.__t = 0; const st = window.setTimeout; window.setTimeout = (...a) => { window.__t++; return st(...a); }; NoyvjAnnounce.say('x'); 0")
    h.page.wait_for_function("NoyvjAnnounce.history().length === 1")
    assert h.page.evaluate("window.__t") == 0 and h.api_calls == [] and h.errors == []
