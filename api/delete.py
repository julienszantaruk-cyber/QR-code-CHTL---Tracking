from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os, json, hashlib
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "change-me-secret-key")

def check_auth(cookie_header):
    if not cookie_header:
        return False
    cookies = dict(c.strip().split("=", 1) for c in cookie_header.split(";") if "=" in c)
    expected = hashlib.sha256(f"{ADMIN_PASS}{SESSION_SECRET}".encode()).hexdigest()
    return cookies.get("session") == expected

class handler(BaseHTTPRequestHandler):
    def do_DELETE(self):
        if not check_auth(self.headers.get("Cookie", "")):
            self.send_response(401)
            self.end_headers()
            return
        
        query = parse_qs(urlparse(self.path).query)
        qr_id = query.get("id", [""])[0]
        
        if qr_id:
            db = create_client(SUPABASE_URL, SUPABASE_KEY)
            db.table("scans").delete().eq("qr_id", qr_id).execute()
            db.table("qr_codes").delete().eq("id", qr_id).execute()
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())
