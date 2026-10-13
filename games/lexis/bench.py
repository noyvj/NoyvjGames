"""Lexis -- Number bench: convert and add Pulse numbers with binary switches."""


def pulse_to_int(marks):
    """Convert a Pulse number mark (e.g., '0101') to an integer."""
    if len(marks) != 4 or marks[0] != "0":
        raise ValueError("Invalid Pulse number")
    return int(marks[1:], 2)


def int_to_pulse(n):
    """Convert an integer (0-7) to a Pulse number mark."""
    if not 0 <= n <= 7:
        raise ValueError("Number out of range")
    return "0" + format(n, "03b")


def add_pulses(a_marks, b_marks):
    """Add two Pulse numbers and return the result as a Pulse mark, or None if overflow."""
    a = pulse_to_int(a_marks)
    b = pulse_to_int(b_marks)
    s = a + b
    if s > 7:
        return None
    return int_to_pulse(s)
