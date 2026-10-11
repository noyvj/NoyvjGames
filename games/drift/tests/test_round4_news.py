"""GI-20: the optional town-news ticker."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def test_every_pool_has_lines_and_none_repeat(game_env):
    m = game_env.module
    lines = [line for pool in m.NEWS_HEADLINES.values() for line in pool]
    assert set(m.NEWS_HEADLINES) == {"stable", "strained", "critical"}
    assert all(len(pool) >= 8 for pool in m.NEWS_HEADLINES.values())
    assert len(lines) == len(set(lines))
    assert all(10 < len(line) <= 140 and line.endswith(".") for line in lines)


def test_the_humour_is_about_institutions_never_the_people_arriving(game_env):
    m = game_env.module
    text = " ".join(
        [line for pool in m.NEWS_HEADLINES.values() for line in pool]
        + [m.NEWS_NET_POSITIVE, m.NEWS_THRIVING, m.NEWS_SECOND_WAVE]
    ).lower()
    for word in ("migrant", "refugee", "illegal", "flood of", "swarm", "invade", "burden", "problem people", "crisis of"):
        assert word not in text
    assert re.search(r"\bsurge\b", text) is None


def test_the_headline_is_deterministic_and_changes_round_to_round(game_env):
    m = game_env.module
    region = game_env.region
    first = m.news_headline(region)
    assert m.news_headline(region) == first
    seen = set()
    for _ in range(6):
        seen.add(m.news_headline(region))
        game_env.advance_round()
    assert len(seen) >= 5


def test_the_pool_follows_the_strain_level(game_env):
    m = game_env.module
    region = game_env.region
    region.total_arrivals = 100.0  # no capacity: critical
    assert m.news_headline(region) in m.NEWS_HEADLINES["critical"]
    region.capacity["housing"] = 80.0  # shortfall 20%: strained is above 25%, so stable
    assert region.strain_level() == "stable" and m.news_headline(region) in m.NEWS_HEADLINES["stable"]
    region.capacity["housing"] = 60.0  # 40% shortfall
    assert region.strain_level() == "strained" and m.news_headline(region) in m.NEWS_HEADLINES["strained"]


def test_milestone_lines_come_the_round_after_and_the_wave_line_while_it_runs(game_env):
    m = game_env.module
    region = game_env.region
    region.round_number = 9
    region.net_positive_round = 8
    assert m.news_headline(region) == m.NEWS_NET_POSITIVE
    region.net_positive_round = 3
    region.thriving_round = 8
    assert m.news_headline(region) == m.NEWS_THRIVING
    region.thriving_round = None
    region.second_wave_status = "active"
    assert m.news_headline(region) == m.NEWS_SECOND_WAVE


def test_render_writes_the_line_and_it_is_never_saved(game_env):
    game_env.module.render()
    assert game_env.elements["news-ticker"].innerText == game_env.module.news_headline(game_env.region)
    assert "news" not in " ".join(game_env.module.get_state())


def test_settings_toggle_defaults_off_and_is_reset_by_reset_to_default():
    js = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert 'applyFlag(NEWS_KEY, "news-ticker-on", readFlag(NEWS_KEY))' in js  # absent key reads false
    assert 'applyFlag(NEWS_KEY, "news-ticker-on", false)' in js
    assert ".news-ticker { display: none;" in css and "html.news-ticker-on .news-ticker { display: block; }" in css
    assert 'id="news-ticker-toggle-button"' in html and "Town news: Off" in html
