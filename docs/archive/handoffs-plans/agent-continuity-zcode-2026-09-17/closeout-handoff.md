# 交接：连续讨论补修收口（ZCode 执行轮，2026-09-17）

> **round=3 修订（最后一轮）**：主控第二轮复核（
> `controller-zcode-continuity-r2-2026-09-17.md`）证实 round=2 的整句级
> 守卫在一句多事时互相误伤；本轮把否定与归属判断改为**分句级**
> （`resolve.py` 的 `_clause_spans`/`_own_clause` 共用结构 +
> `agentUx.ts` 的 `hasAffirmativeExec` 逐动作核实），报告新增 §9。
> 修后证据在 `docs/experiments/raw/agent-continuity-zcode-closeout-r3-2026-09-17/`
> （主控 mixed 探针复跑、ATR 混合 4 例复跑、两入口浏览器链、r3 指纹、
> 回归日志）；主控两轮失败证据原样保留未覆盖。
>
> **round=2 修订**：主控第一轮复核（`controller-zcode-continuity-2026-09-17.md`）
> 三处残余已修复——G1 `web/src/utils/agentUx.ts`（肯定执行要求不被概念词
> 放行）、G2 `src/lei_signal/copilot/resolve.py`（撤销须本人肯定陈述、用途
> 与金额同界）、G3 报告文案纠错。修后证据在
> `docs/experiments/raw/agent-continuity-zcode-closeout-r2-2026-09-17/`。
> 下方为 round=1 原始交接，原样保留。

## 给谁看

主控（Codex）复验本分支时看这份；执行过程细节全在
`docs/experiments/agent-continuity-zcode-closeout-2026-09-17.md` 与同名 raw 目录。

## 本轮做了什么（一句话）

按冻结任务卡验证 e461d838 的两项收口（ATR 继续讨论可达 / 用户事实精确归属），
**全部成立，零产品代码改动**；新增内容只有报告、raw 证据、registry/INDEX 登记
与本目录交接文件。

## 复验路径（主控独立重跑建议）

1. 两套连续讨论测试（41）：命令见报告 §5。
2. 全量回归（144 通过 + 1 已知 xfail）：同一节，注意 xfail 是
   `tests/integration/test_agent_chat_e2e.py` 的既有校验器缺口，不是本轮产物。
3. 浏览器链可复跑：`raw/agent-continuity-zcode-closeout-2026-09-17/`
   下 `serve_iso_r3.py`（MODEL_MODE=degraded ISO_PORT=8022，临时库、无模型、
   不读密钥）→ `ui_atr_chain_r3.py` + `console_concept_recheck.py`；
   端口用 8022/8032，不占 8000/5173，跑完停自己起的进程。
4. G2 矩阵：`g2-fact-matrix.py`（临时库真实 message_id/question_id）；
   ATR 守卫：`atr_guard_probe.py`；归置：`run_hygiene_readonly.py`（只读，
   借运行仓脚本原函数重定向检查根，运行仓与历史文件零改动）。

## 证据清单（raw/agent-continuity-zcode-closeout-2026-09-17/）

- `ui_atr_chain_r3.py` + `screens/r3-*.png` + `screens/r3-atr-chain-notes.json`
  + `atr-chain-requests.json`：两入口 ATR 链页面+请求证据；
- `console_concept_recheck.py` + `console-concept-recheck.json` +
  `screens/r3-console-atr-concept-recheck.png`：控制台概念问法严格复测
  （首轮脚本等待条件可能被上一轮提前满足，严格复测要求轮数净增+新请求）；
- `g2-fact-matrix.py` / `g2-fact-matrix.json`：五反例+正例+真实身份矩阵；
- `atr_guard_probe.py` / `atr-guard-probe.json`：指标词守卫与真实证券保留；
- `serve_iso_r3.py` + `server-r3.log` + `environment-iso-degraded.json`：
  隔离服务与临时库信息；
- `source-fingerprints.json`：11 个关键文件 SHA256（= e461d838 状态）；
- `runtime-dir-readonly-diff.json`：与运行目录只读比对（9 差异 / 2 新增）；
- `hygiene-r3.log` + `hygiene-r3-summary.json` + `run_hygiene_readonly.py`：
  归置 298 项 = 基线 299 − 1 已解决，本次新增 0。

## 已知残留（原样报告，主控裁断，本轮未改）

拦截轮答案卡「接下来（针对 名称待核实（515880.SS））」标签取本轮自身卡片
（拦截轮无卡片）；e461d838 之前的 r2 证据即如此，对象符号正确、显示诚实，
cfix2 显示名修复范围为标题/上下文条（已正常）。详见报告 §4。
