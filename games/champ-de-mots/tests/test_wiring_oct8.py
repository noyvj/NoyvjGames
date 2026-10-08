"""Oct 8 wiring: copy result (Z-20), achievement share (Z-27), share meta (Y-7), JSON-LD (Y-8), the
Credits link (Y-29) and pause-when-hidden for the timed minigames (Z-28) are on Le Champ de Mots'
pages. Static checks on the page files, plus the Python the page reads."""

import json
import re
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
SLUG = "champ-de-mots"
NAME = "Le Champ de Mots"
PAGES = ["index.html", "pc.html"]


def page(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def head(name):
    html = page(name)
    return html[: html.index("</head>")]


@pytest.mark.parametrize("name", PAGES)
def test_share_scripts_are_loaded_with_the_game_id(name):
    html = head(name)
    assert f'<script src="../../shared/copy-result.js" data-game-id="{SLUG}"></script>' in html
    assert f'<script src="../../shared/achievement-share.js" data-game-id="{SLUG}" data-game-name="{NAME}"></script>' in html


@pytest.mark.parametrize("name", PAGES)
def test_credits_link_is_a_plain_keyboard_reachable_link(name):
    assert re.search(r'<a [^>]*id="credits-link"[^>]*href="\.\./\.\./credits\.html"[^>]*>Credits</a>', page(name))


def test_credits_link_is_in_the_desktop_help_menu():
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    help_group = next(g for g in config["toolbar"]["menu"] if g["heading"] == "Help")
    assert "credits-link" in help_group["ids"]


@pytest.mark.parametrize("name", PAGES)
def test_open_graph_twitter_and_canonical_block_is_in_the_head(name):
    html = head(name)
    snippet = (GAME_DIR.parent.parent / "share" / "meta" / f"{SLUG}.html").read_text(encoding="utf-8")
    assert snippet.split("\n", 1)[1] in html   # the Desktop page adds "(Desktop)" to the title
    assert "<title>" + NAME in html
    assert html.count('property="og:title"') == 1
    assert f"games/{SLUG}/" in html and f"share/{SLUG}.png" in html
    assert html.rstrip().endswith('lite-mode.css">')


@pytest.mark.parametrize("name", PAGES)
def test_json_ld_is_inlined_and_valid(name):
    html = head(name)
    match = re.search(r'<script type="application/ld\+json">\n(.*?)\n</script>', html, re.S)
    assert match, "no JSON-LD block"
    data = json.loads(match.group(1).replace("<\\/", "</"))
    expected = json.loads((GAME_DIR.parent.parent / "share" / "jsonld" / f"{SLUG}.json").read_text(encoding="utf-8"))
    assert data == expected
    assert data["name"] == NAME


@pytest.mark.parametrize("name", PAGES)
def test_copy_result_sits_under_the_review_summary(name):
    html = page(name)
    assert html.count('id="result-copy"') == 1
    assert html.count('id="result-copy-review"') == 1
    assert 'mountButton("#result-copy"' in html
    assert 'globals.get("share_result")' in html
    assert html.index('id="review-summary"') < html.index('id="result-copy-review"')


@pytest.mark.parametrize("name", PAGES)
def test_pause_hidden_is_wired_with_a_settings_checkbox(name):
    html = page(name)
    assert f'<script src="../../shared/pause-hidden.js" data-game-id="{SLUG}" data-manual></script>' in html
    assert 'id="pause-hidden-checkbox"' in html
    assert html.index('id="settings-panel"') < html.index('id="pause-hidden-checkbox"') < html.index('id="settings-reset-button"')
    assert "NoyvjPauseHidden.init(" in html
    assert 'gameId: "champ-de-mots"' in html
    assert "CHAMP_MINIGAMES_HELD" in html


def test_the_one_second_timer_holds_while_hidden_and_does_not_change_the_tick_maths():
    html = page("index.html")
    start = html.index("setInterval(() => {")
    block = html[start:html.index("}, 1000);", start)]
    assert block.lstrip().splitlines()[1].strip() == "if (window.CHAMP_MINIGAMES_HELD) return;"
    for name in ("blitz_tick", "sprint_tick", "racer_tick", "boutique_tick", "cafe_tick",
                 "pairs_tick", "gaps_tick", "listenpick_tick", "wordorder_tick"):
        assert name in block
    assert "}, 1000);" in html


def test_share_result_is_headline_numbers_as_json(game_env):
    data = json.loads(game_env.module.share_result())
    assert data["game"] == NAME
    assert data["score"] not in (None, "")
    assert data["stats"], "at least one extra figure"
    for stat in data["stats"]:
        assert isinstance(stat, str) or {"n", "one", "many"} <= set(stat)


def test_share_result_includes_the_review_score_once_a_session_has_answers(game_env):
    module = game_env.module
    assert not any("right" in s for s in json.loads(module.share_result())["stats"] if isinstance(s, str))
    module.review_score = {"correct": 7, "total": 10}
    assert "7/10 right" in json.loads(module.share_result())["stats"]


def test_copy_button_container_is_only_shown_under_a_finished_review(game_env):
    module = game_env.module
    box = game_env.elements["result-copy-review"]
    module.render()
    assert box.hidden is True
    module.start_review("word")
    assert box.hidden is True            # questions still to answer
    module.review_queue = []
    module.review_question = None
    module.review_score = {"correct": 3, "total": 4}
    module.render()
    assert box.hidden is False
    module.close_review()
    module.render()
    assert box.hidden is True


def test_earned_achievement_rows_expose_their_label_for_the_share_button(game_env):
    module = game_env.module
    for plot in module.state.plots[:25]:
        plot.stage = module.STAGE_AUTOMATED
    module.achievements_open = True
    module.render_achievements()
    panel = game_env.elements["achievements-panel"]
    earned = [c for c in panel.children if getattr(c, "className", "") == "achievement-earned"]
    assert earned, "an earned row is rendered"
    row = earned[0]
    assert row.dataset.achievementId
    assert any(getattr(ch, "className", "") == "achievement-card-label" and ch.innerText for ch in row.children)


def test_minigame_run_active_reports_a_running_timed_game(game_env):
    module = game_env.module
    mg = module.minigames
    assert module.minigame_run_active() is False
    mg.blitz_active = True
    try:
        assert module.minigame_run_active() is True
    finally:
        mg.blitz_active = False
    assert module.minigame_run_active() is False
    game = mg.NEW_GAMES[0]
    game.active = True
    try:
        assert module.minigame_run_active() is True
    finally:
        game.active = False
    assert module.minigame_run_active() is False
