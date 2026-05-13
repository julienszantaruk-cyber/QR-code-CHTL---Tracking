from http.server import BaseHTTPRequestHandler
import hashlib
import hmac
import json
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ADMIN_PASS = os.environ["ADMIN_PASS"]
SESSION_SECRET = os.environ["SESSION_SECRET"]

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
    def do_GET(self) -> None:
        if not check_auth(self.headers.get("Cookie", "")):
            self.send_response(401)
            self.end_headers()
            return

        try:
            db = get_db()
            codes = db.table("qr_codes").select("*, scans(count)").execute().data or []
        except Exception as e:
            print(f"[stats] DB error: {e}")
            self.send_response(500)
            self.end_headers()
            return

        result = []
        for c in codes:
            scan_count = (
                c.get("scans", [{}])[0].get("count", 0) if c.get("scans") else 0
            )
            result.append(
                {
                    "id": c["id"],
                    "label": c["label"],
                    "target_url": c["target_url"],
                    "scan_count": scan_count,
                }
            )

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
