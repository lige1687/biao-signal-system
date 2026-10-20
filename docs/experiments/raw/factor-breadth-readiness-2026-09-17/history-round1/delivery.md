# delivery — factor-breadth-readiness-2026-09-17

> **执行者声明横幅**：本目录由 ZCode 委派任务 abf62778-7076-4ea5-88fb-2750016ba03a
> round 1 产出；执行通道 GLM-5.3-Flash（按任务书 v1.0.1 修订说明，Ark 入口未安装，
> 用户指定改走 ZCode）。执行者自报状态为 done，**一切以主控独立复核为准**；
> 本轮无自行验收授权。开工身份：分支 `codex/factor-unit-research-20260915`、
> HEAD `2b05787f7469…`、四个冻结规范 SHA-256 全部匹配；除本目录外零写入、
> 零联网、零安装、零真实信号/状态/目标/收益计算、零 git 写操作。

## 一句话结论（大白话）

「宽度」就是一个指数成分股里，价格站在自己均线上方的股票占比。本轮把沪深300宽度的
**定义、代码、历史数据**三样逐一对上了：定义和代码对得上（比例版=规范实现，百分数版=
冻结研究引擎，两者只差一个 ×100）；历史名单是按"当时的名单"一天天查出来的（不是拿
今天的名单倒推），这条最值钱；价格却是"现在还上市的股票的前复权价"，已退市的老成员
没有价格，而且协议里写的"后复权"和实际不符——这是本轮最大的一个不一致，需要主控裁定。
结论：这个序列**做历史描述研究基本够格（B 档），做"当时就能知道"的预测研究还没资格**
（没有任何证据说明历史上每天的数据当时几点能拿到）。本轮不算任何收益、不提任何新阈值。

## 逐目标状态与证据

### G1 定义与实际实现逐对象对应 — done

- 交付 `definition-implementation-map.csv`：4 张登记卡（common×2 + legacy×2，均
  @1.0.0，从 `docs/research/definitions.v1.json` 容器 1.2.0 解析）逐对象列公式、单位、
  代码入口（文件:行号）、均线含当日与预热、缺报价处理、分子/分母、共同合格集 E200、
  空集合/覆盖门槛处理、严格高于、逐日名单输入、历史序列与消费者、设计与实现差异；
  另附 3 条**非卡补充线**（timing 展示缓存、全A展示 JSON、冻结 all_a 序列）防同名误用。
- 关键对应关系（独立代码走读证据，非自填 verified）：
  - common 卡 → `src/lei_signal/research/definitions.py:395`（经 `:498 calculate`
    参数绑定断言 `:518-526`）；`scripts/verify_research_definitions.py:207-232` 用
    1e-10 容差与冻结引擎逐值比较。
  - legacy_percent 卡 → 冻结引擎
    `docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/research_engine.py:16`
    （同构 E200 共同分母，输出 ×100）。
  - `src/lei_signal/market_context/breadth.py`（registry `breadth_legacy`，哈希实测
    匹配登记表）是**另一条线**：各窗口独立分母、停牌 5 日顺延、覆盖不足仍返回数值
    ——不是任何一张卡的实现，消费者未迁移（与登记表 `consumers.migration` 声明一致）。
- 差异均有准确位置：单位（百分数÷100）、价格底表口径（见 G2）、
  `configs/rules.v1.yaml` 无宽度条目、`docs/trading-spec-v1.md` 正文无宽度概念
  （宽度属市场环境研究层，不动技术判定）。

### G2 历史输入来源与各用途资格 — done

- 交付 `input-qualification.md` + `sources-manifest.json`：全部输入绑实测哈希
  （2026-09-17 复核，指纹清单 12 项 + registry 钉定项全部匹配；registry 未钉的
  `data_quality.json` 记录实测值 `f9b3b788…`）。
- 逐项说明：成员生效（baostock 历史日期逐查 + 20 日探测 + 二分，30 个生效日，
  682 只历史代码、843,900 行整 300×2,813、无重复无空值）；价格（新浪 qfq 当前存续
  回填底表，`backfill_breadth_full.py:88`；协议"后复权"声明与实现不符——
  `prepare_data.py` 的 baostock 后复权函数是死代码）；日历（510300 ETF 交易日）；
  缺失（显式 NaN、不前填、缺原因码）；时间证据（观测=日收盘；抓取=2026-09-09；
  **当时可得=无证据，保持未知**，verify manifest 原文 `historical_available_at:
  unknown`）。
- 三类用途分别裁定（qualification §8）：仅展示=受限（序列止于 2026-06-30）；
  事后历史描述=支持（B 档带缺口清单，2,378/2,813 有效日，覆盖率最低 0.64）；
  当时可知预测=未核验。未知项逐条保持未知（baostock 口径、停牌呈现、到达时间、
  timing 文件生产者）。

### G3 下一步请求可决策且不自行执行 — done

- 交付 `next-study-request.md`：唯一候选对象（csi300 b50/b200 common，比例单位，
  数据源二选一由主控定）、候选窗口 2015-02-09→2026-06-30（不预设裁剪）、最小研究=
  独立宽度历史描述（不强制与双均线组合）、6 项材料缺口逐条列出（价格口径裁定、
  续数到今天、到达时间证据、分档批准、公告日补强、timing 同名文件改名建议）。
- 全文无新阈值（0.2/0.8 只以"须主控批准"的待裁项出现）、无真实信号/收益计算、
  草案未获批不执行。

### G4 交付范围和实际调用可追溯 — done（含 1 项流程偏差披露）

- `run-log.md`：命令清单、10/12 数据文件深查账、结构脚本 **3 次（超预算 1 次，
  从严计数含 1 次路径错误失败）如实披露**并停止后续执行、格式检查/hygiene/零计算
  账目、未核项清单。
- 新增产物仅位于 `docs/experiments/raw/factor-breadth-readiness-2026-09-17/`
  （开工前确认不存在；6 个文件，见 manifest `deliverables`）；现存文件只读——
  src/、configs/、web/、tests/、definitions.v1.json、registry.json、INDEX.md、
  旧 raw、他人未提交改动均未触碰；git 零写操作。
- hygiene 结果见下节。
- **登记建议（由主控统一执行，本轮未写 registry/INDEX）**：结案后可在
  registry.json 登记 `factor-breadth-readiness-2026-09-17`，category 建议
  `research_prep`（按 registry 实际枚举为准），verdict 建议 `mixed`
  （历史描述支持、预测用途未核验），oneLiner 可取本文件一句话结论。

## Hygiene 与格式检查（已执行）

- `python3 scripts/check_repo_hygiene.py` → `✓ 归置自检通过：根层四层均在白名单内，
  关键配置均已入库。`（exit 0，执行 1 次；既有外部问题无需处理，未发现）。
- 文档格式检查 1 批：sources-manifest.json 解析通过（15 顶键、16 输入、10 代码条目）、
  CSV 解析通过（7 行、4 卡行、版本全 1.0.0）；md 断言脚本自身匹配串写错一次
  （next-study-request 标题为「一句话（大白话）」，文件完好），已如实记入 run-log。

## 未核项（保持未知，不在本轮补）

1. baostock 历史名单查询的当时视角与事后修订政策（无供应商认证）。
2. 停牌日在 qfq 价格底表中的呈现（缺行 vs 带值）。
3. 历史逐日数据到达时间（无任何时间戳证据）。
4. `~/.lei_signal_lab/cache/timing/breadth_csi300.parquet` 的生产脚本（仓库 HEAD 无）。
5. csi300 名单变更的公告日（未保存；`prepared/sources/` 33 份公告原件属创业板链）。
6. 冻结序列与底表的一致性深度复核（`verify_research_definitions.py` 可复核其中
   2 个真实交易日，但运行它会计算真实宽度值，超出本轮"零真实计算"边界，未执行）。

## 移交主控的三件事

1. **裁定价格口径不一致**（协议/profile 写后复权，实现是 qfq 存续回填）：
   接受+标注，或补数据重算。
2. **批准/修改下一步研究请求**（`next-study-request.md`），特别是是否续数到今天。
3. **处理 timing 同名文件误用风险**（改名或标注来源，属生产小改，须另行授权）。
