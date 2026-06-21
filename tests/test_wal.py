"""
test_wal.py — Test WAL crash recovery

Simulates a crash: writes to WAL but never saves to disk,
then replays the WAL on a fresh tree and verifies data is recovered.

Run with:  python tests/test_wal.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from btree import BTree
from wal import log_operation, replay, clear, WAL_FILE


def test_crash_recovery():
    # Clean up from any previous run
    if os.path.exists(WAL_FILE):
        os.remove(WAL_FILE)

    # --- Simulate a crash ---
    # We log operations to WAL but never call save() or clear()
    # This is what happens if the program crashes mid-write
    log_operation("SET", "name", "Alice")
    log_operation("SET", "age", "20")
    log_operation("SET", "city", "Delhi")
    log_operation("DELETE", "age")
    # <-- program "crashes" here, main db file was never updated

    # --- Simulate restart ---
    # Fresh tree (as if we just loaded an empty/old db file)
    fresh_tree = BTree(t=2)

    # Replay the WAL — should recover all operations
    replay(fresh_tree)

    assert fresh_tree.get("name") == "Alice", "name should be recovered"
    assert fresh_tree.get("age") is None,     "age was deleted, should be None"
    assert fresh_tree.get("city") == "Delhi", "city should be recovered"

    print("PASS: crash recovery via WAL replay")

    # Clean up
    clear()


if __name__ == "__main__":
    test_crash_recovery()
    print("\nAll WAL tests passed!")
