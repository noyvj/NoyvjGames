"""Round 3 K-section, second group: K-24 naming, K-18 export, K-19 compare,
K-26 par badges, K-31 monument row, K-21 screensaver and K-30 key remap (the
last two are browser code, so those are checked as text)."""

import csv
import io
import json
import re
from pathlib import Path

import archive
import dataexport
import minutes
import monuments
import naming
import par
import save
import sim
import statlog

GAME_DIR = Path(__file__).resolve().parent.parent
SEASON_SECONDS = {"tribal": 10.0, "agrarian": 10.0, "classical": 12.0, "medieval": 12.0,
                  "industrial": 14.0, "digital": 16.0, "space": 18.0, "relay": 20.0}


# --- K-24 naming -----------------------------------------------------------
def test_sanitise_drops_markup_controls_and_symbols():
    assert naming.sanitise("  Reed <b>Ford</b>  & co ") == "Reed Ford co"
    assert naming.sanitise("a​b\x00c‮d") == "abcd"
    assert naming.sanitise("Zoë’s Rest-3.") == "Zoë’s Rest-3"
    assert naming.sanitise("---") == "" and naming.sanitise(None) == "" and naming.sanitise(5) == ""
    assert len(naming.sanitise("x" * 200)) == naming.MAX_LEN


def test_set_get_and_junk_in_ui():
    ui = {}
    assert naming.get(ui) == ""
    assert naming.set_name(ui, " Ash Hollow ") == "Ash Hollow" and naming.get(ui) == "Ash Hollow"
    ui[naming.KEY] = ["junk"]
    assert naming.get(ui) == ""
    naming.set_name(ui, "Bay")
    assert naming.set_name(ui, "   ") == "" and naming.KEY not in ui


def test_every_era_suggests_valid_varied_names():
    for era in sim.ERA_ORDER:
        names = {naming.suggest(era, seed) for seed in range(300)}
        assert len(names) >= 40, era
        assert all(n == naming.sanitise(n) and 3 <= len(n) <= naming.MAX_LEN for n in names)
    assert naming.suggest("tribal", 7) == naming.suggest("tribal", 7)
    assert naming.suggest("mars", "x")  # unknown era / seed degrade, never raise


def test_name_helpers():
    assert naming.title("") == "Continuum" and naming.title("Bay") == "Bay"
    assert naming.with_name("Bay", "Founded") == "Bay: Founded" and naming.with_name("", "Founded") == "Founded"


def test_naming_ui_flow(game_env):
    e = game_env
    e.elements["founders-toggle-button"].dispatch("click", None)
    e.elements["settlement-name-suggest-button"].dispatch("click", None)
    suggestion = e.elements["settlement-name-input"].value
    assert suggestion and "Suggested" in e.elements["settlement-name-status"].innerText
    assert e.module.settlement_name() == ""  # a suggestion is not saved until Save
    e.elements["settlement-name-input"].value = "  Reed <i>Ford</i> "
    e.elements["settlement-name-save-button"].dispatch("click", None)
    assert e.module.settlement_name() == "Reed Ford"
    assert e.elements["settlement-name-input"].value == "Reed Ford"
    assert e.elements["founded-display"].innerText.startswith("Reed Ford: Founded")
    assert e.module.get_state()["ui"]["settlement_name"] == "Reed Ford"
    e.elements["settlement-name-input"].value = ""
    e.elements["settlement-name-save-button"].dispatch("click", None)
    assert e.module.settlement_name() == "" and "settlement_name" not in e.module.campaign.ui


def test_name_survives_save_load_and_consulting_abandon(game_env):
    e = game_env
    naming.set_name(e.module.campaign.ui, "Otter Rock")
    data = json.loads(json.dumps(e.module.get_state()))
    e.module.campaign.ui.clear()
    assert e.module.load_state(data)
    assert e.module.settlement_name() == "Otter Rock"
    assert e.elements["settlement-name-input"].value == "Otter Rock"
    e.elements["consulting-case-smokestack-button"].dispatch("click", None)
    e.elements["consulting-abandon-button"].dispatch("click", None)
    assert e.module.settlement_name() == "Otter Rock"


def test_name_is_in_the_summary_statement_and_archive_record():
    c = save.Campaign()
    import summary
    data = summary.summary(c)
    assert "settlement of Bay:" in summary.stakeholder_statement(data, None, "Bay")
    assert "the settlement:" in summary.stakeholder_statement(data, None)
    rec = archive.make_record(c, 1, "2026-10-07", name="Bay <b>", researched=3, minutes=12)
    assert rec["name"] == "Bay" and rec["researched"] == 3 and rec["minutes"] == 12
    assert archive.title_of(rec) == "Bay" and archive.title_of({"saved_on": "x"}) == "Continuum"
    assert "3 discoveries" in archive.card_lines(rec) and "12 minutes played" in archive.card_lines(rec)


# --- K-18 export -----------------------------------------------------------
def _history(n=3):
    ui = {}
    c = save.Campaign()
    for _ in range(n):
        ef = c.tree.effects()
        report = c.state.advance_season(ef)
        statlog.record(ui, c.state, ef, report, 0)
    return ui


def test_stats_csv_parses_back_with_one_row_per_season():
    ui = _history(3)
    text = dataexport.stats_csv(ui[statlog.KEY])
    rows = list(csv.reader(io.StringIO(text)))
    assert len(rows) == 4 and rows[0][:3] == ["Year", "Season of year", "Era name"]
    assert len(rows[0]) == 3 + len(statlog.COLUMN_KEYS) and all(len(r) == len(rows[0]) for r in rows)
    assert rows[1][2] == "Tribal" and rows[1][1] == "Spring" and rows[1][0] == "1"
    assert dataexport.stats_csv([]).count("\r\n") == 1  # header only


def test_csv_cells_are_quoted_and_defused():
    assert dataexport.csv_cell('a,"b"') == '"a,""b"""'
    assert dataexport.csv_cell("=1+1") == "'=1+1"
    assert dataexport.csv_cell("@x").startswith("'@") and dataexport.csv_cell("-2+3").startswith("'-")
    assert dataexport.csv_cell(float("nan")) == "" and dataexport.csv_cell(None) == ""
    assert dataexport.csv_cell(2.5) == "2.5" and dataexport.csv_cell(1234567.0) == "1234567"


def test_minutes_csv_and_json_export():
    ui = {}
    minutes.record(ui, "research", "Foraging Lore", "tribal", 1)
    minutes.record(ui, "build", "=cmd,Shelter", "tribal", 5)
    text = dataexport.minutes_csv(ui[minutes.KEY])
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0][0] == "Season" and len(rows) == 3
    assert rows[2][1] == "2" and rows[2][2] == "Spring" and "Foraging" in rows[1][5]
    document = json.loads(dataexport.run_json("Bay", "frontier", True, _history(2)[statlog.KEY], ui[minutes.KEY]))
    assert document["settlement"] == "Bay" and document["scenario"] == "frontier" and document["hard_mode"] is True
    assert len(document["seasons"]) == 2 and isinstance(document["seasons"][0]["population"], int)
    assert len(document["council_minutes"]) == 2
    assert json.loads(dataexport.run_json("", "nope", False, "junk", None))["scenario"] == "standard"


def test_filenames_are_safe():
    assert dataexport.filename("stats", "Reed Ford!", "2026-10-07") == "continuum-reed-ford-stats-2026-10-07.csv"
    assert dataexport.filename("run", "", "bad") == "continuum-settlement-run-undated.json"
    assert dataexport.filename("stats", "éé", "2026-10-07").startswith("continuum-settlement-")


def test_export_buttons_download_through_the_card_helper(game_env, monkeypatch):
    e = game_env
    assert e.module.export_text("stats") is None and e.module.export_text("run") is None
    e.advance_season(3)
    got = []
    monkeypatch.setattr(e.module, "_download_text", lambda text, name, mime: got.append((name, mime, text)) or True)
    e.elements["summary-toggle-button"].dispatch("click", None)
    e.elements["export-stats-button"].dispatch("click", None)
    e.elements["export-run-button"].dispatch("click", None)
    assert [g[1] for g in got] == ["text/csv", "application/json"]
    assert got[0][2].count("\r\n") == 4
    assert "Downloaded" in e.elements["export-status"].innerText
    e.elements["export-minutes-button"].dispatch("click", None)  # no decisions yet
    assert "Nothing to export" in e.elements["export-status"].innerText
    assert e.module.export_text("bogus") is None


# --- K-19 compare ------------------------------------------------------------
def _rec(**over):
    base = {"saved_on": "2026-10-07", "era": "tribal", "seasons": 5, "peak_population": 9, "peak_score": 80.0,
            "rank": "Gold", "scenario": "standard", "hard_mode": False, "achievements": 2}
    base.update(over)
    return archive.clean_record(base)


def test_compare_marks_the_leader_and_signs_the_difference():
    rows = {r["label"]: r for r in archive.compare(_rec(), _rec(era="agrarian", seasons=60, rank="Silver", peak_population=9))}
    assert rows["Seasons played"]["delta"] == "▲ +55" and rows["Seasons played"]["lead"] == "b"
    assert rows["Furthest era"]["lead"] == "b" and rows["Efficiency rank"]["lead"] == "a"
    assert rows["Peak population"]["delta"].endswith("same") and rows["Peak population"]["lead"] is None
    assert rows["Discoveries researched"]["delta"] == "no comparison"
    assert archive.compare(_rec(), {"bad": 1}) == [] and archive.compare(None, _rec()) == []


def test_compare_opening_row_and_optional_fields():
    rows = {r["label"]: r for r in archive.compare(_rec(researched=4, minutes=30), _rec(researched=9, minutes=10, hard_mode=True))}
    assert rows["Discoveries researched"]["delta"] == "▲ +5" and rows["Minutes played"]["lead"] == "a"
    assert rows["Opening"]["delta"] == "different"


def test_optional_record_fields_are_cleaned():
    r = archive.clean_record(dict(_rec(), name="<x>Bay", researched=-5, minutes="a"))
    assert r["name"] == "Bay" and r["researched"] == 0 and "minutes" not in r
    assert "name" not in _rec() and archive.same_settlement(_rec(), _rec())
    assert not archive.same_settlement(_rec(name="A"), _rec(name="B"))


def test_compare_ui_two_picks_and_third_replaces_oldest(game_env, monkeypatch):
    e = game_env
    store = [_rec(seasons=s) for s in (3, 4, 5)]
    monkeypatch.setattr(e.module, "archive_load", lambda: [dict(r) for r in store])
    e.elements["summary-toggle-button"].dispatch("click", None)
    e.elements["archive-compare-0-button"].dispatch("click", None)
    assert "archive-compare-box" not in e.elements
    e.elements["archive-compare-1-button"].dispatch("click", None)
    assert e.elements["archive-compare-box"].children  # the table is built
    assert e.elements["archive-compare-1-button"].attributes["aria-pressed"] == "true"
    e.elements["archive-compare-2-button"].dispatch("click", None)
    assert e.module._compare_picks == [1, 2]
    e.elements["archive-compare-clear-button"].dispatch("click", None)
    assert e.module._compare_picks == []


# --- K-26 par ------------------------------------------------------------------
def test_par_comes_from_the_games_own_tables():
    for scenario in sim.SCENARIOS:
        floor = par.floor_seasons(scenario)
        assert par.par_seasons(scenario) >= floor * 1.2 and par.par_seasons(scenario) % 10 == 0
        assert par.par_minutes(scenario, SEASON_SECONDS) * 60 >= par.floor_seconds_at_top_speed(scenario, SEASON_SECONDS)
    assert par.floor_seasons("fertile") < par.floor_seasons("standard") < par.floor_seasons("frontier")
    assert par.par_seasons("standard") == 910 and par.par_minutes("standard", SEASON_SECONDS) == 75
    assert par.final_era() == "relay"


def test_par_record_is_validated_and_one_shot():
    ui = {}
    assert par.record(ui, 800, 3000.0, "standard")
    assert not par.record(ui, 100, 10.0, "standard")  # never overwritten
    assert par.get(ui) == {"season": 800, "seconds": 3000.0, "scenario": "standard"}
    assert not par.record({}, 800, 3000.0, "standard", already_inherited=True)
    for bad in (None, 5, {}, {"season": True, "seconds": 1, "scenario": "standard"},
                {"season": 5, "seconds": float("nan"), "scenario": "standard"},
                {"season": 5, "seconds": -1, "scenario": "standard"}, {"season": 5, "seconds": 1, "scenario": "x"}):
        assert par.clean(bad) is None
    assert not par.seasons_earned(None) and not par.time_earned("junk", SEASON_SECONDS)


def test_par_badges_by_result():
    quick = {"season": 900, "seconds": 70 * 60.0, "scenario": "standard"}
    slow = {"season": 1200, "seconds": 120 * 60.0, "scenario": "standard"}
    assert par.seasons_earned(quick) and par.time_earned(quick, SEASON_SECONDS)
    assert not par.seasons_earned(slow) and not par.time_earned(slow, SEASON_SECONDS)
    assert any("earned" in line and "Seasons par" in line for line in par.lines("standard", SEASON_SECONDS, quick, 1, 0))
    assert any("not earned" in line for line in par.lines("standard", SEASON_SECONDS, slow, 1, 0))
    assert "Not at the Relay Age yet" in par.lines("standard", SEASON_SECONDS, None, 4, 90.0)[1]


def test_entering_the_last_era_records_par_and_earns_badges(game_env):
    e = game_env
    m = e.module
    assert "par_seasons" not in m.achievement_ids_earned()
    m.state.season = 700
    m.campaign.furthest_era = "relay"
    m.campaign.ui["play_seconds"] = 60 * 60.0
    assert m._record_par()
    earned = m.achievement_ids_earned()
    assert "par_seasons" in earned and "par_time" in earned
    assert not m._record_par()


def test_no_par_in_a_consulting_case(game_env):
    e = game_env
    e.elements["consulting-case-smokestack-button"].dispatch("click", None)
    e.module.campaign.furthest_era = "relay"
    assert not e.module._record_par()
    assert "par_seasons" not in e.module.achievement_ids_earned()


def test_par_lines_show_in_the_summary(game_env):
    e = game_env
    e.elements["summary-toggle-button"].dispatch("click", None)
    texts = [c.innerText for c in e.elements["summary-panel"].children]
    assert any(t.startswith("Par for Standard Start") for t in texts)


# --- K-31 monuments --------------------------------------------------------------
def test_every_achievement_has_a_monument_kind():
    ids = [a["id"] for a in json.loads((GAME_DIR / "achievements.json").read_text())["achievements"]]
    assert len(ids) == 23
    for achievement_id in ids:
        assert achievement_id in monuments.ACHIEVEMENT_KIND, achievement_id
        assert monuments.kind_of(achievement_id) in monuments.KIND_ORDER
    assert monuments.kind_of("nope") == "star"


def test_every_monument_kind_has_a_distinct_drawing():
    drawings = {k: monuments.icon_svg(k, True) for k in monuments.KIND_ORDER}
    assert len(set(drawings.values())) == len(monuments.KIND_ORDER)
    for kind in monuments.KIND_ORDER:
        earned, locked = monuments.icon_svg(kind, True), monuments.icon_svg(kind, False)
        assert "monument-svg--earned" in earned and "monument-svg--locked" in locked
        assert 'aria-hidden="true"' in earned and earned.startswith("<svg") and earned.endswith("</svg>")
    assert monuments.icon_svg("zzz", False) == monuments.icon_svg("star", False)


def test_monument_row_is_in_era_order_with_text_state(game_env):
    e = game_env
    e.elements["achievements-toggle-button"].dispatch("click", None)
    cards = e.elements["achievements-panel"].children[:-1]
    kinds = [monuments.kind_of(c.dataset.achievementId) for c in cards]
    assert kinds == sorted(kinds, key=monuments.KIND_ORDER.index)
    for card in cards:
        classes = [c.className for c in card.children]
        assert "monument-icon" in classes and "monument-caption" in classes
        state = [c.innerText for c in card.children if c.className == "monument-state"][0]
        assert state == ("Earned" if "achievement-card--earned" in card.className else "Not yet earned")


# --- K-21 / K-30: browser code, checked as text ------------------------------------
def test_screensaver_is_wired_and_reachable_on_both_pages():
    classic = (GAME_DIR / "index.html").read_text()
    desktop = (GAME_DIR / "pc.html").read_text()
    js = (GAME_DIR / "render3d.js").read_text()
    config = json.loads((GAME_DIR / "pc-config.json").read_text())
    assert 'id="screensaver-button"' in classic and 'id="screensaver-button"' in desktop
    assert "screensaver-button" in [i for g in config["toolbar"]["menu"] for i in g["ids"]]
    for needle in ("requestFullscreen", "reducedMotion()", "stopImmediatePropagation", "exitScreensaver", "SCREENSAVER_FRAME_MS"):
        assert needle in js
    assert "ContinuumCamera.screensaver" in classic
    assert "screensaver-fallback" in (GAME_DIR / "style.css").read_text()


def test_key_remap_is_wired():
    js = (GAME_DIR / "settings.js").read_text()
    html = (GAME_DIR / "index.html").read_text()
    for needle in ("continuum-keys-v1", "ContinuumKeys", "is already used for", "stopImmediatePropagation"):
        assert needle in js
    for element_id in ("keybind-list", "keybind-status", "keybind-reset-button"):
        assert f'id="{element_id}"' in html
    ids = re.findall(r'id: "([a-z-]+)", label', js)
    assert set(ids) == {"pause", "camera-overview", "camera-closeup", "camera-aerial", "camera-isometric", "screensaver", "help"}
    for action in ids:
        assert action in html or action.split("-")[0] in html
    assert "keys.actionFor" in html


def test_card_helper_has_a_text_download():
    assert "downloadText" in (GAME_DIR / "card.js").read_text()
