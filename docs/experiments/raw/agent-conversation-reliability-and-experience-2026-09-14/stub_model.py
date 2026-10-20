"""桩模型服务（验收 B 专用）：OpenAI 风格 /chat/completions，可控延迟与失败。

行为由环境变量控制（每次重启桩前设定）：
- STUB_FIRST_DELAY：收到请求后首字节前等待秒数（默认 0）。
- STUB_TOKEN_GAP：每个 token 之间的间隔秒数（默认 0.05）。
- STUB_FAIL=500：立即返回 HTTP 500。
- STUB_FAIL=hang：先 STUB_FIRST_DELAY 秒后直接断开连接（零字节）。
- STUB_FAIL=drop_mid：发两个 token 后断开（模拟中途失败）。
记录每次请求的时间戳与行为到 stdout，供三段时间核对。
"""
import json
import os
import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()
BEHAVIOR = {
    "first_delay": float(os.environ.get("STUB_FIRST_DELAY", "0")),
    "token_gap": float(os.environ.get("STUB_TOKEN_GAP", "0.05")),
    "fail": os.environ.get("STUB_FAIL", ""),
    # 二轮复验：只前 N 次请求失败（0=失败模式下始终失败），用于「中断→重试
    # 成功」的端到端：第1次断流、第2次（同cid重试）正常完成。
    "fail_first_n": int(os.environ.get("STUB_FAIL_FIRST_N", "0")),
}
TEXT = (
    "按这份数据，510300 处于系统定义的观察区，还没有可执行的入场计划。"
    "这是桩模型的固定文本，只用于验证交互顺序，不代表回答质量。"
)
_REQ_SEQ = {"n": 0}


def _now():
    return datetime.now().isoformat(timespec="milliseconds")


def _should_fail() -> bool:
    if not BEHAVIOR["fail"]:
        return False
    _REQ_SEQ["n"] += 1
    return BEHAVIOR["fail_first_n"] <= 0 or _REQ_SEQ["n"] <= BEHAVIOR["fail_first_n"]


@app.post("/chat/completions")
async def chat(req: Request):
    body = await req.json()
    stream = bool(body.get("stream"))
    fail_now = _should_fail()
    print(f"[{_now()}] req#{_REQ_SEQ['n']} stream={stream} fail={fail_now}", flush=True)
    if not fail_now:
        BEHAVIOR["first_delay"] = float(os.environ.get("STUB_FIRST_DELAY", "0"))
    if fail_now and BEHAVIOR["fail"] == "500":
        print(f"[{_now()}] -> 500", flush=True)
        return JSONResponse({"error": "stub failure"}, status_code=500)
    if fail_now and BEHAVIOR["fail"] == "hang":
        time.sleep(BEHAVIOR["first_delay"])
        print(f"[{_now()}] -> hang-drop (zero bytes)", flush=True)
        return JSONResponse({"error": "stub dropped"}, status_code=502)

    def sse():
        if BEHAVIOR["first_delay"]:
            time.sleep(BEHAVIOR["first_delay"])
        print(f"[{_now()}] first byte", flush=True)
        pieces = [TEXT[i:i + 12] for i in range(0, len(TEXT), 12)]
        if fail_now and BEHAVIOR["fail"] == "drop_mid":
            pieces = pieces[:2]
        for p in pieces:
            chunk = {"choices": [{"delta": {"content": p}}]}
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            time.sleep(BEHAVIOR["token_gap"])
        if fail_now and BEHAVIOR["fail"] == "drop_mid":
            # 真实断流是异常终止（无 chunked 终止块）：抛异常让 uvicorn 直接断开
            print(f"[{_now()}] -> dropped mid-stream (abrupt)", flush=True)
            raise RuntimeError("abrupt connection close (stub drop_mid)")
        yield "data: [DONE]\n\n"
        print(f"[{_now()}] done", flush=True)

    if stream:
        return StreamingResponse(sse(), media_type="text/event-stream")
    if BEHAVIOR["first_delay"]:
        time.sleep(BEHAVIOR["first_delay"])
    return JSONResponse({
        "choices": [{"message": {"role": "assistant", "content": TEXT}}]
    })


@app.get("/health")
def health():
    return {"ok": True, **BEHAVIOR}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("STUB_PORT", "8031")),
                log_level="warning")
