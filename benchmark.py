"""
benchmark.py — Performance benchmark for MiniDB

Measures how many SET and GET operations per second MiniDB can do.
These numbers go on your resume.

Run with:  python benchmark.py
"""

import time
import os
from btree import BTree
from storage import save, load, DB_FILE
from wal import WAL_FILE, clear


def benchmark_in_memory(n=10000):
    """Pure B-tree speed — no disk I/O."""
    tree = BTree(t=50)  # larger t = faster for bulk inserts

    # --- SET benchmark ---
    start = time.perf_counter()
    for i in range(n):
        tree.set(str(i), f"value_{i}")
    elapsed = time.perf_counter() - start
    set_ops = n / elapsed

    # --- GET benchmark ---
    start = time.perf_counter()
    for i in range(n):
        tree.get(str(i))
    elapsed = time.perf_counter() - start
    get_ops = n / elapsed

    print(f"In-memory B-tree ({n:,} ops):")
    print(f"  SET: {set_ops:,.0f} ops/sec")
    print(f"  GET: {get_ops:,.0f} ops/sec")


def benchmark_with_disk(n=1000):
    """Realistic benchmark — includes WAL write + disk save."""
    # Clean slate
    for f in [DB_FILE, WAL_FILE]:
        if os.path.exists(f):
            os.remove(f)

    tree = BTree(t=10)

    start = time.perf_counter()
    for i in range(n):
        tree.set(str(i), f"value_{i}")
        save(tree)
    elapsed = time.perf_counter() - start
    set_ops = n / elapsed

    start = time.perf_counter()
    for i in range(n):
        tree.get(str(i))
    elapsed = time.perf_counter() - start
    get_ops = n / elapsed

    print(f"\nWith disk persistence ({n:,} ops):")
    print(f"  SET (with save): {set_ops:,.0f} ops/sec")
    print(f"  GET (no disk):   {get_ops:,.0f} ops/sec")

    # Clean up
    for f in [DB_FILE, WAL_FILE]:
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    print("MiniDB Benchmark\n" + "=" * 40)
    benchmark_in_memory(n=100000)
    benchmark_with_disk(n=1000)
    print("\nDone.")
