from http.server import BaseHTTPRequestHandler
import json
import os
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CRON_SECRET = os.environ.get("CRON_SECRET", "")


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        auth = self.headers.get("Authorization", "")
        if CRON_SECRET and auth != f"Bearer {CRON_SECRET}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        try:
            db = create_client(SUPABASE_URL, SUPABASE_KEY)
            result = db.table("qr_codes").select("id").limit(1).execute()
            payload = {"ok": True, "rows": len(result.data or [])}
        except Exception as e:
            print(f"[cron-ping] error: {e}")
            payload = {"ok": False}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())
