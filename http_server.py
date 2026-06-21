"""
http_server.py — HTTP API for MiniDB

Makes MiniDB accessible from a browser or any HTTP client.
Uses Python's built-in http.server — no external libraries needed.

Endpoints:
  GET  /                        → welcome page + usage
  GET  /get?key=name            → returns value or "(nil)"
  POST /set?key=name&value=Alice → stores key-value, returns "OK"
  POST /delete?key=name         → deletes key, returns "OK"
  GET  /display                 → shows all keys in tree structure

Run with:  python http_server.py
"""

import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from btree import BTree
from storage import save, load
from wal import log_operation, replay, clear

PORT = int(os.environ.get("PORT", 8080))

# Load or create the database (shared across all requests)
tree = load()
if tree is None:
    tree = BTree(t=2)
replay(tree)


class MiniDBHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Custom log format
        print(f"[{self.address_string()}] {format % args}")

    def send_text(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def send_html(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path

        if path == "/":
            self.send_html(200, HOME_PAGE)

        elif path == "/get":
            key = params.get("key", [None])[0]
            if not key:
                self.send_text(400, "ERR: missing ?key=")
                return
            result = tree.get(key)
            self.send_text(200, result if result is not None else "(nil)")

        elif path == "/set":
            key = params.get("key", [None])[0]
            value = params.get("value", [None])[0]
            if not key or value is None:
                self.send_text(400, "ERR: missing ?key= or ?value=")
                return
            log_operation("SET", key, value)
            tree.set(key, value)
            save(tree)
            clear()
            self.send_text(200, "OK")

        elif path == "/delete":
            key = params.get("key", [None])[0]
            if not key:
                self.send_text(400, "ERR: missing ?key=")
                return
            log_operation("DELETE", key)
            tree.delete(key)
            save(tree)
            clear()
            self.send_text(200, "OK")

        elif path == "/display":
            lines = []
            collect_display(tree.root, 0, lines)
            self.send_text(200, "\n".join(lines))

        else:
            self.send_text(404, "Not found. Try GET /get?key=name")

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path

        if path == "/set":
            key = params.get("key", [None])[0]
            value = params.get("value", [None])[0]
            if not key or value is None:
                self.send_text(400, "ERR: missing ?key= or ?value=")
                return
            log_operation("SET", key, value)
            tree.set(key, value)
            save(tree)
            clear()
            self.send_text(200, "OK")

        elif path == "/delete":
            key = params.get("key", [None])[0]
            if not key:
                self.send_text(400, "ERR: missing ?key=")
                return
            log_operation("DELETE", key)
            tree.delete(key)
            save(tree)
            clear()
            self.send_text(200, "OK")

        else:
            self.send_text(404, "Not found.")


def collect_display(node, level, lines):
    indent = "  " * level
    keys_only = [k for k, v in node.keys]
    lines.append(f"{indent}[{', '.join(map(str, keys_only))}]")
    for child in node.children:
        collect_display(child, level + 1, lines)


HOME_PAGE = """<!DOCTYPE html>
<html>
<head>
  <title>MiniDB</title>
  <style>
    body { font-family: monospace; max-width: 700px; margin: 60px auto; background: #0d1117; color: #c9d1d9; padding: 20px; }
    h1 { color: #58a6ff; }
    h2 { color: #8b949e; font-size: 14px; margin-top: 30px; }
    code { background: #161b22; padding: 10px; display: block; border-radius: 6px; margin: 8px 0; color: #79c0ff; }
    a { color: #58a6ff; }
    .tag { background: #21262d; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
  </style>
</head>
<body>
  <h1>MiniDB 🗄️</h1>
  <p>A key-value database engine built from scratch — B-tree storage, Write-Ahead Log, TCP + HTTP server.</p>

  <h2>ENDPOINTS</h2>

  <span class="tag">GET</span> Retrieve a value<br>
  <code>/get?key=name</code>

  <span class="tag">POST</span> Store a value<br>
  <code>/set?key=name&value=Alice</code>

  <span class="tag">POST</span> Delete a key<br>
  <code>/delete?key=name</code>

  <span class="tag">GET</span> Show tree structure<br>
  <code>/display</code>

  <h2>TRY IT</h2>
  <p>
    <a href="/get?key=name">/get?key=name</a><br>
    <a href="/display">/display</a>
  </p>

  <h2>SOURCE</h2>
  <p><a href="https://github.com/deekshitha875/minidb" target="_blank">github.com/deekshitha875/minidb</a></p>
</body>
</html>"""


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), MiniDBHandler)
    print(f"MiniDB HTTP server running on port {PORT}")
    print(f"Open: http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
