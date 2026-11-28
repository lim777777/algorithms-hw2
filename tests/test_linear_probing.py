import unittest

from src.linear_probing import LinearProbingHashTable
from src.shortener import Shortener
from test_hash_table import HashTableContract
from test_shortener import ShortenerContract


class LinearProbingHashTableTests(HashTableContract, unittest.TestCase):
    table_type = LinearProbingHashTable
    empty_lookup_cost = 1

    def test_probe_wraps_from_last_slot_to_zero(self):
        table = LinearProbingHashTable(capacity=4, max_load=None)
        # c, g, k and o start at slot 3.
        for key, value in (("c", 1), ("g", 2), ("k", 3)):
            table.put(key, value)

        self.assertEqual(table.bucket_items(), [[("g", 2)], [("k", 3)], [], [("c", 1)]])
        self.assertEqual(table.find("g"), (True, 2, 2))
        self.assertEqual(table.find("k"), (True, 3, 3))
        self.assertEqual(table.find("o"), (False, None, 4))

    def test_full_fixed_table_stops_after_one_cycle_and_still_updates(self):
        table = LinearProbingHashTable(capacity=3, max_load=None)
        for key, value in (("c", 1), ("f", 2), ("i", 3)):
            table.put(key, value)

        self.assertEqual(len(table), 3)
        self.assertEqual(table.load_factor, 1.0)
        self.assertEqual(table.find("i"), (True, 3, 3))
        self.assertEqual(table.find("l"), (False, None, 3))
        with self.assertRaises(OverflowError):
            table.put("l", 4)
        table.put("f", 20)

        self.assertEqual(table.find("f"), (True, 20, 2))
        self.assertEqual(table.get("c"), 1)
        self.assertEqual(table.get("i"), 3)
        self.assertEqual(len(table), 3)
        self.assertNotIn("l", table)

    def test_growth_is_possible_after_a_table_reaches_one(self):
        table = LinearProbingHashTable(capacity=1, max_load=1)
        table.put("a", 1)
        self.assertEqual(table.load_factor, 1.0)

        table.put("c", 2)
        self.assertEqual(table.load_factor, 1.0)
        self.assertEqual(table.get("a"), 1)
        self.assertEqual(table.get("c"), 2)


class LinearShortenerTests(ShortenerContract, unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener(table_factory=LinearProbingHashTable)

    def test_url_buckets_show_linear_storage_positions(self):
        urls = ("https://naver.com", "https://google.com", "https://yonsei.ac.kr")
        for url in urls:
            self.shortener.shorten(url)

        buckets = self.shortener.url_buckets()
        self.assertEqual(len(buckets), 8)
        self.assertEqual(buckets[3], [(urls[1], "1")])
        self.assertEqual(buckets[4], [(urls[0], "0")])
        self.assertEqual(buckets[5], [(urls[2], "2")])
