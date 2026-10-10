"""Exam formats: six practice formats taken from the FREN152 tutorial exercises (TODO FS-17 to FS-22).

A pure, DOM-free module, like the other engines in this repo: every question is plain data made from a
random.Random, so tests can seed it and the game only has to draw it. Each format has its own entry in the
game's practice-mode ledger (the `mode` field), so every answer counts toward the visible practice score.

Formats
  clock       read a clock face and write the time in French (typed)
  truefalse   judge statements about a short text (vrai / faux)
  rewrite     rewrite a sentence in another form: negative or a question (typed)
  pronoun     answer with a pronoun in place of the noun (typed)
  reciprocal  complete a sentence with the reciprocal pronoun (choice)
  pairq       ask and answer a partner's question (choice)

The French here is deliberately plain and standard (A1/A2). Typed answers are compared by the game with its
own normalise function, passed in as `normalize`, so accents, case and end punctuation follow the game's
accent-sensitivity setting.
"""

import random

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
FORMATS = {
    "clock": {
        "mode": "clock", "label": "Clock reading", "typed": True,
        "instruction": "Read the clock and write the time in French, for example: Il est trois heures vingt.",
    },
    "truefalse": {
        "mode": "truefalse", "label": "True or false reading", "typed": False,
        "instruction": "Read the short text, then say whether the statement is vrai or faux.",
    },
    "rewrite": {
        "mode": "rewrite", "label": "Sentence rewriting", "typed": True,
        "instruction": "Rewrite the sentence in the form asked for.",
    },
    "pronoun": {
        "mode": "pronoun", "label": "Answer with a pronoun", "typed": True,
        "instruction": "Answer the question with oui and a pronoun in place of the noun (le, la, l', les, lui, leur).",
    },
    "reciprocal": {
        "mode": "reciprocal", "label": "Reciprocal pronouns", "typed": False,
        "instruction": "Pick the pronoun that completes the sentence (people doing it to each other).",
    },
    "pairq": {
        "mode": "pairq", "label": "Pair questions", "typed": False,
        "instruction": "Work with a partner: pick the question that fits, or the answer that fits.",
    },
}
FORMAT_ORDER = ("clock", "truefalse", "rewrite", "pronoun", "reciprocal", "pairq")
SESSION_LENGTH = 8

# ---------------------------------------------------------------------------
# 1. Clock reading
# ---------------------------------------------------------------------------
_HOUR_WORDS = {
    1: "une", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq", 6: "six", 7: "sept", 8: "huit", 9: "neuf",
    10: "dix", 11: "onze", 12: "douze",
}
_MINUTE_WORDS = {
    5: "cinq", 10: "dix", 15: "quinze", 20: "vingt", 25: "vingt-cinq", 30: "trente", 35: "trente-cinq",
    40: "quarante", 45: "quarante-cinq", 50: "cinquante", 55: "cinquante-cinq",
}
_MOINS_WORDS = {35: "vingt-cinq", 40: "vingt", 45: "le quart", 50: "dix", 55: "cinq"}
CLOCK_MINUTES = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)


def _hour_phrase(hour24):
    """The hour as French says it on the hour: (words with 'heure(s)') plus the special midi and minuit."""
    hour24 %= 24
    if hour24 == 0:
        return "minuit"
    if hour24 == 12:
        return "midi"
    hour = hour24 % 12 or 12
    return f"{_HOUR_WORDS[hour]} heure" + ("" if hour == 1 else "s")


def clock_answers(hour24, minute):
    """Every accepted way to say the time (without a leading 'Il est'; the checker adds both forms)."""
    hour24 %= 24
    base = _hour_phrase(hour24)
    answers = []
    if minute == 0:
        answers.append(base)
        return answers
    special = hour24 in (0, 12)  # midi / minuit take "et quart", "et demi" but no "heures"
    if minute <= 30:
        if minute == 15:
            answers.append(f"{base} et quart")
        if minute == 30:
            answers.append(f"{base} et demi" if special else f"{base} et demie")
            if special:
                answers.append(f"{base} et demie")
        words = _MINUTE_WORDS[minute]
        if not special:
            answers.append(f"{base} {words}")
        else:
            answers.append(f"{'douze heures' if hour24 == 12 else 'zéro heure'} {words}")
        return answers
    # past the half hour: "moins" the next hour, or the plain digits-in-words form
    next_hour = _hour_phrase(hour24 + 1)
    answers.append(f"{next_hour} moins {_MOINS_WORDS[minute]}")
    if not special:
        answers.append(f"{base} {_MINUTE_WORDS[minute]}")
    else:
        answers.append(f"{'douze heures' if hour24 == 12 else 'zéro heure'} {_MINUTE_WORDS[minute]}")
    return answers


def accepted_clock_forms(hour24, minute):
    out = []
    for phrase in clock_answers(hour24, minute):
        out.append(f"il est {phrase}")
        out.append(phrase)
    return out


def clock_svg(hour24, minute):
    """A simple analogue clock as an SVG string; the hands are lines, so it reads without colour."""
    import math
    hour12 = (hour24 % 12) + minute / 60.0
    minute_angle = math.radians(minute * 6 - 90)
    hour_angle = math.radians(hour12 * 30 - 90)

    def hand(angle, length, width):
        return (f'<line x1="60" y1="60" x2="{60 + length * math.cos(angle):.1f}" y2="{60 + length * math.sin(angle):.1f}" '
                f'stroke="currentColor" stroke-width="{width}" stroke-linecap="round"/>')

    ticks = "".join(
        f'<line x1="{60 + 50 * math.cos(math.radians(i * 30)):.1f}" y1="{60 + 50 * math.sin(math.radians(i * 30)):.1f}" '
        f'x2="{60 + 56 * math.cos(math.radians(i * 30)):.1f}" y2="{60 + 56 * math.sin(math.radians(i * 30)):.1f}" '
        f'stroke="currentColor" stroke-width="2"/>' for i in range(12)
    )
    return (
        '<svg viewBox="0 0 120 120" class="formats-clock" role="img" aria-label="An analogue clock">'
        '<circle cx="60" cy="60" r="57" fill="none" stroke="currentColor" stroke-width="3"/>'
        f'{ticks}{hand(hour_angle, 30, 5)}{hand(minute_angle, 45, 3)}'
        '<circle cx="60" cy="60" r="3" fill="currentColor"/></svg>'
    )


def clock_question(rng):
    hour24 = rng.randrange(0, 24)
    minute = rng.choice(CLOCK_MINUTES)
    forms = accepted_clock_forms(hour24, minute)
    display = f"{hour24 % 24:02d}:{minute:02d}"
    return {
        "format": "clock", "typed": True,
        "prompt": "What time is it? Write it in French.",
        "svg": clock_svg(hour24, minute),
        "accepted": forms,
        "answer": forms[0].capitalize() + ".",
        "explain": f"{display}: {forms[0].capitalize()}.",
    }


# ---------------------------------------------------------------------------
# 2. True / false reading
# ---------------------------------------------------------------------------
TRUEFALSE_TEXTS = [
    {
        "text": "Je m'appelle Léa. J'ai vingt ans et j'habite à Lyon avec ma sœur. J'aime la musique et je joue de la guitare. "
                "Le samedi, je mange au café avec mes amis.",
        "statements": [
            ("Léa a vingt ans.", True),
            ("Léa habite avec ses parents.", False),
            ("Léa joue de la guitare.", True),
            ("Léa mange au café le dimanche.", False),
        ],
    },
    {
        "text": "Voici Karim. Il est étudiant à Paris. Le matin, il prend le bus pour aller à l'université. "
                "Il n'aime pas le café, mais il aime beaucoup le thé.",
        "statements": [
            ("Karim est étudiant.", True),
            ("Karim prend le bus le matin.", True),
            ("Karim aime le café.", False),
            ("Karim habite à Lyon.", False),
        ],
    },
    {
        "text": "Nous sommes une famille de quatre personnes. Mon père travaille dans une banque et ma mère est médecin. "
                "J'ai un petit frère. Il a six ans et il adore les chiens.",
        "statements": [
            ("La famille a quatre personnes.", True),
            ("La mère travaille dans une banque.", False),
            ("Le petit frère a six ans.", True),
            ("Le petit frère n'aime pas les chiens.", False),
        ],
    },
    {
        "text": "Aujourd'hui, c'est lundi. Il fait froid et il pleut. Camille reste à la maison. "
                "Elle lit un livre et elle écoute de la musique.",
        "statements": [
            ("Aujourd'hui, c'est mardi.", False),
            ("Il pleut.", True),
            ("Camille sort avec ses amis.", False),
            ("Camille lit un livre.", True),
        ],
    },
    {
        "text": "Le restaurant est près de la gare. Il est ouvert à midi et le soir, mais il est fermé le mardi. "
                "Le plat du jour coûte douze euros.",
        "statements": [
            ("Le restaurant est loin de la gare.", False),
            ("Le restaurant est fermé le mardi.", True),
            ("Le plat du jour coûte douze euros.", True),
            ("Le restaurant est ouvert seulement le soir.", False),
        ],
    },
    {
        "text": "Marc et Julie habitent dans un petit appartement. Il y a une chambre, une cuisine et une salle de bains. "
                "Ils n'ont pas de jardin, mais ils ont un grand balcon.",
        "statements": [
            ("L'appartement a un jardin.", False),
            ("L'appartement a une cuisine.", True),
            ("Marc et Julie ont un grand balcon.", True),
            ("L'appartement a deux chambres.", False),
        ],
    },
    {
        "text": "Sophie travaille dans une librairie. Elle commence à neuf heures et elle finit à six heures. "
                "À midi, elle mange un sandwich dans le parc.",
        "statements": [
            ("Sophie travaille dans une librairie.", True),
            ("Sophie commence à huit heures.", False),
            ("Sophie mange dans le parc à midi.", True),
            ("Sophie finit à cinq heures.", False),
        ],
    },
    {
        "text": "Ce week-end, nous allons à la plage. Il fait beau et chaud. Les enfants nagent et jouent au football. "
                "Le soir, nous mangeons une pizza.",
        "statements": [
            ("Ils vont à la montagne.", False),
            ("Il fait beau.", True),
            ("Les enfants jouent au football.", True),
            ("Le soir, ils mangent une pizza.", True),
        ],
    },
]


def truefalse_question(rng):
    item = rng.choice(TRUEFALSE_TEXTS)
    statement, truth = rng.choice(item["statements"])
    return {
        "format": "truefalse", "typed": False,
        "prompt": f"« {statement} »",
        "context": item["text"],
        "choices": ["Vrai", "Faux"],
        "answer": "Vrai" if truth else "Faux",
        "accepted": ["vrai" if truth else "faux"],
        "explain": f"{'Vrai' if truth else 'Faux'}: re-read the text for \"{statement}\"",
    }


# ---------------------------------------------------------------------------
# 3. Sentence rewriting (affirmative, negative, est-ce que question)
# ---------------------------------------------------------------------------
REWRITE_ITEMS = [
    ("Tu parles français.", "Tu ne parles pas français.", "Est-ce que tu parles français ?"),
    ("Je mange une pomme.", "Je ne mange pas de pomme.", "Est-ce que je mange une pomme ?"),
    ("Nous habitons à Paris.", "Nous n'habitons pas à Paris.", "Est-ce que nous habitons à Paris ?"),
    ("Elle aime le café.", "Elle n'aime pas le café.", "Est-ce qu'elle aime le café ?"),
    ("Ils travaillent le samedi.", "Ils ne travaillent pas le samedi.", "Est-ce qu'ils travaillent le samedi ?"),
    ("Vous écoutez la radio.", "Vous n'écoutez pas la radio.", "Est-ce que vous écoutez la radio ?"),
    ("Il regarde la télévision.", "Il ne regarde pas la télévision.", "Est-ce qu'il regarde la télévision ?"),
    ("Tu as un frère.", "Tu n'as pas de frère.", "Est-ce que tu as un frère ?"),
    ("Marie joue au tennis.", "Marie ne joue pas au tennis.", "Est-ce que Marie joue au tennis ?"),
    ("Je suis fatigué.", "Je ne suis pas fatigué.", "Est-ce que je suis fatigué ?"),
    ("Nous prenons le bus.", "Nous ne prenons pas le bus.", "Est-ce que nous prenons le bus ?"),
    ("Elles chantent bien.", "Elles ne chantent pas bien.", "Est-ce qu'elles chantent bien ?"),
]
REWRITE_FORMS = {
    "negative": ("Rewrite the sentence in the negative.", 1),
    "question": ("Turn the sentence into a question with est-ce que.", 2),
}


def _rewrite_variants(text):
    """The negative accepts both 'pas de' and 'pas un/une' wording only where the item already says so; the item is the key."""
    return [text]


def rewrite_question(rng):
    item = rng.choice(REWRITE_ITEMS)
    form = rng.choice(sorted(REWRITE_FORMS))
    instruction, index = REWRITE_FORMS[form]
    target = item[index]
    accepted = _rewrite_variants(target)
    if form == "question":
        # the same question without the space before the question mark is fine; normalising removes it already
        accepted = [target]
    return {
        "format": "rewrite", "typed": True,
        "prompt": f"{item[0]}",
        "context": instruction,
        "accepted": accepted,
        "answer": target,
        "explain": f"{instruction} {target}",
    }


# ---------------------------------------------------------------------------
# 4. Answer with a pronoun
# ---------------------------------------------------------------------------
PRONOUN_ITEMS = [
    ("Tu manges la pomme ?", "Oui, je la mange.", "la pomme is feminine and the direct object: la"),
    ("Tu regardes le film ?", "Oui, je le regarde.", "le film is masculine: le"),
    ("Vous écoutez les disques ?", "Oui, nous les écoutons.", "plural: les"),
    ("Tu aimes l'école ?", "Oui, je l'aime.", "before a vowel le/la becomes l'"),
    ("Elle prend le bus ?", "Oui, elle le prend.", "le bus: le"),
    ("Il lit la lettre ?", "Oui, il la lit.", "la lettre: la"),
    ("Tu connais Paul ?", "Oui, je le connais.", "a person, direct object: le"),
    ("Tu invites Marie ?", "Oui, je l'invite.", "Marie is feminine and starts the verb with a vowel: l'"),
    ("Tu parles à Marie ?", "Oui, je lui parle.", "parler à someone: lui"),
    ("Il téléphone à ses parents ?", "Oui, il leur téléphone.", "téléphoner à plural people: leur"),
    ("Tu écris à Paul ?", "Oui, je lui écris.", "écrire à someone: lui"),
    ("Vous aidez vos amis ?", "Oui, nous les aidons.", "aider someone: les"),
]


def pronoun_question(rng):
    question, answer, hint = rng.choice(PRONOUN_ITEMS)
    plain = answer.split(", ", 1)[1]
    return {
        "format": "pronoun", "typed": True,
        "prompt": question,
        "context": "Answer with oui and a pronoun.",
        "accepted": [answer, plain],
        "answer": answer,
        "explain": f"{answer} ({hint})",
    }


# ---------------------------------------------------------------------------
# 5. Reciprocal pronoun completion
# ---------------------------------------------------------------------------
RECIPROCAL_ITEMS = [
    ("Marie et Paul ___ téléphonent chaque jour.", "se", ["se", "s'", "nous", "vous"]),
    ("Nous ___ parlons tous les soirs.", "nous", ["se", "s'", "nous", "vous"]),
    ("Vous ___ aidez souvent.", "vous", ["se", "s'", "nous", "vous"]),
    ("Les deux amies ___ écrivent des lettres.", "s'", ["se", "s'", "nous", "vous"]),
    ("Mes parents ___ aiment beaucoup.", "s'", ["se", "s'", "nous", "vous"]),
    ("Julie et moi, nous ___ retrouvons au café.", "nous", ["se", "s'", "nous", "vous"]),
    ("Paul et toi, vous ___ voyez le lundi.", "vous", ["se", "s'", "nous", "vous"]),
    ("Les enfants ___ regardent et ils rient.", "se", ["se", "s'", "nous", "vous"]),
    ("Ils ___ embrassent à la gare.", "s'", ["se", "s'", "nous", "vous"]),
    ("Elles ___ disent bonjour.", "se", ["se", "s'", "nous", "vous"]),
]


def reciprocal_question(rng):
    sentence, answer, choices = rng.choice(RECIPROCAL_ITEMS)
    return {
        "format": "reciprocal", "typed": False,
        "prompt": sentence,
        "context": "Each person does the action to the other: use the reciprocal pronoun.",
        "choices": list(choices),
        "answer": answer,
        "accepted": [answer],
        "explain": sentence.replace("___", answer),
    }


# ---------------------------------------------------------------------------
# 6. Pair questions (partner asks / you answer, or you ask from a statement)
# ---------------------------------------------------------------------------
PAIRQ_ITEMS = [
    # (kind, prompt, right, wrong1, wrong2)
    ("answer", "Ton partenaire demande : « Comment tu t'appelles ? »", "Je m'appelle Anna.", "J'ai vingt ans.", "J'habite à Lyon."),
    ("answer", "Ton partenaire demande : « Où habites-tu ? »", "J'habite à Marseille.", "Je suis étudiante.", "Il fait beau."),
    ("answer", "Ton partenaire demande : « Quel âge as-tu ? »", "J'ai dix-neuf ans.", "Je suis de Paris.", "Je m'appelle Léo."),
    ("answer", "Ton partenaire demande : « Qu'est-ce que tu aimes ? »", "J'aime la musique.", "Je vais bien, merci.", "J'ai un frère."),
    ("answer", "Ton partenaire demande : « Tu as des frères et sœurs ? »", "Oui, j'ai une sœur.", "Oui, je m'appelle Paul.", "Non, j'habite à Nice."),
    ("answer", "Ton partenaire demande : « Quelle heure est-il ? »", "Il est trois heures.", "Il fait chaud.", "Je suis fatigué."),
    ("ask", "Ton partenaire dit : « J'habite à Toulouse. » Quelle question poses-tu ?", "Où habites-tu ?", "Quel âge as-tu ?", "Comment tu t'appelles ?"),
    ("ask", "Ton partenaire dit : « J'ai vingt ans. » Quelle question poses-tu ?", "Quel âge as-tu ?", "Où habites-tu ?", "Tu aimes le café ?"),
    ("ask", "Ton partenaire dit : « Je m'appelle Hugo. » Quelle question poses-tu ?", "Comment tu t'appelles ?", "Quelle heure est-il ?", "Tu as des frères ?"),
    ("ask", "Ton partenaire dit : « J'aime le football. » Quelle question poses-tu ?", "Qu'est-ce que tu aimes ?", "Où habites-tu ?", "Quel âge as-tu ?"),
    ("ask", "Ton partenaire dit : « J'ai deux sœurs. » Quelle question poses-tu ?", "Tu as des frères et sœurs ?", "Quelle heure est-il ?", "Comment tu t'appelles ?"),
    ("ask", "Ton partenaire dit : « Je travaille dans une banque. » Quelle question poses-tu ?", "Où travailles-tu ?", "Quel âge as-tu ?", "Tu as un chien ?"),
]


def pairq_question(rng):
    kind, prompt, right, wrong_a, wrong_b = rng.choice(PAIRQ_ITEMS)
    choices = [right, wrong_a, wrong_b]
    rng.shuffle(choices)
    return {
        "format": "pairq", "typed": False,
        "prompt": prompt,
        "context": "Pick the answer that fits." if kind == "answer" else "Pick the question that fits.",
        "choices": choices,
        "answer": right,
        "accepted": [right.casefold()],
        "explain": right,
    }


_MAKERS = {
    "clock": clock_question, "truefalse": truefalse_question, "rewrite": rewrite_question,
    "pronoun": pronoun_question, "reciprocal": reciprocal_question, "pairq": pairq_question,
}


def make_question(format_id, rng=None):
    rng = rng or random.Random()
    return _MAKERS[format_id](rng)


def make_session(format_id, rng=None, length=SESSION_LENGTH):
    """`length` questions with no repeated prompt where the bank is big enough."""
    rng = rng or random.Random()
    out, seen, tries = [], set(), 0
    while len(out) < length and tries < length * 30:
        tries += 1
        question = make_question(format_id, rng)
        key = (question["prompt"], question.get("context", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(question)
    return out


def check(question, given, normalize):
    """True when `given` is an accepted answer. `normalize` is the game's own comparison function."""
    cleaned = normalize(str(given))
    return any(cleaned == normalize(a) for a in question["accepted"])
