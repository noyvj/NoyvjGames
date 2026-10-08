"""shared/report-problem.js (planning/TODO.md Z-17) in headless Chromium: the button and dialog, the
exact-preview promise, opt-in attachments, the console ring buffer and its scrubbing, keyboard and
layout. The backend is answered by the test (conftest.Harness); no network."""

import json

from conftest import API, page_html

TAG = '<script src="/shared/report-problem.js" data-game-id="canopy" data-schema-version="3"></script>'
PAGE = page_html('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
                 'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>' + TAG,
                 '<h1>A game</h1><button id="other">Something else</button>')
CODE = "ABCD-2345"


def open_page(harness, init=(), page=PAGE, path="/t.html", **kw):
    h = harness(init_scripts=list(init), **kw)
    h.pages[path.split("?")[0]] = page
    h.goto(path)
    h.requests = []
    h.page.on("request", lambda r: h.requests.append(r) if r.url.startswith(API) else None)
    return h


def open_dialog(h):
    h.page.click(".noyvj-report-button")
    h.page.wait_for_selector("dialog.noyvj-report-dialog[open]")


def preview(h):
    return h.page.evaluate("document.getElementById('noyvj-report-preview').textContent")


def ticked(h):
    return h.page.evaluate("[...document.querySelectorAll('.noyvj-report-dialog input[type=checkbox]')].map(c => c.checked)")


def test_button_opens_a_dialog_with_every_extra_off_and_nothing_sent(harness):
    h = open_page(harness)
    assert h.page.inner_text(".noyvj-report-button") == "Report a problem"
    open_dialog(h)
    assert ticked(h) == [False, False, False, False]
    text = preview(h)
    assert "Game: canopy" in text and "Page: /t.html" in text and "Save schema version: 3" in text
    for label in ("Save code: (not attached)", "Browser: (not attached)", "Window size: (not attached)",
                  "Console lines: (not attached)", "Linked to your account: no"):
        assert label in text
    assert h.page.evaluate("document.activeElement.id") == "noyvj-report-note"
    assert h.page.is_disabled("button.nr-primary")          # nothing written yet: nothing to send
    assert h.api_calls == []


def test_typing_and_ticking_change_the_preview_live(harness):
    h = open_page(harness, init=[f"localStorage.setItem('savecode:canopy','{CODE.lower()}')"])
    h.page.evaluate("console.warn('first warning'); console.error('second problem')")
    open_dialog(h)
    h.page.fill("#noyvj-report-note", "The tree button does nothing")
    assert "What happened: The tree button does nothing" in preview(h)
    assert h.page.is_enabled("button.nr-primary")
    h.page.check("#noyvj-report-save")
    h.page.check("#noyvj-report-browser")
    h.page.check("#noyvj-report-console")
    text = preview(h)
    assert f"Save code: {CODE}" in text
    assert "Browser: Mozilla" in text or "Browser: " in text and "(not attached)" not in text.split("Browser:")[1].split("\n")[0]
    assert "Window size: 1440x900" in text
    assert "Console lines (2):" in text and "[warn] first warning" in text and "[error] second problem" in text
    h.page.uncheck("#noyvj-report-save")
    assert "Save code: (not attached)" in preview(h)


def test_what_is_posted_is_exactly_what_the_preview_shows(harness):
    h = open_page(harness, init=[f"localStorage.setItem('savecode:canopy','{CODE}')"], path=f"/t.html?code={CODE}#top")
    h.api_responses[("POST", "/bug-reports")] = (200, {"id": "r1", "received": True})
    h.page.evaluate("console.warn('a warning line')")
    open_dialog(h)
    h.page.fill("#noyvj-report-note", "It froze after I clicked Replant")
    for box in ("save", "browser", "console"):
        h.page.check(f"#noyvj-report-{box}")
    shown = preview(h)
    h.page.click("button.nr-primary")
    h.page.wait_for_function("document.getElementById('noyvj-report-status').textContent.includes('Thank you')")
    posts = [c for c in h.api_calls if c[0] == "POST" and c[1] == "/bug-reports"]
    assert len(posts) == 1
    body = json.loads(posts[0][2])
    assert body["game_id"] == "canopy" and body["schema_version"] == "3"
    assert body["page"] == "/t.html"                       # path only: no query string with a code, no hash
    assert body["note"] == "It froze after I clicked Replant"
    assert body["attachment"] == {"save_code": CODE}
    assert body["viewport"].startswith("1440x900") and body["browser"]
    assert body["console_log"] and "a warning line" in body["console_log"][-1]
    assert body["link_account"] is False
    # every value that goes over the wire is written out in the preview
    for value in (body["game_id"], body["page"], body["schema_version"], body["note"], body["attachment"]["save_code"],
                  body["browser"], body["viewport"], *body["console_log"]):
        assert value in shown, value
    # the note box is emptied after a send, and the page query string never reached the preview
    assert h.page.input_value("#noyvj-report-note") == ""
    assert "?code=" not in shown and "#top" not in shown


def test_a_default_send_attaches_nothing_and_carries_no_credentials(harness):
    h = open_page(harness, init=[f"localStorage.setItem('savecode:canopy','{CODE}');localStorage.setItem('hub_bearer_token','tok-secret');localStorage.setItem('hub_account_username','mara')"])
    h.api_responses[("POST", "/bug-reports")] = (200, {"id": "r1", "received": True})
    open_dialog(h)
    h.page.fill("#noyvj-report-note", "Just a note")
    h.page.click("button.nr-primary")
    h.page.wait_for_function("document.getElementById('noyvj-report-status').textContent.includes('Thank you')")
    body = json.loads([c for c in h.api_calls if c[0] == "POST"][0][2])
    assert body["browser"] is None and body["viewport"] is None and body["console_log"] is None
    assert body["attachment"] is None and body["link_account"] is False
    request = [r for r in h.requests if r.method == "POST"][0]
    assert "authorization" not in {k.lower() for k in request.headers}
    assert "tok-secret" not in (request.post_data or "")


def test_account_link_is_offered_only_when_signed_in_and_sends_the_token_only_when_ticked(harness):
    out = open_page(harness)
    open_dialog(out)
    assert out.page.is_hidden("#noyvj-report-account")
    h = open_page(harness, init=["localStorage.setItem('hub_bearer_token','tok-abc');localStorage.setItem('hub_account_username','mara')"])
    h.api_responses[("POST", "/bug-reports")] = (200, {"id": "r1", "received": True})
    open_dialog(h)
    assert h.page.is_visible("#noyvj-report-account") and not h.page.is_checked("#noyvj-report-account")
    h.page.fill("#noyvj-report-note", "Linked please")
    h.page.check("#noyvj-report-account")
    assert "Linked to your account: yes, as mara" in preview(h)
    h.page.click("button.nr-primary")
    h.page.wait_for_function("document.getElementById('noyvj-report-status').textContent.includes('Thank you')")
    request = [r for r in h.requests if r.method == "POST"][0]
    assert request.headers.get("authorization") == "Bearer tok-abc"
    assert json.loads(request.post_data)["link_account"] is True


def test_save_code_box_is_disabled_when_there_is_no_code(harness):
    h = open_page(harness)
    open_dialog(h)
    assert h.page.is_disabled("#noyvj-report-save")
    assert "nothing to attach" in h.page.inner_text("#noyvj-report-save-hint")


def test_console_ring_keeps_the_last_twenty_lines_and_scrubs_secrets(harness):
    h = open_page(harness)
    h.page.evaluate("""() => {
      for (let i = 0; i < 30; i++) console.log('line ' + i);
      console.log('Authorization: Bearer abc.DEF-123_xyz');
      console.warn('GET /x?token=sekrit123&a=1');
      console.info('loaded save ABCD-2345');
      console.debug('mail me at someone@example.com');
      console.error(new Error('boom'), {a: 1});
      console.log('x'.repeat(900));
    }""")
    lines = h.page.evaluate("NoyvjReport.consoleLines()")
    assert len(lines) == 20
    assert "line 0" not in "\n".join(lines) and "line 25" in "\n".join(lines)
    joined = "\n".join(lines)
    for secret in ("abc.DEF-123_xyz", "sekrit123", "ABCD-2345", "someone@example.com"):
        assert secret not in joined
    assert "[removed]" in joined and "Error: boom" in joined
    assert all(len(line) <= 300 for line in lines)
    assert not h.errors


def test_uncaught_errors_and_rejections_are_captured(harness):
    h = open_page(harness)
    h.page.evaluate("(() => { setTimeout(() => { throw new Error('late failure'); }, 0); Promise.reject(new Error('lost promise')); })()")
    h.page.wait_for_function("NoyvjReport.consoleLines().some(l => l.includes('lost promise')) && NoyvjReport.consoleLines().some(l => l.includes('late failure'))")


def test_console_still_works_for_the_page_itself(harness):
    h = open_page(harness)
    h.page.evaluate("console.log('visible to the developer too')")
    assert any("visible to the developer too" in text for _, text in h.console)


def test_escape_closes_and_focus_returns_to_the_button(harness):
    h = open_page(harness)
    open_dialog(h)
    h.page.keyboard.type("hello")
    h.page.keyboard.press("Escape")
    assert h.page.evaluate("document.querySelector('dialog').open") is False
    assert h.page.evaluate("document.activeElement.className").startswith("noyvj-report-button")
    # the unsent note is still there if the player reopens
    open_dialog(h)
    assert h.page.input_value("#noyvj-report-note") == "hello"


def test_keyboard_only_flow_sends_with_ctrl_enter_and_tab_stays_inside(harness):
    h = open_page(harness)
    h.api_responses[("POST", "/bug-reports")] = (200, {"id": "r1", "received": True})
    h.page.focus(".noyvj-report-button")
    h.page.keyboard.press("Enter")
    h.page.wait_for_selector("dialog.noyvj-report-dialog[open]")
    h.page.keyboard.type("typed without a mouse")
    seen = set()
    for _ in range(14):
        h.page.keyboard.press("Tab")
        seen.add(h.page.evaluate("document.activeElement.id || document.activeElement.tagName"))
    # the modal dialog makes the page behind it unreachable; Tab only cycles its own controls
    assert "other" not in seen and not any(name for name in seen if name == "H1")
    assert h.page.evaluate("document.querySelector('.noyvj-report-button').matches(':focus')") is False
    h.page.focus("#noyvj-report-note")
    h.page.keyboard.press("Control+Enter")
    h.page.wait_for_function("document.getElementById('noyvj-report-status').textContent.includes('Thank you')")


def test_a_failed_send_keeps_the_note_and_says_so(harness):
    h = open_page(harness)
    h.api_responses[("POST", "/bug-reports")] = (500, {"detail": "boom"})
    open_dialog(h)
    h.page.fill("#noyvj-report-note", "keep me")
    h.page.click("button.nr-primary")
    h.page.wait_for_function("document.getElementById('noyvj-report-status').textContent.includes('could not be sent')")
    assert h.page.input_value("#noyvj-report-note") == "keep me" and h.page.is_enabled("button.nr-primary")
    h.api_responses[("POST", "/bug-reports")] = (429, {"detail": "slow down"})
    h.page.click("button.nr-primary")
    h.page.wait_for_function("document.getElementById('noyvj-report-status').textContent.includes('try again in a while')")


def test_copy_report_text_puts_the_preview_on_the_clipboard(harness):
    h = open_page(harness, init=["window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                                 "value: {writeText: (t) => { window.__copied = t; return Promise.resolve(); }}});"])
    open_dialog(h)
    h.page.fill("#noyvj-report-note", "for the clipboard")
    h.page.click("text=Copy report text")
    h.page.wait_for_function("window.__copied !== null")
    assert h.page.evaluate("window.__copied") == preview(h)


def test_button_can_be_left_out_or_mounted_in_a_container(harness):
    bare = open_page(harness, page=page_html('<script src="/shared/report-problem.js" data-game-id="canopy" data-button="none"></script>', "<p>x</p>"))
    assert bare.page.query_selector(".noyvj-report-button") is None
    bare.page.evaluate("NoyvjReport.open()")
    bare.page.wait_for_selector("dialog.noyvj-report-dialog[open]")
    mounted = open_page(harness, page=page_html('<script src="/shared/report-problem.js" data-mount="#slot"></script>',
                                                 '<div id="slot"></div>'), path="/games/thaw/index.html")
    assert mounted.page.query_selector("#slot .noyvj-report-button")
    assert "Game: thaw" in (mounted.page.click("#slot .noyvj-report-button") or preview(mounted))


def test_text_is_never_interpreted_as_markup(harness):
    h = open_page(harness)
    open_dialog(h)
    h.page.fill("#noyvj-report-note", "<img src=x onerror=window.__pwned=1><b>bold</b>")
    assert h.page.evaluate("window.__pwned") is None
    assert h.page.query_selector("#noyvj-report-preview img, #noyvj-report-preview b") is None
    assert "<b>bold</b>" in preview(h)


def test_follows_the_site_theme(harness):
    h = open_page(harness)
    open_dialog(h)
    h.page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
    dark = h.page.evaluate("getComputedStyle(document.querySelector('dialog')).backgroundColor")
    assert dark == "rgb(20, 22, 31)"
    h.page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
    light = h.page.evaluate("getComputedStyle(document.querySelector('dialog')).backgroundColor")
    assert dark != light and light == "rgb(255, 255, 255)"
    text = h.page.evaluate("getComputedStyle(document.querySelector('dialog')).color")
    assert text == "rgb(26, 28, 36)"


def test_phone_width_layout_has_no_sideways_scroll_and_big_targets(harness):
    h = open_page(harness, size=(360, 740), touch=True)
    open_dialog(h)
    h.page.check("#noyvj-report-console")
    h.page.fill("#noyvj-report-note", "x" * 400)
    box = h.page.evaluate("(() => { const r = document.querySelector('dialog').getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom]; })()")
    assert box[0] >= 0 and box[1] <= 360 and box[2] >= 0 and box[3] <= 740
    assert h.page.evaluate("document.documentElement.scrollWidth <= 360")
    assert h.page.evaluate("document.querySelector('dialog form').scrollWidth <= document.querySelector('dialog form').clientWidth")
    small = h.page.evaluate("""[...document.querySelectorAll('dialog button, dialog .nr-check, .noyvj-report-button')]
        .filter(e => e.offsetParent !== null).filter(e => e.getBoundingClientRect().height < 44).map(e => e.className || e.textContent)""")
    assert small == []
    # the Send button is reachable by scrolling the dialog's own body
    h.page.evaluate("document.querySelector('button.nr-primary').scrollIntoView()")
    assert h.page.is_visible("button.nr-primary")


def test_nothing_is_sent_until_send_is_pressed(harness):
    h = open_page(harness)
    open_dialog(h)
    h.page.fill("#noyvj-report-note", "typing, ticking, closing")
    h.page.check("#noyvj-report-browser")
    h.page.keyboard.press("Escape")
    h.page.wait_for_timeout(200)
    assert h.api_calls == []


def test_no_page_errors(harness):
    h = open_page(harness)
    open_dialog(h)
    h.page.fill("#noyvj-report-note", "x")
    assert h.errors == []
