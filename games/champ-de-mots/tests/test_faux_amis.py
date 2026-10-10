"""Faux Amis (TODO L-15) and the farm's false-friend badge (L-16): a game built on a published list
of English-French false friends that the page reads LIVE (French Wiktionary, Annexe:Faux-amis
anglais-francais, CC BY-SA) and names on screen. Nothing from the list is bundled; these tests use a
small synthetic page written in the same wiki layout, and a fake fetch hook, so no network is touched."""

import json
import sys
import types


SOURCE_FRAGMENT = "French Wiktionary"

# (english look-alike, french word, true meaning(s), partial?)
PAIRS = [
    ("ability", "habilete", ["skill"], False),
    ("library", "librairie", ["bookshop", "bookstore"], False),
    ("pain", "pain", ["bread"], False),
    ("sensible", "sensible", ["sensitive"], False),
    ("sale", "sale", ["dirty"], False),
    ("coin", "coin", ["corner"], False),
    ("rest", "rester", ["to stay", "to remain"], False),
    ("chair", "chair", ["flesh"], False),
    ("journey", "journee", ["day"], False),
    ("lecture", "lecture", ["reading"], False),
    ("preservative", "preservatif", ["condom"], False),
    ("injury", "injure", ["insult"], False),
    ("cave", "cave", ["cellar"], False),
    ("large", "large", ["wide"], True),
    ("hazard", "heureux hasard", ["serendipity"], False),
    ("stage", "stage", ["internship"], False),
]


def _wikitext(pairs=PAIRS, noise=True):
    lines = ["Intro text that is not an entry.", "", "=== A ==="]
    for en, fr, means, partial in pairs:
        tag = " (fa p)" if partial else ""
        lines.append(f"* ''{en}'' (n){tag} : something in French")
        quoted = ", ".join(f"''{m}''" for m in means)
        lines.append(f"** fr : {fr} (n m) : {quoted}")
        lines.append("")
    if noise:
        lines += ["* ''commentary'' (v) : x", "** fr : abuser : ''to use too much'' mais preferer le verbe"]
    return "\n".join(lines)


def _api_json(pairs=PAIRS):
    return json.dumps({"query": {"pages": [{"revisions": [{"slots": {"main": {"content": _wikitext(pairs)}}}]}]}})


class FakePromise:
    def __init__(self, text=None, fail=None):
        self.text, self.fail = text, fail

    def then(self, ok, err=None):
        if self.fail is not None:
            if err is not None:
                err(self.fail)
        else:
            ok(self.text)
        return self


def _install_window(responder=None, prefs=None, today="2026-10-09"):
    store = {} if prefs is None else prefs
    calls = []

    def fetch(url):
        calls.append(url)
        return responder(url) if responder else FakePromise(_api_json())

    window = types.SimpleNamespace(
        championFetchText=fetch,
        champPrefGet=lambda key: store.get(key),
        champPrefSet=lambda key, value: store.__setitem__(key, value),
        studyToday=lambda: today,
    )
    sys.modules["js"].window = window
    return store, calls


def _open_and_load(game_env, responder=None, prefs=None, today="2026-10-09"):
    store, calls = _install_window(responder, prefs, today)
    mg = game_env.module.minigames
    mg.amis_status = "idle"
    mg.amis_entries = []
    game_env.elements["amis-toggle-button"].dispatch("click", None)
    return store, calls, mg


# --- the parser ------------------------------------------------------------------------------


def test_parser_reads_the_headword_the_french_word_and_the_true_meaning(game_env):
    mg = game_env.module.minigames
    entries = {e["fr"]: e for e in mg.parse_amis(_wikitext())}
    assert entries["pain"] == {"en": "pain", "fr": "pain", "means": ["bread"], "partial": False}
    assert entries["librairie"]["means"] == ["bookshop", "bookstore"]
    assert entries["large"]["partial"] is True
    assert entries["rester"]["means"] == ["to stay", "to remain"]


def test_parser_drops_multi_word_entries_commentary_and_non_entries(game_env):
    mg = game_env.module.minigames
    entries = mg.parse_amis(_wikitext())
    words = {e["fr"] for e in entries}
    assert "heureux hasard" not in words and "heureux" not in words   # two words: not a single French word
    assert "abuser" in words                                          # the " mais ..." commentary is cut off
    abuser = next(e for e in entries if e["fr"] == "abuser")
    assert abuser["means"] == ["to use too much"]
    assert mg.parse_amis("no entries here at all") == []
    # a word that merely starts with an article's letters keeps them
    assert {e["fr"] for e in mg.parse_amis("* ''xyz'' (n) : x\n** fr : large (a) : ''wide''\n** fr : lecture (n f) : ''reading''")} == {"large", "lecture"}
    assert mg.parse_amis("") == []


def test_parser_removes_a_leading_article_and_grammar_tags(game_env):
    mg = game_env.module.minigames
    text = "* ''bar'' (n) : x\n** fr : (un) barre (n m) : ''bar of metal''\n* ''jam'' (n) : x\n** fr : la jam (n f) : ''crowd''"
    entries = mg.parse_amis(text)
    assert [e["fr"] for e in entries] == ["barre", "jam"]


# --- reading the live list --------------------------------------------------------------------


def test_opening_the_panel_reads_the_live_page_names_it_and_caches_the_entries(game_env):
    store, calls, mg = _open_and_load(game_env)
    assert len(calls) == 1 and calls[0].startswith("https://fr.wiktionary.org/w/api.php")
    assert "Faux-amis" in calls[0] and calls[0].endswith("fran%C3%A7ais")
    assert mg.amis_status == "ready"
    assert mg.amis_read_date == "2026-10-09" and mg.amis_from_cache is False
    line = game_env.elements["amis-source"].innerText
    assert SOURCE_FRAGMENT in line and "read live on 2026-10-09" in line and "CC BY-SA" in line
    cached = json.loads(store["champ-amis-cache"])
    assert cached["date"] == "2026-10-09" and len(cached["entries"]) == len(mg.amis_entries)
    assert game_env.elements["amis-lock-message"].hidden is True


def test_the_source_link_points_at_the_page_the_game_reads():
    html = (__import__("pathlib").Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    assert 'id="amis-source-link" href="https://fr.wiktionary.org/wiki/Annexe:Faux-amis_anglais-fran%C3%A7ais"' in html


def test_a_failed_read_says_so_and_leaves_nothing_to_play(game_env):
    store, calls, mg = _open_and_load(game_env, responder=lambda url: FakePromise(fail="HTTP 503"))
    assert mg.amis_status == "failed"
    assert "could not be read" in game_env.elements["amis-source"].innerText
    assert "HTTP 503" in game_env.elements["amis-source"].innerText
    assert game_env.elements["amis-lock-message"].hidden is False
    assert game_env.elements["amis-start-button"].hidden is True
    assert mg.AMIS.start() is None
    assert "champ-amis-cache" not in store


def test_a_page_that_is_not_the_list_counts_as_a_failed_read(game_env):
    bad = FakePromise(json.dumps({"query": {"pages": [{"missing": True}]}}))
    _store, _calls, mg = _open_and_load(game_env, responder=lambda url: bad)
    assert mg.amis_status == "failed"
    game_env.elements["amis-toggle-button"].dispatch("click", None)   # close, then open again
    junk = FakePromise("not json at all")
    _store, _calls, mg = _open_and_load(game_env, responder=lambda url: junk)
    assert mg.amis_status == "failed"


def test_a_failed_fresh_read_keeps_playing_from_the_cached_copy_and_says_so(game_env):
    first = _open_and_load(game_env)
    store = first[0]
    game_env.elements["amis-toggle-button"].dispatch("click", None)   # close
    mg = game_env.module.minigames
    mg.amis_status, mg.amis_entries = "idle", []
    store2, _calls = _install_window(lambda url: FakePromise(fail="offline"), prefs=store, today="2026-10-12")
    assert mg.load_amis_cache() is True
    game_env.elements["amis-toggle-button"].dispatch("click", None)   # open: fresh read fails
    assert mg.amis_status == "ready" and mg.amis_from_cache is True
    line = game_env.elements["amis-source"].innerText
    assert "Showing the copy read on 2026-10-09" in line and "offline" in line


def test_the_cache_is_stale_after_a_week_and_unreadable_caches_are_ignored(game_env):
    store, _calls, mg = _open_and_load(game_env, today="2026-10-09")
    _install_window(prefs=store, today="2026-10-12")
    assert mg.amis_cache_is_stale() is False
    _install_window(prefs=store, today="2026-10-16")
    assert mg.amis_cache_is_stale() is True
    for junk in ("not json", json.dumps({"entries": "x"}), json.dumps({"date": "x", "entries": [["a"]]}), "{}"):
        mg.amis_status, mg.amis_entries = "idle", []
        _install_window(prefs={"champ-amis-cache": junk})
        assert mg.load_amis_cache() is False and mg.amis_status == "idle"


def test_no_window_hook_means_no_request_and_no_crash(game_env):
    mg = game_env.module.minigames
    sys.modules["js"].window = types.SimpleNamespace()
    assert mg.fetch_amis() is False


# --- the game ---------------------------------------------------------------------------------


def _play_all(game_env, mg, correct=True):
    mg.AMIS.start()
    seen = []
    while mg.AMIS.active:
        question = mg.AMIS.round
        seen.append(question)
        answer = question["answer"] if correct else next(c for c in question["choices"] if c != question["answer"])
        mg.AMIS.submit(answer)
    return seen


def test_a_round_asks_ten_questions_each_with_the_true_meaning_the_trap_and_two_others(game_env):
    _store, _calls, mg = _open_and_load(game_env)
    seen = _play_all(game_env, mg)
    assert len(seen) == 10
    for question in seen:
        entry = question["entry"]
        assert question["mode"] == "choice" and question["plot_id"] is None
        assert question["prompt"] == entry["fr"]
        assert question["answer"] == entry["means"][0]
        assert entry["en"] in question["choices"]                       # the look-alike is the trap
        assert len(question["choices"]) == 4 and len(set(question["choices"])) == 4
        assert question["answer"] in question["choices"]
        assert not entry["partial"]
        assert question["context"] == f"Looks like the English “{entry['en']}”"
    assert mg.AMIS.end_reason == "cleared"


def test_questions_get_sneakier_the_closer_the_french_is_to_the_english(game_env):
    _store, _calls, mg = _open_and_load(game_env)
    mg.AMIS.start()
    scores = [mg._amis_similarity(e) for e in mg.AMIS.run]
    assert scores == sorted(scores)


def test_partial_false_friends_are_never_asked(game_env):
    _store, _calls, mg = _open_and_load(game_env)
    assert all(not e["partial"] for e in mg.AMIS.pool())
    assert "large" not in {e["fr"] for e in mg.AMIS.pool()}


def test_a_right_answer_scores_and_says_what_the_word_means(game_env):
    _store, _calls, mg = _open_and_load(game_env)
    mg.AMIS.start()
    question = mg.AMIS.round
    assert mg.AMIS.submit(question["answer"]) is True
    assert mg.AMIS.score > 0 and mg.AMIS.combo == 1
    note = game_env.elements["amis-feedback"].innerText
    assert note.startswith("Yes") and question["entry"]["fr"] in note and question["entry"]["en"] in note


def test_a_wrong_answer_costs_a_life_not_a_plot_and_teaches_the_real_meaning(game_env):
    module = game_env.module
    _store, _calls, mg = _open_and_load(game_env)
    before = [(p.stage, p.interval_days, p.correct_streak) for p in module.state.plots[:50]]
    mg.AMIS.start()
    lives = mg.AMIS.lives
    question = mg.AMIS.round
    wrong = next(c for c in question["choices"] if c != question["answer"])
    assert mg.AMIS.submit(wrong) is False
    assert mg.AMIS.lives == lives - 1 and mg.AMIS.combo == 0
    assert question["answer"] in game_env.elements["amis-feedback"].innerText
    assert [(p.stage, p.interval_days, p.correct_streak) for p in module.state.plots[:50]] == before


def test_running_out_of_time_on_a_question_is_a_miss(game_env):
    _store, _calls, mg = _open_and_load(game_env)
    mg.AMIS.start()
    lives = mg.AMIS.lives
    for _ in range(mg.AMIS.params()["seconds"]):
        mg.amis_tick()
    assert mg.AMIS.lives == lives - 1
    assert game_env.elements["amis-feedback"].innerText.startswith("Time ran out")


def test_the_game_never_grows_a_plot_and_says_so(game_env):
    module = game_env.module
    _store, _calls, mg = _open_and_load(game_env)
    _play_all(game_env, mg)
    assert not any(p.last_watered is not None for p in module.state.plots)
    kind, text, tip = module.growth_marker("amis")
    assert kind == "none" and text == "Does not grow plots"
    module.render_growth_markers()
    assert game_env.elements["growth-marker-amis"].innerText == "Does not grow plots"
    assert "amis" not in {entry[0] for entry in mg.WATER_GAMES}


def test_every_answer_counts_toward_the_practice_score(game_env):
    module = game_env.module
    _store, _calls, mg = _open_and_load(game_env)
    before = module.practice_score()
    seen = _play_all(game_env, mg)
    entry = module.practice_ledger["amis"]
    assert entry["total"] == len(seen) == entry["correct"]
    assert entry["points"] == min(len(seen), module.PRACTICE_DAILY_CAP)
    assert module.practice_score() == before + entry["points"]
    assert "amis" in module.PRACTICE_MODES


def test_it_has_a_difficulty_setting_like_every_other_game(game_env):
    module = game_env.module
    mg = module.minigames
    for level in mg.DIFFICULTY_LEVELS:
        assert level in mg.AMIS_DIFFICULTY and mg.AMIS_DIFFICULTY[level]["seconds"] > 0
    assert game_env.elements["amis-difficulty-select"] is not None


def test_a_timed_run_is_reported_as_active_for_the_pause_when_hidden_hook(game_env):
    _store, _calls, mg = _open_and_load(game_env)
    assert mg.any_timed_run_active() is False
    mg.AMIS.start()
    assert mg.any_timed_run_active() is True


# --- the badge on the farm (L-16) ---------------------------------------------------------------


def _plot_with_french(module, fr):
    return module.plot_for_fr(fr)


def test_a_plot_whose_french_word_is_on_the_list_gets_a_badge_and_a_tooltip(game_env):
    module = game_env.module
    _open_and_load(game_env)
    plot = _plot_with_french(module, "du pain")
    assert plot is not None
    module.render()
    cell = module.plot_cells[plot.plot_id]
    assert "plot--amis" in cell.className
    assert "false friend" in cell.title and "looks like English “pain” but means bread" in cell.title
    assert cell.getAttribute("aria-label") == cell.title


def test_plots_not_on_the_list_and_partial_friends_get_no_badge(game_env):
    module = game_env.module
    _open_and_load(game_env)
    module.render()
    quiet = _plot_with_french(module, "le lac")
    assert "plot--amis" not in module.plot_cells[quiet.plot_id].className
    assert module.minigames.amis_for_plot(quiet) is None
    big = _plot_with_french(module, "la rue")
    assert module.minigames.amis_for_plot(big) is None


def test_the_badge_appears_when_the_list_finishes_loading_and_not_before(game_env):
    module = game_env.module
    mg = module.minigames
    module.render()
    plot = _plot_with_french(module, "du pain")
    assert "plot--amis" not in module.plot_cells[plot.plot_id].className
    _install_window()
    assert mg.fetch_amis() is True      # the fake answers at once and the page re-renders itself
    assert "plot--amis" in module.plot_cells[plot.plot_id].className


def test_the_badge_is_a_shape_in_the_stylesheet_not_a_colour_alone():
    css = (__import__("pathlib").Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    assert ".plot--amis { background-image: linear-gradient(315deg" in css
    assert "animation" not in css.split("L-16: a farm plot")[1]


# --- the Desktop page ----------------------------------------------------------------------------


def test_faux_amis_is_reachable_on_the_desktop_page():
    base = __import__("pathlib").Path(__file__).resolve().parent.parent
    cfg = json.loads((base / "pc-config.json").read_text(encoding="utf-8"))
    assert ["amis-panel", "amis-toggle-button", "Faux Amis"] in cfg["windows"]
    assert "#amis-toggle-button" in cfg["zones"]["side"]
    html = (base / "pc.html").read_text(encoding="utf-8")
    for element_id in ("amis-panel", "amis-toggle-button", "amis-choices", "amis-source", "amis-source-link", "amis-close-button"):
        assert f'id="{element_id}"' in html, element_id
    assert "amis_tick" in html and "championFetchText" in html


def test_no_badge_when_the_farms_own_english_already_says_the_look_alike(game_env):
    module = game_env.module
    mg = module.minigames
    _open_and_load(game_env)
    plot = _plot_with_french(module, "le lac")          # the farm's English for it is "the lake"
    mg._amis_by_word["lac"] = {"en": "lake", "fr": "lac", "means": ["pond"], "partial": False}
    mg._amis_plot_cache.clear()
    assert mg.amis_for_plot(plot) is None
    mg._amis_by_word["lac"]["en"] = "lacquer"
    mg._amis_plot_cache.clear()
    assert mg.amis_for_plot(plot) is not None
