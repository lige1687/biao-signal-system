# B1 正式运行台账
## 2026-09-16 10:41:35 freeze_build.py（冻结协议+代码原字节+环境）
protocol frozen: /Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/protocol-v1.0.0.json
sha256: 636171734bf363b30a0821b19256c5dc16507600b97d1a98a61766802b249477
validate_b1_protocol: OK
exit=0
## 2026-09-16 10:41:55 正式运行 run-01（预算内唯一正式计算第1次）
cmd: python3 scripts/run_b1_dual_ma_description.py --protocol docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/protocol-v1.0.0.json --out docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/run-01
输入/身份错误: 输入包声明 adjustment_anchor='unknown（精确复权锚点未证）' 与固定声明 'unknown' 不符
exit=3
## 2026-09-16 10:44:12 可定位工程错误记录：FIXED_DATA_DECLARATIONS.adjustment_anchor 与固定输入包实际声明不符（'unknown' vs 'unknown（精确复权锚点未证）'）。run-01 在输入校验阶段 exit 3，未计算状态/目标、无输出目录。修正：常量对齐+协议升 v1.0.1（v1.0.0原字节保留不受理）。
## 2026-09-16 10:44:12 freeze_build.py 1.0.1（排他新协议）
protocol frozen: /Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/protocol-v1.0.1.json
sha256: 00a16465e5232d3760cedbe9bccb5332b05e4f777f1732e8911ee586974c3af2
validate_b1_protocol: OK
exit=0
## 2026-09-16 10:44:24 正式运行 run-02（修正后新编号，预算第2次即末次）
cmd: python3 scripts/run_b1_dual_ma_description.py --protocol docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/protocol-v1.0.1.json --out docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/run-02
EXIT 0: B1 历史描述完成（post_hoc_historical_description；不自动触发任何后续）
exit=0
## 2026-09-16 10:45:26 独立重汇总核验（恢复核验1次，不重算状态/目标）
FAIL: sparse true: 独立(23,11,11,1) != {'n': 26, 'up': 14, 'down': 12, 'zero': 0}
FAIL: sparse false: 独立(43,21,21,1) != {'n': 40, 'up': 18, 'down': 22, 'zero': 0}
exit=1
## 2026-09-16 10:46:38 核验工具纠错记录：reaggregate.py 锚点定位混用含表头枚举索引与 DictReader 列表索引（off-by-one），首轮 FAIL 系工具缺陷非运行数据；修正后重核（工具纠错，非新增真实计算）
独立重汇总一致（容差1e-12）：主比较 n=1516 (真590/假926)；稀疏两组计数一致；未重算状态/目标
真组 mean=0.010424 median=0.006946 up=0.5475
假组 mean=0.003408 median=-0.003828 up=0.4762
exit=0
