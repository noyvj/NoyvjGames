#!/usr/bin/python3
"""Check and freeze three packs of sourced claims for new Chronicle sets (dev tool, never run by the game).

Packs (CH-12 and R4-CLP-5): history-of-food, ancient-greece, history-of-computing. Each claim names three or more public pages. For every page this script
fetches it (one request, a polite pause), requires HTTP 200 and requires the page text to match every pattern listed for it (the date, the name: what the
claim needs), then writes data/<pack>.json with the claims in the sample set's format (games/chronicle/sets/presidents-sample/claims.json and sources.json),
the read date, and for each page the status and the patterns that were found.
All sentences here are original wording; a note is a short neutral summary of what the page says, never a quotation.
The rule of the game: every claim has at least three sources from at least two institutions or authors (the checks run again in tests/test_source_packs_snapshot.py).
Not included, because three real pages could not be reached: see the report's list (for instance the oldest-bread find, the Columbian Exchange, canning, pasteurisation).
Pages that refused this script (HTTP 403 for Britannica, the Smithsonian, the Library of Congress) were NOT used: nothing here was taken on trust.

Usage: python3 tools/fetch_source_packs.py [--read YYYY-MM-DD] [--only pack-id]      (stdlib only; about 2 minutes for all three packs)
"""
import argparse
import datetime
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/; checking public pages for a history game, one request each)"

# source id: (title, institution or author, url, kind, patterns the page text must contain)
SOURCES = {
    "chm-lovelace": ("Ada Lovelace (Babbage Engine)", "Computer History Museum", "https://www.computerhistory.org/babbage/adalovelace/", "museum", ["1843", "Analytical Engine"]),
    "bodleian-lovelace": ("Ada Lovelace: celebrating 200 years of a computer visionary", "Bodleian Libraries, University of Oxford", "https://blogs.bodleian.ox.ac.uk/adalovelace/", "library", ["1843", "Analytical Engine"]),
    "smg-babbage": ("Charles Babbage's Difference Engines and the Science Museum", "Science Museum Group", "https://www.sciencemuseum.org.uk/objects-and-stories/charles-babbages-difference-engines-and-science-museum", "museum", ["In 1843, Lovelace published an account of the Analytical Engine"]),
    "penn-eniac": ("ENIAC (Penn Engineering history)", "University of Pennsylvania, School of Engineering and Applied Science", "https://www.seas.upenn.edu/about/history-heritage/eniac/", "university", ["February 14, 1946", "first general-purpose electronic computer"]),
    "ethw-eniac": ("Milestones: Electronic Numerical Integrator and Computer, 1946", "IEEE, Engineering and Technology History Wiki", "https://ethw.org/Milestones:Electronic_Numerical_Integrator_and_Computer,_1946", "society", ["14 February 1946", "New York Times"]),
    "chm-eniac": ("ENIAC (CHM Revolution)", "Computer History Museum", "https://www.computerhistory.org/revolution/birth-of-the-computer/4/78", "museum", ["February 15, 1946", "front-page news"]),
    "chm-transistor": ("1947: Invention of the Point-Contact Transistor (The Silicon Engine)", "Computer History Museum", "https://www.computerhistory.org/siliconengine/invention-of-the-point-contact-transistor/", "museum", ["December 1947", "Bardeen", "Brattain"]),
    "ethw-transistor": ("Milestones: Invention of the First Transistor at Bell Telephone Laboratories, Inc., 1947", "IEEE, Engineering and Technology History Wiki", "https://ethw.org/Milestones:Invention_of_the_First_Transistor_at_Bell_Telephone_Laboratories,_Inc.,_1947", "society", ["17 November to 23 December 1947", "Brattain"]),
    "nobel-shockley": ("William B. Shockley: Facts (Nobel Prize in Physics 1956)", "Nobel Prize Outreach", "https://www.nobelprize.org/prizes/physics/1956/shockley/facts/", "archive", ["1947 John Bardeen and Walter Brattain", "transistor"]),
    "sim-baby": ("Baby and modern computing", "Science and Industry Museum, Manchester", "https://www.scienceandindustrymuseum.org.uk/objects-and-stories/baby-and-modern-computing", "museum", ["21 June 1948", "stored-program"]),
    "manchester-cs": ("History and heritage, Department of Computer Science", "The University of Manchester", "https://www.cs.manchester.ac.uk/about-us/history/", "university", ["21 June 1948", "stored-program"]),
    "chm-1948": ("1948 (Timeline of Computer History)", "Computer History Museum", "https://www.computerhistory.org/timeline/1948/", "museum", ["June 21st, 1948", "Manchester"]),
    "ethw-arpanet": ("Milestones: Birthplace of the Internet, 1969", "IEEE, Engineering and Technology History Wiki", "https://ethw.org/Milestones:Birthplace_of_the_Internet,_1969", "society", ["29 October 1969", "Stanford Research Institute"]),
    "chm-internet-60s": ("Internet History: the 1960s", "Computer History Museum", "https://www.computerhistory.org/internethistory/1960s/", "museum", ["October 29, 1969", "UCLA to SRI"]),
    "sri-arpanet": ("ARPANET (SRI History of Innovation)", "SRI International", "https://www.sri.com/hoi/arpanet/", "research institute", ["October 29, 1969", "UCLA attempted to send a message to SRI"]),
    "ibm-pc": ("The IBM PC (IBM history)", "IBM", "https://www.ibm.com/history/personal-computer", "company archive", ["August 12, 1981", "IBM PC"]),
    "chm-1981": ("1981 (Timeline of Computer History)", "Computer History Museum", "https://www.computerhistory.org/timeline/1981/", "museum", ["IBM introduces its Personal Computer"]),
    "chm-ibm-pc": ("The IBM PC (CHM Revolution)", "Computer History Museum", "https://www.computerhistory.org/revolution/personal-computers/17/301", "museum", ["IBM introduced its PC in 1981"]),
    "isoc-history": ("A Brief History of the Internet", "Internet Society", "https://www.internetsociety.org/internet/history-internet/brief-history-internet/", "society", ["NCP to TCP/IP as of January 1, 1983"]),
    "rfc801": ("RFC 801: NCP/TCP transition plan", "RFC Editor (Internet Engineering Task Force documents)", "https://www.rfc-editor.org/rfc/rfc801", "standards body", ["1 January 1983", "NCP"]),
    "chm-internet-80s": ("Internet History: the 1980s", "Computer History Museum", "https://www.computerhistory.org/internethistory/1980s/", "museum", ["standardizes on the TCP/IP protocols"]),
    "w3c-proposal": ("Information Management: A Proposal (HTMLized original)", "World Wide Web Consortium (W3C)", "https://www.w3.org/History/1989/proposal.html", "standards body", ["March 1989", "Tim Berners-Lee", "CERN"]),
    "cern-www-history": ("WWW Project History", "CERN", "https://info.cern.ch/hypertext/WWW/History.html", "research institute", ["March 1989", "First project proposal"]),
    "w3c-history": ("A Little History of the World Wide Web", "World Wide Web Consortium (W3C)", "https://www.w3.org/History.html", "standards body", ["1989 March", "Information Management: A Proposal"]),
    "fda-milestones": ("Milestones in U.S. Food and Drug Law", "U.S. Food and Drug Administration", "https://www.fda.gov/about-fda/fda-history/milestones-us-food-and-drug-law", "agency", ["Pure Food and Drugs Act", "1906"]),
    "fda-100": ("Promoting Safe and Effective Drugs for 100 Years", "U.S. Food and Drug Administration", "https://www.fda.gov/about-fda/histories-product-regulation/promoting-safe-effective-drugs-100-years", "agency", ["Pure Food and Drugs Act was passed by Congress in 1906", "Theodore Roosevelt"]),
    "house-pure-food": ("The Pure Food and Drugs Act", "U.S. House of Representatives, History, Art and Archives", "https://history.house.gov/Historical-Highlights/1901-1950/Pure-Food-and-Drug-Act/", "archive", ["June 29th", "signed the Pure Food and Drugs Act into law the next day"]),
    "nobel-haber": ("Fritz Haber: Facts (Nobel Prize in Chemistry 1918)", "Nobel Prize Outreach", "https://www.nobelprize.org/prizes/chemistry/1918/haber/facts/", "archive", ["for the synthesis of ammonia from its elements", "received his Nobel Prize one year later, in 1919"]),
    "shi-haber": ("Fritz Haber (Scientific Biographies)", "Science History Institute", "https://www.sciencehistory.org/education/scientific-biographies/fritz-haber/", "museum", ["1918 Nobel Prize in Chemistry", "mass production of agricultural fertilizers"]),
    "nobel-haber-lecture": ("Fritz Haber: Nobel Lecture, The Synthesis of Ammonia from Its Elements", "Nobel Prize Outreach", "https://www.nobelprize.org/prizes/chemistry/1918/haber/lecture/", "archive", ["The Synthesis of Ammonia from Its Elements"]),
    "nobel-borlaug-facts": ("Norman Borlaug: Facts (Nobel Peace Prize 1970)", "Nobel Prize Outreach", "https://www.nobelprize.org/prizes/peace/1970/borlaug/facts/", "archive", ["Nobel Peace Prize 1970", "Norman Borlaug"]),
    "nobel-peace-1970": ("The Nobel Peace Prize 1970", "Nobel Prize Outreach", "https://www.nobelprize.org/prizes/peace/1970/summary/", "archive", ["The Nobel Peace Prize 1970 was awarded to Norman"]),
    "tamu-borlaug": ("Norman Borlaug Institute for International Agriculture and Development", "Texas A&M University", "https://borlaug.tamu.edu/", "university", ["1970 Nobel Prize winner", "Green Revolution"]),
    "whe-socrates": ("Socrates", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Socrates/", "encyclopedia", ["In 399 BCE Socrates was charged with impiety"]),
    "sep-socrates": ("Socrates", "Stanford Encyclopedia of Philosophy, Stanford University", "https://plato.stanford.edu/entries/socrates/", "encyclopedia", ["Socrates’s trial and execution", "399"]),
    "iep-socrates": ("Socrates", "Internet Encyclopedia of Philosophy (University of Tennessee at Martin)", "https://iep.utm.edu/socrates/", "encyclopedia", ["Socrates (469—399 B.C.E.)"]),
    "whe-marathon": ("Battle of Marathon", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Battle_of_Marathon/", "encyclopedia", ["September 490 BCE", "Darius I"]),
    "livius-marathon": ("Marathon (490 BCE)", "Jona Lendering, Livius.org", "https://www.livius.org/articles/battle/marathon-490-bce/", "encyclopedia", ["Marathon (490 BCE)", "Persian invasion force"]),
    "hh-marathon": ("Marathon: From the battlefield to the sanctuary of the Egyptian gods", "Hellenic Heritage", "https://www.hh.gr/en/?p=2011", "heritage site", ["in 490 BC, the Athenians and their allies defeated the vast Persian army"]),
    "whe-thermopylae": ("Battle of Thermopylae", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Battle_of_Thermopylae/", "encyclopedia", ["August 480 BCE", "Leonidas"]),
    "livius-thermopylae": ("Thermopylae (480 BCE)", "Jona Lendering, Livius.org", "https://www.livius.org/articles/battle/thermopylae-480-bce/", "encyclopedia", ["Thermopylae (480 BCE)", "Xerxes"]),
    "whe-themistocles": ("Themistocles", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Themistocles/", "encyclopedia", ["In August 480 BCE the Persian army was met at the mountain pass of Thermopylae", "Salamis"]),
    "whe-salamis": ("Battle of Salamis", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Battle_of_Salamis/", "encyclopedia", ["September 480 BCE", "Saronic Gulf"]),
    "livius-salamis": ("Salamis (480 BCE)", "Jona Lendering, Livius.org", "https://www.livius.org/articles/battle/salamis-480-bce/", "encyclopedia", ["Naval Battle of Salamis (29 September 480)"]),
    "whe-parthenon": ("Parthenon: Temple of Athena Parthenos", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Parthenon/", "encyclopedia", ["built between 447 and 432 BCE"]),
    "ysma-parthenon": ("Parthenon", "Acropolis Restoration Service (YSMA), Greek Ministry of Culture", "https://ysma.gr/en/monuments/parthenon/", "heritage agency", ["lasted from 447 to 438 B.C."]),
    "whe-pericles": ("Pericles", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Pericles/", "encyclopedia", ["the Parthenon , begun in 447 BCE"]),
    "whe-cleisthenes": ("Cleisthenes", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Cleisthenes/", "encyclopedia", ["reforms c. 508 BCE"]),
    "livius-cleisthenes": ("Cleisthenes", "Jona Lendering, Livius.org", "https://www.livius.org/articles/person/cleisthenes/", "encyclopedia", ["508/507", "Isagoras"]),
    "whe-athenian-democracy": ("Athenian Democracy", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Athenian_Democracy/", "encyclopedia", ["c. 508 BCE Reforms by Cleisthenes establishes democracy in Athens"]),
    "whe-alexander": ("Alexander the Great", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Alexander_the_Great/", "encyclopedia", ["10 or 11 June 323 BCE"]),
    "livius-alexander": ("Alexander the Great", "Jona Lendering, Livius.org", "https://www.livius.org/articles/person/alexander-the-great/", "encyclopedia", ["on 11 June, he died"]),
    "whe-diadochi": ("Wars of the Diadochi", "World History Encyclopedia (World History Publishing)", "https://www.worldhistory.org/Wars_of_the_Diadochi/", "encyclopedia", ["On June 10, 323 BCE Alexander the Great died in Babylon"]),
}

# pack: claims; each claim: id, event id, date value, claim text, confidence, sources [(source id, note)]
PACKS = {
    "history-of-computing": [
        ("c-e-lovelace-notes", "e-lovelace-notes", "Ada Lovelace publishes her paper on the Analytical Engine", "1843",
         "In 1843 Ada Lovelace published a paper on Charles Babbage's unbuilt Analytical Engine.", "documented",
         [("chm-lovelace", "Dates the Lovelace work on the Analytical Engine to 1843."),
          ("bodleian-lovelace", "Says her 1843 paper about Babbage's unbuilt Analytical Engine holds the table of formulae sometimes called the first programme."),
          ("smg-babbage", "States that Lovelace published an account of the Analytical Engine in 1843.")]),
        ("c-e-eniac-announced", "e-eniac-announced", "ENIAC is announced to the public", "1946-02-14",
         "ENIAC, the first general-purpose electronic computer, was announced to the public on 14 February 1946 and was front-page news in The New York Times the next day.", "documented",
         [("penn-eniac", "Says ENIAC was originally announced on 14 February 1946 and calls it the first general-purpose electronic computer."),
          ("ethw-eniac", "Says the New York Times announced the unveiling of the machine on 14 February 1946."),
          ("chm-eniac", "Puts the front-page New York Times story on 15 February 1946, one day later than the other two pages date the announcement.")]),
        ("c-e-transistor", "e-transistor", "Bardeen and Brattain achieve transistor action", "1947-12",
         "In December 1947 John Bardeen and Walter Brattain, working at Bell Telephone Laboratories, achieved transistor action in a germanium point-contact device.", "documented",
         [("chm-transistor", "Names Bardeen and Brattain and gives December 1947 for transistor action in a germanium point-contact device."),
          ("ethw-transistor", "Gives 17 November to 23 December 1947 at Bell Laboratories for the work of Brattain and Bardeen under Shockley."),
          ("nobel-shockley", "Gives 1947 for the semiconductor amplifier of Bardeen and Brattain, later named the transistor; no month.")]),
        ("c-e-baby", "e-baby", "The Manchester Baby runs the first stored program", "1948-06-21",
         "The Manchester Baby, the first stored-program electronic computer, ran its first program on 21 June 1948.", "documented",
         [("sim-baby", "Gives 21 June 1948 for the first program run by Baby, written by Kilburn."),
          ("manchester-cs", "Gives 21 June 1948 for the first successful program run of the machine built by Williams and Kilburn."),
          ("chm-1948", "Gives 21 June 1948 for the first program to run on an electronic stored-program computer at Manchester.")]),
        ("c-e-arpanet-first", "e-arpanet-first", "The first message crosses the ARPANET", "1969-10-29",
         "On 29 October 1969 the first message was sent over the ARPANET, from UCLA to the Stanford Research Institute.", "documented",
         [("ethw-arpanet", "Gives 10:30 p.m. on 29 October 1969 for the first ARPANET message, sent from UCLA to the Stanford Research Institute."),
          ("chm-internet-60s", "Records the first host-to-host connection, UCLA to SRI, on 29 October 1969."),
          ("sri-arpanet", "Gives 10:30 p.m. on 29 October 1969 for the first transmission, when UCLA tried to send a message to SRI.")]),
        ("c-e-ibm-pc", "e-ibm-pc", "IBM unveils the IBM PC", "1981-08-12",
         "IBM unveiled its Personal Computer, the IBM PC, on 12 August 1981 in New York.", "documented",
         [("ibm-pc", "Gives 12 August 1981 for the unveiling of the IBM PC at a New York hotel; the only one of the three that gives the day."),
          ("chm-1981", "Lists the introduction of IBM's Personal Computer under 1981; no day."),
          ("chm-ibm-pc", "Says IBM introduced its PC in 1981; no day.")]),
        ("c-e-tcpip-switch", "e-tcpip-switch", "The ARPANET switches to TCP/IP", "1983-01-01",
         "The ARPANET changed over from the NCP protocol to TCP/IP on 1 January 1983.", "documented",
         [("isoc-history", "Describes the changeover of the ARPANET host protocol from NCP to TCP/IP as of 1 January 1983, in a single flag-day."),
          ("rfc801", "The 1981 plan for the changeover; it sets 1 January 1983 as the date for a complete switch from NCP to TCP."),
          ("chm-internet-80s", "Says the ARPANET standardised on TCP/IP in January 1983.")]),
        ("c-e-web-proposal", "e-web-proposal", "Berners-Lee writes the proposal that becomes the Web", "1989-03",
         "In March 1989 Tim Berners-Lee wrote and circulated at CERN the proposal \"Information Management: A Proposal\", the first proposal for what became the World Wide Web.", "documented",
         [("w3c-proposal", "Holds the proposal itself, written by Tim Berners-Lee at CERN in March 1989 and recirculated in May 1990."),
          ("cern-www-history", "Lists the first project proposal, written and circulated for comment, in March 1989."),
          ("w3c-history", "Dates the writing and circulation of the proposal at CERN to March 1989.")]),
    ],
    "history-of-food": [
        ("c-e-pure-food-act", "e-pure-food-act", "The Pure Food and Drugs Act becomes law", "1906-06-30",
         "President Theodore Roosevelt signed the Pure Food and Drugs Act into law on 30 June 1906.", "documented",
         [("house-pure-food", "Says the House approved the conference report on 29 June and that the President signed the law the next day."),
          ("fda-100", "Says Congress passed the original Pure Food and Drugs Act in 1906 and that President Roosevelt signed it; no day."),
          ("fda-milestones", "Lists the Pure Food and Drugs Act among the 1906 milestones of US food and drug law; no day.")]),
        ("c-e-haber-prize", "e-haber-prize", "Haber is honoured for making ammonia from its elements", "1918",
         "The Nobel Prize in Chemistry for 1918, presented to Fritz Haber in 1919, honoured his synthesis of ammonia from its elements, the basis of mass-produced agricultural fertiliser.", "documented",
         [("nobel-haber", "Gives the prize motivation as the synthesis of ammonia from its elements and says Haber received the prize a year later, in 1919."),
          ("shi-haber", "Says the synthesis earned Haber the 1918 prize and enabled mass production of agricultural fertilisers."),
          ("nobel-haber-lecture", "Hosts the Nobel lecture titled The Synthesis of Ammonia from Its Elements.")]),
        ("c-e-borlaug-prize", "e-borlaug-prize", "Norman Borlaug wins the Nobel Peace Prize", "1970",
         "Norman Borlaug, whose wheat breeding is tied to the Green Revolution, was awarded the Nobel Peace Prize in 1970.", "documented",
         [("nobel-borlaug-facts", "Lists Norman Borlaug as the laureate of the Nobel Peace Prize 1970."),
          ("nobel-peace-1970", "States that the Nobel Peace Prize 1970 was awarded to Norman Borlaug."),
          ("tamu-borlaug", "Calls Borlaug the 1970 Nobel Prize winner and father of the Green Revolution; it does not describe the wheat work.")]),
    ],
    "ancient-greece": [
        ("c-e-athenian-democracy", "e-athenian-democracy", "Cleisthenes reforms Athens", "-0508",
         "Around 508 BCE the Athenian politician Cleisthenes introduced reforms that set up democracy in Athens.", "documented",
         [("whe-cleisthenes", "Dates his reorganisation of the citizen body to about 508 BCE."),
          ("livius-cleisthenes", "Places the election of his rival Isagoras in 508/507 and his reforms as the answer to it; the year is given as a pair."),
          ("whe-athenian-democracy", "Lists the reforms of Cleisthenes about 508 BCE as the establishment of democracy in Athens.")]),
        ("c-e-marathon", "e-marathon", "The Athenians win at Marathon", "-0490",
         "In 490 BCE the Athenians and their allies defeated a Persian force at Marathon.", "documented",
         [("whe-marathon", "Places the battle on the plain of Marathon in September 490 BCE, against the army of Darius I."),
          ("livius-marathon", "Dates the clash between a Persian invasion force and an Athenian army to 490 BCE."),
          ("hh-marathon", "Says the Athenians and their allies defeated the Persian army at Marathon in 490 BC.")]),
        ("c-e-thermopylae", "e-thermopylae", "The Greeks hold the pass at Thermopylae", "-0480",
         "A Greek force led by the Spartan king Leonidas fought the invading Persian army at the pass of Thermopylae in 480 BCE.", "documented",
         [("whe-thermopylae", "Places the best-known battle at Thermopylae in August 480 BCE."),
          ("livius-thermopylae", "Dates the famous Spartan defeat by the Persians at Thermopylae to 480."),
          ("whe-themistocles", "Says the Persian army met a small Greek band under Leonidas at Thermopylae in August 480 BCE.")]),
        ("c-e-salamis", "e-salamis", "The Greek fleet wins at Salamis", "-0480-09",
         "The Greek fleet defeated the Persian navy in the strait of Salamis in September 480 BCE.", "documented",
         [("whe-salamis", "Places the naval battle in the Saronic Gulf in September 480 BCE."),
          ("livius-salamis", "Gives 29 September 480 for the naval battle, a Greek victory over the Persian navy."),
          ("whe-themistocles", "Says the combined Greek fleet gathered at Salamis in September 480 BCE.")]),
        ("c-e-parthenon", "e-parthenon", "Work begins on the Parthenon", "-0447",
         "Construction of the Parthenon on the Acropolis of Athens began in 447 BCE.", "documented",
         [("whe-parthenon", "Says the temple was built between 447 and 432 BCE."),
          ("ysma-parthenon", "Says the construction of the temple lasted from 447 to 438 BC; the carved pediments were finished in 432."),
          ("whe-pericles", "Says the building of the Parthenon, led under Pericles, began in 447 BCE.")]),
        ("c-e-socrates-trial", "e-socrates-trial", "Socrates is tried and put to death", "-0399",
         "Socrates was tried and put to death in Athens in 399 BCE.", "documented",
         [("whe-socrates", "Says that in 399 BCE Socrates was charged with impiety and that his accusers sought the death penalty."),
          ("sep-socrates", "Places the trial and execution of Socrates in the spring and summer of 399."),
          ("iep-socrates", "Gives his life dates as 469 to 399 BCE; its article covers the trial and the death.")]),
        ("c-e-alexander-dies", "e-alexander-dies", "Alexander the Great dies in Babylon", "-0323-06",
         "Alexander the Great died in Babylon in June 323 BCE.", "documented",
         [("whe-alexander", "Gives 10 or 11 June 323 BCE for his death."),
          ("livius-alexander", "Says he fell ill at the end of May and died on 11 June."),
          ("whe-diadochi", "Gives 10 June 323 BCE for his death in Babylon.")]),
    ],
}
PACK_TITLES = {"history-of-computing": "A history of computing", "history-of-food": "A history of food", "ancient-greece": "Ancient Greece"}
PACK_ITEMS = {"history-of-computing": "R4-CLP-5", "history-of-food": "CH-12", "ancient-greece": "CH-12"}


def fetch(url):
    time.sleep(1.5)
    for wait in (0, 10, 40, 90):
        time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=60) as reply:
                return reply.status, reply.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            if err.code != 429 and err.code < 500:
                return err.code, ""
        except OSError as err:
            return 0, str(err)
    return 429, ""                      # still refusing after three tries


def page_text(raw):
    raw = re.sub(r"<(script|style).*?</\1>", "", raw, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def check(sid, read, cache):
    title, who, url, kind, patterns = SOURCES[sid]
    if sid not in cache:
        status, raw = fetch(url)
        text = page_text(raw)
        cache[sid] = (status, text)
    status, text = cache[sid]
    missing = [p for p in patterns if re.sub(r"\s+", " ", p) not in text]
    if status != 200 or missing:
        raise SystemExit("source %s (%s): HTTP %s, missing %s" % (sid, url, status, missing))
    return {"title": title, "institution": who, "url": url, "read": read, "kind": kind, "http_status": status, "text_checked_for": patterns}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    ap.add_argument("--only")
    args = ap.parse_args(argv)
    cache = {}
    (GAME / "data").mkdir(exist_ok=True)
    for pack, claims in PACKS.items():
        if args.only and args.only != pack:
            continue
        used = sorted({sid for c in claims for sid, _ in c[6]})
        sources = {sid: check(sid, args.read, cache) for sid in used}
        out_claims, events = [], []
        for cid, event, event_title, date, text, confidence, srcs in claims:
            out_claims.append({"id": cid, "subject": event, "field": "date", "value": date, "text": text, "confidence": confidence,
                               "sources": [{"source": s, "note": n} for s, n in srcs]})
            events.append({"id": event, "kind": "event", "title": event_title, "date": date, "claim": cid})
        data = {"topic": pack, "title": PACK_TITLES[pack], "item": PACK_ITEMS[pack], "read": args.read,
                "format": "claims and sources as in sets/presidents-sample/claims.json and sources.json; events are proposals (id, title, date) without seq, place or people",
                "events": events, "sources": sources, "claims": out_claims}
        (GAME / "data" / (pack + ".json")).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote data/%s.json: %d claims, %d sources" % (pack, len(out_claims), len(sources)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
