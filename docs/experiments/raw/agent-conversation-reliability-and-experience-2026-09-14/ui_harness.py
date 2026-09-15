"""真实前端 UI 验收脚本（Playwright headless Chromium）。

只驱动真实构建前端与真实 SSE 流；window.fetch 仅做时间戳观测（init script），
不替换任何前端逻辑。所有时间均以发送点击时刻为 t0。

用法：python3 ui_harness.py <scenario>
  b1   桩延迟场景：三段时间 + facts 先显截图 + 完成截图
  b2   桩中途断开场景：部分正文保留 + 资料保留 + 失败提示截图
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAW = Path(__file__).parent
SCREENS = RAW / "screens"
BASE = "http://127.0.0.1:8021"

INIT = """
window.__sseLog = [];
const _origFetch = window.fetch;
window.fetch = async function (...args) {
  const url = String(args[0]);
  if (url.includes('/api/agent/chat/stream')) {
    window.__sseLog.push({ ev: 'request', t: performance.now() });
  }
  const resp = await _origFetch.apply(this, args);
  return resp;
};
// 记录 EventSource 无关；SSE 经 fetch body 读取，事件时间由 DOM 标志补齐
"""

QUESTION_1 = "510300 最近怎么看？先说判断，再讲机会和风险，现有依据够不够？"


def ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def open_workspace(page):
    page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
    page.add_init_script(INIT)  # 对后续导航生效；首载后手动补挂
    page.evaluate(INIT)


def ask(page, question: str) -> float:
    box = page.locator("#agent-question")
    box.fill(question)
    t0 = time.monotonic()
    box.press("Enter")
    return t0


def _launch(p):
    # 系统 Chrome 通道（Playwright 自带二进制未安装；不新增下载）
    return p.chromium.launch(channel="chrome", headless=True)


def run_b1() -> dict:
    out: dict = {"scenario": "b1-stub-delay"}
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        open_workspace(page)
        t0 = ask(page, QUESTION_1)
        # ① 资料就绪（prepared 事件渲染）
        page.wait_for_selector("text=系统资料已就绪", timeout=60_000)
        out["t1_facts_visible_ms"] = ms(t0)
        page.screenshot(path=str(SCREENS / "B1-facts-ready.png"))
        out["facts_only_dom"] = {
            "quick_card": page.locator("section.ar-quick-card").count(),
            "evidence_card": page.locator(".ar-answer details, .evidence-card").count(),
        }
        # ② 模型首个 token（桩固定文本开头）
        page.wait_for_selector("text=按这份数据，510300 处于系统定义", timeout=60_000)
        out["t2_first_model_text_ms"] = ms(t0)
        # ③ 完成（动作条出现）
        page.wait_for_selector("text=复制文字", timeout=60_000)
        out["t3_done_ms"] = ms(t0)
        out["order_facts_before_model_text"] = out["t1_facts_visible_ms"] < out["t2_first_model_text_ms"]
        page.screenshot(path=str(SCREENS / "B1-done.png"))
        out["sse_log"] = page.evaluate("window.__sseLog")
        browser.close()
    (RAW / "acceptance-B1-timings.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    return out


def run_b2() -> dict:
    out: dict = {"scenario": "b2-stub-drop-mid"}
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        open_workspace(page)
        t0 = ask(page, QUESTION_1)
        page.wait_for_selector("text=系统资料已就绪", timeout=60_000)
        out["t1_facts_visible_ms"] = ms(t0)
        page.screenshot(path=str(SCREENS / "B2-facts-ready.png"))
        # 中途断开：部分正文 + 「未完成」标记 + 资料保留
        page.wait_for_selector("text=AI 讲解因连接中断未完成", timeout=60_000)
        out["t2_incomplete_notice_ms"] = ms(t0)
        out["partial_text_kept"] = page.get_by_text("按这份数据，510300 处于系统定义").count() > 0
        out["facts_kept_after_failure"] = {
            "quick_card": page.locator("section.ar-quick-card").count(),
            "facts_ready_hint_or_notice": page.get_by_text("AI 解释未完成").count()
            + page.get_by_text("系统资料已就绪").count(),
        }
        page.screenshot(path=str(SCREENS / "B2-failed-kept.png"))
        browser.close()
    (RAW / "acceptance-B2-timings.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    return out




QUESTIONS_C = [
    "510300 最近怎么看？先说判断，再讲机会和风险，现有依据够不够？",
    "这个判断哪些有历史依据，哪些只是当前观察？现在能不能给胜率？",
    "我先不买，只观察。接下来具体看哪些变化，什么情况再来讨论？",
    "假如后来满足入场条件，进入、失效和退出该怎样讨论？现在还缺哪些信息？先别替我保存计划。",
]


def run_c() -> dict:
    """验收C：真实模型四轮连续案例（每轮1次模型请求，仅首轮失败允许1次重试）。"""
    out: dict = {"scenario": "c-real-model-4-rounds", "rounds": []}
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        open_workspace(page)
        for i, q in enumerate(QUESTIONS_C, start=1):
            round_info: dict = {"round": i, "question": q}
            t0 = ask(page, q)
            try:
                page.wait_for_selector("text=系统资料已就绪", timeout=90_000)
                round_info["t_facts_ms"] = ms(t0)
            except Exception:
                round_info["t_facts_ms"] = None  # 首问失败时无 prepared
            # 完成标志：停止接收按钮消失（busy 结束）
            page.wait_for_selector("text=停止接收", state="detached", timeout=420_000)
            round_info["t_done_ms"] = ms(t0)
            answers = page.locator("article.ar-answer")
            last = answers.last
            round_info["answer_text"] = last.inner_text(timeout=10_000)
            round_info["has_fallback_notice"] = page.get_by_text("本次采用系统提供的结果").count() > 0
            round_info["has_incomplete_notice"] = page.get_by_text("AI 讲解因连接中断未完成").count() > 0
            page.screenshot(path=str(SCREENS / f"C-round{i}.png"))
            out["rounds"].append(round_info)
            (RAW / "acceptance-C-rounds.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2))
            # 首轮零正文且出现模板兜底 → 允许一次重试（重试复用原问题，不重复记录）
            if i == 1 and round_info["has_fallback_notice"]:
                body_text = round_info["answer_text"]
                if "AI 讲解暂时不可用" in body_text or len(body_text.strip()) < 40:
                    out["retry_of_round1"] = True
                    t0 = ask(page, q)
                    page.wait_for_selector("text=停止接收", state="detached", timeout=420_000)
                    last = page.locator("article.ar-answer").last
                    round_info["retry_answer_text"] = last.inner_text(timeout=10_000)
                    round_info["retry_t_done_ms"] = ms(t0)
                    page.screenshot(path=str(SCREENS / "C-round1-retry.png"))
                    (RAW / "acceptance-C-rounds.json").write_text(
                        json.dumps(out, ensure_ascii=False, indent=2))
        browser.close()
    return out


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "b1"
    result = {"b1": run_b1, "b2": run_b2, "c": run_c}[scenario]()
    print(json.dumps(result, ensure_ascii=False, indent=2))
