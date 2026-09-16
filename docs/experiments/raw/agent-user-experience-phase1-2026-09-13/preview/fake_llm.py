"""本地假模型（OpenAI 兼容桩）——仅供本期隔离预览使用，2026-09-13。

监听 127.0.0.1:8015，实现 POST {base}/chat/completions。
回复是固定合成的四要素中文文本（场景 1 的设计输入），**不是真实模型**：
浏览器走查中凡出现本回复，都视为「模拟模型输出」，不构成模型质量证据。
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

REPLY = (
    "沪深300ETF（510300，数据日 2026-08-06）目前系统状态是黑色（空头规避），"
    "处在关键风险阶段。针对你问的整体方向问题：现在不适合按趋势回调的思路"
    "找买点。\n\n"
    "机会：当前没有系统定义的买点候选——直接如实说，不硬凑利好。风险："
    "有效顶部加黑色状态的规避信号还挂着；4573.83 和 4550.19 是下方两个关键位，"
    "跌破 4550.19 说明这轮下跌还没走完。\n\n"
    "历史依据：暂时不能确定是否适用——这个标的还没有和这次问题完全匹配的"
    "历史测试，下方依据卡可展开看原因。\n\n"
    "接下来可以：先不做动作；想验证打法可以点「准备补测」补一次历史测试，"
    "或等价格站回 4663.9 上方再讨论转强。"
)

# 第二合成标的（516220，真实测试夹具、有买点候选）：回复不编具体数值，
# 只给四要素结构——具体候选数值以服务端计划卡/依据卡为准。
REPLY_GENERIC = (
    "这个标的（合成预览数据）当前有系统定义的买点候选，处于可观察状态。"
    "针对你问的问题：方向与状态以下方速览卡和判定为准。\n\n"
    "机会与风险：系统候选的关键价位、触发条件见下方速览卡与依据卡；"
    "被规则挡住的原因也会如实列出。\n\n"
    "历史依据：暂时不能确定是否适用——还没有与这次问题完全匹配的历史测试，"
    "依据卡可展开看原因。\n\n"
    "接下来可以：在下方动作里选一项继续（查看依据详情 / 准备补测 / "
    "讨论进出计划）。"
)


class Handler(BaseHTTPRequestHandler):
    def _reply_chunks(self, payload: dict) -> list[str]:
        import json as _json
        blob = json.dumps(payload, ensure_ascii=False)
        text = REPLY_GENERIC if "516220" in blob else REPLY
        # 按段落切块，模拟流式输出
        return text.split("\n\n")

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if payload.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            for piece in self._reply_chunks(payload):
                if not piece:
                    continue
                chunk = json.dumps({
                    "id": "fake-ux-preview", "object": "chat.completion.chunk",
                    "choices": [{"index": 0, "delta": {"content": piece + "\n\n"},
                                 "finish_reason": None}],
                }, ensure_ascii=False).encode("utf-8")
                self.wfile.write(b"data: " + chunk + b"\n\n")
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            return
        body = json.dumps({
            "id": "fake-ux-preview",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "".join(self._reply_chunks(payload))},
                "finish_reason": "stop",
            }],
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # 静默
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8015), Handler).serve_forever()
