"""Serve already-built LEI web UI with artificial observation metadata; no upstream/DB calls.
Run from repository root: python3 <this-file> --dist web/dist --port 18045
GET /__finish closes this owned fixture server; all POSTs are unsupported.
"""
import argparse
import json
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18045)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--cpi-value", type=float, default=2.5)
    args = parser.parse_args()
    dist = args.dist.resolve()
    assert (dist / "index.html").is_file(), "Build web/dist first"
    finished = False
    def item(metric, label, market, date, precision="unknown", published=None):
        return {"metric_id": metric, "label": label, "market": market,
            "universe": "人工资料；范围只用于页面验收", "value": 12.5, "unit": "%",
            "change": None, "observation_date": date, "published_at": published,
            "publication_precision": precision, "fetched_at": "2026-10-03T06:00:00Z",
            "source_name": "人工验收资料", "source_url": None, "source_access": "unknown",
            "definition_version": "artificial-ui-check/1", "quality_status": "time_unverified",
            "quality_reason": "人工资料，不是已核实的市场读数", "reading": "仅用于检查日期文字",
            "limitations": ["未接上游，也没有验证真实首次可用时间"], "evidence_refs": []}
    payloads = {
        "cn": {"market": "cn", "generated_at": "2026-10-03T06:05:00Z", "errors": [], "items": [
            item("margin_balance", "A股日期精度例", "cn", "2026-09-29", "date", "2026-09-30"),
            item("stock_turnover", "A股固定历史成交额例", "cn", "2026-09-29"),
            item("margin_share", "A股发布时间未知例", "cn", "2026-09-29", "unknown", "2026-10-03")]},
        "us": {"market": "us", "generated_at": "2026-10-03T06:05:00Z", "errors": [], "items": [
            item("vix", "美股时刻精度例", "us", "2026-09-30", "timestamp", "2026-09-30T20:15:00Z"),
            item("vxn", "美股日期精度例", "us", "2026-09-30", "date", "2026-10-01"),
            item("aaii", "AAII调查所属周例", "us", "2026-09-28"),
            item("naaim", "NAAIM调查所属周例", "us", "2026-09-28")]}}

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
            if path == "/api/fundamentals/observations":
                market = parse_qs(urlsplit(self.path).query).get("market", ["cn"])[0]
                if market not in payloads:
                    return self.send_bytes(422, b'{"detail":"unknown artificial market"}', "application/json")
                return self.send_bytes(200, json.dumps(payloads[market], ensure_ascii=False).encode(), "application/json")
            if path.startswith("/api/"):
                return self.send_bytes(503, b'{"detail":"artificial fixture: other endpoints deliberately unavailable"}', "application/json")
            if path == "/" or path == "/fundamentals":
                body = (dist / "index.html").read_text()
                body = body.replace("<body>", "<body><div style=\"background:#ffeb80;padding:8px;color:#111\">人工日期与市场说明验收：所有数字均为人工资料，其他接口不可用；不是市场页面或生产服务。</div>")
                return self.send_bytes(200, body.encode(), "text/html; charset=utf-8")
            return super().do_GET()

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    server.timeout = 1
    deadline = time.monotonic() + args.seconds
    print(f"artificial fixture http://127.0.0.1:{args.port}/fundamentals#fund-sec-market", flush=True)
    try:
        while not finished and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
        print("owned fixture stopped", flush=True)


if __name__ == "__main__":
    main()
