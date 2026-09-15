# 主控探针复测说明（未修改主控探针）

主控探针：`docs/experiments/raw/controller-ask-stability-review-2026-09-15/probe.py`
（执行方未改动；复测用的是原样副本 `probe-rerun.py`）。

## S2/S3 段（探针前半）：全部复测通过

逐项同操作复测结果见 `probe-counterexample-recheck.json`（执行方按探针
相同操作序列编写，输出同名字段）：

| 主控反例 | 修前（主控 results.json） | 修后复测 |
|---|---|---|
| `cursor_write` | tracked=[]（不可见） | tracked 含 `write_lock`（库路径正确） |
| `deferred_begin_without_write` | 被登记为持锁者（explicit） | 登记为 `tx_open_no_write`，不是持锁者 |
| `failed_waiter_registered_as_writer` | 失败等待方在活跃写者中 | 等待方不登记（tracked=[]） |
| `commit_failure`（Tracked） | in_transaction=true、未提交行数 1 | **false / 0，与原生逐项一致** |
| `commit_failure_native` | false / 0 | false / 0（对照不变） |

单元矩阵 `tests/unit/test_write_tx_tracking.py`（15 条）覆盖同场景及
SQL COMMIT/ROLLBACK、executescript 留未结束事务、关闭清理、按库区分快照、
慢等待/慢持有日志、锁失败日志指认同库持锁者且不含 SQL 参数。

## S1 段（探针后半）：场景结论成立，但探针自身的同步点不再触发

未修改的探针副本复测结果：脚本在 `assert finished.wait(5)`（第 81 行）
抛 AssertionError，不产出 S1 结果键。原因：

- 探针用 `fake_prepare`（内部 `finished.set()`）作为「后台工作者已走完全程」
  的同步信号——这预设了**工作者领到号后一定会进入准备**。
- 补修后的行为（主控固定要求「无消费者后不继续启动新的解释生成」）：
  消费者断开后，工作者晚领到号会**先收尾生成权、并跳过准备与生成**——
  `fake_prepare` 按设计不再被调用，`finished` 永远不会置位。
- 探针真正要验收的两个终态（`state_after_worker_finished`、
  `retry_kind`）无法由该同步点观察到；同场景等价验收由
  `tests/unit/test_agent_ask_stability.py::
  test_s1_disconnect_before_identity_late_claim_released`（矩阵 1）承担：
  同一时序（延迟登记 → 回执后关闭 → 放行），断言
  `answer_state=pending`（修前主控实测 generating）且重试
  `kind=proceed`（修前主控实测 incomplete）。

如主控希望探针继续作为回归使用，建议把同步信号从「进入准备」换成
「claim 终态出现」（轮询 answer_state 至 pending/generating 出现），
这超出执行方权限（不修改主控探针），仅作建议记录。
