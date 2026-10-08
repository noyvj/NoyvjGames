"""K-9: the time-lapse run replay."""

import json

import minutes
import sim
import statlog
import timelapse as tl


def played(game_env, seasons=6):
    module = game_env.module
    game_env.build("shelter")
    game_env.advance_season(seasons)
    return module


# --- the pure module -----------------------------------------------------------------
def test_no_history_means_nothing_to_replay():
    assert tl.frames({}) == [] and tl.frames(None) == []
    assert tl.usable([]) is False and tl.pins({}, []) == []
    assert tl.chart_svg([], 0) == "" and tl.strip_svg([]) == ""
    assert tl.sample_indexes(0) == []


def test_frames_follow_the_stat_history(game_env):
    module = played(game_env, 5)
    frames = tl.frames(module.campaign.ui)
    assert len(frames) == 5
    assert [f["season"] for f in frames] == sorted(f["season"] for f in frames)
    last = frames[-1]
    assert last["era"] == "tribal" and last["population"] == module.state.population
    assert set(last["buildings"]) == set(sim.BUILDINGS)
    assert last["buildings"]["shelter"] == module.state.buildings["shelter"]


def test_junk_history_rows_are_dropped_not_fatal():
    ui = {statlog.KEY: [[1, 2, 3], "x", None]}
    assert tl.frames(ui) == []


def test_pins_cover_eras_discoveries_first_buildings_and_notes():
    ui = {}
    rows = []
    for season, era_i in ((1, 0), (2, 0), (3, 1), (4, 1)):
        values = {k: 0.0 for k in statlog.COLUMN_KEYS}
        values.update(season=season, era=era_i, population=6 + season, score=80.0)
        rows.append(statlog._row_from(values))
    ui[statlog.KEY] = rows
    minutes.record(ui, "research", "Fire-Keeping", "tribal", 2)
    minutes.record(ui, "build", "Shelter", "tribal", 2)
    minutes.record(ui, "build", "Shelter", "tribal", 3)   # a second shelter is not pinned again
    minutes.record(ui, "research", "Too Early", "tribal", 0 + 99)  # outside the recorded range
    ui["founders_log"] = [{"era": "tribal", "season": 4, "note": "Held the line."}, {"note": 5}]
    frames = tl.frames(ui)
    pins = tl.pins(ui, frames)
    kinds = [(p["season"], p["kind"]) for p in pins]
    assert (3, "era") in kinds and (2, "research") in kinds and (2, "build") in kinds and (4, "note") in kinds
    assert sum(1 for p in pins if p["kind"] == "build") == 1
    assert all(p["season"] <= 4 for p in pins)
    assert [k[0] for k in kinds] == sorted(k[0] for k in kinds)
    assert "Agrarian" in next(p for p in pins if p["kind"] == "era")["text"]
    assert len(tl.pins_at(pins, 2)) == 2
    assert tl.pin_text(pins[0]).startswith(tl.PIN_GLYPH[pins[0]["kind"]])


def test_chart_has_both_lines_a_cursor_and_text_for_every_number():
    frames = [{"season": s, "era": "tribal", "population": 6 + s, "score": 70.0 + s, "food": 0, "land": 0,
               "researched": 0, "buildings": {b: 0 for b in sim.BUILDINGS}} for s in range(1, 8)]
    svg = tl.chart_svg(frames, 3, [{"season": 4, "kind": "era", "text": "x"}, {"season": 6, "kind": "note", "text": "y"}])
    assert "tl-score" in svg and "tl-pop" in svg and "tl-cursor" in svg
    assert "tl-pin--era" in svg and "tl-pin--note" in svg
    assert "Cursor at season 4" in svg and "from 71 to 77" in svg
    # the cursor clamps
    assert "Cursor at season 7" in tl.chart_svg(frames, 99)
    assert "Cursor at season 1" in tl.chart_svg(frames, -5)


def test_map_svg_draws_the_buildings_of_that_season():
    base = {"season": 1, "era": "tribal", "population": 6, "score": 80, "food": 0, "land": 0, "researched": 0,
            "buildings": {b: 0 for b in sim.BUILDINGS}}
    few = dict(base, buildings=dict(base["buildings"], shelter=1))
    many = dict(base, buildings=dict(base["buildings"], shelter=9))
    assert tl.map_svg(many).count("map-glyph") > tl.map_svg(few).count("map-glyph")


def test_sample_indexes_include_both_ends_and_stay_ordered():
    assert tl.sample_indexes(3) == [0, 1, 2]
    picks = tl.sample_indexes(120)
    assert picks[0] == 0 and picks[-1] == 119 and len(picks) == tl.STRIP_FRAMES and picks == sorted(set(picks))


def test_strip_is_a_standalone_escaped_svg_with_one_cell_per_pick(game_env):
    module = played(game_env, 8)
    frames = tl.frames(module.campaign.ui)
    svg = tl.strip_svg(frames, "Reed <b>Ford</b> & Co")
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"') and svg.endswith("</svg>")
    assert "<b>" not in svg and "Reed &lt;b&gt;Ford" in svg
    assert svg.count("Season ") == len(frames) if len(frames) <= tl.STRIP_FRAMES else tl.STRIP_FRAMES
    assert "<style>" in svg and svg.count("<style>") == 1
    assert tl.strip_filename("Reed Ford!", frames).endswith(f"-season-{frames[-1]['season']}.svg")
    assert tl.strip_filename("", []).startswith("continuum-settlement")


# --- the panel ------------------------------------------------------------------------------
def test_panel_explains_when_there_is_nothing_to_replay(game_env):
    el = game_env.elements
    el["timelapse-toggle-button"].dispatch("click", None)
    assert el["timelapse-panel"].hidden is False
    assert "play at least two seasons" in el["timelapse-caption"].innerText
    assert el["timelapse-play-button"].disabled is True and el["timelapse-strip-button"].disabled is True


def test_panel_opens_on_the_latest_season_and_scrubs(game_env):
    module = played(game_env, 6)
    el = game_env.elements
    el["timelapse-toggle-button"].dispatch("click", None)
    frames = tl.frames(module.campaign.ui)
    assert el["timelapse-scrub"].attributes["max"] == str(len(frames) - 1)
    assert f"Season {frames[-1]['season']}" in el["timelapse-caption"].innerText
    el["timelapse-scrub"].value = "0"
    el["timelapse-scrub"].dispatch("input", None)
    assert f"Season {frames[0]['season']}" in el["timelapse-caption"].innerText
    assert "map-glyph" in el["timelapse-map"].innerHTML and "tl-cursor" in el["timelapse-chart"].innerHTML
    el["timelapse-next-button"].dispatch("click", None)
    assert f"Season {frames[1]['season']}" in el["timelapse-caption"].innerText
    el["timelapse-prev-button"].dispatch("click", None)
    el["timelapse-prev-button"].dispatch("click", None)
    assert f"Season {frames[0]['season']}" in el["timelapse-caption"].innerText  # clamps at the start


def test_pinned_moments_are_buttons_that_jump_to_their_season(game_env):
    module = played(game_env, 6)
    el = game_env.elements
    module.add_founders_note("Held the line.")
    el["timelapse-toggle-button"].dispatch("click", None)
    pins = el["timelapse-pins-list"].children
    assert pins and all(getattr(p, "className", "").startswith("secondary") for p in pins)
    build_pin = next(p for p in pins if "First built" in p.innerText)
    build_pin.dispatch("click", None)
    frames = tl.frames(module.campaign.ui)
    season = next(p["season"] for p in tl.pins(module.campaign.ui, frames) if p["kind"] == "build")
    assert f"Season {season}" in el["timelapse-caption"].innerText
    assert "First built" in el["timelapse-caption"].innerText


def test_play_steps_through_frames_and_stops_at_the_end(game_env):
    module = played(game_env, 5)
    el = game_env.elements
    el["timelapse-toggle-button"].dispatch("click", None)
    frames = tl.frames(module.campaign.ui)
    el["timelapse-play-button"].dispatch("click", None)   # at the end: restarts from the first frame
    assert module._tl_playing and "Season %d" % frames[0]["season"] in el["timelapse-caption"].innerText
    assert "Pause" in el["timelapse-play-button"].innerText
    for _ in range(len(frames) + 2):
        game_env.timers.flush()
    assert module._tl_playing is False
    assert f"Season {frames[-1]['season']}" in el["timelapse-caption"].innerText
    assert "Play" in el["timelapse-play-button"].innerText


def test_pausing_and_closing_stop_playback(game_env):
    played(game_env, 5)
    el = game_env.elements
    el["timelapse-toggle-button"].dispatch("click", None)
    el["timelapse-play-button"].dispatch("click", None)
    el["timelapse-play-button"].dispatch("click", None)
    assert game_env.module._tl_playing is False
    el["timelapse-play-button"].dispatch("click", None)
    el["timelapse-toggle-button"].dispatch("click", None)
    game_env.timers.flush()
    assert game_env.module._tl_playing is False and el["timelapse-panel"].hidden is True


def test_strip_button_downloads_an_svg(game_env):
    module = played(game_env, 5)
    sent = []
    module._download_text = lambda text, filename, mime: sent.append((text, filename, mime)) or True
    el = game_env.elements
    el["timelapse-toggle-button"].dispatch("click", None)
    el["timelapse-strip-button"].dispatch("click", None)
    assert len(sent) == 1 and sent[0][2] == "image/svg+xml" and sent[0][1].endswith(".svg")
    assert sent[0][0].startswith("<svg")


def test_panel_follows_new_seasons_without_losing_its_place(game_env):
    module = played(game_env, 4)
    el = game_env.elements
    el["timelapse-toggle-button"].dispatch("click", None)
    el["timelapse-scrub"].value = "1"
    el["timelapse-scrub"].dispatch("input", None)
    game_env.advance_season(2)
    assert module._tl_index == 1
    assert int(el["timelapse-scrub"].attributes["max"]) == len(tl.frames(module.campaign.ui)) - 1


def test_no_replay_during_a_look_back(game_env):
    module = played(game_env, 4)
    module.campaign.revisiting = "tribal"
    try:
        assert module._tl_frames() == []
    finally:
        module.campaign.revisiting = None
    json.dumps(module.get_state())  # nothing of the replay is saved
    assert "timelapse" not in json.dumps(module.get_state()["ui"])
