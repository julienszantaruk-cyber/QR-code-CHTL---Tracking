from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        qr_id = query.get("id", [""])[0]
        
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = db.table("qr_codes").select("*").eq("id", qr_id).execute()
        
        if not result.data:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>QR introuvable</h1>")
            return
        
        db.table("scans").insert({"qr_id": qr_id}).execute()
        
        self.send_response(302)
        self.send_header("Location", result.data[0]["target_url"])
        self.end_headers()
