# 意图路由扩展（定投/情绪/认知）S2 实现、测试与候选交付 — 2026-09-19

> 状态：S2 阶段交付（候选实现，**未合并、未部署、未生产采用**——主控独立复核后
> 另行授权）。按 S1 冻结方案与用例矩阵实现
> （S1 报告：`agent-intent-routing-audit-2026-09-19.md`）。

## 一句话结论（大白话）

把快捷指令入口「听懂一句话」的路由表扩了三类：说**定投**（如「现在能定投吗」）
直接出定投状态板卡片（只有数据提示，不会替你下单）；说**市场情绪**（如「市场
情绪怎么样」）直接出情绪解说卡（只解释「为什么」，不拦任何信号、不影响判定）；
说**心态/认知**（如「心态崩了」）系统会明说「这类内容库还没建好」，然后转回
普通聊天，转回原因在接口回包里看得见。旧五类指令（报单/机会扫描/推荐/持仓/
复盘）一个字没改，全部回归测试通过；测试全程禁网（会联网的行情数据在测试里
用空值替代，线上代码不变）。**这只是候选，还没上线**。

## 1. 改动清单（5 文件，+236/-2；行号相对 S1 提交 5b2fd8a5）

| 文件 | 改动 |
|---|---|
| `src/lei_signal/copilot/intent.py` | `_INTENT_RULES` 尾部追加三类（dca/sentiment/mindset）；`Intent` 增 `fallback_reason` 字段；`parse_intent` 对 mindset 标 `mindset_seed_missing`；模块 docstring 写明优先级与词表口径 |
| `src/lei_signal/api/schemas.py` | `CopilotDispatchReply` 增 `fallback_reason: str \| None = None`（带默认，非破坏） |
| `src/lei_signal/api/routes/copilot.py` | dispatch 新增 dca/sentiment 两个直达分支；chat 回落分支携带 `fallback_reason` 与说明文案 |
| `tests/unit/test_copilot_intent.py` | +8 个矩阵用例（新三类/否定/交叉优先级/连续讨论/回落原因） |
| `tests/unit/test_copilot_dispatch.py` | +5 个入口级轨迹断言（回包结构判定，不凭回答正文） |

实现要点（对应 S1 冻结方案）：

- **优先级**：旧五类在前、原序原词不动（追加式扩展，旧行为零回归由构造保证）；
  新三类依次 dca→sentiment→mindset。sentiment 先于 mindset 与
  `copilot/resolve.py` 话题词表自身顺序一致。已写进 intent.py docstring 与注释。
- **dca 直达**：调 `lei_signal.dca` 服务层只读适配器出状态卡（证据账本可用性 +
  中美宽度读数 + 带 symbol 时该标的逐状态；先例 agent.py 话题块同款调用）。
  零下单零记账——实际买卖仍走报单确认台账。**不挂载 `/api/dca` REST**（S1 实证
  未挂载属既成事实，挂载与否留主控裁决，本合同不扩）。
- **sentiment 直达**：调 `copilot/sentiment.py` 只叙事模块（板块热度包+两融环境
  +带 symbol 时单标的标注）；note_cn 随卡下带只叙事红线措辞。无任何过滤逻辑。
- **mindset 显式回落**：识别为 mindset 后因种子库缺位（S1 确认）回落通用讨论，
  回包 `intent="chat"`、`chat_fallback=true`、`fallback_reason="mindset_seed_missing"`、
  note_cn 说明。不改语义状态校验任何逻辑。
- **词表口径**：sentiment/mindset 与 resolve.py 逐字一致；dca 窄于 resolve.py
  （不含 闲钱/每月/工资/新收入，理由见 S1 报告 §4.1）。

## 2. 测试证据（原始输出见同名 raw `test-output.txt`）

| 组 | 命令 | 结果 |
|---|---|---|
| 用例矩阵+既有回归 | `pytest tests/unit/test_copilot_intent.py tests/unit/test_copilot_dispatch.py -v` | **26 passed**（旧 14 + 新 12） |
| 名称绑定回归（红线） | `pytest tests/unit/test_agent_name_resolve.py -v` | **10 passed** |
| resolve.py 讨论入口边界 | `pytest test_discussion_backtest_03b.py test_agent_context_contract.py test_agent_continuity_20260916.py -q --deselect …::test_s13…` | **73 passed, 1 deselected** |
| 静态检查 | `ruff check`（4 个改动文件） | All checks passed |

- **test_s13 说明**：首次全量跑第三组出现 1 failed =
  `test_s13_no_llm_degraded_has_evidence_sections`。经 `git stash` 后在 S1 基线
  5b2fd8a5（无本改动）复跑**同样失败** → 基线既有失败，且该用例正是简报红线
  「不运行已知会外呼真实 API 的用例（先例 test_s13）」所指，按红线排除并如实记录。
- **禁网落实**：全部测试为 tmp 库隔离；sentiment 分支的两融行情是唯一外呼来源，
  路由测试用 `monkeypatch` 注入 None（生产代码不变，缺席如实降级）。
- 入口级轨迹断言（不凭回答正文）：dca 直达卡（`card_type=dca`、非回落）、
  sentiment 直达卡、mindset 回落（`fallback_reason` 可观察）、旧 chat 回落
  （`fallback_reason=null`）、连续三条无隐藏会话态、旧报单预览回归。

## 3. 真实边界（主控复核请重点看这里）

1. **未上线**：候选分支提交，未合并、未部署、未生产采用。
2. **前端不渲染新卡**：`web/` 零改动（页面改版红线）。dca/sentiment 卡的
   `card_type` 是新值，前端快捷入口若没有对应渲染分支，表现等同既有未知卡
   处理；API 回包结构已可验。
3. **已知取舍（S1 冻结，主控可改判）**：D4「情绪不好，睡不着」→ sentiment
   （「情绪」兼市场/心情两义，与 resolve.py 同序）；D5「别定投了」→ dca
   （本层无否定处理，与「别买了」今日命中 trade_report 同一既有局限）。
   精细处理归 resolve.py，本合同不复制。
4. **既有问题未顺手修**：copilot.py 有 7 处 ruff 报错与 test_s13 1 处基线失败
   ——均在 S1 提交即存在、位于本合同未触碰区域，按「不覆盖他人多线改动」
   红线保留并留证。
5. **`/api/dca` REST 仍未挂载**：本合同维持现状（S1 裁决项）。dispatch 的
   定投卡不依赖该 REST。

## 4. 验收对照（G2 三条）

- intent.py 三类显式规则+优先级文档化 ✓（docstring+注释）；认知显式回落且原因
  可观察 ✓（`fallback_reason` 回包字段+note_cn）；情绪只叙事无硬过滤 ✓（零过滤
  代码，note_cn 红线措辞）。
- 矩阵全过留原始输出 ✓（raw §1-3）；既有 intent 回归与 test_agent_name_resolve
  不破坏 ✓（26+10 passed）；入口级轨迹断言成立 ✓（5 项结构断言）。
- 候选分支提交+报告+同名 raw+registry/INDEX 增量登记+卫生检查 ✓（见 §ARCHIVE；
  卫生检查仅 1 处既有环境项：worktree 指针文件 `.git`，S1 已留证，非本任务产物）。

---

## ARCHIVE

- 结案时间：2026-09-19（S2 阶段；整体任务待主控独立复核，生产采用另行授权）
- 执行：ZCode（GLM-5.3 Flash），job 09e2707a stage=S2 attempt=initial
- 分支：codex/agent-runtime-adoption-20260917；实现前基线 5b2fd8a5（=S1 交付），
  本阶段候选提交见 git log
- raw 对照：`docs/experiments/raw/agent-intent-routing-2026-09-19/test-output.txt`
- S1 前置：`agent-intent-routing-audit-2026-09-19.md`（链路审计+矩阵冻结）
- 未解决问题：① 前端新卡渲染（页面改版，另立任务）；② D4/D5 词表取舍待主控
  认可或改判；③ `/api/dca` 挂载裁决；④ copilot.py 7 处既有 lint 与 test_s13
  基线失败（他线区域，未动）。
