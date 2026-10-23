#!/usr/bin/env python3
"""Writes games/champ-de-mots/oral-exam-guide.html: a printable study guide for the FREN152 oral exam (two paired tasks: general
questions, and a birthday-party role-play). The vocabulary tables and the list of course questions come from the game's own
catalog (games/champ-de-mots/fren_combined_catalog.json); the exam advice, model answers and model dialogues are written below.

    python3 scripts/generate-oral-exam-guide.py           # write the page
    python3 scripts/generate-oral-exam-guide.py --check   # exit 1 if the page is out of date
"""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "games" / "champ-de-mots" / "fren_combined_catalog.json"
OUT = ROOT / "games" / "champ-de-mots" / "oral-exam-guide.html"


def esc(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------------------------------------------------------- written content
# (question, model answer in French, English). Replace the details with your own: the shape of the answer is the point.
QA = [
    ("Identity and background", [
        ("Comment t'appelles-tu ? / Comment vous appelez-vous ?", "Je m'appelle [prénom]. Je suis australien(ne) et j'habite à Wollongong.", "My name is [name]. I am Australian and I live in Wollongong."),
        ("Quel âge as-tu ?", "J'ai [vingt] ans. Mon anniversaire est le [douze mai].", "I am [20]. My birthday is the [twelfth of May]."),
        ("Qu'est-ce que tu fais dans la vie ?", "Je suis étudiant(e) à l'université. Je travaille aussi [quatorze] heures par semaine.", "I am a student at university. I also work [fourteen] hours a week."),
        ("Où habites-tu ?", "J'habite à [Wollongong]. C'est près de la plage. J'habite avec [ma famille].", "I live in [Wollongong]. It is near the beach. I live with [my family]."),
        ("As-tu des frères ou des sœurs ? / Combien de personnes y a-t-il dans ta famille ?", "Oui, j'ai un frère et une sœur. Il y a quatre personnes dans ma famille : mes parents, ma sœur et moi.", "Yes, I have a brother and a sister. There are four people in my family: my parents, my sister and me."),
        ("Parlez-vous français ?", "Oui, je parle un peu français. J'étudie le français à l'université.", "Yes, I speak a little French. I study French at university."),
    ]),
    ("Daily life", [
        ("À quelle heure te lèves-tu ? Décris ta routine du matin.", "En semaine, je me lève à sept heures. D'abord, je me douche, ensuite je m'habille. Puis je prends le petit-déjeuner : je mange du pain et je bois du café. Le week-end, je me lève tard.", "On weekdays I get up at seven. First I shower, then I get dressed. Then I have breakfast: I eat bread and drink coffee. At the weekend I get up late."),
        ("À quelle heure est ton cours ?", "Mon cours est à dix heures. Il finit à midi.", "My class is at ten. It ends at noon."),
        ("Qu'est-ce que tu fais le week-end ?", "Le samedi matin, je joue au tennis. Le dimanche, je me repose et je joue de la guitare. Le samedi soir, je sors avec mes amis.", "On Saturday mornings I play tennis. On Sundays I rest and play the guitar. On Saturday evenings I go out with friends."),
        ("Combien de fois par semaine fais-tu du sport ?", "Je fais du sport trois fois par semaine. Je vais au cinéma deux fois par mois.", "I do sport three times a week. I go to the cinema twice a month."),
        ("Qu'est-ce que tu as fait hier ?", "Hier, j'ai regardé un film et j'ai mangé une pizza. Samedi dernier, je suis allé(e) au marché.", "Yesterday I watched a film and ate a pizza. Last Saturday I went to the market."),
    ]),
    ("Dates, weather, clothes", [
        ("Quelle est la date de ton anniversaire ?", "Mon anniversaire est le douze mai. Pour mon anniversaire, j'invite mes amis chez moi.", "My birthday is on the twelfth of May. For my birthday I invite my friends to my place."),
        ("Quel temps fait-il en hiver ? Qu'est-ce que tu portes quand il fait froid ?", "En hiver, il fait froid et il pleut souvent. Quand il fait froid, je porte un manteau et une écharpe.", "In winter it is cold and it often rains. When it is cold I wear a coat and a scarf."),
        ("Qu'est-ce que tu portes aujourd'hui ?", "Aujourd'hui, je porte un jean bleu, un pull gris et des baskets blanches.", "Today I am wearing blue jeans, a grey sweater and white trainers."),
        ("Qu'est-ce que tu mets pour aller à un mariage ?", "Pour un mariage, je mets une robe élégante (ou un costume et une cravate).", "For a wedding I put on an elegant dress (or a suit and a tie)."),
        ("Comment trouves-tu ce style ?", "Je trouve que la couleur est jolie, mais c'est un peu trop cher pour moi.", "I think the colour is pretty, but it is a bit too expensive for me."),
    ]),
    ("Food and shops", [
        ("Qu'est-ce que vous prenez au petit-déjeuner ?", "Au petit-déjeuner, je prends des céréales et du lait, et je bois du café.", "For breakfast I have cereal and milk, and I drink coffee."),
        ("Qu'est-ce que tu manges au dîner ?", "Au dîner, nous prenons de la soupe et des pâtes. Je ne mange pas de viande.", "At dinner we have soup and pasta. I do not eat meat."),
        ("Quel est ton plat préféré ?", "Mon plat préféré, c'est les pâtes. J'aime beaucoup le fromage.", "My favourite dish is pasta. I like cheese a lot."),
        ("Tu vas à la boulangerie ? / Tu veux du café ?", "Oui, j'y vais demain matin. / Oui, j'en veux, merci.", "Yes, I am going there tomorrow morning. / Yes, I would like some, thanks."),
        ("Qu'est-ce que vous me conseillez ? (au restaurant)", "Je vous conseille le plat du jour. Je prends le potage, puis un steak à point.", "I recommend the dish of the day. I will have the soup, then a medium steak."),
    ]),
]

DIALOGUES = [
    ("Version A: two friends planning the party", [
        ("A", "Salut ! Ça va ?", "Hi! How are you?"),
        ("B", "Salut ! Oui, ça va bien, et toi ?", "Hi! Yes, fine, and you?"),
        ("A", "Ça va. Alors, mon anniversaire est samedi. On prépare la soirée ?", "Fine. So my birthday is on Saturday. Shall we plan the party?"),
        ("B", "Bien sûr ! À quelle heure est la fête ?", "Of course! What time is the party?"),
        ("A", "À sept heures du soir, chez moi. Je propose une soirée déguisée. Comment trouves-tu cette idée ?", "At seven in the evening, at my place. I suggest a costume party. What do you think of the idea?"),
        ("B", "Je trouve que c'est une très bonne idée ! Je porte un costume de pirate. Et toi ?", "I think it's a very good idea! I'll wear a pirate costume. And you?"),
        ("A", "Moi, je mets une robe rouge et un chapeau noir.", "I'll put on a red dress and a black hat."),
        ("B", "Super ! Qu'est-ce qu'on mange ?", "Great! What are we eating?"),
        ("A", "On mange de la pizza et de la salade. Il faut aussi un gâteau d'anniversaire.", "We eat pizza and salad. We also need a birthday cake."),
        ("B", "Je vais acheter le gâteau à la boulangerie. J'y vais vendredi matin.", "I'll buy the cake at the bakery. I'm going there on Friday morning."),
        ("A", "Merci ! Moi, je vais au supermarché. Il faut deux kilos de tomates, deux cents grammes de fromage et des fruits.", "Thanks! I'll go to the supermarket. We need two kilos of tomatoes, two hundred grams of cheese and some fruit."),
        ("B", "Et pour les boissons ? Qu'est-ce qu'on boit ?", "And for drinks? What are we drinking?"),
        ("A", "On boit du jus d'orange et de l'eau gazeuse. Il faut quatre bouteilles de jus.", "We drink orange juice and sparkling water. We need four bottles of juice."),
        ("B", "D'accord ! Tu as assez de chaises ?", "Okay! Do you have enough chairs?"),
        ("A", "Oui, j'ai assez de chaises, merci !", "Yes, I have enough chairs, thanks!"),
        ("B", "Alors, à samedi, sept heures !", "So, see you Saturday at seven!"),
        ("A", "Oui, à samedi ! Merci, au revoir !", "Yes, see you Saturday! Thanks, goodbye!"),
    ]),
    ("Version B: customer and shop assistant (food shop)", [
        ("Vendeur", "Bonjour ! Je peux vous aider ?", "Hello! Can I help you?"),
        ("Client", "Bonjour ! Je voudrais du fromage pour une fête, s'il vous plaît. Avez-vous du camembert ?", "Hello! I'd like some cheese for a party, please. Do you have any camembert?"),
        ("Vendeur", "Oui, bien sûr. Combien en voulez-vous ?", "Yes, of course. How much would you like?"),
        ("Client", "J'en voudrais deux cents grammes. Et aussi une douzaine d'œufs.", "I'd like two hundred grams. And also a dozen eggs."),
        ("Vendeur", "Voilà. Avec ceci ?", "Here you are. Anything else with that?"),
        ("Client", "Oui, un kilo de pommes, s'il vous plaît.", "Yes, a kilo of apples, please."),
        ("Vendeur", "Voilà. Vous désirez autre chose ?", "Here you are. Would you like anything else?"),
        ("Client", "Non, ce sera tout. Ça fait combien ?", "No, that will be all. How much does that come to?"),
        ("Vendeur", "Ça fait quinze euros. Vous payez comment ?", "That is fifteen euros. How are you paying?"),
        ("Client", "Par carte. Voilà.", "By card. Here you go."),
        ("Vendeur", "Merci, bonne journée !", "Thank you, have a good day!"),
        ("Client", "Vous aussi, bonne journée ! Au revoir !", "You too, have a good day! Goodbye!"),
    ]),
    ("Version C: customer and shop assistant (costume shop)", [
        ("Client", "Bonjour, je cherche un chapeau pour une soirée déguisée.", "Hello, I'm looking for a hat for a costume party."),
        ("Vendeur", "Quelle couleur préférez-vous ?", "Which colour do you prefer?"),
        ("Client", "Je voudrais un chapeau noir. Vous avez ce modèle en noir ?", "I'd like a black hat. Do you have this style in black?"),
        ("Vendeur", "Nous avons ce modèle en noir et en bleu.", "We have this style in black and in blue."),
        ("Client", "Je peux l'essayer ?", "Can I try it on?"),
        ("Vendeur", "Bien sûr. Il vous plaît ?", "Of course. Do you like it?"),
        ("Client", "Oui, il me plaît. C'est combien ?", "Yes, I like it. How much is it?"),
        ("Vendeur", "Ça coûte vingt euros.", "It costs twenty euros."),
        ("Client", "C'est un peu cher, mais je le prends. Merci, bonne journée !", "It's a bit expensive, but I'll take it. Thank you, have a good day!"),
    ]),
]

BANK = [
    ("Starting naturally", ["Salut ! Ça va ?", "Bonjour ! Je peux vous aider ?", "Alors, on prépare la soirée ?"]),
    ("Proposing and agreeing", ["Je propose une soirée déguisée.", "Bonne idée ! / D'accord ! / Bien sûr !", "Comment trouves-tu cette idée ?", "Je trouve que c'est super."]),
    ("Time, date, place", ["La fête est samedi à dix-neuf heures.", "C'est chez moi.", "C'est le douze mai."]),
    ("Food and drink (partitive)", ["On mange du pain, de la salade, des pâtes.", "On boit du jus d'orange et de l'eau.", "Je ne mange pas de viande."]),
    ("Quantities (+ de)", ["un kilo de tomates", "deux cents grammes de fromage", "une douzaine d'œufs", "une bouteille d'eau", "trop de bonbons / assez de pain / peu de lait"]),
    ("Plans (futur proche, il faut)", ["Je vais acheter le gâteau.", "On va préparer la salade.", "Il faut du fromage.", "Il faut acheter des boissons."]),
    ("Shops and pronouns", ["Tu vas à la boulangerie ? Oui, j'y vais.", "Tu veux du café ? Oui, j'en veux.", "J'en voudrais deux cents grammes."]),
    ("In the shop", ["Je voudrais... / Je cherche... / Vous avez... ?", "Avec ceci ? / Ce sera tout. / Ça fait combien ?", "Vous payez comment ? Par carte.", "Je peux l'essayer ? Je le prends."]),
    ("Costume and clothes", ["Je porte un costume de pirate.", "Je mets une robe rouge et un chapeau noir.", "Nous avons ce modèle en noir."]),
    ("Ending naturally", ["Alors, à samedi !", "Merci, au revoir !", "Merci, bonne journée !"]),
]

GRAMMAR = [
    ("Partitive", "du (m), de la (f), de l' (vowel), des (pl): Je mange du pain. After a negative or a quantity it becomes de / d': Je ne mange pas de viande; beaucoup de fromage."),
    ("Liking verbs", "aimer, adorer, détester, préférer take le / la / les: J'aime le fromage, je préfère les pâtes."),
    ("Futur proche", "aller + infinitive: je vais acheter, tu vas boire, on va préparer, nous allons manger, vous allez choisir, ils vont venir."),
    ("vouloir / pouvoir", "je veux (je voudrais = polite), tu veux, il veut, nous voulons, vous voulez, ils veulent; je peux, tu peux, il peut, nous pouvons, vous pouvez, ils peuvent."),
    ("il faut", "Il faut + noun (Il faut du fromage) or + infinitive (Il faut acheter des boissons)."),
    ("y and en", "y = there (J'y vais demain). en = some / of it, with a quantity (J'en voudrais deux cents grammes; Tu en veux ?)."),
    ("Questions", "Est-ce que tu aimes... ? / Aimes-tu... ? / Qu'est-ce que tu fais ? / À quelle heure ? / Combien de... ? / Quel temps fait-il ?"),
    ("Colours agree", "une robe verte, des chaussures noires, un chapeau noir; orange and marron do not change."),
    ("Demonstratives", "ce chapeau, cet anorak, cette jupe, ces bottes; celui-ci / celle-ci / ceux-ci / celles-ci (this one)."),
    ("Reflexive verbs", "je me lève, tu te lèves, il se lève, nous nous levons, vous vous levez, ils se lèvent; je m'habille."),
    ("Past (passé composé)", "avoir + participle: j'ai mangé, j'ai fini, j'ai vendu. Movement and reflexive verbs use être: je suis allé(e), je me suis levé(e)."),
    ("Comparing", "plus / moins / aussi + adjective + que: Ce manteau est plus cher que ce manteau-là."),
    ("Numbers, time, date", "à sept heures et demie; C'est le douze mai; le premier avril; deux cents grammes (cents loses its s before another number: deux cent un)."),
]

TOPICS = {  # catalog topic titles to print as vocabulary tables for the role-play (FREN152 weeks 6 to 10)
    "Food and drink": ["Breakfast foods", "Drinks", "Lunch, dinner & mains", "Fruit", "Vegetables", "Meat, fish and cold meats", "Sweet things", "Seasonings and sauces", "Milk, bread and breakfast extras", "Meals and courses", "Cheese and fresh produce"],
    "Quantities and shops": ["Quantity words: more", "Shops for food", "Food shops and supermarket sections"],
    "Clothes, colours, costumes": ["Clothing", "More clothes", "Colours", "Light and dark colours", "Materials and accessories", "Clothing styles and shoe shopping"],
    "Plans and parties": ["Appointments and parties", "Dates and birthdays", "Months and seasons"],
}

PLAN = [
    ("Day 1", "Read this guide once. Say the 6 'Identity' answers aloud, with your own details, until they come without looking."),
    ("Day 2", "Daily life answers. Time yourself: each answer 20 to 30 seconds, three or four sentences, ending with 'Et toi ?'."),
    ("Day 3", "Dates, weather and clothes answers. Practise numbers, dates and times by saying today's date and the time in French every hour."),
    ("Day 4", "Food and shops answers. Learn the quantity phrases and the vocabulary tables (food, drinks, shops)."),
    ("Day 5", "Role-play: read Version A aloud as both people, then again with the book closed using only the language bank."),
    ("Day 6", "Role-play with a partner or a voice recording: improvise a new party (a different theme, different food) and a shop scene (Version B or C). Swap roles."),
    ("Day 7", "Mock exam: 5 random course questions each way (you ask, they answer), then a 4 minute role-play, start to finish, without notes."),
]


def table(rows, headers=("Français", "English")):
    body = "".join(f'<tr><td lang="fr">{esc(a)}</td><td lang="en">{esc(b)}</td></tr>' for a, b in rows)
    return f'<table><thead><tr><th scope="col">{headers[0]}</th><th scope="col">{headers[1]}</th></tr></thead><tbody>{body}</tbody></table>'


def build():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    topics = {}
    questions = []
    for w in data["weeks"]:
        qs = []
        for t in w["topics"]:
            topics.setdefault(t["title"], []).append(t)
            for i in t["items"]:
                if "?" in i["fr"] and t["topic_type"] in ("phrase", "grammar"):
                    qs.append((i["fr"], i["en"]))
        if qs:
            questions.append((f'{w["course"]} week {w["week"]}', qs))

    parts = []
    # --- exam facts and strategy
    parts.append("""<section id="exam"><h2>The exam in one page</h2>
<ul>
<li><strong>Weight and time:</strong> 20 percent, week 13, 15 minutes per pair (10 to 12 minutes of actual exam).</li>
<li><strong>Notes, learning aids and dictionaries are prohibited.</strong> Everything below is for studying beforehand.</li>
<li><strong>Task 1, general questions (4 to 5 minutes):</strong> on campus you take turns opening an envelope at random and asking your partner the question inside; when it is your turn to answer, give <em>as much detail as possible</em>. Online, the tutor asks you questions taught during the semester.</li>
<li><strong>Task 2, role-play (4 to 5 minutes):</strong> a birthday party at your place at the weekend. Decide the food and drink (what to buy), and a theme (costume or clothes). Either two friends planning the party, or a customer and a shop assistant. <em>Start and end the conversation naturally.</em></li>
<li><strong>Online:</strong> webcam on the whole time, working microphone, a quiet room.</li>
</ul></section>
<section id="strategy"><h2>How to score well (both tasks)</h2>
<ol>
<li><strong>Answer, add detail, hand it back.</strong> A good answer is three or four short sentences: the direct answer, a detail or a reason, and then <em>Et toi ?</em> or a follow-up question. Short, correct, connected sentences beat long, risky ones.</li>
<li><strong>Use what you were taught:</strong> the vocabulary in the tables below, the partitive, <em>aller + infinitive</em>, <em>vouloir / pouvoir</em>, <em>il faut</em>, <em>y</em> and <em>en</em>, reflexive verbs, the passé composé. Showing a range of taught structures matters as much as being fluent.</li>
<li><strong>Do not go silent.</strong> If you lose a word, say it another way with words you know, or use a filler: <em>Euh...</em>, <em>Alors,</em>, <em>Donc,</em>, <em>En fait,</em>. If you did not hear a question: <em>Pardon ? Pouvez-vous répéter, s'il vous plaît ?</em></li>
<li><strong>Listen to your partner and react</strong> (<em>D'accord ! Bonne idée ! Bien sûr ! Moi aussi, j'aime ça.</em>) and take turns: it is a conversation, not two speeches. Do not take over, and do not let your partner carry everything.</li>
<li><strong>Speak clearly, not fast.</strong> Final consonants are usually silent; link words with liaison (<em>les amis, vous avez</em>); say numbers and dates carefully.</li>
<li><strong>Be ready to be the one who asks.</strong> In Task 1 you read a question aloud to your partner: practise reading each question in this guide aloud with the right rising intonation.</li>
</ol></section>""")
    # --- task 1
    parts.append('<section id="task1"><h2>Task 1: General questions</h2><p class="note">Model answers in simple, correct French. Replace the details in [brackets] with your own, and learn the pattern, not the exact words: the examiner is listening for your own answer. <span class="tag">your own details</span></p>')
    for theme, rows in QA:
        parts.append(f"<h3>{esc(theme)}</h3>")
        parts.append('<div class="qa">')
        for q, fr, en in rows:
            parts.append(f'<div class="card"><p class="q" lang="fr">{esc(q)}</p><p class="a" lang="fr">{esc(fr)}</p><p class="en" lang="en">{esc(en)}</p></div>')
        parts.append("</div>")
    parts.append('<h3>Every question taught in the course (so you can ask them too)</h3><p class="note">From the course word list in Le Champ de Mots, by week. Any of these can come out of an envelope: be able to read each aloud and answer it.</p>')
    for label, qs in questions:
        parts.append(f"<details><summary>{esc(label)} ({len(qs)})</summary>{table(qs)}</details>")
    parts.append("</section>")
    # --- task 2
    parts.append('<section id="task2"><h2>Task 2: Role-play (the birthday party)</h2><p class="note">Pick one version in advance, but be ready for the other: you may be told which at the start. Agree on three things in the conversation: <strong>when and where</strong>, <strong>food and drink</strong> (and who buys what), and a <strong>theme or costume</strong>.</p>')
    parts.append("<h3>Language bank</h3><div class=\"bank\">")
    for title, lines in BANK:
        parts.append(f'<div class="card"><h4>{esc(title)}</h4><ul>' + "".join(f'<li lang="fr">{esc(l)}</li>' for l in lines) + "</ul></div>")
    parts.append("</div>")
    for title, lines in DIALOGUES:
        rows = "".join(f'<tr><th scope="row">{esc(who)}</th><td lang="fr">{esc(fr)}</td><td lang="en">{esc(en)}</td></tr>' for who, fr, en in lines)
        parts.append(f'<h3>{esc(title)}</h3><table class="dialogue"><thead><tr><th scope="col"></th><th scope="col">Français</th><th scope="col">English</th></tr></thead><tbody>{rows}</tbody></table>')
    parts.append('<p class="note">Do not memorise these word for word: a rehearsed script sounds rehearsed and falls apart when your partner says something different. Learn the pieces and rebuild the conversation each time with new food, a new theme and new quantities.</p></section>')
    # --- grammar
    parts.append('<section id="grammar"><h2>Grammar checklist for speaking</h2><table><thead><tr><th scope="col">Point</th><th scope="col">What to say</th></tr></thead><tbody>' + "".join(f"<tr><th scope=\"row\">{esc(a)}</th><td>{esc(b)}</td></tr>" for a, b in GRAMMAR) + "</tbody></table></section>")
    # --- vocabulary
    parts.append('<section id="vocab"><h2>Vocabulary for the role-play</h2><p class="note">Copied from the course word list in Le Champ de Mots, so it is exactly what you were taught.</p>')
    for group, titles in TOPICS.items():
        parts.append(f"<h3>{esc(group)}</h3><div class=\"vocab\">")
        for title in titles:
            for t in topics.get(title, []):
                parts.append(f'<div class="card"><h4>{esc(t["title"])}</h4>{table([(i["fr"], i["en"]) for i in t["items"]])}</div>')
        parts.append("</div>")
    parts.append("</section>")
    # --- plan and check
    parts.append('<section id="plan"><h2>One-week practice plan</h2><table><tbody>' + "".join(f"<tr><th scope=\"row\">{esc(a)}</th><td>{esc(b)}</td></tr>" for a, b in PLAN) + '</tbody></table>')
    parts.append("""<h3>Before you walk in (or log on)</h3><ul class="check"><li>I can introduce myself and talk about my family, where I live, my routine and my weekend in four sentences each.</li>
<li>I can say a date, a time and a number up to a hundred without hesitating.</li>
<li>I can say what I wear, what the weather is like, and what I eat and drink, using du / de la / des.</li>
<li>I can order and buy: Je voudrais..., Avec ceci ?, Ce sera tout, Ça fait combien ?, Par carte.</li>
<li>I can plan with a partner: Je propose..., On mange..., Il faut..., Je vais acheter..., À samedi !</li>
<li>I can ask follow-up questions (Et toi ? Qu'est-ce que tu portes ? Tu vas à la boulangerie ?).</li>
<li>Online: camera, microphone and a quiet room tested; on campus: I know who my partner is.</li></ul></section>""")

    nav = '<nav aria-label="Guide sections"><a href="#exam">The exam</a><a href="#strategy">Strategy</a><a href="#task1">Task 1</a><a href="#task2">Task 2</a><a href="#grammar">Grammar</a><a href="#vocab">Vocabulary</a><a href="#plan">Plan</a></nav>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex">
<title>FREN152 oral exam: study guide</title>
<style>
:root {{ --bg: #f6f7fb; --ink: #1b2033; --soft: #4a5275; --line: #c9cfe4; --panel: #ffffff; --accent: #1f4fa3; --good: #1b6b3a; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #0e1020; --ink: #e8e9f0; --soft: #aab0c8; --line: #343a5a; --panel: #181b2b; --accent: #9dbbff; --good: #7ed39b; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: system-ui, sans-serif; line-height: 1.5; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 1rem 1rem 3rem; }}
h1 {{ margin: 0 0 0.3rem; font-size: 1.6rem; }}
h2 {{ margin: 2rem 0 0.6rem; font-size: 1.3rem; padding-bottom: 0.25rem; border-bottom: 2px solid var(--accent); }}
h3 {{ margin: 1.2rem 0 0.4rem; font-size: 1.05rem; }}
h4 {{ margin: 0 0 0.3rem; font-size: 0.95rem; }}
.note {{ color: var(--soft); }}
nav {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.6rem 0 1rem; }}
nav a {{ padding: 0.35rem 0.8rem; border: 1px solid var(--line); border-radius: 999px; color: var(--accent); text-decoration: none; background: var(--panel); }}
nav a:focus-visible, nav a:hover {{ outline: 2px solid var(--accent); }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 0.6rem 0.8rem; break-inside: avoid; }}
.qa, .bank, .vocab {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr)); gap: 0.7rem; align-items: start; }}
.qa .q {{ font-weight: 700; margin: 0 0 0.3rem; }}
.qa .a {{ margin: 0 0 0.25rem; color: var(--good); }}
.qa .en {{ margin: 0; color: var(--soft); font-size: 0.9rem; }}
.bank ul {{ margin: 0; padding-left: 1.1rem; }}
.tag {{ font-size: 0.78rem; border: 1px solid var(--line); border-radius: 999px; padding: 0 0.5rem; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; background: var(--panel); }}
th, td {{ text-align: left; vertical-align: top; padding: 0.25rem 0.45rem; border-bottom: 1px solid var(--line); }}
thead th {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--soft); }}
table.dialogue th[scope=row] {{ width: 6rem; white-space: nowrap; color: var(--accent); }}
.vocab table td:first-child {{ font-weight: 600; width: 48%; }}
details {{ margin: 0.3rem 0; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 0.3rem 0.6rem; }}
summary {{ cursor: pointer; font-weight: 600; }}
.check li {{ margin: 0.2rem 0; }}
@media print {{
  :root {{ --bg: #fff; --ink: #000; --soft: #333; --line: #999; --panel: #fff; --accent: #000; --good: #000; }}
  nav {{ display: none; }}
  h2 {{ break-before: page; }}
  details {{ break-inside: avoid; }}
  details:not([open]) > :not(summary) {{ display: block; }}
}}
</style>
</head>
<body>
<main>
<h1>FREN152 oral exam: study guide</h1>
<p class="note">Built from your exam instructions and the course word list in Le Champ de Mots. Two tasks in pairs: general questions, then a birthday-party role-play. No notes or dictionaries in the exam, so this is for studying beforehand. Check the exact task details your tutor posts two weeks before.</p>
{nav}
{"".join(parts)}
</main>
</body>
</html>
"""


def main():
    page = build()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text(encoding="utf-8") == page else 1)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
