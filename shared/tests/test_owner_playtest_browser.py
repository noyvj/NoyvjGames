"""GN-18: the owner-only "Playtest queue" carousel on the hub (owner-playtest.js).

Hidden, and owner-playtest.json never requested, for a signed-out visitor and for a signed-in non-owner; one
card per valid item for the owner; typing saves to localStorage and the note `playtest-notes` is PUT with
the right shape; a failing PUT keeps the answer and says so; finished items collapse to the end; the Markdown
copy; the keyboard scroll buttons. Real pages in headless Chromium, the backend answered by the test."""

import json

SEEN = "localStorage.setItem('hub-onboarding-seen','1');localStorage.setItem('tutorial-seen:hub','1');"
TOKEN = "localStorage.setItem('hub_bearer_token','t');"
NOTE = ("PUT", "/owner/notes/playtest-notes")


def hub(harness, *, owner=True, token=True, remote=None, put=(200, {"ok": True}), size=(1440, 900), scripts=(), wait=True):
    h = harness(size=size, init_scripts=[SEEN, TOKEN if token else "", *scripts])
    h.api_responses[("GET", "/ratings-summary")] = (200, {"games": {}})
    h.api_responses[("GET", "/users/me")] = (200, {"username": "noyvj" if owner else "someone", "id": 1})
    h.api_responses[("GET", "/owner/notes/playtest-notes")] = (200, {"value": {"version": 1, "answers": remote or {}}})
    h.api_responses[NOTE] = put
    h.json_requests = []
    h.page.on("request", lambda r: h.json_requests.append(r.url) if "owner-playtest.json" in r.url else None)
    page = h.goto("/index.html")
    if wait:
        page.wait_for_selector(".owner-playtest-card")
    return h, page


def stored(page):
    return json.loads(page.evaluate("localStorage.getItem('owner-playtest-v1') || '{}'"))


def puts(h):
    return [c for c in h.api_calls if (c[0], c[1]) == NOTE]


def test_signed_out_stays_empty_and_never_fetches_the_json(harness):
    h, page = hub(harness, token=False, wait=False)
    page.wait_for_selector(".game-row")
    assert page.evaluate("document.getElementById('owner-playtest').hidden") is True
    assert page.evaluate("document.getElementById('owner-playtest').childElementCount") == 0
    assert h.json_requests == []
    assert not [c for c in h.api_calls if c[1] == "/users/me"]


def test_non_owner_stays_empty_and_never_fetches_the_json(harness):
    h, page = hub(harness, owner=False, wait=False)
    page.wait_for_selector(".game-row")
    page.wait_for_timeout(500)
    assert [c for c in h.api_calls if c[1] == "/users/me"]
    assert page.evaluate("document.getElementById('owner-playtest').hidden") is True
    assert page.evaluate("document.getElementById('owner-playtest').childElementCount") == 0
    assert h.json_requests == []


def test_owner_sees_one_card_per_item_with_all_parts(harness):
    h, page = hub(harness)
    data = json.loads(open("owner-playtest.json", encoding="utf-8").read())["items"]
    assert page.locator(".owner-playtest-card").count() == len(data)
    assert page.is_visible("#owner-playtest")
    first = page.locator(".owner-playtest-card").first
    assert data[0]["title"] in first.inner_text() and data[0]["why"] in first.inner_text() and data[0]["how"] in first.inner_text()
    assert first.locator(".owner-playtest-answer").count() == len(data[0]["questions"])
    assert first.locator("ol > li").count() == len(data[0]["questions"])
    assert page.get_attribute(".owner-playtest-card .owner-playtest-game", "href") == "games/tide/index.html"
    assert page.locator(".owner-playtest-card a[href='index.html']").count() >= 1   # the hub items
    assert page.get_attribute(".owner-playtest-answer", "maxlength") == "400"
    assert "Playtest queue" in page.inner_text("#owner-playtest")
    assert h.errors == []


def test_typing_saves_locally_and_puts_the_note(harness):
    h, page = hub(harness)
    box = page.locator("#pt-tide-new-0")
    box.fill("Yes, it matched.")
    s = stored(page)["tide-new"]
    assert s["q"]["0"]["t"] == "Yes, it matched." and s["q"]["0"]["u"] > 0 and s["g"] == "tide"
    assert puts(h) == []                       # nothing goes to the server while typing
    page.locator("#pt-tide-new-1").focus()     # leaving the box syncs
    page.wait_for_function("document.querySelector('.owner-playtest-status').textContent.includes('synced')")
    assert page.inner_text(".owner-playtest-status") == "Saved on this device and synced"
    body = json.loads(puts(h)[-1][2])
    assert body["value"]["version"] == 1
    assert body["value"]["answers"]["tide-new"]["q"]["0"]["t"] == "Yes, it matched."
    assert "ghost" in body["value"]["answers"]["tide-new"]["q"]["0"]["p"]
    # a reload shows the saved text again
    page.reload()
    page.wait_for_selector(".owner-playtest-card")
    assert page.input_value("#pt-tide-new-0") == "Yes, it matched."


def test_a_long_answer_is_cut_at_400_characters(harness):
    h, page = hub(harness)
    page.evaluate("""() => { const t = document.getElementById('pt-tide-new-0'); t.removeAttribute('maxlength');
        t.value = 'x'.repeat(500); t.dispatchEvent(new Event('input', {bubbles: true})); }""")
    assert len(stored(page)["tide-new"]["q"]["0"]["t"]) == 400


def test_a_failing_put_keeps_the_answer_and_says_so(harness):
    h, page = hub(harness, put=(500, {"detail": "boom"}))
    page.fill("#pt-tide-new-0", "keep me")
    page.locator("#pt-tide-new-1").focus()
    page.wait_for_function("document.querySelector('.owner-playtest-status').textContent.includes('not synced')")
    text = page.inner_text(".owner-playtest-status")
    assert "500" in text and "stay on this device" in text
    assert stored(page)["tide-new"]["q"]["0"]["t"] == "keep me"
    assert page.input_value("#pt-tide-new-0") == "keep me"


def test_remote_answers_merge_by_newest_edit(harness):
    remote = {"tide-new": {"q": {"0": {"t": "from the other device", "u": 9999999999999, "p": "q"},
                                 "1": {"t": "old remote", "u": 5, "p": "q"}}, "g": "tide", "n": "Tide"}}
    local = "localStorage.setItem('owner-playtest-v1', JSON.stringify({'tide-new': {q: {'0': {t: 'old local', u: 10}, '1': {t: 'new local', u: 20}}}}));"
    h, page = hub(harness, remote=remote, scripts=[local])
    page.wait_for_function("document.getElementById('pt-tide-new-0').value === 'from the other device'")
    assert page.input_value("#pt-tide-new-1") == "new local"
    # the newer local answer is pushed back up
    page.wait_for_function("true")
    for _ in range(20):
        if puts(h):
            break
        page.wait_for_timeout(100)
    assert json.loads(puts(h)[-1][2])["value"]["answers"]["tide-new"]["q"]["1"]["t"] == "new local"


def test_done_items_collapse_to_the_end_and_can_be_reopened(harness):
    h, page = hub(harness)
    ids = page.eval_on_selector_all(".owner-playtest-card", "els => els.map(e => e.dataset.itemId)")
    page.check("input[data-item-id='tide-new']")
    after = page.eval_on_selector_all(".owner-playtest-card", "els => els.map(e => e.dataset.itemId)")
    assert after[-1] == "tide-new" and after[:-1] == ids[1:]
    last = page.locator(".owner-playtest-card").last
    assert "owner-playtest-card--collapsed" in last.get_attribute("class")
    assert last.locator("textarea").count() == 0 and "Done" in last.inner_text()
    assert "1 done" in page.inner_text(".owner-playtest-count")
    page.wait_for_function("document.querySelector('.owner-playtest-status').textContent.includes('synced')")
    sent = json.loads(puts(h)[-1][2])["value"]["answers"]["tide-new"]
    assert sent["d"] == 1 and sent["du"] > 0
    # focus did not fall to the page body
    assert page.evaluate("document.activeElement.type") == "checkbox"
    page.uncheck("input[data-item-id='tide-new']")
    assert page.eval_on_selector_all(".owner-playtest-card", "els => els.map(e => e.dataset.itemId)") == ids


def test_copy_all_answers_is_readable_markdown(harness):
    h, page = hub(harness, scripts=["window.__copied = null; Object.defineProperty(navigator, 'clipboard', {value: {writeText: async (t) => { window.__copied = t; }}});"])
    page.fill("#pt-tide-new-0", "Matches well")
    page.check("input[data-item-id='aftermath-tree']")
    page.click(".owner-playtest-copy")
    page.wait_for_function("window.__copied !== null")
    md = page.evaluate("window.__copied")
    assert md.startswith("# Playtest answers")
    assert "## Tide: run codes, Daily Tide and named coastlines (tide)" in md
    assert "   Answer: Matches well" in md and "   Answer: (not answered)" in md
    assert "(aftermath) [done]" in md
    assert "1. Does pasting your own run code" in md
    assert "Copied" in page.inner_text(".owner-playtest-status")


def test_scroll_buttons_work_from_the_keyboard_and_are_44px(harness):
    h, page = hub(harness, size=(1440, 900))
    prev, nxt = page.locator(".owner-playtest-controls button").nth(0), page.locator(".owner-playtest-controls button").nth(1)
    assert prev.get_attribute("aria-label") and nxt.get_attribute("aria-label")
    box = nxt.bounding_box()
    assert box["width"] >= 44 and box["height"] >= 44
    assert prev.is_disabled() and nxt.is_enabled()
    assert page.get_attribute(".owner-playtest-track", "tabindex") == "0"
    assert page.get_attribute(".owner-playtest-track", "role") == "region"
    nxt.focus()
    page.keyboard.press("Enter")
    page.wait_for_function("document.querySelector('.owner-playtest-track').scrollLeft > 100")
    assert prev.is_enabled()
    prev.focus()
    page.keyboard.press("Space")
    page.wait_for_function("document.querySelector('.owner-playtest-track').scrollLeft < 5")


def test_no_horizontal_page_scroll_at_360_and_1440_in_both_themes(harness):
    for size in ((360, 740), (1440, 900)):
        for theme in ("light", "dark"):
            h, page = hub(harness, size=size, scripts=[f"localStorage.setItem('hub_theme','{theme}');"])
            page.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), (size, theme)
            assert page.evaluate("document.getElementById('owner-playtest').getBoundingClientRect().width <= window.innerWidth")
            h.close()


def test_malformed_entries_are_ignored(harness):
    h = harness(init_scripts=[SEEN, TOKEN])
    h.api_responses[("GET", "/ratings-summary")] = (200, {"games": {}})
    h.api_responses[("GET", "/users/me")] = (200, {"username": "noyvj", "id": 1})
    h.api_responses[("GET", "/owner/notes/playtest-notes")] = (404, {})
    h.pages["/owner-playtest.json"] = json.dumps({"items": [
        None, 5, {"id": "ok", "game": "tide", "title": "<b>Fine</b>", "questions": ["q1", 7, ""]},
        {"id": "ok", "game": "tide", "title": "dupe"}, {"game": "tide", "title": "no id"},
        {"id": "bad-game", "game": "../x", "title": "x"}]})
    page = h.goto("/index.html")
    page.wait_for_selector(".owner-playtest-card")
    assert page.locator(".owner-playtest-card").count() == 1
    assert page.locator(".owner-playtest-answer").count() == 1
    assert page.inner_text(".owner-playtest-card-title") == "<b>Fine</b>"    # text only, never markup
    assert page.locator(".owner-playtest-card b").count() == 0
