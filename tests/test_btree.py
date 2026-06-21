"""
test_btree.py — Basic tests for the B-tree

Run this with:  python tests/test_btree.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from btree import BTree


def test_basic_set_get():
    db = BTree(t=2)
    db.set("name", "Alice")
    db.set("age", "20")
    db.set("city", "Delhi")

    assert db.get("name") == "Alice", "name should be Alice"
    assert db.get("age") == "20",     "age should be 20"
    assert db.get("city") == "Delhi", "city should be Delhi"
    assert db.get("missing") is None, "missing key should return None"
    print("PASS: basic set/get")


def test_update():
    db = BTree(t=2)
    db.set("name", "Alice")
    db.set("name", "Bob")  # update existing key
    assert db.get("name") == "Bob", "name should be updated to Bob"
    print("PASS: update existing key")


def test_delete():
    db = BTree(t=2)
    db.set("x", "10")
    db.set("y", "20")
    db.delete("x")
    assert db.get("x") is None, "x should be deleted"
    assert db.get("y") == "20", "y should still exist"
    print("PASS: delete")


def test_many_keys():
    """Insert 100 keys and verify all of them are retrievable."""
    db = BTree(t=3)
    for i in range(100):
        db.set(str(i), f"value_{i}")

    for i in range(100):
        result = db.get(str(i))
        assert result == f"value_{i}", f"key {i} returned wrong value: {result}"
    print("PASS: 100 keys inserted and retrieved correctly")


def test_display():
    """Just make sure display doesn't crash."""
    db = BTree(t=2)
    for k in ["banana", "apple", "cherry", "date", "elderberry"]:
        db.set(k, k.upper())
    print("\nTree structure (display test):")
    db.display()
    print("PASS: display")


if __name__ == "__main__":
    test_basic_set_get()
    test_update()
    test_delete()
    test_many_keys()
    test_display()
    print("\nAll tests passed!")
