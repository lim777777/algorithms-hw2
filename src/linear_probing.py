"""String-key hash table with open addressing and linear probing."""

from typing import Generic

from .hash_table import Value, horner_hash


class LinearProbingHashTable(Generic[Value]):
    """Store one entry per slot and inspect consecutive slots on collision."""

    def __init__(self, capacity: int = 8, max_load: float | None = 0.75):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if max_load is not None and not 0 < max_load <= 1:
            raise ValueError("max_load must be in (0, 1]")

        self._slots: list[tuple[str, Value] | None] = [None] * capacity
        self._size = 0
        self._max_load = max_load

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: str) -> bool:
        found, _, _ = self.find(key)
        return found

    @property
    def load_factor(self) -> float:
        return self._size / len(self._slots)

    def put(self, key: str, value: Value) -> None:
        """Insert or update a key. A full fixed table rejects new keys."""
        index, _ = self._locate(key)
        if index is not None and self._slots[index] is not None:
            self._slots[index] = (key, value)
            return

        if self._max_load is not None and (self._size + 1) / len(self._slots) > self._max_load:
            self._grow()
            index, _ = self._locate(key)
        if index is None:
            raise OverflowError("linear probing table is full")

        self._slots[index] = (key, value)
        self._size += 1

    def get(self, key: str, default=None):
        found, value, _ = self.find(key)
        return value if found else default

    def find(self, key: str) -> tuple[bool, Value | None, int]:
        """Return whether a key exists, its value, and the slots inspected."""
        index, probes = self._locate(key)
        if index is not None:
            entry = self._slots[index]
            if entry is not None:
                return True, entry[1], probes
        return False, None, probes

    def bucket_items(self) -> list[list[tuple[str, Value]]]:
        """Copy the slots in the same format as the chained hash table."""
        return [[] if entry is None else [entry] for entry in self._slots]

    def _locate(self, key: str) -> tuple[int | None, int]:
        """Find the key or the first empty slot, counting either one as a probe."""
        capacity = len(self._slots)
        start = horner_hash(key, capacity)
        for offset in range(capacity):
            index = (start + offset) % capacity
            entry = self._slots[index]
            if entry is None or entry[0] == key:
                return index, offset + 1
        return None, capacity

    def _grow(self) -> None:
        old_slots = self._slots
        self._slots = [None] * (2 * len(old_slots))
        for entry in old_slots:
            if entry is not None:
                index, _ = self._locate(entry[0])
                assert index is not None  # The new table has space for every old entry.
                self._slots[index] = entry
