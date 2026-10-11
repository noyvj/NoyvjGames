"""G-25: copy and restore the local settings and personal bests as one short code."""

import base64
import json
import sys

from .fakes import FakeStorage


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def _reencode(m, obj):
    raw = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()
    return m.SETTINGS_CODE_PREFIX + base64.urlsafe_b64encode(raw).decode().rstrip("=") + "." + m._checksum(raw)


def test_code_has_prefix_and_checksum_and_is_short(game_env):
    m = game_env.module
    _storage({"thaw-text-scale": "1.2", "thaw-blindfold": "true"})
    m.set_temp_unit("f")
    code = m.export_settings_code()
    assert code.startswith("THAW1-") and "." in code
    assert len(code) < 700
    data = m.decode_settings_code(code)
    assert data["t"] == 1.2 and data["f"] == {"thaw-blindfold": True} and data["u"] == "f"


def test_round_trip_restores_everything_on_a_fresh_device(game_env):
    m = game_env.module
    _storage({
        "thaw-text-scale": "1.3", "thaw-high-contrast": "true", "thaw-hide-mascots": "false",
        "thaw-instant-digits": "true",
    })
    m.set_temp_unit("k")
    m.set_confirm_threshold(150)
    m.personal_best.update({"temperature_saved": 9.5, "region": "B"})
    m.climate_archive["C"].update({"best_saved": 4.0, "furthest_round": 22, "peak_dampening": 0.6})
    code = m.export_settings_code()

    other = _storage()  # a brand-new browser
    m.temp_unit = "c"
    m.confirm_threshold = 0
    m.personal_best.update({"temperature_saved": 0.0, "region": None})
    m.climate_archive["C"].update({"best_saved": 0.0, "furthest_round": 1, "peak_dampening": 0.0})
    result = m.import_settings_code(code)
    restored, skipped = result
    assert skipped == []
    assert {"text size", "display switches", "temperature unit", "big-spend threshold", "personal best",
            "climate archive"} <= set(restored)
    assert other.data["thaw-text-scale"] == "1.3"
    assert other.data["thaw-high-contrast"] == "true" and other.data["thaw-hide-mascots"] == "false"
    assert other.data["thaw-instant-digits"] == "true"
    assert m.temp_unit == "k" and other.data[m.TEMP_UNIT_STORAGE_KEY] == "k"
    assert m.confirm_threshold == 150
    assert m.personal_best["temperature_saved"] == 9.5 and m.personal_best["region"] == "B"
    assert m.climate_archive["C"] == {"best_saved": 4.0, "furthest_round": 22, "peak_dampening": 0.6}


def test_import_never_lowers_a_record(game_env):
    m = game_env.module
    _storage()
    m.personal_best.update({"temperature_saved": 3.0, "region": "A"})
    m.climate_archive["A"].update({"best_saved": 8.0, "furthest_round": 5, "peak_dampening": 0.2})
    incoming = {
        "pb": {"temperature_saved": 1.0, "region": "C"},
        "ar": {"A": {"best_saved": 2.0, "furthest_round": 30, "peak_dampening": 0.1}},
    }
    m.import_settings_code(_reencode(m, incoming))
    assert m.personal_best["temperature_saved"] == 3.0 and m.personal_best["region"] == "A"
    assert m.climate_archive["A"] == {"best_saved": 8.0, "furthest_round": 30, "peak_dampening": 0.2}


def test_unreadable_codes_are_refused_without_changing_anything(game_env):
    m = game_env.module
    storage = _storage()
    good = m.export_settings_code()
    bad_codes = [
        "", "hello", "THAW1-", "THAW1-abc", "THAW1-!!!.0000", good[:-1] + ("0" if good[-1] != "0" else "1"),
        good.replace("THAW1-", "THAW2-"), None, 123, "THAW1-" + "A" * 5000 + ".0000",
        "THAW1-" + base64.urlsafe_b64encode(b"[1,2]").decode() + "." + m._checksum(b"[1,2]"),
    ]
    for code in bad_codes:
        assert m.import_settings_code(code) is None, code
    assert storage.writes == 0


def test_bad_fields_inside_a_valid_code_are_skipped_and_named(game_env):
    m = game_env.module
    storage = _storage()
    code = _reencode(m, {
        "t": 9.0, "f": {"thaw-blindfold": "yes", "evil-key": True, "thaw-tip-shake": True},
        "u": "x", "c": 77, "pb": {"temperature_saved": -3}, "ar": 5,
    })
    restored, skipped = m.import_settings_code(code)
    assert restored == ["display switches"]
    assert set(skipped) == {"text size", "a display switch", "temperature unit", "big-spend threshold",
                            "personal best", "climate archive"}
    assert storage.data == {"thaw-tip-shake": "true"}  # the one good switch; nothing else written
    assert m.temp_unit == "c" and m.confirm_threshold == 0


def test_only_known_switch_keys_are_ever_written(game_env):
    m = game_env.module
    storage = _storage()
    m.import_settings_code(_reencode(m, {"f": {"constructor": True, "__proto__": True, "thaw-hide-pace": True}}))
    assert set(storage.data) == {"thaw-hide-pace"}


def test_copy_button_fills_the_box_and_says_what_to_do(game_env):
    m = game_env.module
    _storage()
    game_env.elements["settings-code-copy-button"].dispatch("click", None)
    box = game_env.elements["settings-code-input"]
    assert box.value.startswith("THAW1-")
    assert "copy" in game_env.elements["settings-code-status"].innerText.lower()
    assert m.decode_settings_code(box.value) is not None


def test_restore_button_reports_the_result(game_env):
    m = game_env.module
    _storage()
    box = game_env.elements["settings-code-input"]
    status = game_env.elements["settings-code-status"]
    box.value = "nonsense"
    game_env.elements["settings-code-restore-button"].dispatch("click", None)
    assert "does not look like a Thaw settings code" in status.innerText
    m.set_confirm_threshold(100)
    box.value = m.export_settings_code()
    m.confirm_threshold = 0
    game_env.elements["settings-code-restore-button"].dispatch("click", None)
    assert "Restored:" in status.innerText and "keep the higher" in status.innerText
    assert m.confirm_threshold == 100


def test_the_code_holds_no_game_state(game_env):
    m = game_env.module
    _storage()
    for _ in range(4):
        game_env.advance_round()
    text = json.dumps(m.decode_settings_code(m.export_settings_code()))
    for word in ("region_b", "science_log", "funds", "capacity", "hard_mode", "custom_preset"):
        assert word not in text


def test_restore_asks_the_page_to_reapply(game_env):
    import types

    m = game_env.module
    _storage()
    calls = []
    sys.modules["js"].window = types.SimpleNamespace(ThawSettings=types.SimpleNamespace(reapply=lambda: calls.append(1)))
    m.import_settings_code(m.export_settings_code())
    assert calls == [1]
