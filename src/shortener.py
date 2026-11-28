"""Issue sequential base62 codes for HTTP and HTTPS URLs."""

from urllib.parse import urlsplit

from .base62 import encode
from .hash_table import HashTable


MAX_URL_LENGTH = 2048


def _validate_url(url: str) -> None:
    if not isinstance(url, str) or not 0 < len(url) <= MAX_URL_LENGTH:
        raise ValueError(f"URL must be a string of 1 to {MAX_URL_LENGTH} characters")
    if any(not 33 <= ord(char) <= 126 for char in url):
        raise ValueError("URL must use printable ASCII without spaces")

    try:
        parts = urlsplit(url)
        # Reading the port also validates its format and range.
        _ = parts.port
    except ValueError as error:
        raise ValueError("URL has an invalid host or port") from error
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("URL must use HTTP or HTTPS and include a host")


class Shortener:
    """Store both directions of a URL-to-code mapping in memory."""

    def __init__(self):
        self._url_to_code: HashTable[str] = HashTable()
        self._code_to_url: HashTable[str] = HashTable()
        self._next_number = 0

    def shorten(self, url: str) -> str:
        _validate_url(url)
        existing = self._url_to_code.get(url)
        if existing is not None:
            return existing

        code = encode(self._next_number)
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        self._next_number += 1
        return code

    def expand(self, code: str) -> str | None:
        return self._code_to_url.get(code)
