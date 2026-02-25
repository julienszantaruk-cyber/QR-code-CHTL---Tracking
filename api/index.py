from http.server import BaseHTTPRequestHandler
import json, qrcode, io, base64, os
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "change-me-secret-key")

def get_db():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def check_auth(cookie_header):
    if not cookie_header:
        return False
    cookies = dict(c.strip().split("=", 1) for c in cookie_header.split(";") if "=" in c)
    import hashlib
    expected = hashlib.sha256(f"{ADMIN_PASS}{SESSION_SECRET}".encode()).hexdigest()
    return cookies.get("session") == expected

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        cookie = self.headers.get("Cookie", "")
        if not check_auth(cookie):
            self.send_response(303)
            self.send_header("Location", "/api/login")
            self.end_headers()
            return
        
        db = get_db()
        codes = db.table("qr_codes").select("*, scans(count)").execute().data
        
        base = f"https://{self.headers.get('Host', 'localhost')}"
        rows = ""
        for c in codes:
            scan_count = c.get("scans", [{}])[0].get("count", 0) if c.get("scans") else 0
            track_url = f"{base}/s/{c['id']}"
            img = qrcode.make(track_url)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()
            
            rows += f"""<tr id="row-{c['id']}">
                <td style="font-weight:bold">{c['label']}</td>
                <td><a href="{c['target_url']}" target="_blank">{c['target_url'][:50]}</a></td>
                <td class="scan-count" data-id="{c['id']}" style="text-align:center;font-size:1.4rem;font-weight:bold">{scan_count}</td>
                <td><img src="data:image/png;base64,{qr_b64}" width="120"></td>
                <td>
                    <a href="data:image/png;base64,{qr_b64}" download="{c['label']}.png" class="btn-dl">Telecharger</a>
                    <button onclick="deleteQR('{c['id']}')" class="btn-del">Supprimer</button>
                </td>
            </tr>"""

        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <title>QR Tracker</title>
        <style>
            body {{ font-family:system-ui; max-width:1000px; margin:2rem auto; padding:1rem; background:#0d1117; color:#e6edf3; }}
            h1 {{ color:#58a6ff; display:inline-block; }}
            .topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; }}
            .logout {{ color:#f85149; text-decoration:none; padding:6px 14px; border:1px solid #f8514930; border-radius:6px; }}
            .logout:hover {{ background:#f8514920; }}
            .live {{ display:inline-block; width:8px; height:8px; background:#3fb950; border-radius:50%; margin-left:8px; animation:pulse 2s infinite; }}
            @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}
            table {{ width:100%; border-collapse:collapse; margin-top:1rem; }}
            td,th {{ padding:12px; border-bottom:1px solid #30363d; text-align:left; vertical-align:middle; }}
            th {{ color:#8b949e; }}
            a {{ color:#58a6ff; }}
            form {{ background:#161b22; padding:1rem; border-radius:8px; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
            input {{ padding:10px; background:#0d1117; color:#e6edf3; border:1px solid #30363d; border-radius:6px; font-size:14px; }}
            input:focus {{ border-color:#58a6ff; outline:none; }}
            .btn {{ padding:10px 20px; background:#238636; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:bold; }}
            .btn-dl {{ background:#238636; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; display:inline-block; margin-bottom:4px; }}
            .btn-del {{ background:#da3633; color:white; padding:6px 12px; border-radius:6px; border:none; cursor:pointer; }}
            .updated {{ animation:flash .5s; }}
            @keyframes flash {{ 0%{{background:#238636}} 100%{{background:transparent}} }}
        </style></head>
        <body>
            <div class="topbar">
                <div><h1>QR Tracker</h1><span class="live"></span></div>
                <a href="/api/logout" class="logout">Deconnexion</a>
            </div>
            <form method="POST" action="/api/create">
                <input name="label" placeholder="Nom du QR" required>
                <input name="target_url" placeholder="https://exemple.com" size="40" required>
                <button class="btn" type="submit">+ Creer un QR</button>
            </form>
            <table>
                <tr><th>Label</th><th>Destination</th><th>Scans</th><th>QR Code</th><th>Actions</th></tr>
                <tbody id="tbody">
                {rows if rows else '<tr><td colspan="5" style="text-align:center;color:#8b949e;padding:3rem">Aucun QR code encore !</td></tr>'}
                </tbody>
            </table>
            <script>
                setInterval(async()=>{{
                    try{{
                        const r=await fetch('/api/stats');
                        if(!r.ok)return;
                        const d=await r.json();
                        d.forEach(q=>{{
                            const el=document.querySelector(`.scan-count[data-id="${{q.id}}"]`);
                            if(el&&el.textContent!==String(q.scan_count)){{
                                el.textContent=q.scan_count;
                                el.classList.add('updated');
                                setTimeout(()=>el.classList.remove('updated'),600);
                            }}
                        }});
                    }}catch(e){{}}
                }},5000);
                async function deleteQR(id){{
                    if(!confirm('Supprimer ce QR code ?'))return;
                    const r=await fetch('/api/delete/'+id,{{method:'DELETE'}});
                    if(r.ok){{
                        document.getElementById('row-'+id)?.remove();
                        if(!document.querySelectorAll('[id^="row-"]').length)
                            document.getElementById('tbody').innerHTML='<tr><td colspan="5" style="text-align:center;color:#8b949e;padding:3rem">Aucun QR code encore !</td></tr>';
                    }}
                }}
            </script>
        </body></html>"""
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())
