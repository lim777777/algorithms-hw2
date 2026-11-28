"""Encode and decode non-negative integers using base62."""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode(n: int) -> str:
    """Return the base62 representation of a non-negative integer."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return ALPHABET[0]

    digits = []
    while n:
        n, remainder = divmod(n, BASE)
        digits.append(ALPHABET[remainder])
    return "".join(reversed(digits))


def decode(s: str) -> int:
    """Return the integer represented by a non-empty base62 string."""
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    if not s:
        raise ValueError("s must not be empty")

    value = 0
    for char in s:
        digit = ALPHABET.find(char)
        if digit == -1:
            raise ValueError(f"invalid base62 character: {char!r}")
        value = value * BASE + digit
    return value
