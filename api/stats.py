from http.server import BaseHTTPRequestHandler
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
    def do_GET(self):
        if not check_auth(self.headers.get("Cookie", "")):
            self.send_response(401)
            self.end_headers()
            return
        
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        codes = db.table("qr_codes").select("*, scans(count)").execute().data
        
        result = []
        for c in codes:
            scan_count = c.get("scans", [{}])[0].get("count", 0) if c.get("scans") else 0
            result.append({"id": c["id"], "label": c["label"], "target_url": c["target_url"], "scan_count": scan_count})
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
