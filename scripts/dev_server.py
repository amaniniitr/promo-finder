"""Local stand-in for Vercel: serves web/ and /api/run on http://localhost:3000
.venv/bin/python scripts/dev_server.py   (reads keys and RUN_PASSPHRASE from .env)"""
import mimetypes
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
from api.run import handler as api  # noqa: E402

WEB = (ROOT / "web").resolve()


class Dev(api):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/run"):
            return super().do_GET()
        f = (WEB / path.lstrip("/")).resolve()
        if f.is_dir():
            f = f / "index.html"
        if not str(f).startswith(str(WEB)) or not f.exists():
            self.send_error(404)
            return
        body = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(f.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.split("?")[0].startswith("/api/run"):
            return super().do_POST()
        self.send_error(404)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    print(f"http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Dev).serve_forever()
