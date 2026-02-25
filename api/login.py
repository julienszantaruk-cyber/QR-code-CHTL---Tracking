from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import hashlib, os

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "change-me-secret-key")

LOGIN_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>QR Tracker - Connexion</title>
<style>
    body { font-family:system-ui; background:#0d1117; color:#e6edf3; display:flex; justify-content:center; align-items:center; min-height:100vh; margin:0; }
    .card { background:#161b22; padding:2.5rem; border-radius:12px; border:1px solid #30363d; width:340px; }
    h1 { text-align:center; color:#58a6ff; }
    .sub { text-align:center; color:#8b949e; margin-bottom:1.5rem; }
    label { display:block; margin-bottom:4px; color:#8b949e; font-size:.85rem; }
    input { width:100%; padding:10px; background:#0d1117; color:#e6edf3; border:1px solid #30363d; border-radius:6px; margin-bottom:1rem; box-sizing:border-box; }
    button { width:100%; padding:12px; background:#238636; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:bold; font-size:15px; }
    .error { background:#da363340; color:#f85149; padding:10px; border-radius:6px; text-align:center; margin-bottom:1rem; }
</style></head>
<body><div class="card">
    <h1>🔐 QR Tracker</h1>
    <p class="sub">Connecte-toi pour acceder au dashboard</p>
    %%ERROR%%
    <form method="POST" action="/api/login">
        <label>Identifiant</label><input name="username" required>
        <label>Mot de passe</label><input name="password" type="password" required>
        <button>Se connecter</button>
    </form>
</div></body></html>"""

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(LOGIN_HTML.replace("%%ERROR%%", "").encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = parse_qs(body)
        username = params.get("username", [""])[0]
        password = params.get("password", [""])[0]
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            token = hashlib.sha256(f"{ADMIN_PASS}{SESSION_SECRET}".encode()).hexdigest()
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", f"session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(LOGIN_HTML.replace("%%ERROR%%", '<div class="error">Identifiants incorrects</div>').encode())
