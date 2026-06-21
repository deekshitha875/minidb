"""
wal.py — Write-Ahead Log (WAL) for crash recovery

How it works:
  1. Before every SET/DELETE, we FIRST write the operation to a log file
  2. Then we apply it to the B-tree and save to disk
  3. If the program crashes between step 1 and 2, on next startup
     we replay the log to finish what was interrupted

This guarantees no data is ever lost due to a crash.

Log format (one operation per line, JSON):
  {"op": "SET", "key": "name", "value": "Alice"}
  {"op": "DELETE", "key": "name"}
"""

import json
import os

WAL_FILE = "minidb.wal"


def log_operation(op, key, value=None):
    """Append one operation to the WAL before applying it."""
    entry = {"op": op, "key": key}
    if value is not None:
        entry["value"] = value

    with open(WAL_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()          # make sure it hits disk immediately
        os.fsync(f.fileno())  # force OS to write to physical disk


def replay(tree):
    """
    On startup, read the WAL and re-apply any operations that
    didn't make it into the main data file before a crash.
    """
    if not os.path.exists(WAL_FILE):
        return  # no log, nothing to replay

    replayed = 0
    with open(WAL_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry["op"] == "SET":
                    tree.set(entry["key"], entry["value"])
                elif entry["op"] == "DELETE":
                    tree.delete(entry["key"])
                replayed += 1
            except (json.JSONDecodeError, KeyError):
                pass  # skip corrupted lines

    if replayed > 0:
        print(f"WAL recovery: replayed {replayed} operation(s).")


def clear():
    """
    Clear the WAL after a successful checkpoint (full save to disk).
    Once data is safely in the main file, the log is no longer needed.
    """
    if os.path.exists(WAL_FILE):
        open(WAL_FILE, "w").close()  # truncate to empty
