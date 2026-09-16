# 消费者清单（research-input-preflight-2026-09-13 Task 1）

方法：只读检索 + 逐处读代码确认。"函数存在"不等于"已消费"。
检索式：`rg -n 'check_prices\(|check_snapshot\(|require_use\(|bind_definitions\(|build_mixed_batch\(' scripts src/lei_signal/research`

## 实际调用点

| 入口 | 位置 | 读快照 | 验哈希 | 检查用途 | 传声明 | 绑对象 | 真的计算 | 状态 |
|---|---|---|---|---|---|---|---|---|
| `scripts/run_research_data_snapshot.py::_run_quality` | `:66` | 有（`load_snapshot`，`cmd_verify` 先核 `verified`） | 有 | **无**（不调 `require_use`，只输出 report 打印） | **是**——`declared_basis`、`calendar_authority` 由调用方声明，**不传日历对象** | 无 | 无 | **legacy**：走旧的"调用方声明口径"路径，未接 `check_snapshot`/用途闸门 |
| `scripts/run_research_data_snapshot.py::cmd_bind` | `:162` | 无 | 无 | 有（`purpose` 参数可选传入） | 无 | 有（`bind_definitions`）但**不传 snapshot**——`provided_fields` 退回 `NORMALIZED_FIELDS` 常量 | 无 | **legacy**：绑定基于常量而非实际快照字段（这正是此前缺陷 T 的路径，未改） |
| `scripts/run_factor_library_v0.py` | `:545` | 有（冻结输入） | 有（`verify_sources` + 快照哈希） | 有（v0 自有资格逻辑） | 有 | 有 | **有**（`build_mixed_batch` 计算动量/波动/趋势，含 `historical_reconstruction_only` 闸门） | **frozen legacy**：v0 冻结研究计算链，本轮只映射，不迁移、不倒填合规版本 |
| `src/lei_signal/research/factor_runtime.py::build_mixed_batch` | `:246` | （被 v0 脚本调用） | — | — | — | — | 有 | **frozen legacy**（同上） |

## 明确未接入

- **没有任何生产或既有研究消费者**调用 `check_snapshot` / `require_use`（除本轮及此前各轮的测试）。
- `factor_account_adapter`、`factor_diagnostics`、生产宽度与全 A 日常计算、所有冻结实验脚本：legacy，未接新检查层。
- `trading_halt` 的规范化函数（`factor_runtime.py:161-182`）会丢弃停牌类型——本轮检查缺口**不**经由它，行动原始记录直接交 `check_actions`。

## 结论

新建 `input_preflight` 是**第一个**把"完整性 → 用途闸门 → 对象绑定"串起来的消费者；
旧 CLI 与 v0 脚本保持 legacy，本轮不改、不宣称迁移完成。
