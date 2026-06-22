"""
http_server.py -- HTTP API for MiniDB + Developer Bio Cards app

Endpoints:
  GET  /              -> Developer Bio Cards page
  GET  /db            -> MiniDB raw API page
  GET  /get?key=      -> get a value
  GET  /set?key=&value= -> set a value
  GET  /delete?key=   -> delete a value
  GET  /display       -> show tree structure
  GET  /devs          -> return all developer cards as JSON
  POST /submit        -> submit a new developer bio card
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

    def send_json(self, code, data):
        body = json.dumps(data)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def send_html(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path

        if path == "/":
            self.send_html(200, DEVCARD_PAGE)

        elif path == "/db":
            self.send_html(200, DB_PAGE)

        elif path == "/devs":
            # Return all developer cards as JSON
            count_raw = tree.get("devs:count")
            count = int(count_raw) if count_raw else 0
            devs = []
            for i in range(1, count + 1):
                raw = tree.get(f"dev:{i}")
                if raw:
                    try:
                        devs.append(json.loads(raw))
                    except Exception:
                        pass
            self.send_json(200, devs)

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

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/submit":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                name = data.get("name", "").strip()
                skills = data.get("skills", "").strip()
                github = data.get("github", "").strip()
                bio = data.get("bio", "").strip()

                if not name or not skills:
                    self.send_json(400, {"error": "Name and skills are required."})
                    return

                # Get current count and increment
                count_raw = tree.get("devs:count")
                count = int(count_raw) if count_raw else 0
                count += 1

                card = {"id": count, "name": name, "skills": skills,
                        "github": github, "bio": bio}

                # Save to MiniDB
                log_operation("SET", f"dev:{count}", json.dumps(card))
                tree.set(f"dev:{count}", json.dumps(card))
                log_operation("SET", "devs:count", str(count))
                tree.set("devs:count", str(count))
                save(tree)
                clear()

                self.send_json(200, {"success": True, "id": count})

            except (json.JSONDecodeError, Exception) as e:
                self.send_json(400, {"error": str(e)})

        else:
            self.send_text(404, "Not found.")


def collect_display(node, level, lines):
    indent = "  " * level
    keys_only = [k for k, v in node.keys]
    lines.append(f"{indent}[{', '.join(map(str, keys_only))}]")
    for child in node.children:
        collect_display(child, level + 1, lines)


# ------------------------------------------------------------------
# Developer Bio Cards Page
# ------------------------------------------------------------------
DEVCARD_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DevCards - Powered by MiniDB</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; }

    header { background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
    header h1 { color: #58a6ff; font-size: 20px; }
    header span { font-size: 12px; color: #8b949e; }

    .main { max-width: 1000px; margin: 0 auto; padding: 30px 20px; }

    .submit-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 24px; margin-bottom: 32px; }
    .submit-card h2 { color: #f0f6fc; font-size: 16px; margin-bottom: 16px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .form-grid .full { grid-column: 1 / -1; }
    input, textarea { width: 100%; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 10px 12px; color: #c9d1d9; font-family: inherit; font-size: 14px; }
    input:focus, textarea:focus { outline: none; border-color: #58a6ff; }
    textarea { resize: vertical; min-height: 70px; }
    .submit-btn { margin-top: 14px; background: #238636; border: none; border-radius: 6px; padding: 10px 24px; color: white; font-size: 14px; cursor: pointer; font-family: inherit; }
    .submit-btn:hover { background: #2ea043; }
    .msg { margin-top: 10px; font-size: 13px; display: none; }
    .msg.ok { color: #56d364; display: block; }
    .msg.err { color: #f85149; display: block; }

    .section-title { font-size: 14px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }

    .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }

    .dev-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; transition: border-color 0.2s; }
    .dev-card:hover { border-color: #58a6ff; }
    .dev-name { font-size: 16px; font-weight: 600; color: #f0f6fc; margin-bottom: 6px; }
    .dev-bio { font-size: 13px; color: #8b949e; margin-bottom: 12px; line-height: 1.5; }
    .skills { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
    .skill-tag { background: #21262d; border: 1px solid #30363d; border-radius: 20px; padding: 3px 10px; font-size: 12px; color: #79c0ff; }
    .github-link { font-size: 12px; color: #58a6ff; text-decoration: none; }
    .github-link:hover { text-decoration: underline; }
    .no-cards { color: #8b949e; font-size: 14px; text-align: center; padding: 40px; }

    footer { text-align: center; padding: 24px; font-size: 12px; color: #8b949e; border-top: 1px solid #30363d; margin-top: 40px; }
    footer a { color: #58a6ff; text-decoration: none; }
  </style>
</head>
<body>

<header>
  <h1>DevCards</h1>
  <span>Powered by MiniDB &nbsp;|&nbsp; <a href="/db" style="color:#58a6ff;">DB Console</a></span>
</header>

<div class="main">

  <!-- Submit Form -->
  <div class="submit-card">
    <h2>Add Your Developer Card</h2>
    <div class="form-grid">
      <input id="f-name" placeholder="Your name *" />
      <input id="f-skills" placeholder="Skills (e.g. Python, React) *" />
      <input id="f-github" placeholder="GitHub URL (optional)" />
      <div></div>
      <textarea id="f-bio" class="full" placeholder="Short bio (optional)"></textarea>
    </div>
    <button class="submit-btn" onclick="submitCard()">Add My Card</button>
    <div class="msg" id="submit-msg"></div>
  </div>

  <!-- Cards Grid -->
  <div class="section-title" id="cards-title">Developer Cards</div>
  <div class="cards-grid" id="cards-grid">
    <div class="no-cards">Loading...</div>
  </div>
</div>

<footer>
  Built with <a href="https://github.com/deekshitha875/minidb" target="_blank">MiniDB</a> - a key-value database engine built from scratch
</footer>

<script>
  async function loadCards() {
    const grid = document.getElementById('cards-grid');
    const title = document.getElementById('cards-title');
    try {
      const res = await fetch('/devs');
      const devs = await res.json();
      title.textContent = `Developer Cards (${devs.length})`;
      if (devs.length === 0) {
        grid.innerHTML = '<div class="no-cards">No cards yet. Be the first to add yours!</div>';
        return;
      }
      grid.innerHTML = devs.reverse().map(d => `
        <div class="dev-card">
          <div class="dev-name">${esc(d.name)}</div>
          ${d.bio ? `<div class="dev-bio">${esc(d.bio)}</div>` : ''}
          <div class="skills">
            ${d.skills.split(',').map(s => `<span class="skill-tag">${esc(s.trim())}</span>`).join('')}
          </div>
          ${d.github ? `<a class="github-link" href="${esc(d.github)}" target="_blank">GitHub</a>` : ''}
        </div>
      `).join('');
    } catch(e) {
      grid.innerHTML = '<div class="no-cards">Failed to load cards.</div>';
    }
  }

  async function submitCard() {
    const name = document.getElementById('f-name').value.trim();
    const skills = document.getElementById('f-skills').value.trim();
    const github = document.getElementById('f-github').value.trim();
    const bio = document.getElementById('f-bio').value.trim();
    const msg = document.getElementById('submit-msg');

    if (!name || !skills) {
      msg.textContent = 'Name and skills are required.';
      msg.className = 'msg err';
      return;
    }

    try {
      const res = await fetch('/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, skills, github, bio })
      });
      const data = await res.json();
      if (data.success) {
        msg.textContent = 'Card added successfully!';
        msg.className = 'msg ok';
        document.getElementById('f-name').value = '';
        document.getElementById('f-skills').value = '';
        document.getElementById('f-github').value = '';
        document.getElementById('f-bio').value = '';
        loadCards();
      } else {
        msg.textContent = data.error || 'Something went wrong.';
        msg.className = 'msg err';
      }
    } catch(e) {
      msg.textContent = 'Failed to submit.';
      msg.className = 'msg err';
    }
  }

  function esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  loadCards();
</script>
</body>
</html>"""


# ------------------------------------------------------------------
# Raw DB Console Page
# ------------------------------------------------------------------
DB_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
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
    button { background: #238636; border: none; border-radius: 6px; padding: 8px 16px; color: white; font-family: monospace; font-size: 14px; cursor: pointer; }
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
  <h1>MiniDB Console</h1>
  <p>Raw key-value database interface. <a href="/">Back to DevCards</a></p>

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
