# 四场景验收 + 三卡视觉走查 · 走查记录（raw）

- 时间：2026-09-19 02:36–02:47（本地）
- 被验收对象：生产运行系统。前端 vite `http://127.0.0.1:5173`（dev server，
  `/api` 代理到后端 `http://127.0.0.1:8000`），后端 `/api/health` =
  `{"status":"ok"}`。全程未重启服务、未写任何库、未改任何生产文件。
- 页面驱动：本机 Chrome headless（Playwright `channel="chrome"`），
  **全新 context**（独立 profile，无任何历史 cookie/登录态，未登录任何账号）。
- 脚本：`page_walkthrough.py`（与本记录同目录）；最终一次运行
  **21/21 断言通过**，原始输出 `walkthrough-run.log`，网络留痕
  `browser-walkthrough.json`（含每条 /api 请求的 URL、状态码、时间戳、
  dispatch/resolve 的完整响应 JSON）。

## 红线落实（可复核）

1. **零产品代码改动**：本目录所有文件都是新增 raw/报告产物；`git status`
   里 src/、web/、configs/ 零改动（结案前跑 `git status --short` 留证）。
2. **禁真模型调用**：`/api/agent/chat/stream` 被 Playwright 路由拦截一律
   abort，全程共掐断 **4 次**（场景1/2/4 + mindset 回落演示各 1 次），
   明细在 `browser-walkthrough.json` 的 `guards.model_calls_blocked`。
   页面上表现为「未能完成：Failed to fetch」——这是测试防护造成的，
   不是生产缺陷（见报告缺口清单第 3 条的说明）。
3. **mock 范围（生产文件零改动）**：
   - B 段（真实卡页面渲染）：仅 mock `/api/copilot/resolve` 的**分类结果**
     （返回生产真实 existing_action 模板 `resolve-existing-action-template.json`），
     让页面把探针消息送进 `/api/copilot/dispatch`——**dispatch 响应是真实
     生产数据**，卡上所有数字/出处都来自生产。探针 3 条：
     「帮我打开定投状态板」「市场情绪速览」「心态速览」。
   - C 段（降级态）：resolve 同上，另 mock `/api/copilot/dispatch` 返回
     与后端代码同构的降级 payload（降级字段标注「模拟演示」）。探针 4 条：
     「定投状态板模拟缺账本」「市场情绪模拟缺数据」「拿不住模拟缺种子」
     「怕跌模拟种子缺失回落」。
   - 除上述 7 条探针外，所有请求原样放行。

## 双通道取证对照表

| 场景/走查项 | 接口通道（curl 直打 dispatch） | 页面通道（真实 Chrome 驱动） | 结论 |
|---|---|---|---|
| 1「现在能定投吗」 | `dispatch-s1-dca.json`：intent=dca，card_type=dca，证据账本可用（版本 2026-09-08-r2），HTTP 200 | `02-*.png`：页面先弹 resolve 澄清问句「这笔钱是新收入还是闲钱分批？」，随后转讨论管线（被测试掐断），**页面不出 dca 卡** | **链路缺口**：dispatch 层直达卡成立；页面自由输入被 03B 预路由截走（见报告缺口1） |
| 2「这个买点为什么成立」 | `dispatch-s2-buywhy.json`：intent=chat，chat_fallback=true，「未命中快捷指令，已转通用讨论。」 | `03-*.png`：页面经 resolve 直接进讨论管线（被掐断），无卡 | 路由事实与代码一致（intent.py 无命中→chat）；讨论回答未跑（禁真模型） |
| 3「我的持仓需要关注什么」 | `dispatch-s3-holdings.json`：intent=holdings，active_plans=[]，fund_positions=[] | `04-*.png`：真实持仓卡渲染，空态话术「暂无进行中的计划与基金持仓。」 | 页面链路全通（resolve=existing_action→dispatch→卡）；生产台账当前为空，空态话术即数据缺失降级表现（真实数据非 mock） |
| 4「美股科技弱对我有什么影响」 | `dispatch-s4-ustech.json`：intent=chat，chat_fallback=true | `05-*.png`：页面直接进讨论管线（被掐断），无卡 | 同场景2；跨市场传导未验证，如实记边界 |
| dca 卡·真实 | `dispatch-s1-dca.json`（A股宽度 26.235、美股 71.1%、11 标的） | `06a-dca-card-real.png`：卡渲染真实生产数据 | 页面渲染与接口数据一致 |
| sentiment 卡·真实 | `dispatch-extra-sentiment.json`（available=true） | `06b-sentiment-card-real.png` | 同上 |
| mindset 卡·真实（种子在场） | `dispatch-extra-mindset.json`（count=26；种子文件 sha256=4bff4b76…b03e4） | `06c-mindset-card-real.png`（26 条、心态/纪律/复盘分类、文主任出处） | 同上 |
| dca 卡·缺数据降级 | —（生产账本在场，无法在生产复现缺账本；C 段 mock） | `07-dca-card-degraded.png`：「证据账本数据不可用…状态无法计算。」+ 两行「数据不可用（健康度：未核实）」 | 降级话术真实存在 |
| sentiment 卡·缺数据降级 | 同上（mock） | `08-sentiment-card-degraded.png`：「情绪面数据不可用：模拟演示…。」 | 同上 |
| mindset 卡·缺种子（卡内态） | 同上（mock available=false） | `09-mindset-card-degraded.png`：「心态内容库不可用，本轮没有可展示的内容。」 | 前端防御渲染真实存在 |
| mindset·缺种子（dispatch 显式回落形状） | mock 与 `copilot.py:391-397` 逐字段同构（fallback_reason=mindset_seed_missing） | `10-mindset-fallback-blocked.png`：页面转讨论管线（被掐断） | 回落形状经接口层核验；生产种子在场，该分支休眠 |

## 截图与产物清单（含截图时页面 URL）

所有截图为 full-page，页面 URL 均为 `http://127.0.0.1:5173/`（工作台首页，
抽屉为全局「AI 助手」侧栏）。捕获时间戳见 `browser-walkthrough.json` 与
`walkthrough-run.log`（逐行 `SHOT <名> :: <url> @ <ISO时间>`）。

- `00-home.png` 首页基线；`01-console-open.png` 打开 AI 助手抽屉
- `02-s1-dingtou-page-realpath.png` 场景1页面真实路径（澄清问句+掐断）
- `03-s2-buywhy-blocked.png` 场景2（无卡+掐断）
- `04-s3-holdings-empty.png` 场景3 真实持仓卡（空态降级话术）
- `05-s4-ustech-blocked.png` 场景4（无卡+掐断）
- `06-three-real-cards.png` B 段三卡同屏（滚动到底，mindset 可见）
- `06a/06b/06c-*-card-real.png` dca/sentiment/mindset 真实卡单卡截图
- `07/08/09-*-degraded.png` 三卡缺数据降级态截图
- `10-mindset-fallback-blocked.png` mindset 缺种子回落形状的页面行为
- `dispatch-*.json`（6 份接口通道原始响应）、`resolve-existing-action-template.json`
- `browser-walkthrough.json`（21 项断言明细 + 全量网络留痕 + mock 范围声明）
- `page_walkthrough.py`（复现脚本）、`walkthrough-run.log`（原始运行输出）

## 复现

```bash
cd docs/experiments/raw/agent-scenario-acceptance-2026-09-19
curl -s -X POST http://127.0.0.1:8000/api/copilot/dispatch \
  -H 'Content-Type: application/json' -d '{"message":"现在能定投吗"}'   # 接口通道
python3 page_walkthrough.py                                            # 页面通道（需前端 5173 在跑）
```
