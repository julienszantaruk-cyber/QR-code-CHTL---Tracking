from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import hashlib
import hmac
import json
import os
import re
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ADMIN_PASS = os.environ["ADMIN_PASS"]
SESSION_SECRET = os.environ["SESSION_SECRET"]

QR_ID_PATTERN = re.compile(r"^[a-f0-9]{8}$")

_db: Client | None = None


def get_db() -> Client:
    global _db
    if _db is None:
        _db = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _db


def check_auth(cookie_header: str | None) -> bool:
    if not cookie_header:
        return False
    try:
        cookies = dict(
            c.strip().split("=", 1) for c in cookie_header.split(";") if "=" in c
        )
    except Exception:
        return False
    expected = hashlib.sha256(f"{ADMIN_PASS}{SESSION_SECRET}".encode()).hexdigest()
    return hmac.compare_digest(cookies.get("session", ""), expected)


class handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_DELETE(self) -> None:
        if not check_auth(self.headers.get("Cookie", "")):
            return self._json(401, {"ok": False, "error": "unauthorized"})

        query = parse_qs(urlparse(self.path).query)
        qr_id = query.get("id", [""])[0].strip().lower()

        if not QR_ID_PATTERN.match(qr_id):
            return self._json(400, {"ok": False, "error": "invalid id"})

        try:
            db = get_db()
            db.table("scans").delete().eq("qr_id", qr_id).execute()
            db.table("qr_codes").delete().eq("id", qr_id).execute()
        except Exception as e:
            print(f"[delete] DB error: {e}")
            return self._json(500, {"ok": False, "error": "db"})

        return self._json(200, {"ok": True})
