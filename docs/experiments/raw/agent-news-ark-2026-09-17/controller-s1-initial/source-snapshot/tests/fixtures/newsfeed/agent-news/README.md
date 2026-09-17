# agent-news 夹具（2026-09-17 S1）

出处逐文件说明：

- `fed-press-monetary-sample.xml`：**手工构造**，结构按美联储官方
  `https://www.federalreserve.gov/feeds/press_monetary.xml` 的 RSS 2.0 形态
  （item = title/link/description/pubDate/guid）。其中 2026-09-16 14:00 EDT
  加息 0.25 个百分点、目标区间 3.75%–4% 的事实，来自上一轮只读核对
  `docs/experiments/raw/agent-news-priorities-2026-09-17/read-only-check.json`
  的 `official_source` 段。S1 受控采集的真实响应存于
  `docs/experiments/raw/agent-news-ark-2026-09-17/fed-press-monetary-live-2026-09-17.xml`：
  **实测真实 feed 的 pubDate 用 GMT 命名时区 + CDATA 包裹、响应带 UTF-8 BOM
  且无 charset 头**；本夹具故意使用 `EDT` 命名时区写法，专测解析器的
  美东命名时区（zoneinfo 夏令/冬令）路径，GMT/数字偏移路径另有测试覆盖。
- `item-expectation-20260904.json`：真实库条目 124 的字段快照（来源
  同上 read-only-check.json 的 `local_expectation_item`），新浪源、URL 为空、
  8 分/利空是模型标签——它是**概率报道（预期）**，不是正式决议。
- `item-fed-statement-20260916.json`：模拟 `sources/fed.py` 采集后的入库行
  形态（source=fed、带原文 URL、带时区发布时间、**未评分**）。用于验证
  正式声明无 AI 评分仍可展示。
