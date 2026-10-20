# Task 0 身份冻结与接口核对（2026-09-17）

执行者：ZCode（GLM-5.3-Flash），受主控 Astra 委派（job_id=da7dabfc-ab2c-4cc1-9686-0c7c0a538a9b, round=1）。

## 1. 环境与工作区

- 仓库：`/Users/yongbiaoli/Desktop/lei-signal-lab`
- HEAD：`29b150f58b3f6d8c6e558a748c12dac3384af173`（与任务书一致 ✓）
- 分支：`codex/factor-unit-research-20260915`（与任务书一致 ✓）
- 工作区存在他人脏改动（factor_evidence、web/、docs 等），**全部保留**，未回滚。
- Python 3.11.7 / pandas 2.3.3 / numpy 2.1.1；未联网、未装新依赖。

## 2. 哈希核对（全部一致 ✓）

五份规范、四份输入、两份旧数学核（momentum_prototype `5425e4f5…`、trading_calendar
`4651fa7d…`）逐字节 SHA-256 与任务书表格一致。核对命令输出见当日会话日志；
冻结副本落在 `freeze/v1.0.0/`（`freeze-manifest.json` 记录源路径与哈希，副本与
原字节逐一比对一致）。

## 3. 冻结内容

- `freeze/v1.0.0/inputs/`：breadth_csi300.parquet、observations.csv、prices.csv、
  calendar.json（只读复制；复制不提升用途资格）。
- `freeze/v1.0.0/specs/`：五份规范原字节。
- `freeze/v1.0.0/cards/`：用 `definitions.load_registry` + `definitions.resolve`
  解析的两张定义卡只读快照（legacy_percent@1.0.0、common@1.0.0）。
- `freeze/v1.0.0/code-legacy/`：definitions.py、trading_calendar.py、
  momentum_prototype.py、factor_runtime.py 原字节。
- 新增模块与 CLI 的原字节在 Task 2 协议冻结时补入 `freeze/v1.0.0/code/`。

## 4. 输入数据实际范围（纯检查，未算任何相关系数）

| 输入 | 实际范围 | 行数 | 备注 |
|---|---|---|---|
| prices.csv | 2019-09-02 → 2026-02-03 | 1558 | 覆盖日历核验窗两端 |
| observations.csv | 2019-10-08 → 2025-12-31 | 1516 | 与评价轴交易日数一致；末行 x=2026-02-03 未越出价格覆盖 |
| calendar.json | 2019-09-01 → 2026-06-30 | 2495 日（1652 交易日） | months_requested 82 个月，months_failed 空 |
| breadth_csi300.parquet | 2014-12-01 → 2026-06-30 | 2818 | 列：pool_total/quoted/eligible/missing_quote/insufficient_history/missing/coverage/valid/b50/b200；只消费 b200 与质量列 |

评价轴（日历推导 2019-10-08→2025-12-31）= 1516 个交易日，与观察表行数一致。

## 5. 复用方法与导入安全

- `momentum_prototype.rank_diagnostic(frame)`：入参含 `momentum`/`target` 两列的
  DataFrame，返回 `{n, value, reason}`；并列平均名次后 Pearson。顶层只导入
  definitions 与 factor_runtime，无联网/写盘。
- `trading_calendar.TradingCalendar(payload)`：`trading_days(start,end)` 给出已确认
  交易日；`coverage(start,end).complete` 核月份覆盖完整性。纯 JSON 构造，无 I/O。
- `definitions.resolve(registry, reference)`：按精确 `id@version` 解析卡；本次
  用途 `restricted_post_hoc_description` 不是卡内登记用途，故 resolve 不传
  purpose，卡内 `uses=["description","diagnostic"]` 如实记录，受限用途由主控
  裁定授予，不冒称卡内许可。
- **不调用** `definitions.calculate` / `definitions.breadth` 重建宽度。

## 6. 单位与目标端点确认

- 宽度实际输入为百分数（0–100），消费时按卡 `transforms: 乘100` 的逆转换
  `b200_fraction = b200 / 100`；对照对象 common@1.0.0 单位为比例。
- 目标端点沿用 B1：e = t 后第 1 个交易日收盘，x = t 后第 22 个交易日收盘，
  `main = close(x)/close(e) - 1`，21 段相邻价格区间（B1 报告 §目标口径与
  使用手册一致）。
- 数据质量固定 `restricted`：available_at=null、
  historical_availability_verified=false、source_price_basis=unverified_per_column。
  不存在自动升级。

## 7. 禁止项重申

不把旧合成 runner 的 synthetic 标记伪造为真；不绕过用途拒绝；本阶段未计算
任何相关系数（真实统计在 Task 3 唯一正式运行中产生）。
