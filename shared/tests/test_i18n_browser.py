"""shared/i18n.js in a real browser (TODO Z-13): English stays exactly as it was and fetches nothing,
Spanish and French reach the confirm dialog, the tutorial card, the achievements panel labels and the
save widget, a missing key falls back to English, and a language that arrives late relabels the page.
Runs the real scripts against a fake origin (conftest.Harness); no network."""

import json
from pathlib import Path

import pytest

from conftest import Harness, page_html, ORIGIN  # noqa: F401  (Harness is built by the harness fixture)

ROOT = Path(__file__).resolve().parents[2]

HEAD = """
<script src="/shared/confirm-dialog.js"></script>
<script src="/shared/tutorial.js"></script>
<script src="/shared/hub-auth.js"></script>
<script src="/shared/i18n.js"></script>
"""
BODY = '<div id="a">A</div><div id="b">B</div>'


def open_page(harness, lang=None, head=HEAD, body=BODY, size=(1440, 900)):
    h = harness(size=size, init_scripts=[f"try {{ localStorage.setItem('hub_lang', {json.dumps(lang)}) }} catch (e) {{}}"] if lang else ())
    h.pages["/t.html"] = page_html(head=head, body=body)
    h.requested = []
    h.context.on("request", lambda r: h.requested.append(r.url))
    h.goto("/t.html")
    h.page.wait_for_function("window.NoyvjI18n")
    h.page.evaluate("window.NoyvjI18n.ready")
    return h


def dialog_texts(h):
    h.page.evaluate("ConfirmDialog.ask({id: 'i18n-x', message: null, onConfirm: () => {}})")
    return h.page.evaluate("""() => ({
      message: document.getElementById('confirm-dialog-message').textContent,
      confirm: document.getElementById('confirm-dialog-confirm').textContent,
      cancel: document.getElementById('confirm-dialog-cancel').textContent,
      skip: document.getElementById('confirm-dialog-skip-row').textContent.trim()})""")


def test_english_is_the_default_and_fetches_no_language_file(harness):
    h = open_page(harness)
    assert dialog_texts(h) == {"message": "Are you sure?", "confirm": "Confirm", "cancel": "Cancel",
                               "skip": "Don't ask me again for this"}
    assert h.page.evaluate("NoyvjI18n.lang()") == "en"
    assert not [u for u in h.requested if "/shared/strings/" in u]
    assert h.errors == []


def test_t_fills_placeholders_and_falls_back_to_english(harness):
    h = open_page(harness, "es")
    out = h.page.evaluate("""() => ({
      known: NoyvjI18n.t('tutorial.step', 'Step {n} of {total}', {n: 2, total: 5}),
      missing: NoyvjI18n.t('no.such.key', 'Only English {x}', {x: 'here'}),
      bare: NoyvjI18n.t('no.such.key'),
      shortcut: typeof window.t, unfilled: NoyvjI18n.t('tutorial.step', 'Step {n} of {total}')})""")
    assert out["known"] == "Paso 2 de 5"
    assert out["missing"] == "Only English here"
    assert out["bare"] == "no.such.key"
    assert out["shortcut"] == "function"
    assert out["unfilled"] == "Paso {n} de {total}"


@pytest.mark.parametrize("lang,expected", [
    ("es", {"message": "¿Seguro?", "confirm": "Confirmar", "cancel": "Cancelar", "skip": "No volver a preguntar esto"}),
    ("fr", {"message": "Êtes-vous sûr ?", "confirm": "Confirmer", "cancel": "Annuler", "skip": "Ne plus me demander pour cette action"}),
])
def test_confirm_dialog_speaks_the_chosen_language_and_a_game_label_wins(harness, lang, expected):
    h = open_page(harness, lang)
    assert dialog_texts(h) == expected
    h.page.evaluate("document.getElementById('confirm-dialog-cancel').click()")
    h.page.evaluate("ConfirmDialog.ask({id: 'i18n-y', message: 'Retire it?', confirmLabel: 'Retire', onConfirm: () => {}})")
    assert h.page.evaluate("document.getElementById('confirm-dialog-message').textContent") == "Retire it?"
    assert h.page.evaluate("document.getElementById('confirm-dialog-confirm').textContent") == "Retire"
    assert h.page.evaluate("document.getElementById('confirm-dialog-cancel').textContent") == expected["cancel"]


def test_tutorial_card_words_and_relabel_when_the_language_arrives(harness):
    h = open_page(harness)       # English page ...
    h.page.evaluate("""GameTutorial.init([{title: 'One', text: 'First'}, {selector: '#b', title: 'Two', text: 'Second'}],
                                         {gameId: 'i18n-t'}); GameTutorial.start();""")
    card = lambda: h.page.evaluate("document.getElementById('tutorial-step-counter').textContent + '|' + "
                                   "[...document.querySelectorAll('#tutorial-card-buttons button')].map(b => b.textContent).join(',')")
    assert card() == "Step 1 of 2|Next,Skip tutorial"
    h.page.evaluate("NoyvjI18n.setLang('fr')")     # ... then French arrives while the card is open
    h.page.wait_for_function("document.getElementById('tutorial-step-counter').textContent.startsWith('Étape')")
    assert card() == "Étape 1 sur 2|Suivant,Passer le tutoriel"
    h.page.evaluate("document.querySelector('.tutorial-next-button').click()")
    assert card() == "Étape 2 sur 2|Retour,Terminé,Passer le tutoriel"
    assert h.page.evaluate("localStorage.getItem('hub_lang')") == "fr"
    assert h.page.evaluate("NoyvjI18n.setLang('de')") is False
    h.page.evaluate("NoyvjI18n.setLang('en')")
    h.page.evaluate("document.querySelector('.tutorial-next-button').click()")


def test_a_broken_language_file_leaves_english(harness):
    h = harness()
    h.pages["/t.html"] = page_html(head=HEAD, body=BODY)
    h.context.route("**/shared/strings/es.json", lambda route, request: route.fulfill(status=500, body="no"))
    h.page.add_init_script("localStorage.setItem('hub_lang', 'es')")
    h.goto("/t.html")
    h.page.wait_for_function("window.NoyvjI18n")
    h.page.evaluate("NoyvjI18n.ready")
    assert dialog_texts(h)["confirm"] == "Confirm"


def test_achievement_labels_are_translated_and_redrawn(harness):
    stats = {"achievements": {"a1": {"earned_pct": 4.0, "earned_count": 9}, "a2": {"earned_pct": 80.0, "earned_count": 90}}, "suppressed": False}
    head = HEAD + '<script src="/shared/achievement-stats.js" data-game-id="i18n-g"></script>'
    body = ('<div id="achievements-panel"><div data-achievement-id="a1"><p class="achievement-card-description">One</p></div>'
            '<div data-achievement-id="a2"><p class="achievement-card-description">Two</p></div></div>')
    h = harness()
    h.api_responses[("GET", "/stats/games/i18n-g")] = (200, stats)
    h.pages["/t.html"] = page_html(head=head, body=body)
    h.goto("/t.html")
    h.page.wait_for_function("window.NoyvjI18n")
    h.page.evaluate("applyAchievementStats()")
    h.page.wait_for_selector(".achievement-rarity")
    text = lambda: h.page.evaluate("[...document.querySelectorAll('.achievement-earn-rate, .achievement-rarity')].map(e => e.textContent.trim()).join(' / ')")
    assert text() == "Earned by 4% of players. / ★ Gold · rare / Earned by 80% of players. / ● Bronze · common"
    h.page.evaluate("NoyvjI18n.setLang('es')")
    h.page.wait_for_function("document.querySelector('.achievement-earn-rate').textContent.startsWith('Conseguido')")
    assert text() == "Conseguido por el 4% de los jugadores. / ★ Oro · raro / Conseguido por el 80% de los jugadores. / ● Bronce · común"
    assert h.page.evaluate("document.querySelectorAll('.achievement-rarity').length") == 2


SAVE_HEAD = ('<script src="/shared/hub-auth.js"></script><script src="/shared/confirm-dialog.js"></script>'
             '<script src="/shared/save-widget.js" data-game-id="i18n-game"></script>')


def widget(h):
    return h.page.evaluate("""() => ({
      line: document.querySelector('.save-widget-saved-line').textContent,
      save: document.querySelector('.save-widget-save-button').textContent,
      autosave: document.querySelector('.save-widget-autosave-label').textContent.trim(),
      load: document.querySelector('.save-widget-load-button').textContent,
      restore: document.querySelector('.save-widget-restore-toggle').textContent,
      toggle: document.querySelector('.save-widget-toggle').title})""")


def test_save_widget_in_english_loads_no_i18n_script_and_reads_as_before(harness):
    h = harness()
    h.pages["/t.html"] = page_html(head=SAVE_HEAD, body="<main>game</main>")
    requested = []
    h.context.on("request", lambda r: requested.append(r.url))
    h.goto("/t.html")
    h.page.wait_for_selector(".save-widget-saved-line")
    assert widget(h) == {"line": "Not saved yet", "save": "Save Progress", "autosave": "Autosave every 5 minutes",
                         "load": "Load", "restore": "Restore an earlier state", "toggle": "Show save/load options"}
    assert not [u for u in requested if "i18n" in u or "/strings/" in u]
    assert h.errors == []


@pytest.mark.parametrize("lang,expected", [
    ("fr", {"line": "Non sauvegardé", "save": "Enregistrer la progression", "autosave": "Sauvegarde automatique toutes les 5 minutes",
            "load": "Charger", "restore": "Restaurer un état précédent", "toggle": "Afficher les options de sauvegarde et de chargement"}),
    ("es", {"line": "Sin guardar", "save": "Guardar progreso", "autosave": "Guardado automático cada 5 minutos",
            "load": "Cargar", "restore": "Restaurar un estado anterior", "toggle": "Mostrar opciones de guardado y carga"}),
])
def test_save_widget_asks_for_the_translation_itself_and_relabels(harness, lang, expected):
    h = harness(init_scripts=[f"localStorage.setItem('hub_lang', '{lang}')"])
    h.pages["/t.html"] = page_html(head=SAVE_HEAD, body="<main>game</main>")
    h.goto("/t.html")
    h.page.wait_for_function("window.NoyvjI18n")                       # injected by the widget, not by the page
    h.page.evaluate("NoyvjI18n.ready")
    h.page.wait_for_function(f"document.querySelector('.save-widget-save-button').textContent === {json.dumps(expected['save'])}")
    assert widget(h) == expected
    assert h.errors == []
    # a pressed Save with the game not ready says so in the chosen language
    h.page.evaluate("document.querySelector('.save-widget-load-input').value = ''; document.querySelector('.save-widget-load-button').click()")
    said = h.page.evaluate("document.querySelector('.save-widget-status').textContent")
    assert said in ("Todavía está cargando. Inténtalo de nuevo en un momento.", "Chargement en cours. Réessayez dans un instant.")


def test_switching_back_to_english_restores_every_label(harness):
    h = harness(init_scripts=["localStorage.setItem('hub_lang', 'fr')"])
    h.pages["/t.html"] = page_html(head=SAVE_HEAD, body="<main>game</main>")
    h.goto("/t.html")
    h.page.wait_for_function("window.NoyvjI18n")
    h.page.wait_for_function("document.querySelector('.save-widget-save-button').textContent === 'Enregistrer la progression'")
    h.page.evaluate("NoyvjI18n.setLang('en')")
    h.page.wait_for_function("document.querySelector('.save-widget-save-button').textContent === 'Save Progress'")
    assert widget(h) == {"line": "Not saved yet", "save": "Save Progress", "autosave": "Autosave every 5 minutes",
                         "load": "Load", "restore": "Restore an earlier state", "toggle": "Show save/load options"}


def test_hub_settings_chooser_stores_the_language_and_reset_clears_it(harness):
    h = harness(init_scripts=["localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1');"])
    page = h.goto("/settings.html")
    page.wait_for_selector("#settings-lang option[value='fr']", state="attached")
    assert page.evaluate("[...document.querySelectorAll('#settings-lang option')].map(o => o.textContent)") == ["English", "Español", "Français"]
    assert page.evaluate("document.getElementById('settings-lang').value") == "en"
    page.select_option("#settings-lang", "es")
    assert page.evaluate("localStorage.getItem('hub_lang')") == "es"
    assert "Español" in page.inner_text("#settings-games-status")
    page.click("#settings-clear-prefs")
    page.click("#settings-confirm-yes")
    assert page.evaluate("localStorage.getItem('hub_lang')") is None
    assert h.errors == []
