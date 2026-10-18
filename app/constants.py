"""Length caps shared by several request models. Layer 1: imports nothing from this app."""


# Text-length caps on public write routes (the body-size limit in main.py is the
# backstop; these keep one row from being megabytes of text).
ID_MAX_LENGTH = 64
TEXT_MAX_LENGTH = 5000
