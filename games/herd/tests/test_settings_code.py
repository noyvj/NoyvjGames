"""F-25: the settings code. One paste moves every local Herd setting, the ranch rules, the pinned
stats and the best coupling ratio to another device; a bad code changes nothing."""
import json


def set_local(env, key, value):
    env.local_storage.setItem(key, value)


def decode(g, code):
    ok, payload = g.export_progress.decode_progress_code(code, g.SETTINGS_CODE_PREFIX)
    assert ok
    return payload


def test_export_carries_set_values_only(game_env):
    g = game_env.module
    code = g.export_settings_code()
    assert code.startswith("HERDSET1:")
    payload = decode(g, code)
    assert payload["s"] == {}  # nothing set on a fresh browser
    set_local(game_env, "herd-text-scale", "1.2")
    set_local(game_env, "herd-high-contrast", "true")
    set_local(game_env, "herd-profile", "expert")
    payload = decode(g, g.export_settings_code())
    assert payload["s"] == {"herd-text-scale": 1.2, "herd-high-contrast": "true", "herd-profile": "expert"}


def test_round_trip_into_a_second_browser(game_env):
    g = game_env.module
    set_local(game_env, "herd-text-scale", "1.3")
    set_local(game_env, "herd-dyslexia-font", "true")
    set_local(game_env, "herd-confirm-percent", "50")
    g.set_rule("season_swing", 50)
    g.set_pin("funds", True)
    g.set_pin("score", True)
    g.record_coupling_ratio = 0.42
    code = g.export_settings_code()

    # a second browser: reload the game against a clean storage
    game_env.local_storage._store.clear()
    module = game_env.reload()
    assert module.rule("season_swing") == 100
    assert module.pinned_stats == []
    ok, message = module.import_settings_code(code)
    assert ok, message
    assert game_env.local_storage.getItem("herd-text-scale") == "1.3"
    assert game_env.local_storage.getItem("herd-dyslexia-font") == "true"
    assert game_env.local_storage.getItem("herd-confirm-percent") == "50"
    assert module.rule("season_swing") == 50
    assert module.pinned_stats == ["funds", "score"]
    assert module.record_coupling_ratio == 0.42
    assert "unranked" in message


def test_import_keeps_the_better_record(game_env):
    g = game_env.module
    g.record_coupling_ratio = 0.8
    code = g.export_settings_code()
    g.record_coupling_ratio = 0.3
    ok, _ = g.import_settings_code(code)
    assert ok
    assert g.record_coupling_ratio == 0.3, "an older, worse record never replaces a better one"
    g.record_coupling_ratio = 0.9
    g.import_settings_code(code)
    assert g.record_coupling_ratio == 0.8


def test_bad_codes_change_nothing(game_env):
    g = game_env.module
    set_local(game_env, "herd-profile", "beginner")
    before = dict(game_env.local_storage._store)
    for bad in ["", "hello", "HERDSET1:", "HERDSET1:!!!", "HERDSET1:" + "bm90IGpzb24=",
                g.export_progress.encode_progress_code({"v": 2, "s": {}}, "HERDSET1:"),
                g.export_progress.encode_progress_code({"v": 1, "s": {"herd-profile": "wizard"}, "rules": {"starting_funds": "x"}}, "HERDSET1:"),
                g.export_progress.encode_progress_code([1, 2], "HERDSET1:")]:
        ok, message = g.import_settings_code(bad)
        assert ok is False and message
        assert dict(game_env.local_storage._store) == before
    assert g.rule("starting_funds") == 300


def test_hostile_values_are_dropped_not_stored(game_env):
    g = game_env.module
    payload = {
        "v": 1,
        "s": {"herd-text-scale": 99, "herd-profile": "expert", "herd-reduced-motion": "maybe", "evil-key": "x",
              "herd-confirm-percent": "25"},
        "rules": {"starting_funds": 99999, "season_swing": True},
        "pins": ["funds", "nonsense", "funds", "score", "herd", "pressure"],
        "record": 5,
    }
    ok, message = g.import_settings_code(g.export_progress.encode_progress_code(payload, "HERDSET1:"))
    assert ok, message
    store = game_env.local_storage._store
    assert store.get("herd-profile") == "expert"
    assert store.get("herd-confirm-percent") == "25"
    assert "herd-text-scale" not in store and "herd-reduced-motion" not in store and "evil-key" not in store
    assert g.rule("starting_funds") == 600  # clamped into its range, never beyond
    assert g.rule("season_swing") == 100
    assert g.pinned_stats == ["funds", "score", "herd"]
    assert g.record_coupling_ratio is None  # 5 is not a possible ratio


def test_buttons_work_and_status_is_plain(game_env):
    g = game_env.module
    el = game_env.elements
    set_local(game_env, "herd-profile", "expert")
    el["settings-export-button"].dispatch("click")
    code = el["settings-code-box"].value
    assert code.startswith("HERDSET1:")
    assert "code made" in el["settings-code-status"].innerText.lower()
    el["settings-code-box"].value = "nonsense"
    el["settings-import-button"].dispatch("click")
    assert "settings code" in el["settings-code-status"].innerText.lower()
    el["settings-code-box"].value = code
    el["settings-import-button"].dispatch("click")
    assert el["settings-code-status"].innerText.startswith("Restored")
    assert g.settings_code_status_text.startswith("Restored")


def test_a_settings_import_never_touches_the_farm_or_a_save(game_env):
    g = game_env.module
    g.farm.funds += 100
    g.farm.herd_size = 3
    before = json.dumps(g.get_state(), sort_keys=True)
    code = g.export_settings_code()
    g.import_settings_code(code)
    assert json.dumps(g.get_state(), sort_keys=True) == before


def test_both_pages_have_the_ids_and_the_boot_loads_the_helper():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for page in ("index.html", "pc.html"):
        text = (root / page).read_text()
        for ident in ("settings-code-box", "settings-export-button", "settings-import-button", "settings-code-status"):
            assert f'id="{ident}"' in text, (page, ident)
        assert "shared/export_progress.py" in text
