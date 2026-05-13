from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(303)
        self.send_header("Location", "/api/login")
        # Mêmes flags qu'à la création pour que le navigateur supprime bien le cookie
        self.send_header(
            "Set-Cookie",
            "session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0",
        )
        self.end_headers()
