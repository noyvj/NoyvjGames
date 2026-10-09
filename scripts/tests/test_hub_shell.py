"""Static checks for the hub shell batch (Y-10, Y-15, Y-19, Y-21, Y-22, Y-25, Y-27, Y-29, Y-30).

Run from the repo root:  python3 -m pytest -q scripts/tests
They read the real files, so they catch drift between the lobby, the data files and the pages.
"""

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
NEW_PAGES = ["settings.html", "help.html", "credits.html"]
NEW_FILES = NEW_PAGES + [
    "settings.js", "help.js", "help-data.json", "hub-status.js", "hub-shortcuts.js", "hub-prefs.js",
    "hub-games.js", "game-sessions.json", "terms-meta.json",
]


def cards():
    """(slug, href, name) for every title card on the lobby page."""
    out = []
    for block in re.findall(r'<article class="title-card".*?</article>', INDEX, re.S):
        href = re.search(r'class="title-card-link" href="([^"]+)"', block).group(1)
        name = re.search(r'class="title-card-name">([^<]+)<', block).group(1)
        slug = re.search(r'data-game-slug="([^"]+)"', block).group(1)
        out.append((slug, href, name))
    return out


def load_script(filename, module_name):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---- Y-21: noscript fallback ----

def test_noscript_lists_a_link_to_every_game_on_the_lobby():
    noscript = re.search(r"<noscript>(.*?)</noscript>", INDEX, re.S).group(1)
    linked = re.findall(r'<a href="(games/[^"]+)">', noscript)
    assert linked == [href for _, href, _ in cards()]
    assert len(linked) == 15


def test_noscript_and_compat_notice_exist_with_alert_role():
    assert 'id="noscript-notice"' in INDEX and 'id="compat-notice"' in INDEX
    assert "typeof WebAssembly" in INDEX
    assert "window.__hubScriptRan = true" in (ROOT / "script.js").read_text(encoding="utf-8").splitlines()[0]


# ---- Y-22: session lengths ----

def test_every_lobby_game_has_a_known_session_tier():
    data = json.loads((ROOT / "game-sessions.json").read_text(encoding="utf-8"))
    assert set(data["tiers"]) == {"short", "medium", "long"}
    slugs = {slug for slug, _, _ in cards()}
    assert set(data["games"]) == slugs
    assert set(data["games"].values()) <= set(data["tiers"])


def test_session_filter_options_match_the_tiers():
    data = json.loads((ROOT / "game-sessions.json").read_text(encoding="utf-8"))
    select = re.search(r'<select id="game-session-filter".*?</select>', INDEX, re.S).group(0)
    values = re.findall(r'<option value="([^"]*)"', select)
    assert values == [""] + list(data["tiers"])


# ---- Y-15: help data ----

def test_help_data_is_well_formed_and_its_links_exist():
    data = json.loads((ROOT / "help-data.json").read_text(encoding="utf-8"))
    topics = {t["id"] for t in data["topics"]}
    ids = [i["id"] for i in data["items"]]
    assert len(ids) == len(set(ids)) >= 15
    for item in data["items"]:
        assert item["topic"] in topics, item["id"]
        assert item["q"].strip() and len(item["a"]) > 40, item["id"]
        assert "<" not in item["a"], "answers are plain text"
        for link in item.get("links", []):
            target = ROOT / link["href"].split("#")[0]
            assert target.exists(), (item["id"], link["href"])


def test_help_answers_match_facts_in_the_code():
    text = json.dumps(json.loads((ROOT / "help-data.json").read_text(encoding="utf-8")))
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "SAVE_SLOTS_PER_GAME = 3" in main and "three save slots" in text
    assert 'SAVE_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"' in main
    widget = (ROOT / "shared" / "save-widget.js").read_text(encoding="utf-8")
    assert "AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000" in widget and "every five minutes" in text
    example = re.search(r"like ([A-Z0-9]{4}-[A-Z0-9]{4})", text).group(1)
    assert set(example.replace("-", "")) <= set("23456789ABCDEFGHJKMNPQRSTUVWXYZ")


# ---- Y-10: settings keys are the keys the games really use ----

def test_settings_page_game_keys_exist_in_the_games():
    settings_js = (ROOT / "settings.js").read_text(encoding="utf-8")
    exempt = re.search(r"NO_DISPLAY_PREFS = \[(.*?)\]", settings_js).group(1)
    exempt = set(re.findall(r'"([^"]+)"', exempt))
    for slug, _, _ in cards():
        game_settings = ROOT / "games" / slug / "settings.js"
        if slug in exempt:
            assert not game_settings.exists(), f"{slug} now has a settings.js: remove it from NO_DISPLAY_PREFS"
            continue
        source = game_settings.read_text(encoding="utf-8")
        prefix = re.search(r'KEY_PREFIX = \{(.*?)\}', settings_js).group(1)
        prefix = dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', prefix)).get(slug, slug)
        assert f'"{prefix}-text-scale"' in source, slug
        assert f'"{prefix}-reduced-motion"' in source, slug


def test_settings_storage_keys_match_the_shared_scripts():
    settings_js = (ROOT / "settings.js").read_text(encoding="utf-8")
    assert "`autosave-enabled:${g.slug}`" in settings_js
    assert "autosave-enabled:${GAME_ID}" in (ROOT / "shared" / "save-widget.js").read_text(encoding="utf-8")
    assert "tutorial-seen:${gameId}" in (ROOT / "shared" / "tutorial.js").read_text(encoding="utf-8")
    assert "`tutorial-seen:${g.slug}`" in settings_js
    script = (ROOT / "script.js").read_text(encoding="utf-8")
    for key in ("hub-onboarding-seen", "hub-new-player-banner-dismissed", "hub_announcement_dismissed",
                "pwa_install_banner_dismissed", "claim_save_nudge_dismissed", "hub_pageview_opt_in"):
        assert key in script and key in settings_js, key
    # the token must never be exported
    assert 'SECRET_KEYS = ["hub_bearer_token"]' in settings_js
    assert 'TOKEN_KEY = "hub_bearer_token"' in (ROOT / "shared" / "owner-links.js").read_text(encoding="utf-8")


# ---- Y-19: shortcuts ----

def test_shortcut_defaults_have_no_clashes_and_point_at_real_pages():
    js = (ROOT / "hub-shortcuts.js").read_text(encoding="utf-8")
    block = js[js.index("const ACTIONS = ["):js.index("];", js.index("const ACTIONS = ["))]
    rows = re.findall(r'\{ id: "(\w+)", type: "(single|go)", key: "(.)"(?:, label: "[^"]*")?(?:, scope: "[^"]*")?(?:, href: "([^"]+)")?', block)
    assert len(rows) >= 10
    seen = set()
    for action_id, kind, key, href in rows:
        assert (kind, key.lower()) not in seen, (action_id, key)
        seen.add((kind, key.lower()))
        assert key.lower() != "g"
        if href:
            assert (ROOT / href).exists(), href


# ---- Y-29 / hygiene: new public files ----

def test_new_pages_load_only_files_that_exist():
    for name in NEW_PAGES + ["terms.html"]:
        html = (ROOT / name).read_text(encoding="utf-8")
        for ref in re.findall(r'(?:src|href)="([^"#?]+)', html):
            if ref.startswith(("http", "mailto:", "data:")):
                continue
            assert (ROOT / ref).exists(), (name, ref)


def test_new_public_files_keep_owner_pages_and_the_tracker_off_the_public_site():
    for name in NEW_FILES + ["index.html", "hub-prefs.js"]:
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        for forbidden in ("warframe", "ideas.html", "admin.html", "owner-only"):
            assert forbidden not in text, (name, forbidden)


def test_credits_only_names_what_the_site_really_uses():
    credits = (ROOT / "credits.html").read_text(encoding="utf-8")
    assert "v0.26.4" in (ROOT / "games" / "sol" / "index.html").read_text(encoding="utf-8")
    assert "(version 0.26.4)" in credits
    assert "three@0.128.0" in (ROOT / "games" / "continuum" / "index.html").read_text(encoding="utf-8")
    assert "(version r128)" in credits
    deps = (ROOT / "app" / "pyproject.toml").read_text(encoding="utf-8")
    for dep in ("fastapi", "sqlalchemy", "pydantic"):
        assert dep in deps and dep in credits.lower(), dep
    # no web fonts are loaded anywhere on the hub, which is what the page claims
    assert "fonts.googleapis" not in INDEX and "@font-face" not in (ROOT / "style.css").read_text(encoding="utf-8")


# ---- Y-30: terms meta generator ----

def test_terms_meta_parser_and_builder():
    gen = load_script("generate-terms-meta.py", "generate_terms_meta")
    log = "2026-10-08\tHub shell batch\n2026-09-26\tTerms: optional email\nnot a line\n2026-09-20\t\n"
    changes = gen.parse_log(log)
    assert changes == [
        {"date": "2026-10-08", "subject": "Hub shell batch"},
        {"date": "2026-09-26", "subject": "Terms: optional email"},
    ]
    meta = gen.build_meta(changes)
    assert meta["last_changed"] == "2026-10-08" and meta["file"] == "terms.html"
    assert gen.build_meta([])["last_changed"] is None
    many = "".join(f"2026-01-{d:02d}\tchange {d}\n" for d in range(1, 15))
    assert len(gen.parse_log(many)) == gen.MAX_CHANGES


def test_terms_meta_file_and_page_agree_on_shape():
    meta = json.loads((ROOT / "terms-meta.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["last_changed"])
    assert isinstance(meta["changes"], list)
    terms = (ROOT / "terms.html").read_text(encoding="utf-8")
    assert 'fetch("terms-meta.json")' in terms and 'id="terms-updated"' in terms
