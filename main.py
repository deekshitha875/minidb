"""
main.py — Command-line interface for MiniDB

Run with:  python main.py

Commands:
  SET key value   — store a value
  GET key         — retrieve a value
  DELETE key      — remove a key
  DISPLAY         — show the tree structure
  EXIT            — quit
"""

from btree import BTree
from storage import save, load
from wal import log_operation, replay, clear


def main():
    # Step 1: Load existing data from disk (or start fresh)
    tree = load()
    if tree is None:
        tree = BTree(t=2)
        print("MiniDB started — new database created.")
    else:
        print("MiniDB started — loaded existing database.")

    # Step 2: Replay WAL — recover any operations lost in a crash
    replay(tree)

    print("Commands: SET key value | GET key | DELETE key | DISPLAY | EXIT\n")

    while True:
        try:
            line = input("minidb> ").strip()
        except (EOFError, KeyboardInterrupt):
            save(tree)
            clear()  # checkpoint: data is safe, clear the log
            print("\nData saved. Bye!")
            break

        if not line:
            continue

        parts = line.split(maxsplit=2)
        cmd = parts[0].upper()

        if cmd == "SET":
            if len(parts) < 3:
                print("Usage: SET key value")
            else:
                log_operation("SET", parts[1], parts[2])  # WAL first
                tree.set(parts[1], parts[2])
                save(tree)
                clear()  # checkpoint after successful save
                print("OK")

        elif cmd == "GET":
            if len(parts) < 2:
                print("Usage: GET key")
            else:
                result = tree.get(parts[1])
                if result is None:
                    print("(nil)")
                else:
                    print(result)

        elif cmd == "DELETE":
            if len(parts) < 2:
                print("Usage: DELETE key")
            else:
                log_operation("DELETE", parts[1])  # WAL first
                tree.delete(parts[1])
                save(tree)
                clear()  # checkpoint after successful save
                print("OK")

        elif cmd == "DISPLAY":
            tree.display()

        elif cmd == "EXIT":
            save(tree)
            clear()
            print("Data saved. Bye!")
            break

        else:
            print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
