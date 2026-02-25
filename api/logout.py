from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(303)
        self.send_header("Location", "/api/login")
        self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0")
        self.end_headers()
