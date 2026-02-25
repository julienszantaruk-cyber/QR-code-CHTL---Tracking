from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import os, uuid, hashlib
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
    def do_POST(self):
        if not check_auth(self.headers.get("Cookie", "")):
            self.send_response(303)
            self.send_header("Location", "/api/login")
            self.end_headers()
            return
        
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = parse_qs(body)
        label = params.get("label", [""])[0]
        target_url = params.get("target_url", [""])[0]
        
        if label and target_url:
            db = create_client(SUPABASE_URL, SUPABASE_KEY)
            qr_id = uuid.uuid4().hex[:8]
            db.table("qr_codes").insert({"id": qr_id, "label": label, "target_url": target_url}).execute()
        
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()
