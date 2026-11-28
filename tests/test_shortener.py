import unittest

from src.shortener import Shortener


class ShortenerContract:
    def test_codes_start_at_zero_and_expand_to_the_original_url(self):
        first = "http://example.com:8080/path"
        second = "https://example.org/%ED%95%9C?q=a%20b&n=1#section"

        self.assertEqual(self.shortener.shorten(first), "0")
        self.assertEqual(self.shortener.shorten(second), "1")
        self.assertEqual(self.shortener.expand("0"), first)
        self.assertEqual(self.shortener.expand("1"), second)

    def test_duplicate_url_reuses_code_without_advancing_counter(self):
        url = "https://example.com"
        self.assertEqual(self.shortener.shorten(url), "0")
        self.assertEqual(self.shortener.shorten(url), "0")
        self.assertEqual(self.shortener.shorten("https://example.org"), "1")

    def test_urls_with_and_without_a_trailing_slash_get_distinct_codes(self):
        original = "https://example.com"
        with_slash = original + "/"
        original_code = self.shortener.shorten(original)
        slash_code = self.shortener.shorten(with_slash)

        self.assertNotEqual(original_code, slash_code)
        self.assertEqual(self.shortener.expand(original_code), original)
        self.assertEqual(self.shortener.expand(slash_code), with_slash)

    def test_unissued_codes_return_none(self):
        self.assertIsNone(self.shortener.expand("0"))
        self.shortener.shorten("https://example.com")
        for code in ("", "00", "1", "!"):
            with self.subTest(code=code):
                self.assertIsNone(self.shortener.expand(code))

    def test_invalid_urls_do_not_advance_counter(self):
        self.assertEqual(self.shortener.shorten("https://example.com"), "0")
        for url in (
            "",
            "example.com/path",
            "http:///path",
            "https://:443/path",
            "ftp://example.com",
            " https://example.com",
            "https://example.com/a b",
            "https://example.com/a\tb",
            "https://example.com/a\r\nb",
            "https://example.com/a\x7f",
            "https://example.com/한글",
            "https://example.com:abc",
            "https://example.com:65536",
            "https://[::1/path",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.shortener.shorten(url)
        self.assertEqual(self.shortener.shorten("https://example.org"), "1")

    def test_url_length_boundary(self):
        prefix = "https://example.com/"
        at_limit = prefix + "a" * (2048 - len(prefix))
        self.assertEqual(self.shortener.shorten(at_limit), "0")
        self.assertEqual(self.shortener.expand("0"), at_limit)

        with self.assertRaises(ValueError):
            self.shortener.shorten(at_limit + "a")
        self.assertEqual(self.shortener.shorten("https://example.org"), "1")

    def test_codes_cross_base62_digit_boundary_and_old_codes_remain_valid(self):
        prefix = "https://example.com/"
        for number in range(61):
            self.shortener.shorten(prefix + str(number))

        self.assertEqual(self.shortener.shorten(prefix + "61"), "Z")
        self.assertEqual(self.shortener.shorten(prefix + "62"), "10")
        self.assertEqual(self.shortener.expand("0"), prefix + "0")
        self.assertEqual(self.shortener.expand("Z"), prefix + "61")
        self.assertEqual(self.shortener.expand("10"), prefix + "62")


class ShortenerTests(ShortenerContract, unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener()
