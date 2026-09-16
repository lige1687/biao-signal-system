# 消费者接入图（consumer-map）— fixed-etf-evidence-integration 2026-09-13

## 本轮已实际接入

| 入口/模块 | 接入内容 | 证据 |
|---|---|---|
| `scripts/prepare_momentum_qualified_inputs.py`（新） | 证据包校验 → 派生 economic_index 快照 → 离线读回 → 字段绑定 → 772 正式键算术核对 | run-02（checked=772, mismatch=0；两对象 directly_satisfiable=true） |
| `src/lei_signal/research/qualification_bundle.py`（新） | 证据包结构/来源/身份/事实校验 + listing 桥接生成 | tests/unit/test_qualification_bundle.py（14 项，含 11 类反例） |
| `scripts/run_momentum_research_prototype.py` | 可选 `research_evidence` 协议字段：校验真实证据包；已核上市事实经桥接进 `check_snapshot(listing_evidence=…)`；时间资格（早/晚/null/同日时区/目标未成熟）；历史模式晚取得标注 | run-03 vs run-05 发现对照（2 条发现文案改变：515050/562590 → 日期自洽但资格未授予）；run-04/06 资格拒绝；momentum 测试 14 项时间/桥接用例 |
| 派生快照（run-02/snapshot） | 名义 OHLCV 逐字节保留 + economic_index 事后重建列；`historical_reconstruction_only=true` 保留 | snapshot.json derivation 段 + manifest 输出哈希 |

## 明确未接入（保持原状）

- 原 v0 因子库入口（`run_factor_library_v0.py`）——未接证据/派生快照。
- 生产/API/UI（`src/lei_signal/api/`、`web/`）——未消费任何本轮产物。
- 账户适配（`factor_account_adapter.py`）——本轮零账户计算。
- 生产价格引擎（`data/calendar.py`、信号链路）——未动。

## 严格时间卡的差异（不能吃日期界限）

对象卡的时间语义要求 `available_at`（精确可得时刻）。本轮证据只提供
**公布日期下界**（公告送出日期/公告日期），按任务书不写入
`available_at`，只作旁置 `time_evidence`。因此：

- `quality.json` 的 `uses` 中 ranking/research_signal 仍不可用；
- qualified 分支的时间资格对 null available_at 一律拒绝；
- 若要让日期界限进入正式资格判定，需要**另行版本化的时间规则与授权**
  （例如"公布日次日开盘视为可得"这类保守规则的制定与批准），本轮只列差异。
