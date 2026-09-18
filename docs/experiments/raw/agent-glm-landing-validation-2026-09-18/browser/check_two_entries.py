#!/usr/bin/env python3
"""S2 两入口真实浏览器检查（本机 Chrome，headless）。

前置（由调用方保证）：隔离后端 127.0.0.1:18765（进程级禁网+合成行情+模型桩+
临时库；上证指数 000001.SS 刻意无行情）、vite 前端 127.0.0.1:18766、
自选已预置 515880.SS。

检查（DOM 断言 + 全页截图存证）：
  工作台 /agent：515880 提问 → 通信ETF 卡；追问「沪深300…」→ 沪深300 卡
  （S1 修复的用户可见效果）；「那失效位呢」→ 继承（composer 芯片仍 沪深300）。
  控制台 /：顶栏「AI 助手」→ 515880 → 通信ETF 卡；「上证指数…」→ 无行情
  → 不出现上证指数卡、不附旧通信ETF新卡；「000300.SS…」→ 沪深300 卡。

输出：browser-checks.json（逐步断言明细）+ 同目录 PNG 截图。退出码非零=有断言失败。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:18766"
HERE = Path(__file__).resolve().parent
WS_Q1 = "515880 现在有哪些系统定义的买点？"
WS_Q2 = "沪深300 现在有哪些系统定义的买点？"
WS_Q3 = "那失效位呢"
RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + detail)


def reply_marker_count(page, scope: str) -> int:
    text = page.locator(scope or "body").text_content() or ""
    return text.count("首段结论")  # 模型桩每条回复都带该文本


def send_and_settle(page, message: str, scope: str = "") -> None:
    """填问题并点发送；轮询等待回复完成（桩回复文本计数增加且非 busy）。

    工作台输入是 textarea，控制台抽屉输入是 input——两者都匹配。"""
    box = page.locator(f'{scope} textarea, {scope} input[type="text"], '
                       f'{scope} input:not([type])').first
    box.fill(message)
    before = reply_marker_count(page, scope)
    send_btn = page.locator(f'{scope} button:has-text("发送")').first
    send_btn.click()
    deadline = time.time() + 60
    last = ""
    while time.time() < deadline:
        time.sleep(0.5)
        busy = page.locator(f'{scope} button:has-text("停止接收")').count() > 0
        now = reply_marker_count(page, scope)
        last = f"busy={busy} replies={now}(before={before})"
        if not busy and now > before:
            time.sleep(0.6)  # 渲染余量
            return
    raise TimeoutError(f"reply not settled in 60s: {last}")


def card_labels(page, scope: str = "") -> list[str]:
    labels = page.locator(f'{scope} [aria-label$="关键数据"]').evaluate_all(
        "els => els.map(e => e.getAttribute('aria-label'))")
    return list(labels)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1560, "height": 950})

        # ---------- 工作台 /agent ----------
        page.goto(BASE + "/agent")
        page.wait_for_selector("#agent-question", timeout=30_000)
        page.wait_for_load_state("domcontentloaded")

        send_and_settle(page, WS_Q1, "")
        labels = card_labels(page)
        check("ws.step1_515880_card", any("通信ETF" in x for x in labels),
              f"cards={labels}")
        page.screenshot(path=str(HERE / "ws-step1-515880.png"))

        send_and_settle(page, WS_Q2, "")
        labels = card_labels(page)
        check("ws.step2_hs300_switch", any("沪深300" in x for x in labels),
              f"cards={labels}")
        chip = page.locator(".ar-composer-context strong").first.text_content()
        check("ws.step2_chip_hs300", bool(chip and "沪深300" in chip),
              f"composer chip={chip!r}")
        page.screenshot(path=str(HERE / "ws-step2-hs300-switch.png"))

        send_and_settle(page, WS_Q3, "")
        chip = page.locator(".ar-composer-context strong").first.text_content()
        labels = card_labels(page)
        check("ws.step3_followup_inherit",
              bool(chip and "沪深300" in chip) and any("沪深300" in x for x in labels),
              f"chip={chip!r} cards={labels}")
        page.screenshot(path=str(HERE / "ws-step3-inherit.png"))

        # ---------- 控制台 /（顶栏 AI 助手）----------
        page.goto(BASE + "/")
        page.wait_for_load_state("domcontentloaded")
        page.locator('nav button:has-text("AI 助手")').first.click()
        page.wait_for_selector(".drawer-panel.agent-console", timeout=15_000)

        send_and_settle(page, WS_Q1, ".drawer-panel.agent-console")
        drawer = page.locator(".drawer-panel.agent-console").text_content() or ""
        check("console.step1_515880_card",
              "通信ETF" in drawer and "515880.SS" in drawer,
              "drawer 含 通信ETF/515880.SS")
        page.screenshot(path=str(HERE / "console-step1-515880.png"))

        send_and_settle(page, "上证指数 现在有哪些系统定义的买点？",
                        ".drawer-panel.agent-console")
        drawer = page.locator(".drawer-panel.agent-console").text_content() or ""
        body_text = page.locator(".drawer-body").text_content() or ""
        sse_cards = page.locator('.drawer-panel [aria-label*="上证指数"]').count()
        # 「上证指数」只允许出现在用户问题回显里（恰好1次）；不得出现
        # 上证指数资料卡，也不得出现 000001.SS 代码或旧卡新附。
        check("console.step2_sse_nodata_no_stale_card",
              drawer.count("上证指数") == 1 and sse_cards == 0
              and "000001.SS" not in body_text,
              f"drawer上证指数出现{drawer.count('上证指数')}次(应为1=仅问题回显) "
              f"上证指数卡={sse_cards}(应0) body含000001.SS={'000001.SS' in body_text}")
        page.screenshot(path=str(HERE / "console-step2-sse-nodata.png"))

        send_and_settle(page, "000300.SS 现在的买点", ".drawer-panel.agent-console")
        drawer = page.locator(".drawer-panel.agent-console").text_content() or ""
        check("console.step3_hs300_code_switch",
              "沪深300" in drawer and "000300.SS" in drawer,
              "drawer 含 沪深300/000300.SS")
        page.screenshot(path=str(HERE / "console-step3-hs300-code.png"))

        browser.close()

    (HERE / "browser-checks.json").write_text(
        json.dumps(RESULTS, ensure_ascii=False, indent=1), encoding="utf-8")
    failed = [r for r in RESULTS if not r["ok"]]
    print(f"browser checks: {len(RESULTS)} total, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
