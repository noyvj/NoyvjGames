"""The conversation simulator: short scripted exchanges that chain phrases from several topics.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_catalog import CATALOG
from champ_model import state
from champ_util import _element
from champ_points import record_practice


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# L5 -- the conversation simulator: a short scripted exchange that chains the
# phrases from several topics. Each turn is either the other person speaking
# (npc, with an English gloss) or an English cue for what you want to say; you
# pick the fitting French line from three. Every line is a phrase from the
# course catalog (placeholders filled in), and a dialogue only opens once every
# topic it draws on sits in an unlocked week, so it can never preview a locked
# week. Wrong picks show the right line and carry on (no punishment); each
# turn lands in the practice ledger as "conversation".
# ===========================================================================
CONVERSATIONS = [
    {
        "id": "meeting", "title": "Meeting someone new",
        "topics": ["fren151-w1-phrase001", "fren151-w2-phrase001", "fren151-w2-phrase002", "fren151-w3-phrase001"],
        "turns": [
            {"npc": "Comment vous appelez-vous?", "gloss": "What's your name? (formal)",
             "options": ["Je m'appelle Léa.", "Ça va bien.", "J'ai vingt ans."]},
            {"npc": "Comment allez-vous?", "gloss": "How are you? (formal)",
             "options": ["Bien, merci. Et vous?", "Je m'appelle Léa.", "Je suis australienne."]},
            {"npc": "Quelle est votre nationalité?", "gloss": "What is your nationality?",
             "options": ["Je suis australienne.", "Ça va bien.", "J'ai vingt ans."]},
            {"npc": "Quel âge avez-vous?", "gloss": "How old are you? (formal)",
             "options": ["J'ai vingt ans.", "Je m'appelle Léa.", "Bien, merci."]},
        ],
    },
    {
        "id": "getting_to_know", "title": "Getting to know you",
        "topics": ["fren151-w4-phrase001", "fren151-w5-phrase001", "fren151-w10-phrase001", "fren151-w9-phrase001"],
        "turns": [
            {"npc": "Qu'est-ce que vous faites dans la vie?", "gloss": "What do you do for a living? (formal)",
             "options": ["Je travaille comme cuisinier.", "J'habite à Sydney.", "Je m'appelle Paul."]},
            {"npc": "Où habitez-vous?", "gloss": "Where do you live?",
             "options": ["J'habite à Sydney.", "Je suis au chômage.", "Bien, merci."]},
            {"npc": "Parlez-vous français?", "gloss": "Do you speak French?",
             "options": ["Je parle un peu de français.", "J'habite à Sydney.", "Je suis fils unique."]},
            {"npc": "As-tu des frères ou des sœurs?", "gloss": "Do you have brothers or sisters?",
             "options": ["Je suis fils unique.", "Je parle un peu de français.", "Je travaille à temps plein."]},
        ],
    },
    {
        "id": "directions", "title": "Asking the way",
        "topics": ["fren151-w6-phrase001", "fren151-w6-phrase002"],
        "turns": [
            {"cue": "You are lost. Ask how to get to the museum.",
             "options": ["Pour aller au musée, s'il vous plaît?", "Où habitez-vous?", "Quelle heure est-il?"]},
            {"cue": "Ask if it is far from here.",
             "options": ["C'est loin d'ici?", "Je préfère Paris.", "Je m'appelle Léa."]},
            {"cue": "Ask if there is a bakery near here.",
             "options": ["Est-ce qu'il y a une boulangerie près d'ici?", "C'est loin d'ici?", "Je préfère Paris."]},
            {"cue": "Say you are looking for the station.",
             "options": ["Je cherche la gare.", "Où habitez-vous?", "Est-ce qu'il y a une boulangerie près d'ici?"]},
        ],
    },
    {
        "id": "shopping", "title": "Shopping for clothes",
        "topics": ["fren152-w7-phrase-slide001"],
        "turns": [
            {"npc": "Je peux vous aider?", "gloss": "Can I help you?",
             "options": ["Je cherche un pull.", "Par carte.", "Je fais du 38."]},
            {"npc": "Vous faites quelle taille?", "gloss": "What size are you?",
             "options": ["Je fais du 38.", "Par carte.", "Je cherche un pull."]},
            {"cue": "Ask if you can try it on.",
             "options": ["Je peux l'essayer?", "C'est combien?", "Vous payez comment?"]},
            {"cue": "Ask how much it is.",
             "options": ["C'est combien?", "Je peux l'essayer?", "En espèces."]},
            {"npc": "Vous payez comment?", "gloss": "How are you paying?",
             "options": ["Par carte.", "Je fais du 38.", "Je cherche un pull."]},
        ],
    },
    {
        "id": "restaurant", "title": "At a restaurant",
        "topics": ["fren152-w11-phrase001", "fren152-w9-phrase001"],
        "turns": [
            {"cue": "Ask the waiter for the menu.",
             "options": ["Pouvez-vous me donner la carte?", "L'addition, s'il vous plaît?", "Avez-vous choisi?"]},
            {"npc": "Avez-vous choisi?", "gloss": "Have you chosen?",
             "options": ["Comme plat principal, je voudrais un steak à point.", "Pouvez-vous me donner la carte?", "Quel est le plat du jour?"]},
            {"cue": "Ask what today's special is.",
             "options": ["Quel est le plat du jour?", "L'addition, s'il vous plaît?", "Avez-vous choisi?"]},
            {"cue": "You have finished. Ask for the bill.",
             "options": ["L'addition, s'il vous plaît?", "Pouvez-vous me donner la carte?", "Quel est le plat du jour?"]},
        ],
    },
    {
        "id": "time_and_dates", "title": "Time and dates",
        "topics": ["fren152-w2-phrase001", "fren152-w5-phrase001", "fren152-w5-phrase002"],
        "turns": [
            {"npc": "Quelle heure est-il?", "gloss": "What time is it?",
             "options": ["Il est seize heures quarante.", "C'est le douze mai.", "J'ai vingt ans."]},
            {"npc": "Quelle est la date de ton anniversaire?", "gloss": "When is your birthday?",
             "options": ["C'est le douze mai.", "Il est seize heures quarante.", "Je m'appelle Léa."]},
            {"cue": "Say that it is noon.",
             "options": ["Il est midi.", "Il est minuit.", "C'est le douze mai."]},
            {"cue": "Ask someone how many hours a week they work.",
             "options": ["Combien d'heures par semaine travaillez-vous?", "Combien de fois par jour travaillez-vous?", "Quelle heure est-il?"]},
        ],
    },
]
CONVERSATION_RNG = random.Random()
CONVERSATION_EMPTY_MESSAGE = (
    "No conversations are unlocked yet. Each one opens once the weeks whose phrases it uses are unlocked."
)
CONVERSATION_CORRECT = "Yes, that fits."
CONVERSATION_INCORRECT = "Not quite. The line that fits is: {line}"
CONVERSATION_SUMMARY = "Conversation complete: {correct}/{total} fitting replies."


conversation_proxies = []


def _destroy_conversation_proxies():
    for proxy in conversation_proxies:
        proxy.destroy()
    conversation_proxies.clear()


def _topic_sequence(topic_id):
    for week in CATALOG["weeks"]:
        for topic in week["topics"]:
            if topic["id"] == topic_id:
                return week["sequence"]
    return None


def conversation_available(entry):
    sequences = [_topic_sequence(t) for t in entry["topics"]]
    return all(s is not None and state.is_row_unlocked(s) for s in sequences)


def available_conversations():
    return [c for c in CONVERSATIONS if conversation_available(c)]


def _begin_conversation_turn():
    runstate.conversation_result = None
    runstate.conversation_picked = None
    if runstate.conversation is None or runstate.conversation_turn >= len(runstate.conversation["turns"]):
        runstate.conversation_choices = []
        return
    choices = list(runstate.conversation["turns"][runstate.conversation_turn]["options"])
    CONVERSATION_RNG.shuffle(choices)
    runstate.conversation_choices = choices


def start_conversation(event=None, conversation_id=None):
    """Opens one available dialogue (the named one, else a random one other
    than the last played when there is a choice)."""
    options = available_conversations()
    runstate.conversation_active = True
    runstate.conversation_turn = 0
    runstate.conversation_score = {"correct": 0, "total": 0}
    if conversation_id is not None:
        options = [c for c in options if c["id"] == conversation_id]
    elif len(options) > 1:
        options = [c for c in options if c["id"] != runstate.conversation_last_id] or options
    runstate.conversation = CONVERSATION_RNG.choice(options) if options else None
    if runstate.conversation is not None:
        runstate.conversation_last_id = runstate.conversation["id"]
    _begin_conversation_turn()
    render()
    return runstate.conversation


def pick_conversation_line(index):
    """Answers the current turn with the option at `index` (of the shuffled
    choices). Returns True/False, or None when the pick is not allowed now."""
    if not runstate.conversation_active or runstate.conversation is None or runstate.conversation_result is not None:
        return None
    if not (0 <= index < len(runstate.conversation_choices)):
        return None
    turn = runstate.conversation["turns"][runstate.conversation_turn]
    runstate.conversation_picked = runstate.conversation_choices[index]
    runstate.conversation_result = runstate.conversation_picked == turn["options"][0]
    runstate.conversation_score["total"] += 1
    if runstate.conversation_result:
        runstate.conversation_score["correct"] += 1
    record_practice("conversation", runstate.conversation_result)
    render()
    return runstate.conversation_result


def next_conversation_turn(event=None):
    if not runstate.conversation_active or runstate.conversation is None or runstate.conversation_result is None:
        return None
    runstate.conversation_turn += 1
    _begin_conversation_turn()
    render()
    return runstate.conversation_turn < len(runstate.conversation["turns"])


def close_conversation(event=None):
    runstate.conversation_active = False
    runstate.conversation = None
    runstate.conversation_turn = 0
    runstate.conversation_choices = []
    runstate.conversation_result = None
    runstate.conversation_picked = None
    render()


def _make_conversation_handler(index):
    def handler(event=None):
        pick_conversation_line(index)
    return handler


def render_conversation():
    panel = _element("conversation-panel")
    choices_box = _element("conversation-choices")
    _destroy_conversation_proxies()
    choices_box.innerHTML = ""
    if not runstate.conversation_active:
        panel.hidden = True
        return
    panel.hidden = False
    empty = _element("conversation-empty-message")
    summary = _element("conversation-summary")
    card = _element("conversation-card")
    if runstate.conversation is None:
        empty.hidden = False
        empty.innerText = CONVERSATION_EMPTY_MESSAGE
        summary.hidden = True
        card.hidden = True
        _element("conversation-title").innerText = ""
        _element("conversation-progress").innerText = ""
        return
    empty.hidden = True
    _element("conversation-title").innerText = runstate.conversation["title"]
    if runstate.conversation_turn >= len(runstate.conversation["turns"]):
        card.hidden = True
        summary.hidden = False
        summary.innerText = CONVERSATION_SUMMARY.format(**runstate.conversation_score)
        _element("conversation-progress").innerText = ""
        return
    card.hidden = False
    summary.hidden = True
    turn = runstate.conversation["turns"][runstate.conversation_turn]
    _element("conversation-progress").innerText = f"Turn {runstate.conversation_turn + 1} of {len(runstate.conversation['turns'])}"
    if "npc" in turn:
        _element("conversation-line").innerText = turn["npc"]
        _element("conversation-gloss").innerText = turn["gloss"]
    else:
        _element("conversation-line").innerText = turn["cue"]
        _element("conversation-gloss").innerText = "Choose what you would say."
    for index, choice in enumerate(runstate.conversation_choices):
        button = document.createElement("button")
        button.id = f"conversation-choice-{index}"
        button.className = "secondary"
        button.innerText = choice
        button.disabled = runstate.conversation_result is not None
        proxy = create_proxy(_make_conversation_handler(index))
        button.addEventListener("click", proxy)
        conversation_proxies.append(proxy)
        choices_box.appendChild(button)
    feedback = _element("conversation-feedback")
    if runstate.conversation_result is None:
        feedback.innerText = ""
    else:
        feedback.innerText = CONVERSATION_CORRECT if runstate.conversation_result else CONVERSATION_INCORRECT.format(
            line=turn["options"][0]
        )
    _element("conversation-next-button").hidden = runstate.conversation_result is None
