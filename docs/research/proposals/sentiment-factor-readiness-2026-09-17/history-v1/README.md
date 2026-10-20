# 情绪因子就绪核对与首个单位实验候选 · 提案 README

【来源：Ark 委派阶段 S1 执行产物，**待主控复核的提案**】
日期：2026-09-17。分支 `codex/factor-unit-research-20260915`，参考 HEAD
`29b150f58b3f6d8c6e558a748c12dac3384af173`（本轮未切换、未提交、未暂存）。
本目录所有内容不代表主控认可或新增授权；不登记 registry / INDEX / OKR；
不宣称结案或已采纳。

## 一句话结论（大白话）

我们把仓库里和"投资者情绪"有关的既有家底逐个核了一遍：目前**没有一个**
情绪对象登记进正式定义账本，真正"数据带逐行可得时间、可以直接追溯"的
只有两套美国周度调查（NAAIM 机构仓位、AAII 散户调查），其中 NAAIM 的
本地数据最完整。按"定义清晰、数据可追溯、问题适配"三条标准，本轮只推荐
**一个**候选进入下一步待批实验：用 NAAIM 周度读数的极端状态，对美股宽基
指数后续表现做**纯历史描述**（不是择时、不是买卖点、不是硬过滤）。A 股
散户资金流和"冰点机会"复合状态这次都不推荐直接做单因子实验，原因见
candidate-review.md。所有旧报告的收益类结论本轮**只转引、未复验**。

## 本轮做了什么（成果）

1. **核对既有情绪对象**（object-evidence.csv，4 个对象）：逐个给出公式、
   单位、频率、适用市场、真实来源、历史区间、三个时刻（观察时点 / 可得
   时点 / 本地取得时点，术语对齐 definition-standard.md §5 的 `time`
   字段口径）、回填情况、登记状态、历史使用、代码位置、数据指纹与证据
   限制。叙事仪表盘与可计算序列分列；AAII / NAAIM / VIX / 散户热度
   均按不同测量处理，未合并。
2. **验证了 2026-09-15 情绪档案（sentiment-dossier）的关键声明**：
   - 属实：情绪族在 `definitions.v1.json`（81 对象）中**零登记**；
     loader 强制 `survey_week/available_at/source/license_status` 列、
     缺列报错（sentiment.py:51-53）；`public_delayed` 永不合路
     （`_is_current_eligible_at`，"Public-delayed data is never
     current-eligible"）；分位分类默认 ≥52 期预热（sentiment.py:255）；
     散户资金流 z 口径 20 日/120 日/阈值 1.5（sentiment_signals.py:30-33）；
     三票多数需 ≥2 票（market_mood.py:105）且自述"只标注不判定"。
   - **需要更新**：dossier §4/§6 称"本地 CSV 缺 survey_week/available_at
     列"——该说法针对的文件名（aaii_clean/naaim_clean）在当前树中不存在；
     现行数据 `data/sentiment/naaim.csv`、`data/sentiment/aaii.csv`
     **已带完整的可得时点列结构**（本轮逐列核对）。dossier §7 提议的
     "调查周→发布时点映射表"在结构上**已经落地**（回填行用固定星期四
     +延迟天数的建模时刻，自动行标 `auto:`）。剩余未闭环的是：回填行的
     建模发布时刻**未经逐行核证**，且 git 未跟踪、经
     `scripts/sync/export_sync.py` 从 `$LEI_SENTIMENT_ROOT` 同步。
3. **按标准选出唯一候选**（candidate-review.md）：NAAIM 周度敞口读数。
   选择依据是定义与数据纪律，**不是**旧收益排名；旧政策层证据（美股
   情绪择时七轮全输）按其原范围保留引用。
4. **写出待批最小实验方案**（experiment-proposal.md）：指数状态历史描述
   研究，含载体备选、时间对齐、重叠处理、能/不能解释什么的边界，以及
   可交执行者的下一轮 prompt 草案。**本提案不授权运行**；真实统计、
   联网、新数据源均需后续许可。

## 主要缺口（仍未解决）

- NAAIM 本地只有 127 周（2023-11-20→2026-09-07），几乎全是单边上涨市段；
  52 期预热后可判状态约 75 周，极端冷/热带样本必然只有个位数。
- AAII 本地 84 行、30 处超 10 天缺口，覆盖太稀，本轮不达标。
- A 股散户资金流无逐行发布时间，"当时是否已知"无法判定；板块覆盖缺口
  大（四输入审计：半导体 0 个完整 140 日窗口）。
- "冰点机会"是复合状态（含价格与宽度成分），按任务与档案纪律不能当作
  单一情绪因子；其定义权威在 `configs/sentiment_evidence.json`，与
  定义账本的映射关系需主控确认（方向提案 C3 同款待决）。
- 全部旧收益/胜率类数字（含冰点 92% 同向、VIX 归档各证伪项）本轮
  **未复验**，逐条复核深度见 sources-and-checks.json。

## 本目录文件

- `object-evidence.csv` — 4 个既有对象的事实核对表（每列含义见表头注释行）。
- `candidate-review.md` — 候选比较与唯一推荐，含不适合用途与选择偏差。
- `experiment-proposal.md` — 待批准的最小单因子历史描述方案 + 下一轮
  执行者 prompt 草案。
- `sources-and-checks.json` — 输入指纹、核验深度、命令与预算台账、
  漂移检查、隔离声明。

## 边界声明

- 服务独立环境研究层；情绪不进入生产硬过滤（AGENTS 红线，
  trading-spec-v1.md 全文无"情绪"条目，本轮已核）。
- 本轮零联网、零安装、零真实因子/目标重算、零回测、零收益统计；
  仅做 rg、只读、哈希、CSV/JSON 结构检查。
- ZCode 独占区（`src/lei_signal/research/breadth_description*.py`、
  `tests/unit/test_breadth_description.py`、
  `docs/experiments/raw/breadth-b200-first-description-2026-09-17/`）
  未读取、未写入。
- 关键输入在核验前后两次哈希比对**零漂移**（见 sources-and-checks.json）。
