"""shared/info-footer.js (SR-1): the footer ends with a Sources link to sources.html?game=<slug>."""

from conftest import ORIGIN, page_html

BODY = '<h1>Thaw</h1><section id="howto-panel"><p>steps</p></section><section id="info-page-panel"><p>real story</p></section>'


def test_footer_links_to_the_games_sources_page(harness):
    h = harness()
    h.pages["/games/thaw/t.html"] = page_html('<script src="/shared/info-footer.js" data-game-id="thaw"></script>', BODY)
    h.goto("/games/thaw/t.html")
    h.page.wait_for_selector("#howto-panel .noyvj-info-footer a")
    for panel in ("howto-panel", "info-page-panel"):
        link = h.page.query_selector(f"#{panel} .noyvj-info-footer a.noyvj-info-footer-link")
        assert link.inner_text() == "Sources"
        assert link.get_attribute("href") == f"{ORIGIN}/sources.html?game=thaw"
    # the plain-text line is unchanged and the link is separate from it
    assert h.page.evaluate("NoyvjInfoFooter.text()").startswith("NoyvjGames · Thaw")
    assert h.page.evaluate("NoyvjInfoFooter.sourcesHref()") == f"{ORIGIN}/sources.html?game=thaw"
    assert h.errors == []


def test_the_link_survives_the_game_rewriting_its_panel_and_is_not_duplicated(harness):
    h = harness()
    h.pages["/games/thaw/t.html"] = page_html('<script src="/shared/info-footer.js" data-game-id="thaw"></script>', BODY)
    h.goto("/games/thaw/t.html")
    h.page.wait_for_selector("#info-page-panel .noyvj-info-footer a")
    h.page.evaluate("document.getElementById('info-page-panel').innerHTML = '<p>new framing</p>'")
    h.page.wait_for_selector("#info-page-panel .noyvj-info-footer a")
    h.page.wait_for_timeout(700)    # the polling tick runs; it must not add a second link
    assert len(h.page.query_selector_all("#info-page-panel .noyvj-info-footer a")) == 1
    assert len(h.page.query_selector_all("#info-page-panel .noyvj-info-footer")) == 1


def test_game_id_is_taken_from_the_folder_when_the_attribute_is_missing_and_odd_ids_are_encoded(harness):
    h = harness()
    h.pages["/games/dead-reckoning/t.html"] = page_html('<script src="/shared/info-footer.js"></script>', BODY)
    h.goto("/games/dead-reckoning/t.html")
    h.page.wait_for_selector("#howto-panel .noyvj-info-footer a")
    assert h.page.get_attribute("#howto-panel .noyvj-info-footer a", "href") == f"{ORIGIN}/sources.html?game=dead-reckoning"
    h.pages["/t2.html"] = page_html('<script src="/shared/info-footer.js" data-game-id="a b&c"></script>', BODY)
    h.goto("/t2.html")
    h.page.wait_for_selector("#howto-panel .noyvj-info-footer a")
    assert h.page.get_attribute("#howto-panel .noyvj-info-footer a", "href").endswith("sources.html?game=a%20b%26c")


def test_no_link_when_the_game_is_unknown(harness):
    h = harness()
    h.pages["/t.html"] = page_html('<script src="/shared/info-footer.js"></script>', BODY)
    h.goto("/t.html")
    h.page.wait_for_selector("#howto-panel .noyvj-info-footer")
    assert h.page.query_selector(".noyvj-info-footer a") is None


def test_every_game_page_that_includes_the_footer_names_its_game():
    """The link is only as good as data-game-id: it must equal the game's folder name."""
    import re
    from conftest import ROOT
    checked = 0
    for page in sorted((ROOT / "games").glob("*/index.html")):
        for m in re.finditer(r'<script[^>]*info-footer\.js[^>]*>', page.read_text(encoding="utf-8")):
            gid = re.search(r'data-game-id="([^"]+)"', m.group(0))
            assert gid and gid.group(1) == page.parent.name, f"{page}: {m.group(0)}"
            checked += 1
    assert checked >= 20
