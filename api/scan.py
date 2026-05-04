from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

# Cache du client Supabase
_db: Client | None = None

def get_db() -> Client:
    global _db
    if _db is None:
        _db = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _db

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        qr_id = query.get("id", [""])[0]
        
        if not qr_id:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>ID manquant</h1>")
            return
        
        db = get_db()
        result = db.table("qr_codes").select("*").eq("id", qr_id).execute()
        
        if not result.data:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>QR introuvable</h1>")
            return
        
        # Log du scan (best-effort, on n'échoue pas la redirection si ça plante)
        try:
            db.table("scans").insert({"qr_id": qr_id}).execute()
        except Exception as e:
            print(f"[scan] insert failed: {e}")
        
        self.send_response(302)
        self.send_header("Location", result.data[0]["target_url"])
        self.end_headers()
