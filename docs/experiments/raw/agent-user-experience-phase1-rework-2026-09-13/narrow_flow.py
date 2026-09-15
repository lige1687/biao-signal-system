"""窄屏（390×844）完整流程走查——UX 返修验证专用，2026-09-13。

真实浏览器（Playwright/Chromium，本机已有依赖）+ 真前端 + 隔离预览后端
（合成数据 + 本地假模型）。验证：实际回答、依据展开、补测面板操作。
只看溢出、可点击、输入与联动，不做视觉重设计。
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
BASE = "http://127.0.0.1:5174"


def main() -> int:
    results: list[tuple[str, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # 1) 输入并发送问题
        page.get_by_role("textbox", name="输入问题").fill("510300 现在怎么看")
        page.get_by_role("button", name="发送 ↑").click()
        page.wait_for_timeout(20000)
        # 等回答完成（动作条出现即完成）；首次分析可能较慢
        page.get_by_role("button", name="查看依据详情").first.wait_for(state="attached", timeout=60000)
        # 窄屏：图表资料区自动展开会盖住动作条——按既有设计先收起资料区
        close_res = page.get_by_role("button", name="关闭资料区")
        if close_res.count() > 0 and close_res.first.is_visible():
            close_res.first.click()
            page.wait_for_timeout(400)
        page.get_by_role("button", name="查看依据详情").first.wait_for(state="visible", timeout=60000)
        n_answers = page.locator(".ar-answer").count()
        results.append(("narrow-send-answer", "PASS" if n_answers >= 1 else "FAIL"))

        # 2) 点动作条"查看依据详情"→ 依据折叠区展开
        expand = page.get_by_role("button", name="查看依据详情").first
        expand.click()
        page.wait_for_timeout(600)
        open_details = page.locator("details.evidence-card-details[open]").count()
        results.append(("narrow-expand-evidence", "PASS" if open_details >= 1 else "FAIL"))
        page.screenshot(path=str(OUT / "narrow-390-answer-expanded.png"))
        page.get_by_role("button", name="查看依据详情").first.click()  # 保持展开状态

        # 3) 动作条"准备补测"→ 中文面板 → 选打法 → 面板可用
        prep = page.get_by_role("button", name="准备补测")
        if prep.count() == 0:
            results.append(("narrow-setup-panel", "FAIL(no button)"))
        else:
            prep.first.click()
            page.wait_for_timeout(1200)
            panel = page.locator(".backtest-setup-panel")
            visible = panel.count() >= 1 and panel.first.is_visible()
            # 横向溢出检查
            overflow = page.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if visible:
                panel.get_by_text("上升趋势中的回调", exact=False).click()
                page.wait_for_timeout(400)
            submit_disabled = page.get_by_role("button", name="创建这次补测").is_disabled()
            results.append(("narrow-setup-panel", "PASS" if visible and not submit_disabled else "FAIL"))
            results.append(("narrow-no-h-overflow",
                            "PASS" if overflow <= 2 else f"FAIL({overflow}px)"))
            page.screenshot(path=str(OUT / "narrow-390-panel.png"))
            page.get_by_role("button", name="先不测了").click()

        # 4) 窄屏欢迎页截图（既有基线证据）
        browser.close()

    for name, verdict in results:
        print(f"{name}: {verdict}")
    return 0 if all(v == "PASS" for _, v in results) else 1


if __name__ == "__main__":
    sys.exit(main())
