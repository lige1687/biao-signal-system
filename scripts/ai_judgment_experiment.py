"""AI 参与决策三档实验：LLM 对历史信号逐笔判定（做/不做 + 仓位档）。

设定（用户口径 2026-09-06）：测三档——纯系统 / AI 有否决权 / AI 有仓位权。
- 每笔信号给 LLM 的材料全部**截至信号日**（形态分类/宽度/信号参数/历史
  回测经验）——未来结果字段（_r_*）绝不出现在 prompt；
- LLM temperature=0 输出结构化 JSON {action, size, reason}；
- 全部响应存档（复现审计）；经验条目含近两年回测结论属方法论限制，
  实盘中 Agent 同样携带事后经验，如实标注于报告。

用法：python scripts/ai_judgment_experiment.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

PROMPT_TMPL = """你是一个趋势交易系统的风控决策员。系统刚生成了一笔入场信号，你来决定做不做、下多大注。

【纪律背景】这是规则型趋势系统（趋势回调/突破/反转模块）。历史上：
- 稳涨型标的（涨势稳回调浅）配趋势回调打法是唯一持续正期望组合（两年+93倍风险金）；
- 急涨型（涨得猛均线乱）上趋势回调几乎上不了车、仅有的信号买在顶部；
- 下跌型上抄底打法10笔9亏；止损距离过近（<1%）的信号脆弱（正常波动就穿、跳空放大亏损）；
- 宽度（站上20日线的个股占比）反映市场环境：200日占比<25%属长期弱市。

【当前信号材料】
{material}

【你的任务】只依据以上材料判断：
1. action：做（do）还是放弃（skip）——考虑形态与打法匹配度、止损距离是否脆弱、市场宽度环境、账面盈亏比；
2. size：若做，仓位档 0.5（试探）/ 1.0（标准）/ 1.5（加大）——依据把握度；
3. reason：一句话理由（大白话，不超30字）。

只输出 JSON：{{"action": "do"|"skip", "size": 0.5|1.0|1.5, "reason": "..."}}"""


def load_env() -> None:
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def call_glm(material: str) -> dict:
    import urllib.request

    key = os.environ["GLM_API_KEY"]
    model = os.environ.get("GLM_MODEL", "glm-5.3")
    base = os.environ.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4")
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [{"role": "user", "content": PROMPT_TMPL.format(material=material)}],
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.load(resp)
    text = (out.get("choices") or [{}])[0].get("message", {}).get("content", "")
    # 提取 JSON（模型可能带 ```json 包裹）
    import re
    m = re.search(r"\{[^{}]*\}", text, re.S)
    if not m:
        return {"action": "do", "size": 1.0, "reason": "", "_raw": text[:120]}
    try:
        d = json.loads(m.group(0))
        d["action"] = "do" if str(d.get("action")).lower() in ("do", "做") else "skip"
        if d.get("size") not in (0.5, 1.0, 1.5):
            d["size"] = 1.0
        return d
    except json.JSONDecodeError:
        return {"action": "do", "size": 1.0, "reason": "", "_raw": text[:120]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    load_env()
    signals = json.load(open("/tmp/ai_signals.json"))
    if args.limit:
        signals = signals[: args.limit]
    out_path = Path("/tmp/ai_judgments.jsonl")
    done_ids = set()
    if out_path.exists():  # 断点续跑
        for line in out_path.read_text().splitlines():
            try:
                done_ids.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue
    with open(out_path, "a") as fh:
        for s in signals:
            if s["id"] in done_ids:
                continue
            material = json.dumps(
                {k: v for k, v in s.items() if not k.startswith("_")},
                ensure_ascii=False,
            )
            try:
                judge = call_glm(material)
            except Exception as e:  # noqa: BLE001 — 单笔失败不中断
                judge = {"action": "do", "size": 1.0, "reason": f"调用失败:{type(e).__name__}"}
            fh.write(json.dumps({"id": s["id"], **judge}, ensure_ascii=False) + "\n")
            fh.flush()
            time.sleep(0.3)
    print(f"完成 {len(signals)} 笔判定 → {out_path}")


if __name__ == "__main__":
    main()
