"""Dead Reckoning's lazy content packs (planning/LAZY-LOAD-REPORT.md, TODO LZ-5 pilot): modules.json is valid, the core boots and works
with every pack missing, each mode works once its pack is present, and a save that mentions a pack never breaks or changes when the
pack cannot load. The "lazy" runs are subprocesses with DR_LAZY=1 (charts.py then imports a chapter only on demand, the way the page
does) and the pack modules blocked, so they cannot be confused with the eager mode every other test file uses."""

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parent.parent
MANIFEST = json.loads((GAME_DIR / "modules.json").read_text(encoding="utf-8"))
PACKS = {p["id"]: p for p in MANIFEST["packs"]}
PACK_MODULES = sorted(Path(p["url"]).stem for p in MANIFEST["packs"])
ID_RE = re.compile(r"^[a-z0-9_-]{1,40}$")
TOLERANCE = 3                    # the loader refuses a body more than three times its listed size (plus 32 KB)
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def _boot_modules():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    return [m for m in re.findall(r'"([a-z_]+)\.py"', block) if m != "lazy_packs"]


def _precache():
    text = (ROOT / "sw.js").read_text(encoding="utf-8")
    return set(re.findall(r'"(games/dead-reckoning/[^"]+)"', text.split("PRECACHE_URLS")[1].split("];")[0]))


# --- modules.json -----------------------------------------------------------------------------------
def test_modules_json_is_valid():
    assert MANIFEST["version"] == 1 and MANIFEST["game"] == "dead-reckoning"
    ids = [p["id"] for p in MANIFEST["packs"]]
    assert len(ids) == len(set(ids)), "pack ids must be unique"
    for p in MANIFEST["packs"]:
        assert ID_RE.match(p["id"]), p["id"]
        assert p["kind"] == "python" and p["label"] and p["modes"]
        target = GAME_DIR / p["url"]
        assert target.is_file() and target.resolve().parent == GAME_DIR, "every pack file lives in the game folder: " + p["url"]
        real = target.stat().st_size
        assert p["bytes"] > 0 and real <= p["bytes"] * TOLERANCE + 32768 and p["bytes"] <= real * TOLERANCE, (p["id"], p["bytes"], real)
        for need in p.get("needs", []):
            assert need in PACKS, f"{p['id']} needs the unknown pack {need}"
    for p in MANIFEST["packs"]:                      # no cycles
        seen, todo = set(), list(p.get("needs", []))
        while todo:
            n = todo.pop()
            assert n != p["id"], f"{p['id']} needs itself"
            if n not in seen:
                seen.add(n)
                todo += PACKS[n].get("needs", [])


def test_no_pack_file_is_in_the_service_worker_precache_and_every_core_file_is():
    precache = _precache()
    for p in MANIFEST["packs"]:
        assert "games/dead-reckoning/" + p["url"] not in precache, f"{p['url']} is a lazy pack: it must not be in PRECACHE_URLS"
    assert "games/dead-reckoning/modules.json" not in precache
    for module in _boot_modules():
        assert f"games/dead-reckoning/{module}.py" in precache, f"{module}.py is fetched at boot, so it is precached"


def test_the_chart_index_is_current():
    result = subprocess.run([sys.executable, str(GAME_DIR / "tools" / "build_charts_index.py"), "--check"], capture_output=True)
    assert result.returncode == 0, "charts_index.py is out of date: run python3 tools/build_charts_index.py"


def test_the_core_never_imports_a_pack_at_the_top_level():
    for name in _boot_modules() + ["game"]:
        tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
        for node in tree.body:
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) else []
            for imported in names:
                assert imported not in PACK_MODULES, f"{name}.py imports the lazy pack {imported} at import time"


def test_the_page_and_the_desktop_page_include_the_loader_before_app_js():
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text(encoding="utf-8")
        tag = '<script src="../../shared/lazy-packs.js" data-game-id="dead-reckoning" data-manifest="modules.json"></script>'
        assert tag in html and html.index(tag) < html.index('src="app.js"'), page


# --- running the engine with packs missing or arriving -------------------------------------------------
def run_lazy(body):
    """Run a script in a fresh interpreter in lazy mode with every pack module blocked; the script prints one JSON value."""
    prelude = f"""
import json, sys
sys.path.insert(0, {str(GAME_DIR)!r})
PACKS = {PACK_MODULES!r}
def block():
    for m in PACKS:
        sys.modules[m] = None
def arrive(*names):
    for m in names:
        sys.modules.pop(m, None)
block()
import game
def call(action, **fields):
    return json.loads(game.handle(json.dumps(dict(fields, action=action))))
"""
    env = dict(os.environ, DR_LAZY="1", PYTHONPATH="")
    result = subprocess.run([sys.executable, "-c", prelude + body], capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_the_game_boots_and_plays_the_first_chapter_with_every_pack_missing():
    out = run_lazy("""
v = call("open")
first = v["chart"]["id"]
v2 = call("add_leg"); v2 = call("sail")
print(json.dumps({"first": first, "phase": v2["phase"], "stars": v2["reveal"]["stars"] in (0, 1, 2, 3),
                  "loaded": [c["loaded"] for c in v["picker"]], "totals": [c["total"] for c in v["picker"]],
                  "names_ok": all(ch["charts"] for ch in v["picker"]), "progress": v["progress"]["total"],
                  "ach": len(v["achievements"]), "info": bool(v["info"]), "daily": v["daily"]}))
""")
    assert out["first"] == "open-01" and out["phase"] == "reveal" and out["stars"]
    assert out["loaded"] == [True] + [False] * 6, "only the core chapter is on the page"
    assert sum(out["totals"]) == out["progress"] == 36
    assert out["names_ok"] and out["ach"] == 15 and out["info"]


def test_with_packs_missing_other_chapters_practice_and_daily_decline_politely_and_change_nothing():
    out = run_lazy("""
v = call("open")
before = json.dumps(v["svg"]), v["chart"]["id"]
res = {}
for label, req in [("wind", dict(chart_id="wind-01")), ("practice", dict(difficulty=1, seed=5)), ("two", dict(difficulty=2, two=True, seed=9)),
                   ("code", dict(code="DR1-ABC12")), ("daily", dict(date="2026-10-05", today="2026-10-20"))]:
    action = {"wind": "start", "practice": "practice", "two": "practice", "code": "practice", "daily": "start_daily"}[label]
    r = call(action, **req)
    res[label] = {"error": r.get("error"), "note": r.get("note", ""), "chart": r.get("chart", {}).get("id")}
# "wind" is not unlocked in a new game, so it answers with that; unlock it to test the pack note
import state
game.meta["charts"].update({cid: dict(state.new_record(), stars=1) for cid in ("open-01", "open-02", "open-03", "open-04")})
r = call("start", chart_id="wind-01")
res["wind_unlocked"] = {"error": r.get("error"), "note": r.get("note", ""), "chart": r["chart"]["id"]}
print(json.dumps(res))
""")
    for label in ("practice", "two", "code", "daily"):
        assert "has not finished loading" in out[label]["note"], (label, out[label])
        assert out[label]["chart"] == "open-01", label
    assert out["wind"]["error"] == "that chapter is not open yet"
    assert out["wind_unlocked"]["note"] and out["wind_unlocked"]["chart"] == "open-01", "an unavailable chapter leaves the current chart alone"


def test_needs_names_the_packs_a_request_needs_and_changes_nothing():
    out = run_lazy("""
n = lambda **r: json.loads(game.needs(json.dumps(r)))
print(json.dumps({
  "open": n(action="open"), "start1": n(action="start", chart_id="open-02"), "start7": n(action="start", chart_id="two-01"),
  "start4": n(action="start", chart_id="fog-02"), "practice": n(action="practice", difficulty=3),
  "two": n(action="practice", difficulty=3, two=True), "code": n(action="practice", code="dr2-1k9x2"),
  "codeT": n(action="practice", code="DR3T-1K9X2"), "daily": n(action="start_daily", date="2026-10-05"),
  "plain": n(action="add_leg"), "junk": n(action="start", chart_id=5), "bad": json.loads(game.needs("not json"))}))
""")
    assert out["open"] == [] and out["start1"] == [] and out["start7"] == ["chapter-ships"] and out["start4"] == ["chapter-fog"]
    assert out["practice"] == ["practice"] and out["two"] == ["practice", "two-ships"] and out["code"] == ["practice"]
    assert out["codeT"] == ["practice", "two-ships"] and out["daily"] == ["practice"]
    assert out["plain"] == [] and out["junk"] == [] and out["bad"] == []


def test_each_mode_works_once_its_pack_arrives():
    out = run_lazy("""
import state
game.meta["charts"].update({cid: dict(state.new_record(), stars=1) for cid in ("open-01", "open-02", "open-03", "open-04")})
res = {}
chapters = [("chapter-wind", "charts_wind", "wind-01", "wind"), ("chapter-fixes", "charts_fixes", "fix-01", "fixes"), ("chapter-fog", "charts_fog", "fog-01", "fog"),
            ("chapter-tides", "charts_tides", "tide-01", "tides"), ("chapter-compass", "charts_compass", "comp-01", "compass"),
            ("chapter-ships", "charts_two", "two-01", "ships")]
for ch, module, cid, chapter_id in chapters:
    # open every gate in the records, then let the chapter's pack arrive
    for c in game.charts.CHAPTERS:
        for stub in c["charts"]:
            game.meta["charts"][stub["id"]] = dict(state.new_record(), stars=1)
    arrive(module)
    r = call("start", chart_id=cid)
    v = call("add_leg")
    res[ch] = {"chart": r["chart"]["id"], "note": r["note"], "legs": len(v["legs"]) + len((v.get("fleet") or {"ships": []})["ships"]),
               "loaded": [c["loaded"] for c in v["picker"] if c["id"] == chapter_id][0], "svg": "<svg" in v["svg"]}
arrive("genmake")
p = call("practice", difficulty=2, seed=11)
res["practice"] = {"id": p["chart"]["id"], "practice": bool(p["chart"]["practice"])}
code = p["chart"]["practice"]["code"]
res["code_reopen"] = call("practice", code=code)["chart"]["id"]
t = call("practice", difficulty=1, two=True, seed=3)
res["two_without_pack"] = {"note": t["note"], "chart": t["chart"]["id"]}
arrive("gentwo")
t = call("practice", difficulty=1, two=True, seed=3)
res["two"] = {"id": t["chart"]["id"], "two": t["chart"]["two"], "fleet": bool(t["fleet"])}
d = call("start_daily", date="2026-10-05", today="2026-10-20")
res["daily"] = d["chart"]["name"]
print(json.dumps(res))
""")
    first = {"chapter-wind": "wind-01", "chapter-fixes": "fix-01", "chapter-fog": "fog-01", "chapter-tides": "tide-01",
             "chapter-compass": "comp-01", "chapter-ships": "two-01"}
    for ch, cid in first.items():
        assert out[ch]["chart"] == cid, (ch, out[ch])
        assert not out[ch]["note"] and out[ch]["loaded"] and out[ch]["svg"] and out[ch]["legs"] >= 1, (ch, out[ch])
    assert out["practice"]["practice"] and out["code_reopen"] == out["practice"]["id"]
    assert "has not finished loading" in out["two_without_pack"]["note"] and out["two_without_pack"]["chart"] == out["practice"]["id"]
    assert out["two"]["two"] and out["two"]["fleet"] and out["daily"] == "Daily Chart 5"


# --- saves --------------------------------------------------------------------------------------------
FAKE_LOADER = """
import asyncio, types
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
fake = types.ModuleType("lazy_packs")
fake.have = set()
fake.outcome = "ok"        # "ok": the packs arrive; "fail": they do not
fake.asked = []
fake.available = lambda: True
fake.missing = lambda ids: [i for i in ids if i not in fake.have]
fake.used = lambda: sorted(fake.have)
async def require(*ids):
    fake.asked.append(list(ids))
    if fake.outcome == "fail":
        return {"ok": False, "loaded": [], "failed": [{"id": i, "code": "network", "message": "Could not reach the server."} for i in ids], "message": "Could not reach the server."}
    for i in ids:
        fake.have.add(i)
        arrive({"chapter-wind": "charts_wind", "chapter-fog": "charts_fog", "practice": "genmake", "two-ships": "gentwo"}.get(i, "none"))
    return {"ok": True, "loaded": list(ids), "failed": [], "message": ""}
fake.require = require
fake.spawn = lambda coro: loop.create_task(coro)
sys.modules["lazy_packs"] = fake
SAVE = {"schema": 1, "packs_used": ["chapter-wind", "practice"],
        "meta": {"charts": {"wind-01": {"stars": 2, "attempts": 3, "best_error_nm": 0.4}, "open-01": {"stars": 3, "attempts": 1}}, "practice_seeds_played": 4},
        "run": {"chart_id": "wind-02", "legs": [{"heading": 45, "speed": 5.0, "hours": 2.0}], "allow": False}}
"""


def test_a_save_on_a_lazy_chapter_is_fetched_through_require_and_then_restored():
    out = run_lazy(FAKE_LOADER + """
game.load_state(SAVE)
early = {"run_now": game.run["chart_id"] if game.run else None, "held": game._held["run"] is not None}
mid = game.get_state()                       # saved while the pack is still on its way: the run and the pack ids are written back
loop.run_until_complete(game.load_settled())
v = call("open")
final = game.get_state()
print(json.dumps({"early": early, "asked": fake.asked, "mid_run": mid.get("run", {}).get("chart_id"), "mid_packs": mid.get("packs_used"),
                  "chart": v["chart"]["id"], "legs": v["legs"], "allow": v["allow"], "records": sorted(game.meta["charts"]),
                  "stars": game.meta["charts"]["wind-01"]["stars"], "final_packs": final.get("packs_used"), "held": game._held["run"]}))
""")
    assert out["asked"] == [["chapter-wind", "practice"]], "the packs the save names are fetched in one soft require, before anything is restored"
    assert out["early"] == {"run_now": None, "held": True}
    assert out["mid_run"] == "wind-02" and out["mid_packs"] == ["chapter-wind", "practice"]
    assert out["chart"] == "wind-02" and out["legs"] == [{"heading": 45, "speed": 5.0, "hours": 2.0}] and out["allow"] is False
    assert out["stars"] == 2 and "open-01" in out["records"] and out["held"] is None
    assert out["final_packs"] == ["chapter-wind", "practice"]


def test_a_save_whose_pack_cannot_load_keeps_its_records_and_is_written_back_unchanged():
    out = run_lazy(FAKE_LOADER + """
fake.outcome = "fail"
game.load_state(SAVE)
loop.run_until_complete(game.load_settled())
v = call("open")                              # the page still opens on a core chart, and tells the player in plain words
state_now = game.get_state()
print(json.dumps({"chart": v["chart"]["id"], "note": v["note"], "stars": game.meta["charts"]["wind-01"]["stars"],
                  "saved_run": state_now.get("run"), "saved_packs": state_now.get("packs_used")}))
""")
    assert out["chart"] == "open-02" and "could not be loaded" in out["note"] and "Nothing in the save was changed" in out["note"]
    assert out["stars"] == 2, "the records are applied from the index even when the chapter's pack is missing"
    assert out["saved_run"] == {"chart_id": "wind-02", "legs": [{"heading": 45, "speed": 5.0, "hours": 2.0}], "allow": False}
    assert out["saved_packs"] == ["chapter-wind", "practice"]


def test_an_old_save_without_packs_used_still_names_the_pack_its_run_needs():
    out = run_lazy(FAKE_LOADER + """
old = {k: v for k, v in SAVE.items() if k != "packs_used"}
old["run"] = {"chart_id": "practice-2t-1k9x2", "legs": [{"heading": 90, "speed": 4.0, "hours": 1.0}]}
game.load_state(old)
loop.run_until_complete(game.load_settled())
print(json.dumps({"asked": fake.asked}))
""")
    assert out["asked"] == [["practice", "two-ships"]]


def test_a_junk_packs_used_is_ignored_and_never_raises():
    out = run_lazy(FAKE_LOADER + """
junk = dict(SAVE, packs_used=["Chapter Wind", 5, None, "x" * 99, "ok-id", "ok-id", {"a": 1}])
game.load_state(junk)
loop.run_until_complete(game.load_settled())
game.load_state({"packs_used": "chapter-wind", "run": "nonsense", "meta": 5})
print(json.dumps({"asked": fake.asked, "saved": game.get_state().get("packs_used")}))
""")
    assert out["asked"][0] == ["ok-id", "chapter-wind"], "bad ids are dropped, the rest kept in order, plus the pack the run needs"
    assert out["saved"] and all(ID_RE.match(p) for p in out["saved"])


def test_a_player_who_starts_playing_before_the_late_load_finishes_keeps_what_they_started():
    out = run_lazy(FAKE_LOADER + """
game.load_state(SAVE)
call("open"); call("add_leg")                  # the player has already put a leg on the first chart
loop.run_until_complete(game.load_settled())
v = call("open")
print(json.dumps({"chart": v["chart"]["id"], "legs": len(v["legs"]), "held": game._held["run"] is not None}))
""")
    assert out["chart"] == "open-02" and out["legs"] == 1


def test_get_state_lists_the_loaded_packs_and_a_state_without_the_loader_has_none():
    out = run_lazy("""
print(json.dumps({"none": "packs_used" in game.get_state()}))
""")
    assert out["none"] is False
