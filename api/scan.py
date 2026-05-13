from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import re
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# uuid.uuid4().hex[:8] => 8 chars hexa, on valide strictement
QR_ID_PATTERN = re.compile(r"^[a-f0-9]{8}$")

_db: Client | None = None


def get_db() -> Client:
    global _db
    if _db is None:
        _db = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _db


class handler(BaseHTTPRequestHandler):
    def _error(self, status: int, msg: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<h1>{msg}</h1>".encode())

    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        qr_id = query.get("id", [""])[0].strip().lower()

        if not QR_ID_PATTERN.match(qr_id):
            return self._error(400, "ID invalide")

        try:
            db = get_db()
            result = (
                db.table("qr_codes")
                .select("target_url")
                .eq("id", qr_id)
                .limit(1)
                .execute()
            )
        except Exception as e:
            print(f"[scan] DB lookup error: {e}")
            return self._error(500, "Erreur serveur")

        if not result.data:
            return self._error(404, "QR introuvable")

        target_url = result.data[0]["target_url"]

        # Log du scan (best-effort)
        try:
            db.table("scans").insert({"qr_id": qr_id}).execute()
        except Exception as e:
            print(f"[scan] insert failed: {e}")

        self.send_response(302)
        self.send_header("Location", target_url)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
