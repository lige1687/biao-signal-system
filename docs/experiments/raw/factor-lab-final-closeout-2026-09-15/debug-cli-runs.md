# 终版收尾：临时目录完整 CLI 调试运行清单（如实逐次记录）

本轮（factor-lab-final-closeout-2026-09-15）在 /tmp 的完整 CLI 执行：

| # | 协议 | 结果 | 说明 |
|---|---|---|---|
| 1 | protocol-1-numerical (v1.2.0) | 退出1 | `_dump_json` 返回元组后残留旧调用点（sidecar 写盘 TypeError）→ 修复 |
| 2 | 3 案例批量 | 各退出3 | 修复后代码哈希与已冻结协议不符（机制正确），重冻结 v1.2.0 |
| 3 | 3 案例批量 | 全部退出0 | 重冻结后全过（62 项期望） |

pytest 临时目录的集成测试执行单列（test_formal_protocol_exits_zero 等），
不冒称正式证据。正式批次见 `runs/final-*-run-01`（各 1 次，全部退出 0）。
上一轮（concentrated-repair）的 /tmp 调试约 4 批×3 案例及若干单案执行，
详见该轮报告披露；v1.1.0 交付时 runner.py 原字节未单独存档且未被 git 跟踪，
源码不可从哈希恢复。
