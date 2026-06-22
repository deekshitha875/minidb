"""
http_server.py -- HTTP API for MiniDB

Makes MiniDB accessible from a browser or any HTTP client.
Uses Python's built-in http.server -- no external libraries needed.

Endpoints:
  GET  /                          -> MiniDB console page
  GET  /get?key=name              -> returns value or "(nil)"
  GET  /set?key=name&value=Alice  -> stores key-value, returns "OK"
  GET  /delete?key=name           -> deletes key, returns "OK"
  GET  /display                   -> shows tree structure

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

# Load or create the database
tree = load()
if tree is None:
    tree = BTree(t=2)
replay(tree)


class MiniDBHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def send_text(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def send_html(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
            self.send_text(200, "\n".join(lines) if lines else "(empty tree)")

        else:
            self.send_text(404, "Not found.")


def collect_display(node, level, lines):
    indent = "  " * level
    keys_only = [k for k, v in node.keys]
    lines.append(f"{indent}[{', '.join(map(str, keys_only))}]")
    for child in node.children:
        collect_display(child, level + 1, lines)


HOME_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MiniDB Console</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 40px 20px; }
    .container { max-width: 600px; margin: 0 auto; }
    h1 { color: #58a6ff; margin-bottom: 6px; }
    p { color: #8b949e; margin-bottom: 30px; font-size: 13px; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
    .card h2 { font-size: 13px; color: #8b949e; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .row { display: flex; gap: 8px; margin-bottom: 8px; }
    input { flex: 1; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; color: #c9d1d9; font-family: monospace; font-size: 14px; }
    input:focus { outline: none; border-color: #58a6ff; }
    button { background: #238636; border: none; border-radius: 6px; padding: 8px 16px; color: white; font-family: monospace; font-size: 14px; cursor: pointer; white-space: nowrap; }
    button:hover { background: #2ea043; }
    button.red { background: #b62324; }
    button.red:hover { background: #cf3131; }
    button.blue { background: #1f6feb; }
    button.blue:hover { background: #388bfd; }
    .result { margin-top: 10px; padding: 10px; background: #0d1117; border-radius: 6px; border-left: 3px solid #58a6ff; font-size: 14px; min-height: 36px; color: #79c0ff; display: none; }
    .result.show { display: block; }
    .result.ok { border-left-color: #2ea043; color: #56d364; }
    .result.err { border-left-color: #f85149; color: #f85149; }
    a { color: #58a6ff; font-size: 12px; }
  </style>
</head>
<body>
<div class="container">
  <h1>MiniDB</h1>
  <p>A key-value database engine built from scratch. B-tree storage, Write-Ahead Log, HTTP server.</p>

  <div class="card">
    <h2>SET - Store a value</h2>
    <div class="row">
      <input id="set-key" placeholder="key" />
      <input id="set-val" placeholder="value" />
      <button onclick="doSet()">SET</button>
    </div>
    <div class="result" id="set-result"></div>
  </div>

  <div class="card">
    <h2>GET - Retrieve a value</h2>
    <div class="row">
      <input id="get-key" placeholder="key" />
      <button class="blue" onclick="doGet()">GET</button>
    </div>
    <div class="result" id="get-result"></div>
  </div>

  <div class="card">
    <h2>DELETE - Remove a key</h2>
    <div class="row">
      <input id="del-key" placeholder="key" />
      <button class="red" onclick="doDelete()">DELETE</button>
    </div>
    <div class="result" id="del-result"></div>
  </div>

  <div class="card">
    <h2>DISPLAY - Show tree structure</h2>
    <button class="blue" onclick="doDisplay()">Show Tree</button>
    <div class="result" id="disp-result" style="white-space:pre;"></div>
  </div>

  <p style="margin-top:20px;">
    Source: <a href="https://github.com/deekshitha875/minidb" target="_blank">github.com/deekshitha875/minidb</a>
  </p>
</div>
<script>
  function show(id, text, type) {
    const el = document.getElementById(id);
    el.textContent = text;
    el.className = 'result show ' + (type || '');
  }
  async function doSet() {
    const key = document.getElementById('set-key').value.trim();
    const val = document.getElementById('set-val').value.trim();
    if (!key || !val) { show('set-result', 'Please enter both key and value.', 'err'); return; }
    const res = await fetch('/set?key=' + encodeURIComponent(key) + '&value=' + encodeURIComponent(val));
    const text = await res.text();
    show('set-result', text, text === 'OK' ? 'ok' : 'err');
  }
  async function doGet() {
    const key = document.getElementById('get-key').value.trim();
    if (!key) { show('get-result', 'Please enter a key.', 'err'); return; }
    const res = await fetch('/get?key=' + encodeURIComponent(key));
    const text = await res.text();
    show('get-result', text, text === '(nil)' ? 'err' : 'ok');
  }
  async function doDelete() {
    const key = document.getElementById('del-key').value.trim();
    if (!key) { show('del-result', 'Please enter a key.', 'err'); return; }
    const res = await fetch('/delete?key=' + encodeURIComponent(key));
    const text = await res.text();
    show('del-result', text, text === 'OK' ? 'ok' : 'err');
  }
  async function doDisplay() {
    const res = await fetch('/display');
    const text = await res.text();
    show('disp-result', text || '(empty tree)', 'ok');
  }
</script>
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
