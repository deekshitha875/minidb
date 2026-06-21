"""
storage.py — Save and load the B-tree to/from disk

We use Python's built-in 'pickle' module to serialize the entire tree
into a binary file. Simple and effective for now.

Later (month 2) we'll replace this with a proper WAL-based approach.
"""

import pickle
import os

DB_FILE = "minidb.db"


def save(tree):
    """Serialize the entire B-tree to disk."""
    with open(DB_FILE, "wb") as f:
        pickle.dump(tree, f)


def load():
    """Load the B-tree from disk. Returns None if no file exists yet."""
    if not os.path.exists(DB_FILE):
        return None
    with open(DB_FILE, "rb") as f:
        return pickle.load(f)
