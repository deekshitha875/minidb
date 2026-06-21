# MiniDB

A minimal key-value database engine built from scratch in Python.  
Supports crash recovery, disk persistence, and a TCP server interface.

---

## Features

- **B-tree storage** — O(log n) SET, GET, DELETE operations
- **Disk persistence** — data survives process restarts
- **Write-Ahead Log (WAL)** — crash recovery, no data loss
- **TCP server** — connect from any program over the network
- **Benchmarked** — see performance numbers below

---

## Project Structure

```
minidb/
├── btree.py       # B-tree implementation (core data structure)
├── storage.py     # Serialize/deserialize tree to disk
├── wal.py         # Write-Ahead Log for crash recovery
├── main.py        # Interactive CLI
├── server.py      # TCP server (multi-client, threaded)
├── client.py      # TCP client
├── benchmark.py   # Performance benchmarks
└── tests/
    ├── test_btree.py   # B-tree correctness tests
    └── test_wal.py     # Crash recovery tests
```

---

## Quick Start

**CLI mode:**
```bash
python main.py
```
```
minidb> SET name Alice
OK
minidb> GET name
Alice
minidb> DELETE name
OK
minidb> EXIT
```

**Server mode** (two terminals):
```bash
# Terminal 1 — start the server
python server.py

# Terminal 2 — connect a client
python client.py
```

---

## Design Decisions

### Why a B-tree?

A B-tree keeps keys sorted and the tree balanced automatically.  
Each node holds multiple keys, so the tree stays shallow — meaning
fewer comparisons to find any key. For a database with millions of
records, `GET` still takes roughly 20-30 comparisons.

Alternative considered: **LSM-tree** (used by LevelDB, RocksDB).  
LSM-trees are faster for writes but slower for reads, and require
a background compaction process. B-tree was chosen here because it's
simpler to implement correctly and reads are more common in typical
workloads.

### Why a Write-Ahead Log?

Without a WAL, a crash mid-write leaves the database file in an
unknown state — some keys written, some not. The WAL solves this:

1. Write the intended operation to the log **first**
2. Apply it to the main data file
3. Clear the log entry after a successful save

On restart, any unfinished operations in the log are replayed.
This is the same approach used by PostgreSQL, SQLite, and MySQL.

### Why pickle for storage?

`pickle` is Python's built-in serialization — simple and fast for
prototyping. A production system would use a custom binary format
(like SQLite's page format) to allow partial reads and writes
without loading the entire database into memory.

---

## Performance

Run `python benchmark.py` to see results on your machine.

Benchmarked on Windows (Python 3.14, 100,000 in-memory ops / 1,000 disk ops):

| Operation | In-memory | With disk persistence |
|-----------|-----------|----------------------|
| SET       | 23,772 ops/sec | 1,156 ops/sec |
| GET       | 44,399 ops/sec | 169,279 ops/sec |

The disk bottleneck is expected — each SET rewrites the full database
file. A production B-tree uses fixed-size pages and only rewrites
changed pages.

---

## Running Tests

```bash
python tests/test_btree.py
python tests/test_wal.py
```

---

## What I Learned

- How B-trees maintain sorted order and balance through node splits
- Why databases use Write-Ahead Logging instead of writing directly
- How TCP servers handle multiple clients using threads
- The performance tradeoff between durability and throughput
