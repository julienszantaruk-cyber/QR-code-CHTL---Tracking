from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import os
import uuid
import hashlib
from supabase import create_client, Client

# === Configuration (variables obligatoires, plus de défaut faible) ===
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]  # ⚠️ Doit être la service_role key
ADMIN_PASS = os.environ["ADMIN_PASS"]
SESSION_SECRET = os.environ["SESSION_SECRET"]

# === Limites de sécurité ===
MAX_LABEL_LENGTH = 200
MAX_URL_LENGTH = 2000
MAX_BODY_SIZE = 10 * 1024  # 10 KB suffisent largement

# === Client Supabase mis en cache ===
_db: Client | None = None


def get_db() -> Client:
    global _db
    if _db is None:
        _db = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _db


def check_auth(cookie_header: str | None) -> bool:
    """Vérifie le cookie de session admin."""
    if not cookie_header:
        return False
    try:
        cookies = dict(
            c.strip().split("=", 1)
            for c in cookie_header.split(";")
            if "=" in c
        )
    except Exception:
        return False
    expected = hashlib.sha256(
        f"{ADMIN_PASS}{SESSION_SECRET}".encode()
    ).hexdigest()
    # Comparaison en temps constant pour éviter les timing attacks
    return hashlib.compare_digest(cookies.get("session", ""), expected)


def is_safe_url(url: str) -> bool:
    """N'accepte que http(s) avec un hostname valide."""
    if not url or len(url) > MAX_URL_LENGTH:
        return False
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


class handler(BaseHTTPRequestHandler):
    def _redirect(self, location: str, status: int = 303) -> None:
        self.send_response(status)
        self.send_header("Location", location)
        self.end_headers()

    def do_POST(self) -> None:
        # 1) Auth
        if not check_auth(self.headers.get("Cookie", "")):
            return self._redirect("/api/login")

        # 2) Lecture du body avec limite de taille
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_SIZE:
            return self._redirect("/?error=invalid")

        try:
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            params = parse_qs(body)
        except Exception:
            return self._redirect("/?error=parse")

        label = params.get("label", [""])[0].strip()[:MAX_LABEL_LENGTH]
        target_url = params.get("target_url", [""])[0].strip()

        # 3) Validation
        if not label or not is_safe_url(target_url):
            return self._redirect("/?error=validation")

        # 4) Insertion
        try:
            db = get_db()
            qr_id = uuid.uuid4().hex[:8]
            db.table("qr_codes").insert({
                "id": qr_id,
                "label": label,
                "target_url": target_url,
            }).execute()
        except Exception as e:
            # Log côté Vercel mais ne pas exposer l'erreur au client
            print(f"[create] DB error: {e}")
            return self._redirect("/?error=db")

        return self._redirect("/?ok=1")
