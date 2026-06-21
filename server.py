"""
server.py — TCP server for MiniDB

Makes MiniDB a real network service. Any program can connect and
send commands over TCP, just like connecting to Redis or PostgreSQL.

Run with:  python server.py
Connect:   telnet 127.0.0.1 6379   (or use the client below)

Protocol (dead simple):
  Client sends:  "SET name Alice\n"
  Server replies: "OK\n"

  Client sends:  "GET name\n"
  Server replies: "Alice\n"
"""

import socket
import threading
from btree import BTree
from storage import save, load
from wal import log_operation, replay, clear

HOST = "127.0.0.1"
PORT = 6379  # same default port as Redis (easy to remember)


def handle_client(conn, addr, tree, lock):
    """Handle one connected client in its own thread."""
    print(f"[+] Client connected: {addr}")
    with conn:
        buffer = ""
        while True:
            try:
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    break  # client disconnected
                buffer += data

                # Process all complete lines (commands end with \n)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    response = process_command(line, tree, lock)
                    conn.sendall((response + "\n").encode("utf-8"))

            except (ConnectionResetError, BrokenPipeError):
                break

    print(f"[-] Client disconnected: {addr}")


def process_command(line, tree, lock):
    """Parse and execute one command. Returns response string."""
    parts = line.split(maxsplit=2)
    if not parts:
        return "ERR empty command"

    cmd = parts[0].upper()

    with lock:  # thread-safe access to the tree
        if cmd == "SET":
            if len(parts) < 3:
                return "ERR usage: SET key value"
            log_operation("SET", parts[1], parts[2])
            tree.set(parts[1], parts[2])
            save(tree)
            clear()
            return "OK"

        elif cmd == "GET":
            if len(parts) < 2:
                return "ERR usage: GET key"
            result = tree.get(parts[1])
            return result if result is not None else "(nil)"

        elif cmd == "DELETE":
            if len(parts) < 2:
                return "ERR usage: DELETE key"
            log_operation("DELETE", parts[1])
            tree.delete(parts[1])
            save(tree)
            clear()
            return "OK"

        else:
            return f"ERR unknown command: {cmd}"


def main():
    # Load existing data
    tree = load()
    if tree is None:
        tree = BTree(t=2)
        print("MiniDB server — new database.")
    else:
        print("MiniDB server — loaded existing database.")

    replay(tree)

    lock = threading.Lock()  # protects tree from concurrent writes

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"MiniDB listening on {HOST}:{PORT}")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr, tree, lock))
            t.daemon = True
            t.start()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
