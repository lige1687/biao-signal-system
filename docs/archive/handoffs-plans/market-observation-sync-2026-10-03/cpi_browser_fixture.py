"""Serve already-built LEI web UI with artificial CPI data; no upstream/DB calls.
Run from repository root: python3 <this-file> --dist web/dist --port 18043
GET /__finish closes this owned fixture server; all POSTs are unsupported.
"""
import argparse
import json
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18043)
    parser.add_argument("--seconds", type=int, default=600)
    args = parser.parse_args()
    dist = args.dist.resolve()
    assert (dist / "index.html").is_file(), "Build web/dist first"
    finished = False
    dates = [f"2026-{month:02d}-01" for month in range(1, 10)]
    values = [1.1, 1.5, 1.8, 2.1, 2.3, 2.7, 2.5, 2.8, 2.5]
    payload = {"as_of": "2026-09-01", "items": [{"key": "cpiaucsl_yoy",
        "name_cn": "CPI同比（人工验收资料）", "freq": "月", "date": dates[-1],
        "value": values[-1], "note_cn": "人工值，不能用于市场判断"}],
        "series": {"cpiaucsl_yoy": {"dates": dates, "values": values,
            "unit": "%", "label": "CPI同比（人工验收资料）"}}, "errors": []}

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(dist), **kw)

        def send_bytes(self, status, data, kind):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "connect-src 'self'; object-src 'none'")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            nonlocal finished
            path = urlsplit(self.path).path
            if path == "/__finish":
                finished = True
                return self.send_bytes(200, b"owned fixture finished", "text/plain")
            if path == "/api/fundamentals/us-macro":
                return self.send_bytes(200, json.dumps(payload, ensure_ascii=False).encode(), "application/json")
            if path.startswith("/api/"):
                return self.send_bytes(503, b'{"detail":"artificial fixture: other endpoints deliberately unavailable"}', "application/json")
            if path == "/" or path == "/fundamentals":
                body = (dist / "index.html").read_text()
                body = body.replace("<body>", "<body><div style=\"background:#ffeb80;padding:8px;color:#111\">人工CPI显示验收：所有数字均为人工资料，其他接口不可用；不是市场页面或生产服务。</div>")
                return self.send_bytes(200, body.encode(), "text/html; charset=utf-8")
            return super().do_GET()

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    server.timeout = 1
    deadline = time.monotonic() + args.seconds
    print(f"artificial fixture http://127.0.0.1:{args.port}/fundamentals#fund-sec-usmacro", flush=True)
    try:
        while not finished and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
        print("owned fixture stopped", flush=True)


if __name__ == "__main__":
    main()
