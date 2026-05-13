from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import hashlib
import hmac
import os
import html

# === Variables obligatoires (plus de fallback faible) ===
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ["ADMIN_PASS"]
SESSION_SECRET = os.environ["SESSION_SECRET"]

MAX_BODY_SIZE = 4 * 1024  # 4 KB suffisent largement pour un form de login

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
        <label>Identifiant</label><input name="username" required autocomplete="username">
        <label>Mot de passe</label><input name="password" type="password" required autocomplete="current-password">
        <button>Se connecter</button>
    </form>
</div></body></html>"""


def make_session_token() -> str:
    return hashlib.sha256(f"{ADMIN_PASS}{SESSION_SECRET}".encode()).hexdigest()


def constant_time_eq(a: str, b: str) -> bool:
    """Comparaison en temps constant pour bloquer les timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


class handler(BaseHTTPRequestHandler):
    def _render(self, error_html: str = "", status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(LOGIN_HTML.replace("%%ERROR%%", error_html).encode())

    def do_GET(self) -> None:
        self._render()

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_SIZE:
            return self._render(
                '<div class="error">Requete invalide</div>', status=400
            )

        try:
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            params = parse_qs(body)
        except Exception:
            return self._render('<div class="error">Requete invalide</div>', status=400)

        username = params.get("username", [""])[0]
        password = params.get("password", [""])[0]

        # Comparaison en temps constant des deux champs
        user_ok = constant_time_eq(username, ADMIN_USER)
        pass_ok = constant_time_eq(password, ADMIN_PASS)

        if user_ok and pass_ok:
            token = make_session_token()
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header(
                "Set-Cookie",
                f"session={token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=86400",
            )
            self.end_headers()
        else:
            # On n'expose JAMAIS si c'est le user ou le pass qui est faux
            self._render(
                '<div class="error">Identifiants incorrects</div>', status=401
            )
