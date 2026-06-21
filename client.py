"""
client.py — Simple TCP client for MiniDB

Run with:  python client.py

This connects to the MiniDB server and lets you type commands
just like main.py, but over the network.
"""

import socket

HOST = "127.0.0.1"
PORT = 6379


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
        except ConnectionRefusedError:
            print(f"Could not connect to MiniDB server at {HOST}:{PORT}")
            print("Make sure the server is running: python server.py")
            return

        print(f"Connected to MiniDB at {HOST}:{PORT}")
        print("Commands: SET key value | GET key | DELETE key | quit\n")

        while True:
            try:
                line = input("minidb> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not line:
                continue
            if line.lower() == "quit":
                break

            s.sendall((line + "\n").encode("utf-8"))
            response = s.recv(4096).decode("utf-8").strip()
            print(response)


if __name__ == "__main__":
    main()
