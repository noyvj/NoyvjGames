# Radio Decode (slug `radio-decode`, TODO QI-11) - Groundwork Plan

Source: the Quick ideas round (A11), owner-approved: "decode binary, hex and simple ciphers from a drifting signal, each message a short log entry." Checked against `PLAYER-PROFILE.md`: computers and coding as interests, a radio-signal story sketch, quiet tragic-but-gentle characters, notebook-style collecting, short wins forming a story, a hint ladder, working things out themselves, no timers, nothing lost. Personal project, no BCM tag, working title.

Pitch: tune a dial across a quiet band, pick up strange transmissions as bits, hex and cipher text, decode each with a small toolkit and read the short log entry hidden inside.

## 1. Concept
- You are the night listener at a lonely receiving post (invented: Cold Harbour Post). The Band is a dial; stations sit at fixed positions and each carries one message. "Drift" is the dial's own wobble you steady by turning the knob, not a clock: nothing moves by itself and nothing is lost if you leave.
- You capture a message as raw symbols (a bit grid, hex bytes or letters), choose a decoder from the toolkit, set its settings (a shift wheel, a key, a table) and read the result. A correct decode files a log entry in the Logbook.
- 2-minute session: one short message. 20-minute session: a run of eight messages that tell a small story.
- Look: dark receiver panel, glowing scope line, faceted low-poly dial. Quiet voice; the messages come from a lone relay operator, Wren, who is kind, tired and not always right.

## 2. Core rules (pure functions)
- Tuning: the dial position picks a station; static (noise on the display) shrinks as you approach the right value; display noise is a pure function of the offset, never of time. At the right setting the symbols are clean.
- Decoders (the toolkit, handed over, not discovered): Bits to letters (8-bit ASCII grid), Hex to letters, Morse-style dots and dashes, Shift wheel (Caesar), Mirror alphabet (Atbash), Word reverse and Rail fence (2 rails), Keyword shift (Vigenere, key found in an earlier message), Two-step (a chain of two decoders).
- A decode is correct when the player's output equals the plaintext (case and spacing forgiven). The player does the work with helper tools (a bit-column helper, a letter table, a wheel); an Auto-fill is never given except through the Answer rung.
- Messages are 20 to 140 characters of original fiction. Wrong attempts cost nothing; the screen just shows what the player's setting produced.

## 3. Content size
50 messages in 5 bands of 10: Night Band (bits and hex), Dots and Dashes, Shifted Voices (Caesar, Atbash), Cross Wires (rail fence, reverse, two-step), The Long Call (keyword cipher whose keys are in earlier messages). Band n+1 opens at 6 of band n; any order inside. Each band is one short thread of Wren's story, readable in any order; nobody dies on screen.

## 4. How correctness is PROVED
- Round trip: for every message the encoder (dev tool) and decoder round-trip exactly with the stored plaintext and settings.
- Uniqueness: for shift and rail ciphers a brute-force over all settings, filtered by the bundled word list, yields exactly one readable plaintext (the stored one), so a player brute-forcing by hand cannot be fooled.
- Dependency check: the key graph (which message holds which keyword) is acyclic and every keyword message is reachable without needing a later band.
- Determinism: station list, noise function and messages are fixed data; no clock, no random.

## 5. Collection and 100%
- The Logbook: 50 entries in order of band, filled as decoded, with the raw signal kept beside the plaintext; the Toolkit shelf shows each decoder with a card (how it works, one worked example) that fills when first used. A band map of 50 stations lights up. 100% = all 50 decoded. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order. Stats strip: Messages decoded, Decoders found, Bands cleared, Hints. The tally counts tune turns and attempts.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which kind of decoder this looks like and why), Hint (the decoder chosen, settings blank), Answer (the settings filled in and the first word shown). Free, on request.

## 7. Achievements (14)
First Signal; Ten Heard; Twenty-Five Heard; Fifty Heard; Bits and Bytes (all Night Band); Morse Reader; Shift Worker; Cross Wires Done; Long Call Answered; Toolkit Full (all decoders used); Two-Step (a chained decode); Key Keeper (find a keyword in a message and use it); Sharp Ear (10 decodes with no wrong attempt); Late Listener (200 tune turns).

## 8. Real-world facts
The story is fiction. The About page's Sources panel shows the ASCII table and Morse code table read live from the Wikipedia REST service (Wikipedia: ASCII, Morse code) with the read date and a bundled copy as fallback. More game than teaching.

## 9. Reuse
Pure-Python engine with `handle(json)`; `narrative_log.py` and the story toggle for Wren's lines; Lexis's log and message panel idea; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `announcer.js`, `pc-shell.js`; optional `sfx.js` tuning hiss.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Codecs and checks | Encoders and decoders, noise function, band data, band 1 (10 messages) with round-trip and uniqueness tests |
| 2 | Receiver UI | Dial, scope, decoder bench, helper tools, Logbook entry, save contract. Playable slice |
| 3 | Bands 2-3 | 20 more messages, Morse, shift wheel, Atbash, Toolkit shelf |
| 4 | Bands 4-5, hints, goals | 20 more (50), rail, reverse, two-step, keyword ciphers, hint ladder, three-goals strip. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should Wren's thread be a real story with an ending, or only loose log entries? Default: loose threads per band with a short quiet ending line in the last message.
