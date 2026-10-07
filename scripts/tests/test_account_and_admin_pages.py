"""Static checks for Y-13, Y-14, Y-23, Y-24 and Y-26 (the page side; the backend side is tested in
app/tests). Run from the repo root:  python3 -m pytest -q scripts/tests"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_new_root_files_exist_and_pages_load_only_existing_files():
    for name in ("whats-new-data.js", "whats-new.html", "settings.html", "settings.js", "admin.html", "terms.html"):
        assert (ROOT / name).exists(), name
    for name in ("whats-new.html", "settings.html", "admin.html"):
        for ref in re.findall(r'<script[^>]+src="([^"#?]+)', read(name)):
            if not ref.startswith("http"):
                assert (ROOT / ref).exists(), (name, ref)


def test_entry_id_shape_matches_the_server_pattern():
    js = read("whats-new-data.js")
    # the id built on the page: "<game|site>-<date>-<8 hex>"
    assert "`${source.key}-${dateMatch[1]}-${hash8(oneLine)}`" in js
    assert 'key: "game"' in js and 'key: "site"' in js
    assert ".padStart(8," in js
    server = (ROOT / "app" / "account_data.py").read_text(encoding="utf-8")
    assert 'ENTRY_ID_RE = re.compile(r"^(game|site)-\\d{4}-\\d{2}-\\d{2}-[0-9a-f]{8}$")' in server
    # the vote token the page makes must satisfy the server's token pattern
    assert 'TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")' in server
    assert "/^[A-Za-z0-9_-]{16,64}$/" in read("whats-new.html")


def test_whats_new_page_has_votes_and_keeps_warframe_off_the_public_feed():
    page = read("whats-new.html")
    assert "whats-new/votes/" in page and "X-Vote-Token" in page
    data = read("whats-new-data.js")
    assert "warframe" in data.lower()  # the filter that keeps the tracker off the public feed
    assert "warframe" not in page.lower()


def test_admin_page_shows_activity_votes_and_the_missing_error_data():
    page = read("admin.html")
    for needle in ("/admin/timeseries", "/admin/whats-new-votes", "panel-activity", "panel-votes", "panel-errors",
                   "whats-new-data.js", "nothing on the server records errors"):
        assert needle in page, needle


def test_settings_account_controls_and_reduce_data_switch():
    html, js = read("settings.html"), read("settings.js")
    for needle in ('id="settings-account-export"', 'id="settings-delete-confirm"', 'id="settings-delete-go"',
                   'id="settings-reduce-data"'):
        assert needle in html, needle
    assert 'id="settings-delete-go" disabled' in html  # cannot be pressed before the typed confirmation
    assert "/users/me/export" in js and 'method: "DELETE"' in js and "confirm_username" in js
    assert "hub_reduce_data" in js and "hub_reduce_data" in read("script.js")
    # the hub preference reset must catch the new key (it starts with hub_)
    assert re.search(r"hub\[_-\]", js)
    # settings pages stay free of owner-only references
    for forbidden in ("admin.html", "warframe", "ideas.html", "owner-only"):
        assert forbidden not in (html + js).lower(), forbidden


def test_lobby_caption_and_reduce_data_gating():
    index, script = read("index.html"), read("script.js")
    assert 'id="game-sort-leaders"' in index
    assert "renderSortLeaders" in script and "hubReduceData()" in script
    # no "most played" statistic exists, so the caption must not pretend to have one
    assert "Most played" not in script
    # the community highlights fetch is behind the reduce-data check
    body = script[script.index("async function loadCommunityHighlights()"):]
    assert body.index("hubReduceData()") < body.index("/stats/achievements")
    # the startup save-count load for the caption is also behind it
    assert re.search(r"if \(!hubReduceData\(\)\) \{\s*loadSaveCounts\(\)", script)


def test_terms_describe_what_deletion_really_does():
    terms = read("terms.html").lower()
    for needle in ("download my data", "delete my account", "type your username", "settings.html#account",
                   "not linked to an account", "owner's own"):
        assert needle in terms, needle
    assert "dealt with by hand" in terms  # still the route for anything the buttons do not cover
