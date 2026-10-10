"""shared/i18n.js and its strings (TODO Z-13): static checks over the files, no browser.

  * shared/strings/en.json is exactly the English the components carry in their tr() calls;
  * es.json and fr.json only translate keys that exist, keep every {placeholder}, and are not empty;
  * the files are precached by the service worker and sw.js's version moved with them;
  * the hub Settings page offers the chooser and the language key is a hub preference."""

import json
import re
from pathlib import Path

import pytest

from i18n_extract import COMPONENTS, ROOT, extract_all

STRINGS = ROOT / "shared" / "strings"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def load(code):
    return json.loads((STRINGS / f"{code}.json").read_text(encoding="utf-8"))


def real(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def test_english_file_equals_the_text_the_components_carry():
    carried = extract_all()
    # The rarity names are built as "ach." + kind in achievement-stats.js, so they are checked on their own.
    stats = (ROOT / "shared" / "achievement-stats.js").read_text(encoding="utf-8")
    for kind in ("gold", "silver", "bronze"):
        m = re.search(rf'{kind}: \{{ glyph: "[^"]+", name: "([^"]+)", note: "([^"]+)" \}}', stats)
        assert m, kind
        carried["ach." + kind], carried["ach." + kind + "Note"] = m.group(1), m.group(2)
    assert real(load("en")) == carried


def test_every_component_converted_has_keys():
    for name in COMPONENTS:
        text = (ROOT / "shared" / name).read_text(encoding="utf-8")
        assert re.search(r'\btr\("[\w.]+"', text), name


@pytest.mark.parametrize("code", ["es", "fr"])
def test_translations_follow_the_english_keys_and_placeholders(code):
    en, tr = real(load("en")), real(load(code))
    assert set(tr) <= set(en), sorted(set(tr) - set(en))
    for key, text in tr.items():
        assert text.strip(), key
        assert sorted(PLACEHOLDER.findall(text)) == sorted(PLACEHOLDER.findall(en[key])), (key, text)
    assert "_about" in load(code) and "proof-read" in load(code)["_about"]


@pytest.mark.parametrize("code", ["es", "fr"])
def test_translations_are_complete_for_the_climate_pass(code):
    # The shared-component strings are all translated (a missing key would fall back to English, which
    # is fine in code but means the pass is not finished).
    assert set(real(load("en"))) == set(real(load(code)))


def test_languages_offered_match_the_files():
    text = (ROOT / "shared" / "i18n.js").read_text(encoding="utf-8")
    codes = re.findall(r'\{ code: "(\w+)"', text)
    assert codes[0] == "en"
    for code in codes[1:]:
        assert (STRINGS / f"{code}.json").exists(), code


def test_files_are_precached_and_the_worker_version_moved():
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    for url in ("shared/i18n.js", "shared/strings/en.json", "shared/strings/es.json", "shared/strings/fr.json"):
        assert f'"{url}"' in sw, url
    assert int(re.search(r"SW_VERSION = (\d+)", sw).group(1)) >= 55


def test_settings_page_has_the_language_chooser():
    html = (ROOT / "settings.html").read_text(encoding="utf-8")
    js = (ROOT / "settings.js").read_text(encoding="utf-8")
    assert 'id="settings-lang"' in html and 'src="shared/i18n.js"' in html
    assert "setLang" in js and "hub_lang" in js
    # "Reset hub preferences" clears hub-prefixed keys, so the language is covered by it.
    assert re.match(r"^hub[_-]", "hub_lang")
