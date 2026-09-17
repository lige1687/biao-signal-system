# Agent 跨标的名称绑定修复（S1）：隔离复现与最小实现

## 一句话结论（大白话）

修好了一个答非所问的毛病：先问通信ETF、再问"沪深300"或"上证指数"时，
系统此前仍会把通信ETF的资料交给AI、把回答挂在通信ETF名下。现在再问
沪深300就会真正切换到沪深300（代码000300.SS）、资料卡和落库记录都跟着
换；追问"那失效位呢"这类没有提到新名字的话，仍正确沿用上一个标的；
明确点名的新对象没有行情数据时，不再错拿旧标的的资料卡来充数。修复只在
两处目录表里补上了系统本来就有的大盘指数名单，没有改任何交易规则、阈值
或判定逻辑。全部证据来自真实接口路由＋禁网隔离＋临时数据库，**尚未合入
运行环境，也未做真实模型和浏览器验证**（后者属S2范围）。

## 服务于策略体系的哪一层

解释展示层（`docs/trading-spec-v1.md` 体系下的资料呈现）：用户讨论对象
（阶段、路牌、触发条件、失效位）必须与系统实际分析的标的一致。不改变
双均线方向、顶底构造/关键波动/量能异常预警、A/B/C/D 入场触发、过滤纪律
的任何判定；不扩展多标的比较；不引入模糊别名匹配。

## 缺陷与根因（引用既有核实，不重复研究）

缺陷核实见运行目录
`docs/experiments/agent-symbol-binding-review-2026-09-17.md`（只读引用）：
先问515880通信ETF，再说"沪深300/上证指数"名称时，resolved 仍是515880。

根因（该报告已定位，本轮确认属实）：

- `src/lei_signal/api/routes/agent.py::_resolve_symbol_by_catalog` 装入
  STRATEGY_INDICES / US_ETFS / THS行业 / 概念目录，**唯独没装
  `DASHBOARD_INDICES`**（`src/lei_signal/api/config.py` 里已定义
  上证指数/沪深300/科创50 等9条精确名称代码）。名称层全部落空后，
  解析优先级跌到"页面选中/会话继承"，旧对象接管。
- `src/lei_signal/copilot/subjects.py::catalog_names` 同样缺
  DASHBOARD_INDICES：识别接口对 000300.SS 返回空显示名，
  对"沪深300"问法回显旧选中对象的名称「通信ETF」。

## 实际修改（最小实现，2文件 +17/-4）

1. `src/lei_signal/api/routes/agent.py::_resolve_symbol_by_catalog`：
   目录条目加入 `DASHBOARD_INDICES`（精确名称完整出现才命中，无模糊扩展）。
2. `src/lei_signal/copilot/subjects.py::catalog_names`：显示名目录加入
   `DASHBOARD_INDICES`。

`/api/agent/chat`、`/api/agent/chat/stream`、`/api/copilot/resolve` 三个
入口共用该目录层，一处修复同时覆盖。前端零改动（名称一律由后端下发，
前端不猜标的）。

## 验证方法与结果

复现脚本：`docs/experiments/raw/agent-glm-symbol-binding-fix-2026-09-18/
repro_symbol_binding_fix.py`（`baseline`/`fixed` 两种模式同一脚本）。
隔离强度：审计钩子先于业务导入安装，硬阻断并记录全部 DNS/连接、沙箱外
写入、真实 `.env`/业务库读取、非临时 SQLite；模型双路打桩（流式/非流式）、
合成行情、一次性临时库、工作目录独立；结束断言四类计数全零。

### 失败基线（修复前，工作区 00e0fa05，产品基线 71070885）

50条机检0失败、护栏四类全0，其中3例缺陷按预期复现：

| 场景 | 修复前实际结果 |
|---|---|
| 515880→「沪深300」（stream，有数据） | 仍绑 515880.SS，资料卡/AI材料都是通信ETF（缺陷复现） |
| 515880→「上证指数」（plain，有数据） | 同上（缺陷复现） |
| 515880→「上证指数」且指数无行情（stream） | 附旧515880卡（缺陷复现，最坏形态） |
| 515880→明确000300.SS代码（selected 保留旧值） | 正确绑 000300.SS（既有保护保持） |
| 「那失效位呢」追问 | 正确继承 515880.SS（保持） |
| 明确新代码但无行情 | 无旧卡、退全局（保持） |
| 科创50板块 / 科创板整体 | 000688.SS指数身份 / 不冒充指数（语义保持） |
| 显示名目录 | 000300.SS→`null`；resolve探针回空名或「通信ETF」（缺口实证） |

### 修复后（同脚本 `fixed` 模式）

61条机检0失败、护栏四类全0：

| 场景 | 修复后实际结果 |
|---|---|
| 515880→「沪深300」（stream） | resolved=000300.SS，资料卡/速览卡/AI材料=沪深300，落库一致 |
| 515880→「上证指数」（plain） | resolved=000001.SS，全链一致 |
| 「上证指数」且指数无行情（stream） | resolved=None、无旧卡、AI材料=全局（不附旧卡） |
| 明确代码 / 追问继承 / 缺行情保护 / 科创语义 | 全部保持通过 |
| 显示名目录 | catalog_names/_static_symbol_name/resolve探针均回「沪深300」「上证指数」 |
| 两个标的并列比较 | 维持现状：chat取首个代码、识别接口另提示澄清（本轮不发明比较引擎） |

### 既有测试回归

`PYTHONPATH=src /opt/homebrew/bin/python3.11 -m pytest`，受影响区域
13个测试文件 155 项：153 通过，2 失败均与本次改动无关（修复前基线
`git stash` 复跑同样失败）：

- `test_symbol_extraction.py::test_extract_from_chinese_context`：测试期望
  `TH881157`（不带后缀），正则实际产出 `TH881157.SECTOR`——期望滞后于
  既有实现；运行时提取实际正常（两种写法都归一到 .SECTOR 并正确解析）。
- `test_discussion_backtest_03b.py::test_s13_no_llm_degraded_has_evidence_sections`：
  任务书已知会外呼真实 API 的测试，沙箱内 404 失败，环境性问题。

## 限制与边界

- 证据来自隔离桩环境：不代表真实模型正文质量；未做真实浏览器渲染验证
  （S2 按主控安排执行）；未覆盖会话中断恢复。
- 显示名可读性验证到接口层（resolve/chat 载荷、catalog_names）；页面
  呈现属 S2 浏览器核验。
- 继承来源字段（`subject_source`）下发给前端、双标的比较引擎：维持
  上轮复核的独立待定范围，本轮未实施。
- 两个既有失败测试不属本轮范围，未改动（保留其他在制工作）。
- **尚未实际合入**：改动仅在本任务分支，运行工作区/服务/main 未动，
  合入由主控在阶段验收后执行。

## ARCHIVE：复现与证据

- raw 目录：`docs/experiments/raw/agent-glm-symbol-binding-fix-2026-09-18/`
- `repro_symbol_binding_fix.py` — 复现脚本（先 `baseline` 后 `fixed`，
  两次退出码均须为0；`baseline` 模式必须在**未含修复**的源码树上跑——
  本目录 matrix-baseline.json 即以 stash 两处修复文件的方式在修复前
  代码态生成，修复合入后重跑 baseline 报「缺陷未复现」属预期）
  - `matrix-baseline.json` / `matrix-fixed.json` — 全量请求响应、逐案例
    verdict、显示名对照、护栏计数
  - `logs/case-checks-*.json` — 50/61 条逐条机检明细
  - `logs/guard-attempts-*.json` — 隔离护栏记录（全空）
  - `isolated-cwd/` — 运行沙箱
- 修复前复核底稿（只读引用）：运行目录
  `docs/experiments/agent-symbol-binding-review-2026-09-17.md` 及其 raw；
  controller-recheck-v2 证据在
  `/Users/yongbiaoli/.codex/zcode-delegate/briefs/symbol-binding-recheck-2026-09-17/controller-recheck-v2/`。
- 被测代码：本工作区 `codex/agent-runtime-adoption-20260917` 分支，
  修复前 HEAD 00e0fa05（产品冻结基线 71070885），运行目录只读重核
  HEAD 7f8c38c3、来源main目录 f8638b9f（与任务书一致）。
