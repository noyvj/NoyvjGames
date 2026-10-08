"""The story's words obey the design's promise: nothing frightening, nothing cruel, every gate reachable, every
gift attached to a letter, every sailor with something to say."""

import re

import lore

BANNED = re.compile(r"\b(death|dead|die|dies|died|dying|corpse|blood\w*|bleed\w*|murder\w*|kill\w*|scream\w*|drown\w*|stab\w*|gore|ghost\w*|haunt\w*|"
                    r"horror|terror|slaughter\w*|suicid\w*|grave\w*|wound\w*|torture\w*|victim\w*)\b", re.I)


def all_strings():
    for s in lore.SAILORS.values():
        yield from (s["name"], s["role"], s["blurb"])
    for letter in lore.LETTERS.values():
        yield letter["subject"]
        yield letter["text"]
        for reply in letter.get("replies", ()):
            yield from reply[1:]
    for g in lore.GIFTS.values():
        yield g["name"]
        yield g["text"]
    yield lore.CONTENT_NOTE


def test_no_banned_word_anywhere_in_the_shipped_story():
    for text in all_strings():
        assert not BANNED.search(text), text


def test_no_em_dashes_or_exclamation_overload():
    for text in all_strings():
        assert "—" not in text and "–" not in text, text
    assert sum(t.count("!") for t in all_strings()) <= 6


def test_letters_are_a_good_length_and_every_sailor_writes():
    for lid, letter in lore.LETTERS.items():
        words = len(letter["text"].split())
        assert 30 <= words <= 120, (lid, words)
        assert letter["from"] in lore.SAILORS and letter["subject"]
    written = {item["from"] for item in lore.LETTERS.values()}
    ashore_and_story_later = {"hesper", "berit"}
    assert set(lore.SAILORS) - written <= ashore_and_story_later


def test_gates_refer_to_real_letters_and_never_loop():
    for lid, letter in lore.LETTERS.items():
        after = letter["gate"].get("after")
        if after:
            assert after in lore.LETTERS and lore.LETTERS[after]["from"] in lore.SAILORS
            chain, cur = {lid}, after
            while cur:
                assert cur not in chain, lid
                chain.add(cur)
                cur = lore.LETTERS[cur]["gate"].get("after")


def test_replies_have_ids_labels_and_answers():
    for lid, letter in lore.LETTERS.items():
        ids = [r[0] for r in letter.get("replies", ())]
        assert len(ids) == len(set(ids)) and len(ids) in (0, 2), lid
        for r in letter.get("replies", ()):
            assert len(r) == 3 and all(isinstance(x, str) and x for x in r)


def test_every_gift_comes_from_exactly_one_letter_and_has_a_slot():
    attached = [item["gift"] for item in lore.LETTERS.values() if item.get("gift")]
    assert sorted(attached) == sorted(lore.GIFTS)
    for g in lore.GIFTS.values():
        assert g["slot"] in ("shelf", "table", "wall", "window", "floor")


def test_the_cast_is_flawed_and_specific_not_all_good():
    assert len(lore.SAILORS) >= 8
    blurbs = " ".join(s["blurb"] for s in lore.SAILORS.values())
    assert len({s["name"] for s in lore.SAILORS.values()}) == len(lore.SAILORS)
    assert "bad at it" in blurbs and "never catches" in blurbs.lower()
