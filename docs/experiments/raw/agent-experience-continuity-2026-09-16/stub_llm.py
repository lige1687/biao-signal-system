"""桩模型服务（OpenAI 兼容，支持流式慢速滴出）：案例 9c 浏览器中断重试验证用。

合成标记：输出是固定合成文本（无数字、无禁用词、无 rule_id 字样，能过接地校验），
只用于验证工程链路（流式 token、停止接收、同 cid 重试），不证明真实表达质量。

POST /chat/completions  stream=true  → SSE 逐段慢出（默认每段 400ms，全程 ~12s，
足够人工/脚本点「停止接收」）；stream=false → 一次性返回。
"""
from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

ANSWER = (
    "这是合成回答，用来验证中断与重试的工程链路。系统资料已经在上方卡片里，"
    "这段文字只是占位：真正的解释质量要看真实模型的输出。"
    "如果你看到这段话停在一半，说明中断生效了；点重试会针对原问题重新生成，"
    "不会重复记录问题。"
)
CHUNK = 6          # 每段字符数
DELAY = 0.4        # 每段间隔秒


def _sse(chunk: dict) -> bytes:
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静音
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if not self.path.endswith("/chat/completions"):
            self.send_response(404)
            self.end_headers()
            return
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for i in range(0, len(ANSWER), CHUNK):
                piece = ANSWER[i:i + CHUNK]
                self.wfile.write(_sse({
                    "choices": [{"delta": {"content": piece}, "index": 0}]}))
                self.wfile.flush()
                time.sleep(DELAY)
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            payload = {"choices": [{"message": {"content": ANSWER}, "index": 0}]}
            data = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8032), Handler).serve_forever()
