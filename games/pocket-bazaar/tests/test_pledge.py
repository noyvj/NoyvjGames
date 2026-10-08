"""The pledge (planning/pocket-bazaar-plan.md section 1) as tests. Each rule the owner asked for has a check here, so
a later change that slides toward the genre's habits fails the build instead of shipping."""

import ast
import json
import re
from pathlib import Path

import pytest

import game
import pledge
import shop
from .bot import call, play_day

GAME_DIR = Path(__file__).resolve().parent.parent
BANNED = re.compile(r"\b(" + "|".join(re.escape(w) for w in pledge.BANNED_WORDS) + r")\b", re.IGNORECASE)
ENGINE = [p for p in sorted(GAME_DIR.glob("*.py")) if p.name != "pledge.py"]


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


# ---- 1. no banned words in anything the player can read -------------------------------------------------------
def _py_strings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr):
            docstrings.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


def _js_strings(text):
    return re.findall(r'"((?:[^"\\\n]|\\.)*)"', text)


def _html_text(text):
    text = re.sub(r"<!--.*?-->|<script.*?</script>|<style.*?</style>", "", text, flags=re.S)
    return re.findall(r">([^<]+)<", text) + re.findall(r'(?:aria-label|title|content|placeholder)="([^"]*)"', text)


def _json_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _json_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _json_strings(v)


def test_the_words_the_pledge_rules_out_appear_nowhere_but_the_pledge_itself():
    found = []
    for path in ENGINE:
        found += [(path.name, s) for s in _py_strings(path) if BANNED.search(s)]
    for name in ("app.js", "settings.js"):
        found += [(name, s) for s in _js_strings((GAME_DIR / name).read_text(encoding="utf-8")) if BANNED.search(s)]
    found += [("index.html", s) for s in _html_text((GAME_DIR / "index.html").read_text(encoding="utf-8")) if BANNED.search(s)]
    for name in ("changelog.json", "achievements.json"):
        path = GAME_DIR / name
        if path.exists():
            found += [(name, s) for s in _json_strings(json.loads(path.read_text(encoding="utf-8"))) if BANNED.search(s)]
    assert not found, found


def test_the_about_page_shows_the_pledge_and_the_pledge_is_the_only_place_that_names_the_banned_things():
    view = call(action="open")
    assert view["about"]["pledge"] == list(pledge.PLEDGE) and len(pledge.PLEDGE) >= 8
    assert BANNED.search(" ".join(pledge.PLEDGE))               # it names them, to promise not to
    assert "never do" in view["about"]["pledge_heading"]


# ---- 2. one currency, earned only by play ------------------------------------------------------------------
def test_there_is_exactly_one_currency_and_the_shop_prices_are_only_in_coins():
    views = [call(action="open"), call(action="start_day")]
    for v in views:
        money = [k for k in v if re.search(r"coin|gem|cash|money|price|usd|dollar|token|ticket|crystal", k)]
        assert money == ["coins"], money
    for u in shop.UPGRADES:
        assert set(u) == {"id", "name", "cost", "blurb"} and isinstance(u["cost"], int)


def test_coins_only_ever_change_through_play():
    """Opening and closing the stall, reloading and asking again never adds a coin; only served customers, chains,
    sales and sweeps (with the polish) do."""
    assert call(action="open")["coins"] == 0
    for _ in range(5):
        call(action="start_day")
        game.load_state(json.loads(json.dumps(game.get_state())))
        assert call(action="open")["coins"] == 0
    day = game.stall.day
    day.queue, day.total = [], 0
    game.stall.close_day()
    assert game.stall.coins == 0                              # a day with nobody served pays nothing


def test_no_page_script_can_reach_a_payment_or_the_network_beyond_its_own_files():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    assert "https://" not in app and "http://" not in app and "XMLHttpRequest" not in app and "sendBeacon" not in app
    fetched = set(re.findall(r'fetch\(\s*([^,)]+)', app))
    assert fetched <= {'"changelog.json"', 'ENGINE_MODULES[i]', '"game.py"'}, fetched
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert "<form" not in html and "stripe" not in html.lower() and "paypal" not in html.lower()


# ---- 3. no clock anywhere in the game ---------------------------------------------------------------------------
def test_no_game_code_reads_the_real_clock():
    for path in ENGINE + [p for p in (GAME_DIR / "tests").glob("bot.py")]:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\b(import|from)\s+(time|datetime|calendar|random|sched|threading)\b", text), path.name
        assert not re.search(r"\b(time|datetime)\.(time|now|today|sleep|monotonic)\b", text), path.name
    for name in ("app.js", "settings.js"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert not re.search(r"\bDate\b|performance\.now|setInterval|requestAnimationFrame|Intl\.DateTimeFormat", text), name


def test_the_only_timeouts_are_tiny_display_effects_that_never_touch_the_game():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    matches = re.findall(r"setTimeout\(function \(\) \{(.*?)\}, (\d+)\);", app, flags=re.S)
    assert len(matches) == app.count("setTimeout(") and matches
    for body, delay in matches:
        assert int(delay) <= 700, body
        assert "send(" not in body and "engine." not in body and "deliver" not in body


def test_patience_never_moves_without_a_player_action():
    call(action="start_day")
    before = json.dumps(game.get_state(), sort_keys=True)
    for _ in range(50):
        call(action="open")
        game.get_state()
    assert json.dumps(game.get_state(), sort_keys=True) == before


def test_a_day_left_open_for_ever_is_exactly_as_it_was():
    call(action="start_day")
    call(action="crate", family="produce")
    snapshot = json.dumps(game.get_state(), sort_keys=True)
    data = json.loads(snapshot)
    game.stall.__init__()
    game.load_state(data)
    assert json.dumps(game.get_state(), sort_keys=True) == snapshot


# ---- 4. the save holds nothing about time, cooldowns or locks ----------------------------------------------------
def _keys(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path + "/" + str(k)
            yield from _keys(v, path + "/" + str(k))
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v, path)


def test_the_save_has_no_timestamps_cooldowns_or_lockouts_in_any_state_of_play():
    states = [game.get_state()]
    for _ in range(3):
        call(action="start_day")
        for _step in range(6):
            call(action="crate", family="produce")
        states.append(game.get_state())                                   # mid-day, with a shelf day too
        game.stall.coins = 2000
        game.stall.day.queue, game.stall.day.total = [], 0
        game.stall.close_day()
        for u in shop.UPGRADES:
            call(action="buy", id=u["id"])
        states.append(game.get_state())
    bad = re.compile(r"time|date|stamp|cooldown|expire|until|ready|energy|life|lives|gem|premium|streak_day|login|daily|refill|wait_?until", re.I)
    for state in states:
        assert not [k for k in _keys(state) if bad.search(k.split("/")[-1])], [k for k in _keys(state)]
        text = json.dumps(state)
        assert not re.search(r"\d{4}-\d{2}-\d{2}", text) and not re.search(r"\b1[5-9]\d{8}\b", text)


def test_the_view_has_no_lockout_or_countdown_field_either():
    v = call(action="start_day")
    flat = " ".join(_keys(v)).lower()
    for word in ("countdown", "cooldown", "expires", "energy", "lives", "gems", "login", "daily"):
        assert word not in flat


# ---- 5. nothing nags -------------------------------------------------------------------------------------------
def test_there_are_no_leave_prompts_notifications_or_other_nags():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    for needle in ("beforeunload", "onbeforeunload", "Notification", "requestPermission", "serviceWorker.ready", "alert(", "confirm(", "prompt("):
        assert needle not in app, needle
    assert "beforeunload" not in html


def test_the_only_questions_the_game_ever_asks_are_selling_a_high_tier_good_and_erasing_everything():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    ids = set(re.findall(r'askThen\("([^"]+)"', app))
    assert ids == {"pocket-bazaar-sell-high", "pocket-bazaar-reset"}
    assert 'allowSkip: id !== "pocket-bazaar-reset"' in app


def test_the_only_ad_is_the_hubs_labelled_footer_bar_outside_the_game():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert html.count("adsbygoogle") == 1 and html.count('<div class="ad-bar') == 1
    game_part = html[html.index('<main id="game">'):html.index("</main>")]
    assert "adsbygoogle" not in game_part and "ad-bar" not in game_part
    assert "Advertisement" in html


def test_a_fresh_player_can_finish_a_day_with_nothing_bought():
    v, _steps = play_day()
    assert v["summary"]["served"] >= 5 and game.stall.upgrades == []


def test_no_festival_or_day_is_gated_on_a_wait_or_on_having_played_yesterday():
    """Day N+1 opens the moment day N is finished, however many real days have gone by (there are none in the save)."""
    for n in range(1, 8):
        v = call(action="start_day")
        assert v["phase"] == "open" and v["day"]["number"] == n
        play_day(v)
    assert call(action="start_day")["day"]["number"] == 8
