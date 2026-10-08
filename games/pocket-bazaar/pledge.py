"""Pocket Bazaar -- the pledge, in the player's own words, shown on the About page.

This file is the ONE place the words the pledge rules out may appear in the game's text, because it is where the game
names them to promise it will not do them. tests/test_pledge.py scans every other player-visible string for those words.
"""

PLEDGE = (
    "No energy, lives, stamina or hearts. Nothing runs out; you can play for exactly as long as you like.",
    "No real-money purchases and no premium currency. There is one currency, coins, and you earn it only by playing.",
    "No timers that decide when you may play. Customers wait in beats (your own actions), so nothing expires while "
    "you are away or the tab is in the background.",
    "No daily-login rewards, no streaks that punish a missed day, no fake scarcity or countdown banners, no guilt "
    "when you leave.",
    "No ads inside the game. The only ad is the labelled bar at the foot of the page.",
    "Your stall is saved after every action, so closing the tab never loses progress.",
    "Every day can be finished: Sell and the Broom always work, so the counter can never jam.",
    "Difficulty is in the open: each festival says whether it makes the day harder, and nothing gets quietly harder "
    "to sell you help.",
)

# The words the pledge rules out, for the test that keeps them out of everything else.
BANNED_WORDS = ("energy", "lives", "stamina", "refill", "gems", "premium", "watch an ad", "limited time", "hurry")
