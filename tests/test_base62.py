import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(decode("0"), 0)

    def test_digit_order_and_place_values(self):
        for number, code in (
            (9, "9"),
            (10, "a"),
            (35, "z"),
            (36, "A"),
            (61, "Z"),
            (62, "10"),
            (63, "11"),
            (3843, "ZZ"),
            (3844, "100"),
        ):
            with self.subTest(number=number, code=code):
                self.assertEqual(encode(number), code)
                self.assertEqual(decode(code), number)

    def test_large_integer_round_trip(self):
        number = 10**100 + 12345
        self.assertEqual(decode(encode(number)), number)

    def test_encode_rejects_negative_integer(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_encode_rejects_non_integers(self):
        for value in (1.5, "62", True):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode(value)

    def test_decode_rejects_empty_string_and_invalid_characters(self):
        for code in ("", "a!", "a b", "가", "0\n"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    decode(code)

    def test_decode_rejects_non_strings(self):
        for value in (62, b"10", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    decode(value)
