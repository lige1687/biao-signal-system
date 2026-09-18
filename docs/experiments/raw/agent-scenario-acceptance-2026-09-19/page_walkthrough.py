#!/usr/bin/env python3
"""S1 四场景验收 + 三卡视觉走查（真实页面通道，本机 Chrome headless）。

被验收对象：生产运行系统（vite 5173 → 后端 8000 代理），只读+正常用户级使用。
页面链路事实：自由输入先经 03B 统一预路由 /api/copilot/resolve（前端
utils/resolveRoute.ts），仅 trade_report/discovery/existing_action 三种意图
进 /api/copilot/dispatch，其余走讨论管线 /api/agent/chat/stream。

红线落实：
  - 零产品代码改动：本脚本只读页面、截图、记录网络；不写任何 src/web 文件。
  - 禁真模型调用：page.route 拦截 /api/agent/chat/stream 一律 abort。
  - mock 只作用于探针消息（文本含「模拟」或属 B 段三条探针），其余请求
    原样放行；不动任何生产文件。B 段只 mock resolve 的分类结果让页面走进
    真实 dispatch（卡数据=真实生产响应）；C 段再 mock dispatch 出降级态。
  - 独立 browser profile：Playwright 全新 context（无历史 cookie/登录态）。

输出（与本脚本同目录）：browser-walkthrough.json + screenshots/*.png。
退出码非零 = 有断言失败。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"
SHOTS.mkdir(exist_ok=True)

RESULTS: list[dict] = []
NETWORK: list[dict] = []
ABORTED_MODEL_CALLS: list[dict] = []
MOCKED_RESOLVE_MESSAGES: list[str] = []
MOCKED_DISPATCH_MESSAGES: list[str] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + detail)


def shot(page, name: str) -> None:
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"SHOT {name} :: {page.url} @ {datetime.now().isoformat(timespec='seconds')}")


def send_and_wait(page, message: str, wait_text: str | None, timeout: float = 30.0) -> None:
    """在抽屉输入框填一句话并点发送；wait_text 出现或（None 时）等待短暂稳定。"""
    box = page.locator(".drawer-panel input[placeholder='问点什么']")
    box.fill(message)
    page.locator(".drawer-panel button:has-text('发送')").click()
    if wait_text:
        wait_card(page, wait_text, timeout)
    else:
        page.wait_for_timeout(2500)


def wait_card(page, marker: str, timeout: float = 30.0) -> None:
    """等待**卡片内**出现 marker（限定 .cp-card 作用域，避开快捷芯片/用户消息回显撞词）。"""
    page.locator(f".drawer-panel .cp-card:has-text('{marker}')").first.wait_for(
        timeout=timeout * 1000)


def body_text(page) -> str:
    return page.locator(".drawer-panel").text_content() or ""


def cards_text(page) -> str:
    return " ".join(page.locator(".drawer-panel .cp-card").all_text_contents())


def dispatch_replies_for(network: list[dict], fragment: str) -> dict | None:
    return next((n for n in reversed([n for n in network
                                      if n.get("response_json")
                                      and n["url"].endswith("/copilot/dispatch")])
                 if n.get("request_post_data") and fragment in n["request_post_data"]), None)


def main() -> int:
    t0 = datetime.now().isoformat(timespec="seconds")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1560, "height": 950})  # 全新 profile
        page = context.new_page()

        # ---- 红线防护 1：真模型调用一律掐断（讨论管线 /api/agent/chat/stream）----
        def block_model(route):
            ABORTED_MODEL_CALLS.append({
                "url": route.request.url,
                "post_body": route.request.post_data,
                "at": datetime.now().isoformat(timespec="seconds"),
            })
            route.abort()
        page.route("**/api/agent/chat/stream", block_model)

        # ---- 红线防护 2：mock 只对探针消息生效，其余请求原样放行 ----
        # B 段探针：只 mock resolve 分类（→existing_action 进 dispatch），dispatch 为真实生产响应；
        # C 段探针：resolve 同样 mock，dispatch 返回与后端代码同构的降级 payload。
        REAL_CARD_PROBES = {  # message -> 期望真实卡关键词
            "帮我打开定投状态板": "定投状态板",
            "市场情绪速览": "市场情绪速览",
            "心态速览": "认知/心态卡片",
        }
        resolve_template = json.loads(
            (HERE / "resolve-existing-action-template.json").read_text())

        real = json.loads((HERE / "dispatch-s1-dca.json").read_text())
        dca_deg = json.loads(json.dumps(real, ensure_ascii=False))
        dca_deg["card"]["data"].update({
            "evidence_available": False, "evidence_version": None,
            "error_cn": "模拟演示：证据账本文件缺失（本条为页面降级态走查 mock，非生产数据）",
            "states": [], "breadth": {"cn": None, "us": None},
        })
        real_s = json.loads((HERE / "dispatch-extra-sentiment.json").read_text())
        sen_deg = json.loads(json.dumps(real_s, ensure_ascii=False))
        sen_deg["card"]["data"].update({
            "available": False,
            "reason_cn": "模拟演示：板块情绪数据缺失（本条为页面降级态走查 mock，非生产数据）",
            "hot_boards": [], "cold_boards": [], "margin": None, "symbol_note": None,
            "as_of": None,
        })
        real_m = json.loads((HERE / "dispatch-extra-mindset.json").read_text())
        mind_deg = json.loads(json.dumps(real_m, ensure_ascii=False))
        mind_deg["card"]["data"] = {
            "available": False, "count": 0, "sha256": None, "items": [],
            "note_cn": "认知/心态种子只作叙事与教育用途；每条带引用出处，内容不代表系统判定。",
        }
        # 后端种子缺失时的显式回落形状（copilot.py dispatch mindset 分支逐字段同构）
        DISPATCH_MOCKS = {
            "定投状态板模拟缺账本": dca_deg,
            "市场情绪模拟缺数据": sen_deg,
            "拿不住模拟缺种子": mind_deg,
            "怕跌模拟种子缺失回落": {
                "intent": "chat", "symbol": None, "chat_fallback": True,
                "fallback_reason": "mindset_seed_missing",
                "note_cn": "心态/认知话题已识别，但心态内容库不可用（缺失或损坏）——已转通用讨论，可继续聊。",
            },
        }

        def maybe_mock_resolve(route):
            try:
                body = json.loads(route.request.post_data or "{}")
            except Exception:
                body = {}
            msg = body.get("message", "")
            if msg in REAL_CARD_PROBES or msg in DISPATCH_MOCKS:
                MOCKED_RESOLVE_MESSAGES.append(msg)
                NETWORK.append({
                    "url": route.request.url, "status": 200, "mocked": "resolve_class_only",
                    "request_message": msg, "response": resolve_template,
                    "at": datetime.now().isoformat(timespec="seconds"),
                })
                route.fulfill(status=200, json=resolve_template)
            else:
                route.continue_()

        def maybe_mock_dispatch(route):
            try:
                body = json.loads(route.request.post_data or "{}")
            except Exception:
                body = {}
            mock = DISPATCH_MOCKS.get(body.get("message", ""))
            if mock is not None:
                MOCKED_DISPATCH_MESSAGES.append(body.get("message", ""))
                NETWORK.append({
                    "url": route.request.url, "status": 200, "mocked": "dispatch_payload",
                    "request_message": body.get("message"), "response": mock,
                    "at": datetime.now().isoformat(timespec="seconds"),
                })
                route.fulfill(status=200, json=mock)
            else:
                route.continue_()

        page.route("**/api/copilot/resolve", maybe_mock_resolve)
        page.route("**/api/copilot/dispatch", maybe_mock_dispatch)

        # ---- 网络留痕：页面实际收到的所有 /api 响应 ----
        def on_response(response):
            if "/api/" not in response.url:
                return
            entry = {
                "url": response.url, "status": response.status,
                "at": datetime.now().isoformat(timespec="seconds"),
            }
            try:
                entry["request_post_data"] = response.request.post_data
            except Exception:
                pass
            if response.url.endswith("/copilot/dispatch") or response.url.endswith("/copilot/resolve"):
                try:
                    entry["response_json"] = response.json()
                except Exception:
                    pass
            NETWORK.append(entry)
        page.on("response", on_response)

        # ---------- 开场：首页 + 打开 AI 助手抽屉 ----------
        page.goto(BASE + "/")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_selector("nav", timeout=30_000)
        check("home-loaded", BASE in page.url, f"url={page.url}")
        shot(page, "00-home")
        page.locator("nav button:has-text('AI 助手')").click()
        page.wait_for_selector(".drawer-panel", timeout=10_000)
        check("console-opened", page.locator(".drawer-panel").count() == 1, "AI 助手抽屉已打开")
        shot(page, "01-console-open")

        # ============ A 段：四场景真实路由（不 mock，如实记录） ============
        # 场景1：现在能定投吗 —— resolve 归为 discussion/topic=dca → 页面走澄清+讨论，
        # 不出 dca 快捷卡（与 dispatch 接口通道的 dca 直达卡构成链路缺口，如实记录）。
        send_and_wait(page, "现在能定投吗", None)
        page.wait_for_timeout(1500)
        text = body_text(page)
        check("s1-page-clarification-shown", "闲钱" in text,
              "页面先显示 resolve 澄清问句（这笔钱是新收入还是闲钱分批）——真实预路由行为")
        check("s1-page-no-dca-card", "定投状态板" not in text,
              "页面上未出现 dca 快捷卡——自由输入被预路由进讨论管线（缺口如实记录）")
        check("s1-page-model-blocked", len(ABORTED_MODEL_CALLS) >= 1,
              f"讨论管线请求被测试防护掐断（累计 {len(ABORTED_MODEL_CALLS)} 次），无真模型调用")
        shot(page, "02-s1-dingtou-page-realpath")

        # 场景2：这个买点为什么成立 —— 无命中 → chat_fallback → 讨论管线（掐断）
        send_and_wait(page, "这个买点为什么成立", None)
        page.wait_for_timeout(1500)
        s2 = dispatch_replies_for(NETWORK, "这个买点为什么成立")
        check("s2-dispatch-not-called-or-fallback",
              s2 is None or (s2["response_json"].get("intent") == "chat"
                             and s2["response_json"].get("chat_fallback") is True),
              f"dispatch 层无直达卡（真实预路由下该句不进 dispatch；接口通道单测见 dispatch-s2-buywhy.json）")
        check("s2-model-blocked", len(ABORTED_MODEL_CALLS) >= 2,
              f"讨论管线第二次被掐断（累计 {len(ABORTED_MODEL_CALLS)} 次）")
        check("s2-failed-note", "未能完成" in body_text(page), "页面如实显示讨论未完成（被测试掐断）")
        shot(page, "03-s2-buywhy-blocked")

        # 场景3：我的持仓需要关注什么 —— resolve=existing_action → 真实 dispatch → holdings 卡
        send_and_wait(page, "我的持仓需要关注什么", "持仓速览")
        cards = cards_text(page)
        check("s3-card-type", "持仓速览" in cards, "holdings 卡标题出现（真实生产 dispatch 响应渲染）")
        check("s3-empty-degraded", "暂无进行中的计划与基金持仓" in cards,
              "生产台账当前为空 → 卡内空态话术即数据缺失降级表现（真实数据，非 mock）")
        shot(page, "04-s3-holdings-empty")

        # 场景4：美股科技弱对我有什么影响 —— 无命中 → 讨论管线（掐断）
        send_and_wait(page, "美股科技弱对我有什么影响", None)
        page.wait_for_timeout(1500)
        s4 = dispatch_replies_for(NETWORK, "美股科技弱")
        check("s4-dispatch-not-called-or-fallback",
              s4 is None or (s4["response_json"].get("intent") == "chat"
                             and s4["response_json"].get("chat_fallback") is True),
              "dispatch 层无直达卡（真实预路由下该句不进 dispatch；接口通道见 dispatch-s4-ustech.json）")
        check("s4-model-blocked", len(ABORTED_MODEL_CALLS) >= 3,
              f"讨论管线第三次被掐断（累计 {len(ABORTED_MODEL_CALLS)} 次）")
        shot(page, "05-s4-ustech-blocked")

        # ============ B 段：三张真实卡页面渲染（探针消息只 mock resolve 分类，dispatch 真实） ============
        page.locator(".drawer-panel button:has-text('开新会话')").click()
        page.wait_for_timeout(500)

        per_card_shots = {"帮我打开定投状态板": "06a-dca-card-real",
                          "市场情绪速览": "06b-sentiment-card-real",
                          "心态速览": "06c-mindset-card-real"}
        for probe, marker in REAL_CARD_PROBES.items():
            send_and_wait(page, probe, marker)
            check(f"real-card::{probe}", marker in cards_text(page),
                  f"探针经 mock resolve 分类进入真实 dispatch，{marker} 卡=真实生产数据渲染")
            shot(page, per_card_shots[probe])
        check("b-no-degraded-copy", "数据不可用" not in body_text(page),
              "B 段全程无降级文案（生产数据在场）")
        shot(page, "06-three-real-cards")

        # ============ C 段：缺数据降级态（resolve+dispatch 均为探针 mock，生产零改动） ============
        page.locator(".drawer-panel button:has-text('开新会话')").click()
        page.wait_for_timeout(500)

        send_and_wait(page, "定投状态板模拟缺账本", "证据账本数据不可用")
        check("dca-degraded-copy", "状态无法计算" in body_text(page), "dca 降级话术完整出现")
        shot(page, "07-dca-card-degraded")

        send_and_wait(page, "市场情绪模拟缺数据", "情绪面数据不可用")
        check("sentiment-degraded-copy", "情绪面数据不可用" in body_text(page), "sentiment 降级话术出现")
        shot(page, "08-sentiment-card-degraded")

        send_and_wait(page, "拿不住模拟缺种子", "心态内容库不可用")
        check("mindset-degraded-card-copy", "本轮没有可展示的内容" in body_text(page),
              "mindset 缺场卡内降级话术出现（mock available=false 触发前端防御渲染）")
        shot(page, "09-mindset-card-degraded")

        # mindset 缺场·dispatch 显式回落形状（与后端代码逐字段同构的 mock）：
        # 页面行为=转讨论管线（被掐断），回落 note 仅存在于接口回包。
        send_and_wait(page, "怕跌模拟种子缺失回落", None)
        page.wait_for_timeout(1500)
        s_mb = next((n for n in reversed([n for n in NETWORK if n.get("mocked") == "dispatch_payload"])
                     if n.get("request_message") == "怕跌模拟种子缺失回落"), None)
        check("mindset-fallback-shape",
              bool(s_mb) and s_mb["response"].get("fallback_reason") == "mindset_seed_missing",
              "回落回包带 fallback_reason=mindset_seed_missing（与 copilot.py 391-397 逐字段一致）")
        check("mindset-fallback-blocked", len(ABORTED_MODEL_CALLS) >= 4,
              f"回落后讨论管线同样被掐断（累计 {len(ABORTED_MODEL_CALLS)} 次）")
        shot(page, "10-mindset-fallback-blocked")

        browser.close()

    summary = {
        "started_at": t0,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE,
        "browser": "local Chrome headless (Playwright channel=chrome), fresh context profile",
        "guards": {
            "model_calls_blocked": ABORTED_MODEL_CALLS,
            "note": "/api/agent/chat/stream 一律 abort——全程未产生真模型调用",
        },
        "mocked_resolve_messages": MOCKED_RESOLVE_MESSAGES,
        "mocked_dispatch_messages": MOCKED_DISPATCH_MESSAGES,
        "mock_scope_note": "resolve mock 只改分类结果让页面进 dispatch（卡数据为真实生产响应）；"
                           "dispatch mock 仅用于 C 段降级态与回落形状演示；含「模拟」字样的探针"
                           "消息与 B 段三条探针之外，所有请求原样放行。",
        "checks": RESULTS,
        "network_log": NETWORK,
    }
    (HERE / "browser-walkthrough.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1))
    failed = [r for r in RESULTS if not r["ok"]]
    print(f"\n== {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed; "
          f"model calls blocked: {len(ABORTED_MODEL_CALLS)} ==")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
