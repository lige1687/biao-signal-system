# 认知/心态种子库后端接入（叙事内容接入）— 2026-09-19

## 一句话结论（大白话）

把一套 26 条「投资心态/认知」的短句（每条注明出处）接进了系统的对话入口：
用户说「心态崩了、拿不住」这类话时，现在会弹出一张只讲道理、带出处的
「心态卡」；这些内容只用来讲解，**不参与任何买卖判断**——文件丢了或坏了，
系统就回到原来的通用聊天模式，不会坏。

## 测的是什么、结果是什么

- **测的**：GPT 计划 A 阶段（ITERATION:4）S1——种子库数据落地、加载校验、
  copilot dispatch 叙事卡、缺文件降级、判定层隔离。
- **结果**：全部落地并通过测试（核心 37 用例 + 回归 277 用例通过）。
  口径明确：这是「**叙事内容接入**」，不是「认知能力上线」——系统没有
  因此多出任何判断行情的能力。

## 数据与字段实测（与任务书预设有出入，如实记录）

- 来源：`lei-signal-sync/configs/mindset_seed.json` 原样复制入仓，26 条不改。
- sha256：`4bff4b76c120b2ac429e479752602…` 全值见 raw（`4bff4b76c120b2ac429e479752606390402b578d1bb248a533def927151b03e4`）。
- **字段取舍**：任务书预判四字段齐备；实测 `quote` 仅 3/26 条存在。加载器
  按 `category/text/source` 必需、`quote` 可选（缺失归一为空串）校验，
  已文档化于 `src/lei_signal/copilot/mindset.py` docstring。
- 类别分布：认知 10、心态 8、纪律 5、复盘 3。

## 实现要点

1. **加载器** `src/lei_signal/copilot/mindset.py`：读盘→必需字段校验→按自拟
   键去重（文件无显式 seed_key，自拟键 = `sha256(category+"\x00"+text)[:16]`，
   在模块 docstring 与本文档登记）→返回 available/items/count/sha256。
   四种降级（缺文件/JSON 损坏/结构错/零有效条目）均 `available=False`+reason。
2. **加载时机取舍**：任务书允许「首启自动导入」，但运行主线无首启钩子；
   采用**按需加载**（每次调用读盘，文件仅数 KB），行为等价、零新机制。
3. **intent.py**：mindset 命中时经 `_mindset_seeds_ok()` 判断——种子在场不带
   fallback_reason；缺位仍返回 `mindset_seed_missing`（回落行为与接入前一致）。
4. **copilot dispatch**：mindset 分支出 `card_type="mindset"` 叙事卡，data 含
   count/sha256/items（每条带 category/text/quote/source/seed_key），note_cn
   带只叙事红线；种子不可用时显式回落 chat + fallback_reason。
5. **agent.py** mindset 话题块：available 随种子在场翻转（附 count），仍只叙事。
6. **semantic_states.py 未加条目**（按任务书默认口径：种子是叙事内容，不是
   经实验验证的市场状态，不进 03B 严格目录）。

## 红线证明（双证）

- **代码路径**：`tests/unit/test_copilot_mindset.py::test_seed_content_isolated_from_decision_paths`
  逐一断言判定/评分/过滤/排序模块（research_proxy/recommend/resolve/sizing/
  fit/winrate/breadth/scout/review/sentiment）源码零 mindset 引用。
- **测试**：dispatch 出卡用例断言「不参与」红线措辞随卡下带；种子只经
  `copilot/mindset.py` → 叙事卡与话题块两个消费点，resolve.py 既有逻辑、
  情绪线、基本面线、交易规则零改动（diff 可核）。

## 验证证据

- 核心用例：`tests/unit/test_copilot_mindset.py`（10 例，含四降级+去重+隔离）
  与更新后的 intent/dispatch mindset 用例，共 37 通过（原始输出
  `raw/agent-mindset-seed-2026-09-19/pytest-core.log`）。
- 回归：`-k "resolve or intent or copilot or agent"`（排除 test_s13 外呼）
  277 passed / 2137 deselected；`test_agent_name_resolve` 在内通过。
- loader 实跑证据与降级路径证据：`raw/agent-mindset-seed-2026-09-19/
  loader_summary.json`、`degradation_evidence.json`。
- 仓库卫生：`python3 scripts/check_repo_hygiene.py` 全绿（见 raw）。

## 过程记录

- 执行中途本机磁盘写满（ENOSPC），实现与测试已完成但归档/提交被阻断，
  以 needs_input 上报；主控清理可再生空间后（约 1.2GB 可用）续跑收尾，
  实现与测试未重写。本轮为磁盘空间恢复续跑，非返修。

## 最小决策卡

| 项 | 内容 |
|---|---|
| 变更性质 | 叙事内容接入（非判定能力变更） |
| 影响面 | copilot dispatch 出卡、agent 话题块 available、intent 回落标注条件化 |
| 回滚方式 | revert 本提交；删 configs/mindset_seed.json 即自动回落旧行为 |
| 遗留 | 前端渲染（web/）为下一阶段另一批活，本次未动 |
