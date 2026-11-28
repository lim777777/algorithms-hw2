import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_empty_bucket_returns_default_without_comparisons(self):
        table = HashTable()
        self.assertEqual(len(table), 0)
        self.assertEqual(table.load_factor, 0)
        self.assertEqual(table.find("a"), (False, None, 0))
        self.assertIsNone(table.get("a"))
        self.assertEqual(table.get("a", "missing"), "missing")
        self.assertNotIn("a", table)

    def test_colliding_keys_are_found_in_insertion_order(self):
        table = HashTable()
        # With eight buckets, a, i and q all hash to bucket 1.
        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(len(table), 2)
        self.assertIn("a", table)
        self.assertEqual(table.find("a"), (True, "first", 1))
        self.assertEqual(table.find("i"), (True, "second", 2))
        self.assertEqual(table.find("q"), (False, None, 2))

    def test_horner_hash_depends_on_character_order(self):
        table = HashTable(capacity=11, max_load=None)
        # Horner puts ab and f in bucket 3, and ba and c in bucket 0.
        table.put("ab", "first")
        table.put("ba", "second")

        self.assertEqual(table.find("f"), (False, None, 1))
        self.assertEqual(table.find("c"), (False, None, 1))
        self.assertEqual(table.find("ab"), (True, "first", 1))
        self.assertEqual(table.find("ba"), (True, "second", 1))

    def test_update_and_stored_none_are_distinct_from_a_missing_key(self):
        table = HashTable()
        table.put("a", "original")
        table.put("i", "neighbor")
        table.put("a", None)

        self.assertEqual(len(table), 2)
        self.assertIn("a", table)
        self.assertIsNone(table.get("a", "missing"))
        self.assertEqual(table.find("a"), (True, None, 1))
        self.assertEqual(table.find("i"), (True, "neighbor", 2))
        self.assertNotIn("q", table)
        self.assertEqual(table.get("q", "missing"), "missing")

    def test_growth_occurs_only_above_threshold_and_rehashes_entries(self):
        table = HashTable()
        keys = ("a", "i", "b", "c", "d", "e")
        for key in keys:
            table.put(key, key.upper())

        self.assertEqual(table.load_factor, 0.75)
        self.assertEqual(table.find("i"), (True, "I", 2))

        table.put("b", "updated")
        self.assertEqual(len(table), 6)
        self.assertEqual(table.load_factor, 0.75)

        table.put("f", "F")
        self.assertEqual(len(table), 7)
        self.assertEqual(table.load_factor, 7 / 16)
        self.assertEqual(table.find("i"), (True, "I", 1))
        for key in (*keys, "f"):
            with self.subTest(key=key):
                expected_value = "updated" if key == "b" else key.upper()
                self.assertEqual(table.get(key), expected_value)

    def test_fixed_capacity_allows_load_above_one(self):
        table = HashTable(capacity=2, max_load=None)
        table.put("a", 1)
        table.put("c", 2)
        table.put("e", 3)

        self.assertEqual(len(table), 3)
        self.assertEqual(table.load_factor, 1.5)
        self.assertEqual(table.find("e"), (True, 3, 3))
        self.assertEqual(table.find("g"), (False, None, 3))
