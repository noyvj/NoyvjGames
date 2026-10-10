"""The pledge, applied to the Daily Market (M-4b-9): no daily-login reward, no streak, no penalty for a missed day, no
timer, no gate, and the only clock read is the date the view asks the engine to build (market.js)."""

import json
import re
from pathlib import Path

import pytest

import game
import pledge
from .bot import call, step

GAME_DIR = Path(__file__).resolve().parent.parent
TODAY = "2026-10-11"
BANNED = re.compile(r"\b(" + "|".join(re.escape(w) for w in pledge.BANNED_WORDS) + r")\b", re.IGNORECASE)
PRESSURE_KEYS = re.compile(r"streak|missed|miss|bonus|reward|login|countdown|cooldown|expire|until|remaining|deadline|ends|timer|stamp|lock", re.I)


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    game._today = None
    yield
    game.stall.__init__()
    game._today = None


def keys(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path + "/" + str(k)
            yield from keys(v, path + "/" + str(k))
    elif isinstance(node, list):
        for v in node:
            yield from keys(v, path)


def finish(date):
    view = call(action="start_market", date=date, today=TODAY)
    while view["phase"] == "open":
        view = step(view)
    return view


def test_the_market_view_has_no_streak_reward_countdown_or_deadline_field():
    v = call(action="open", today=TODAY)
    assert not [k for k in keys(v["market"]) if PRESSURE_KEYS.search(k.split("/")[-1])], list(keys(v["market"]))
    v = finish("2026-10-05")
    assert not [k for k in keys(v["market"]) if PRESSURE_KEYS.search(k.split("/")[-1])], list(keys(v["market"]))


def test_a_market_pays_no_reward_for_opening_it_or_for_opening_it_every_day():
    call(action="open", today=TODAY)
    for date in ("2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"):         # four days in a row, then compare
        finish(date)
    assert game.stall.coins == 0 and game.stall.renown == 0 and game.stall.days_played == 0
    assert game.stall.tally == {k: 0 for k in game.TALLY_KEYS} and game.stall.flags == [] and game.stall.visits == {}
    assert game.stall.upgrades == [] and game.stall.decor_owned == [] and game.stall.best == {"combo": 0, "day_coins": 0}
    save = game.get_state()
    assert set(save) == {"market_days"} and len(save["market_days"]) == 4


def test_skipping_days_costs_nothing_and_the_dates_can_be_played_in_any_order():
    call(action="open", today=TODAY)
    finish("2026-10-10")                       # yesterday first
    finish("2026-10-03")                       # then a long-ago day
    finish("2026-10-11")                       # then today
    tally = call(action="open", today=TODAY)["market"]["tally"]
    assert tally == {"open": 11, "played": 3, "perfect": tally["perfect"]}
    assert set(game.get_state()["market_days"]) == {"2026-10-10", "2026-10-03", "2026-10-11"}
    # nothing was gated on having played the day before
    assert call(action="start_market", date="2026-10-07", today=TODAY)["phase"] == "open"


def test_the_market_save_holds_only_the_dates_played_and_small_numbers():
    call(action="open", today=TODAY)
    finish("2026-10-05")
    call(action="start_market", date="2026-10-06", today=TODAY)
    for _ in range(4):
        call(action="crate", family="produce")
    save = json.loads(json.dumps(game.get_state()))
    assert set(save) == {"market_days", "market_day"}
    assert set(save["market_day"]) == {"date", "day"} and save["market_day"]["date"] == "2026-10-06"
    assert not [k for k in keys(save) if PRESSURE_KEYS.search(k.split("/")[-1])]
    for rec in save["market_days"].values():
        assert set(rec) == {"stars", "served", "total", "coins"}
    text = json.dumps(save)
    assert set(re.findall(r"\d{4}-\d{2}-\d{2}", text)) == {"2026-10-05", "2026-10-06"}      # only the dates played
    assert not re.search(r"\b1[5-9]\d{8}\b", text)                                          # no epoch timestamps


def test_the_open_market_is_exactly_as_left_however_long_the_tab_stays_open():
    call(action="start_market", date="2026-10-05", today=TODAY)
    call(action="crate", family="produce")
    snapshot = json.dumps(game.get_state(), sort_keys=True)
    for _ in range(50):
        call(action="open", today=TODAY)
        game.get_state()
    assert json.dumps(game.get_state(), sort_keys=True) == snapshot


def test_the_only_clock_read_is_in_market_js_and_it_only_names_a_date():
    for name in ("app.js", "settings.js"):
        assert not re.search(r"\bDate\b", (GAME_DIR / name).read_text(encoding="utf-8")), name
    text = (GAME_DIR / "market.js").read_text(encoding="utf-8")
    assert text.count("new Date().toISOString()") == 1 and "function today()" in text
    assert not re.search(r"setInterval|setTimeout|requestAnimationFrame|performance\.now|Date\.now|getTime\(\)|localStorage|fetch\(", text)
    for name in ("app.js", "settings.js", "market.js"):
        assert not re.search(r"setInterval|performance\.now|Date\.now", (GAME_DIR / name).read_text(encoding="utf-8")), name
    assert 'window.PocketBazaarMarket.today()' in (GAME_DIR / "app.js").read_text(encoding="utf-8")


def test_the_words_the_pledge_rules_out_are_not_in_the_market_text_either():
    text = (GAME_DIR / "market.js").read_text(encoding="utf-8")
    found = [s for s in re.findall(r'"((?:[^"\\\n]|\\.)*)"', text) if BANNED.search(s)]
    assert not found, found
    for name in ("market.py", "marketbot.py"):
        assert not BANNED.search(" ".join(re.findall(r'"([^"\n]*)"', (GAME_DIR / name).read_text(encoding="utf-8")))), name


def test_the_market_panel_text_promises_nothing_extra_and_no_streaks():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    panel = html[html.index('id="market-panel"'):html.index("</section>", html.index('id="market-panel"'))]
    assert "pays nothing extra" in panel and "no streaks" in panel and "every past day stays open" in panel
    assert not BANNED.search(panel)


def test_the_about_page_describes_the_market_in_the_pledges_own_terms():
    how = " ".join(call(action="open")["about"]["how"])
    assert "Daily Market" in how and "pays nothing extra" in how and "Skipping a day costs nothing" in how
