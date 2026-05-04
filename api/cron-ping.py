from http.server import BaseHTTPRequestHandler
import os, json
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CRON_SECRET = os.environ.get("CRON_SECRET", "")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Vercel ajoute ce header sur les appels cron
        auth = self.headers.get("Authorization", "")
        if CRON_SECRET and auth != f"Bearer {CRON_SECRET}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        try:
            db = create_client(SUPABASE_URL, SUPABASE_KEY)
            # Une requête triviale qui réveille la DB
            result = db.table("qr_codes").select("id").limit(1).execute()
            payload = {"ok": True, "rows": len(result.data)}
        except Exception as e:
            payload = {"ok": False, "error": str(e)}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())
