"""String-key hash table with separate chaining."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar


Value = TypeVar("Value")


def horner_hash(key: str, capacity: int) -> int:
    """Return the starting bucket for a string key."""
    if not isinstance(key, str):
        raise TypeError("hash table keys must be strings")

    index = 0
    for char in key:
        index = (31 * index + ord(char)) % capacity
    return index


@dataclass(slots=True)
class _Node(Generic[Value]):
    key: str
    value: Value
    next: _Node[Value] | None = None


class HashTable(Generic[Value]):
    """Keep colliding entries in a linked list in each bucket."""

    def __init__(self, capacity: int = 8, max_load: float | None = 0.75):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if max_load is not None and not 0 < max_load < float("inf"):
            raise ValueError("max_load must be positive and finite")

        self._buckets: list[_Node[Value] | None] = [None] * capacity
        self._size = 0
        self._max_load = max_load

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: str) -> bool:
        found, _, _ = self.find(key)
        return found

    @property
    def load_factor(self) -> float:
        return self._size / len(self._buckets)

    def put(self, key: str, value: Value) -> None:
        """Insert a new key at the end of its chain or update an existing key."""
        index = horner_hash(key, len(self._buckets))
        node = self._buckets[index]
        tail = None
        while node is not None:
            if node.key == key:
                node.value = value
                return
            tail = node
            node = node.next

        entry = _Node(key, value)
        if tail is None:
            self._buckets[index] = entry
        else:
            tail.next = entry
        self._size += 1

        if self._max_load is not None and self.load_factor > self._max_load:
            self._grow()

    def get(self, key: str, default=None):
        found, value, _ = self.find(key)
        return value if found else default

    def find(self, key: str) -> tuple[bool, Value | None, int]:
        """Return whether a key exists, its value, and the node comparisons."""
        index = horner_hash(key, len(self._buckets))
        node = self._buckets[index]
        comparisons = 0
        while node is not None:
            comparisons += 1
            if node.key == key:
                return True, node.value, comparisons
            node = node.next
        return False, None, comparisons

    def _grow(self) -> None:
        capacity = 2 * len(self._buckets)
        buckets: list[_Node[Value] | None] = [None] * capacity
        tails: list[_Node[Value] | None] = [None] * capacity

        for head in self._buckets:
            node = head
            while node is not None:
                following = node.next
                index = horner_hash(node.key, capacity)
                node.next = None
                tail = tails[index]
                if tail is None:
                    buckets[index] = node
                else:
                    tail.next = node
                tails[index] = node
                node = following

        self._buckets = buckets
