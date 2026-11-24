# Bar 完成度：final 证据口径与接线设计稿（W2-S2，2026-09-20）

> **本文档为设计稿，实现需 W2-S3 独立授权。** 本单零代码改动。
>
> 上游：`docs/ops/bar-completeness-contract.md` v1.0（W2-S1 冻结：三态定义、
> 两条调用契约、A股判定纯函数原型 `src/lei_signal/data/bar_completeness.py`）。
> 事实依据：GPT 第 6/19/26 轮（共识文档
> `docs/archive/handoffs-plans/2026-09-19-arch-review-gpt6pro-consensus.md`）。

## 一句话结论（大白话）

「现在过了收盘时间」只能说明**交易所已经收盘**，不能说明**你手里这份 K 线数据
是收盘之后才拿的**。如果这份数据是 14:59 拿的、之后没再更新，那它永远停在
收盘前，哪怕 15:01 再看它也不是完整的一天的 K 线。本设计稿定的规矩就一条：
**判断一根 K 线走没走完，看的是「这份数据是什么时候拿到的」加上「K 线标的是
哪一天」，不是看「现在几点」**。拿到数据的时间早于那天收盘，就一律不许当作
收盘数据用于正式信号；说不清楚什么时候拿的，按「说不清」处理，也不许用。

---

## 0. 核心反例与回答（GPT 第 26 轮，本稿的灵魂）

**反例**：「交易时段结束 ≠ 这份数据完整」。一份 14:59 获取后再未更新的帧，
15:01 再送入分类器，不能仅因当前时刻越过收盘就升格 final。交易日历与时钟
最多证明「时段已结束」，还要回答「参与计算的这一份数据凭什么被认为覆盖了
该时段」。

**回答**：final 的判定输入里**没有「当前时刻」这个变量**——只有「这份数据的
观测时刻」（这份数据是什么时候从数据源拿到/写入的）。「现在几点」只出现在
W2-S1 原型 `classify_a_share_bar(bar_date, observed_at, ...)` 的形参名里，本
设计稿冻结其语义为：**`observed_at` 必须取「该帧的获取/写入时刻」，禁止取
「分类执行时刻」**。14:59 获取的帧，observed_at=14:59 < 15:00 收盘，无论
何时分类都判 **partial**，永不升格 final。同理，编排层的 `as_of="close"`
只是「本次扫描按收盘语义跑」的声明标签，**不能反证输入数据已完成**——
声明想跑收盘语义，恰恰是必须先过完成度守卫的理由（契约文档 §2）。

---

## 1. final 的证据口径（G1）

### 1.1 证据分类与逐一核对结果

对 `src/lei_signal/data/providers.py` 全部在役日线源逐一核对「源响应是否含
当日完整日线的显式信号」：

| 源 | 盘中是否返回当日 bar | 响应中有无「已完成」显式声明 | 核对依据 |
|---|---|---|---|
| tencent（A股主源） | 是，形成中 bar | **无**。qfqday/day 数组只有 OHLCV，无完成标志 | `_parse_payload` |
| eastmoney | 是（THS 注释互证：东财含当日形成中 bar+量） | **无**。klines 纯数值行 | docstring §EastmoneySectorProvider + `_parse_payload` |
| yahoo / yahoo_v8 | 是（日线端点盘中返回当日形成中 bar，`services.py` 模块头注释明确） | **无**。timestamp+quote 数组 | `YahooV8PriceProvider.fetch` |
| tencent_global | 是（海外指数同接口语义） | **无** | 同 tencent |
| ths_board | 年文件收盘后才写当日；盘中由 `today.js` **合成形成中 bar 追加** | **无显式标志，但合成路径有内部标记**：`_augment_today` 追加的 bar 在函数内可识别，**追加后标记丢失**（返回的 DataFrame 不区分年文件 bar 与合成 bar） | `_augment_today` |
| sohu_sector | **否**：收盘后才出当日 K（docstring 明确「盘中无当日形成中 bar」） | **隐式**：返回了日期 D 的 bar ⇒ 按源自身语义 D 已收盘。但这是行为推断，非显式声明，且搜狐历史接口有已知 code 截断 bug，不作为 final 的独立证明 | docstring「局限」节 |
| sina（已退出默认链） | 是 | 无 | — |

**结论**：任何源都**没有**可依赖的显式完成声明。因此 final 的证据口径采用
**观测时间戳为主的组合**：

> **final ⇔ 最后一根 bar 的日期 D 是交易日（按注入日历） ∧ 该帧的观测时刻
> （换算到标的交易所时区）≥ D 的收盘时刻 ∧ 该帧无「形成中 bar 合成」标记。**

三个证据分量：

1. **观测时间戳（主证据）**：这份数据从源获取（或写入缓存）的时刻。
   - 在线抓取：`AnalysisEntry.fetched_at`（`services.py::_run` 在调用
     analyze 前取 `datetime.now(UTC)`，即抓取时刻，语义正确）；
   - 缓存：`.meta.json` 的 `fetched_at`（`cache.py::write` 在**写入时**记录，
     不是读取时）；
   - 叠加链路（海外指数）：`IntradayOverlayProvider` 在 provider 名后缀
     `+<realtime_source>` 标记「最后一根 bar 是实时合成」——**这是现成的
     「形成中」正向证据**（见 §1.3）。
2. **交易日历 + 收盘时刻**（W2-S1 已冻结：注入式 `TradingCalendar` +
   注入式 `close_time`，缺省 15:00 / 美股 16:00 ET，均为参数非硬编码）。
3. **来源契约组合**（辅助）：`cache.py` 的 trusted-provider 门（fixture/
   synthetic/upload/parquet_cache/无 meta ⇒ 未命中）保证观测时间戳来自真实
   行情源写入；ths 的 `today.js` 合成路径在 W2-S3 接线时应把「本帧含合成
   当日 bar」透出为旁侧标记（设计要求，属 W2-S3 改动点）。

### 1.1.1 三种时间事实（分开定义，GPT 第 27 轮修订一）

判定 final 时必须把三个容易被混为一谈的「时间」拆开：

| 时间事实 | 定义 | 承担什么 / 不承担什么 |
|---|---|---|
| **原始观测时间** | 这份数据从行情源**取得**的时刻（网络响应返回的那一次）。它决定「这份数据看到的是几点钟的世界」，是 final/partial 判定的唯一主证据 | 只能由「取得动作」产生；缓存读取、缓存重写、文件复制都**不产生**新的原始观测时间 |
| **缓存写入时间** | 这份数据**持久化到磁盘**的时刻（`.meta.json::fetched_at`，`cache.py::write` 第 79 行取 now） | 只承担存储事实（这份文件是什么时候写的）。仅当写入由「一次真实在线抓取直接落盘」触发时，可作为原始观测时间的近似（见 1.1.2 的误差方向分析） |
| **完成依据** | 凭什么认定这份数据覆盖了目标交易时段：交易日历判定 D 是交易日 + 观测时刻（交易所时区）≥ D 收盘 + 帧无「形成中 bar 合成」标记 | 这是**结论**，不是时间戳；由前两项证据 + 日历推出，不能反过来用「现在已收盘」充当 |

### 1.1.2 fetched_at 的实际赋值位置（逐一核实，字段名≠语义）

**AnalysisEntry.fetched_at（内存条目）**：`api/services.py::_run` 第 183 行，
`fetched_at = datetime.now(UTC)` 取在**调用 analyze 之前**，即「本次抓取轮的启动
时刻」。证据链：

- 内存缓存命中时**不刷新**：`_get_locked`（services.py:140-145）在
  `_is_fresh` 通过后原样返回旧 entry，fetched_at 保持该 entry 产生时的值
  ——读动作不产生新观测时间，语义正确；
- 但 **analyze 内部落盘缓存兜底时会错位**：`pipeline.py::analyze` 第
  180-215 行，网络失败→读 Parquet 缓存回放，此时 bars 是旧缓存内容，
  而 entry.fetched_at 是「现在」——**数据是旧的、时间戳是新的**。
  该路径可检测：`result.cache_fallback_used=True` 且
  `price_data.report.provider=="parquet_cache"`（pipeline.py:204）。
  **结论：AnalysisEntry.fetched_at 只在 `cache_fallback_used=False`
  时可承担原始观测时间；兜底路径必须改用缓存 meta 的写入时间
  （W2-S3 接线改动点）**。

**.meta.json::fetched_at（磁盘缓存）**：`data/cache.py::write` 第 79 行，
在**写入时**取 now，不是读取时——读取（`read`/`read_meta`）从不改写它。
它本身只证明「写入时刻」；能否当原始观测时间的**近似**，取决于这次写入
是不是「一次真实在线抓取直接落盘」：

- **在线抓取后落盘**（pipeline.py:229-237，仅在未走缓存兜底时执行）：
  帧来自本次 fetch，fetched_at 是同一轮 analyze 内 fetch 完成后的落盘时刻。
  误差方向 = **偏晚**（真实抓取时刻 ≤ 写入时刻），量级为一次网络请求返回到
  落盘之间的耗时（同一次 `_run` 内，通常秒级以内）。偏晚方向理论上存在
  「14:59:58 抓、15:00:01 落盘」被记成收盘后观测的边缘误差，W2-S3 若要
  消除，应在 provider.fetch 返回处即时记录（列入 S3 改动点，成本一行）；
  本稿先冻结「落盘时刻=观测时间的保守近似，误差偏晚且秒级」。
- **任何复制/合并/重写写入**：fetched_at 被刷新为重写时刻，原始观测时间
  **丢失且不可恢复**——此时 meta.fetched_at 退化为纯存储事实，不得再当
  观测时间用（反例见 1.1.3 第 2 行）。

### 1.1.3 写入时间升级反例逐一回答（GPT 第 27 轮指定）

| 反例 | 实际代码行为（已核） | 回答 / 处置 |
|---|---|---|
| ① 14:59 取帧、15:01 落盘 | 在线路径：帧是 15:01 这次 fetch 拿的（不是 14:59 的旧帧），meta.fetched_at=15:01 是真观测近似 ⇒ 若源 15:01 返回的当日 bar 已是收盘后最终值，判 final **合法**。真正危险的是「14:59 的帧被 15:01 **重写**」——见② | 在线抓取落盘的时间戳可用（近似偏晚秒级）；「取帧时刻」与「落盘时刻」分属两轮 fetch 时不得混用 |
| ② partial 帧收盘后被复制/合并/重写 | **已核实的真实路径**：海外指数链 `CacheFirstProvider.fetch`（realtime.py:532-537）缓存命中直接返回旧帧 → `IntradayOverlayProvider.fetch`（realtime.py:426-450）叠加实时 bar 后，`pipeline.py:229-237` 把合并帧**重新写缓存**，meta.fetched_at 刷成 now。且叠加后 provider 名为 `parquet_cache+tencent_rt`，**不落在 UNTRUSTED_PROVIDERS 精确匹配里**，下次读取仍算可信源 | 该路径原始观测时间不可恢复 ⇒ **不许用刷新后的 fetched_at 判 final**。处置：带 `+<rt>` 后缀=有形成中 bar 正向证据 ⇒ 直接 partial（§1.5）；无后缀的重写帧 ⇒ unknown。规则冻结为：**meta.fetched_at 只在「写入者是一次在线抓取」时是观测近似；被合并/重写的文件，观测时间按丢失处理** |
| ③ 收盘后新请求返回旧缓存内容 | 内存：A股 `session.is_cache_fresh`（session.py:112-113）要求 `fetched_at ≥ last_close` 才算收盘后新鲜，14:59 条目收盘后会过期重抓——A股内存路径自洽；但**海外指数走扁平 TTL**（services.py:106-107，只看 age），盘中观察产生的条目收盘后仍「新鲜」可被消费（§2.2 反例）。磁盘：`CacheFirstProvider._from_cache` 只看 age（30min），同样可能收盘后返回盘中写的旧帧 | 内存侧由 §2.2 用途隔离锁死；磁盘侧由本表②规则处置（旧缓存帧观测时间=旧 meta.fetched_at，不被读取动作刷新，按真实旧时刻判 partial/unknown） |
| ④ 合成标记转换丢失 | **已核实**：ths `_augment_today`（providers.py:1387-1417）追加的合成 bar 在返回的 DataFrame 里与年文件 bar 无区分，标记**函数返回即丢失**；随后 pipeline 落盘，合成 bar 永久混入缓存。叠加链路的 `+<rt>` 后缀活在 `report.provider` 字符串里，一旦中间层重写 report（如 `analyze` 兜底构造 `provider="parquet_cache"`，pipeline.py:204）同样丢失。**「未见标记」≠「确认无合成」** | 各源处置：ths_board ⇒ W2-S3 必须在 `_augment_today` 追加处透出旁侧标记（§1.1-3 已列）；叠加链 ⇒ 判定输入必须读 `report.provider` 的后缀而不是依赖中间传递；兜底路径（provider 重置为 parquet_cache）⇒ 合成标记已丢 ⇒ **unknown**，不落 partial 也不落 final |

### 1.1.4 逐源准入表（8 个在役源，准入=「系统按约定接受」非「供应商声明」）

「准入依据」指本仓库源码/文档中可核验的接口行为约定；无依据者标 unknown。
**准入是本系统的契约选择，不宣称供应商承诺完成。**

| 源 | 接口 | 交易时段内发布行为（依据） | 准入结论 |
|---|---|---|---|
| tencent | `web.ifzq.gtimg.cn` qfqday/day | 盘中含当日形成中 bar，无完成标志（`_parse_payload`） | 准入依据：观测时间戳口径（§1.1-1）。盘中帧必 partial，收盘后抓取帧准 final |
| eastmoney | kline/get | 盘中含当日形成中 bar（docstring），无完成标志 | 同上 |
| yahoo_v8 | v8 chart API | 盘中含当日形成中 bar（services.py 模块头注释），无完成标志 | 同上；日期语义见 §1.5 |
| yahoo（yfinance） | query2 端点 | 同 Yahoo 语义，长期 IP 限流 | 同上；且该源常不可用，失败走链路降级，不单独准入 |
| tencent_global | 同 tencent 接口（海外指数） | 同 tencent 语义 | 准入依据同 tencent；配合叠加链 `+rt` 后缀作 partial 证据 |
| ths_board | 年文件 + today.js | 年文件收盘后才写当日；盘中合成 bar 追加且**标记丢失**（`_augment_today`，已核） | **有条件准入**：仅在 W2-S3 透出合成旁侧标记后，无标记帧才可按观测时间判；接线前一律 unknown |
| eastmoney_sector | kline/get secid=90.BK | 盘中含当日形成中 bar + 量（docstring），无完成标志 | 同 tencent 口径 |
| sohu_sector | hisHq | 收盘后才出当日 K（docstring「盘中无当日形成中 bar」）——**隐式**：返回了 D ⇒ 源自身语义 D 已收盘 | **行为推断非显式声明**，且该接口有已知 code 截断 bug ⇒ 降级为准入依据=观测时间戳（同其他源），不用「返回即完成」当独立证明 |

预期拒绝范围（「零误伤」不覆盖这些）：ths_board 在合成标记透出接线**之前**的
全部收盘判定（unknown）；无 meta 旧缓存 / provider 不可信的全部帧
（`cache.py::read` 已判未命中，落 unknown）；`cache_fallback_used=True`
且无法取得原写入时间的兜底帧（unknown）；叠加链被中间层剥掉后缀的重写帧
（unknown）。这些拒绝是**设计行为**，不是误伤。

### 1.1.5 「零误伤」限定修正

§5-3 与 §6-3 的「零误伤」**仅指**：已满足冻结准入契约的输入（真实行情源
在线抓取、观测时间可证、交易日、无合成标记，含 1.1.2 认可的缓存路径）
不被误拒。对 1.1.4 列明的缺证据来源，拒绝是预期行为——「全部来源零影响」
与「生产只吃 final」不可能同时承诺，本稿明确选择后者。

### 1.2 证据缺失 → unknown，不许落 partial 冒充

- **partial 是正向判断**：有明确证据表明最后一根 bar 形成中——观测时刻
  早于该 bar 日收盘（14:59 反例即此类），或帧带实时合成标记
  （`+tencent_rt` 等）。
- **unknown 是证据不足**：无法取得观测时刻（无 meta 的旧缓存、上游没传
  `fetched_at`）、bar 日期非日历交易日、观测时刻早于 bar 当天（数据与时间
  矛盾）、来源不可信。**证据不够时落 unknown，禁止落 partial**——partial
  听起来「更确定」，实则没有证据支撑；unknown 在生产路径与 partial 同等
  拒绝（契约 §1 保守缺省），所以落 unknown 不损失安全性，只损失虚假的精确感。
- 空帧 / 无数据：unknown（W2-S1 原型已如此）。

### 1.3 缓存读取如何保留原始证据

- **禁止用「现在读到了缓存」当「缓存内容刚更新」**：缓存帧的观测时刻 =
  `.meta.json::fetched_at`（写入时刻）。15:01 读到 14:59 写入的缓存，
  观测时刻仍是 14:59 ⇒ partial。读盘动作本身不产生任何证据。
- **禁止用 as_of=close 反证**：`as_of` 是编排层标签（signal_scan.py），只
  描述意图，不描述数据，见 §0。
- `analyze()` 的离线兜底分支（`pipeline.py`：网络失败→读缓存）与
  `IntradayOverlayProvider._from_cache`（缓存历史+实时叠加）都必须把
  meta 的 `fetched_at` 一并透传给完成度判定，而不是在兜底处重新取当前时间。
  这是 W2-S3 的接线改动点（本稿只冻结口径）。
- W2-S1 原型的 `annotate_bars` 入参 `observed_at` 由此获得唯一合法取值来源；
  「分类执行时刻」不是合法取值。

### 1.4 A股口径（分节）

- 时区：`Asia/Shanghai`；收盘缺省 15:00（可注入）；日历：注入式，缺省
  `WeekdayCalendar`（保守：宁晚不提前，与周线完成语义同一设计取舍）。
- 判定：D 是交易日 ∧ 观测时刻（沪时）≥ D 15:00 ⇒ final；观测时刻 < 15:00
  且 ≥ D 0:00 ⇒ partial；其余 ⇒ unknown。14:59 帧在 15:01 分类 = partial。
- A股日线源盘中自带形成中 bar（services.py 模块头注释），因此「帧里有没有
  当日 bar」不构成任何完成证据——有没有都可能是不完整的，唯一证据是观测
  时刻。ths 板块路径另需 §1.1-3 的合成标记。

### 1.5 美股口径（分节，禁钟点启发式）

- **禁北京钟点启发式**（GPT 第 6 轮冻结）：美股 final 判定 = 交易所时区
  （`America/New_York`）+ 市场日历 + bar 时间戳三要素，缺一落 unknown。
- bar 日期归属（GPT 第 27 轮修订三，语义冻结）：Yahoo v8 原始字段
  `result.timestamp[]` 是 **UTC 纪元秒，表示该 bar 的物理时刻**（日线取
  该交易时段在交易所当地的开盘时刻，再折算成 UTC 表达）——**不是交易日
  标签**。当前转换位置：`providers.py::YahooV8PriceProvider.fetch` 第
  227 行 `datetime.fromtimestamp(t, tz=UTC).date()`，取的是 **UTC 日期**。
  这对美股（13:30/14:30 UTC，与美东同日）**碰巧正确**，但对 UTC 偏移为正
  且开盘换算后落到 UTC 前一日的市场会**错一天**。独立预期样本（前后对照，
  非真实行情，仅示意换算）：
  - 日经 `^N225` 某交易日 D=2026-09-15，开盘 09:00 JST = **D-1 15:00 UTC**。
    当前代码取 UTC 日期 ⇒ bar 被标成 **2026-09-14（错）**；按交易所时区
    换算后取日期 ⇒ **2026-09-15（对）**。
  - 标普 `^GSPC` 交易日 D 开盘 09:30 ET = 同日 13:30/14:30 UTC，两种取法
    同为 D——这正是当前代码「多数时段恰好等于美东日期」的由来，是巧合
    不是定义。
  修正口径：bar 日期 = `datetime.fromtimestamp(t, tz=ZoneInfo(交易所时区)).date()`。
  **该修正是实质数据处理变化（会改变既有非美股 Yahoo 标的的 bar 日期与
  后续一切判定），不是纯接线，显式列入 W2-S3 授权范围**；同时限定为
  v8 适配器内这一处换算，不做全面 provider 重构。
- 收盘：16:00 ET 常规时段，注入式参数；**夏令时由时区换算天然处理**
  （`ZoneInfo("America/New_York")` 自动 DST），不写固定偏移、不写「北京时间
  凌晨 X 点」类钟点规则。
- 海外指数链路的现成 partial 证据：`IntradayOverlayProvider` 的
  `+<source>` 后缀 = 最后一根 bar 为实时合成 ⇒ 直接判 partial，无需时钟。
  无后缀时按观测时刻判定。
- 美股观测时刻同样取帧获取/写入时刻（`fetched_at`），规则与 A股一致。

---

## 2. 用途映射（G2）：按调用契约，不按目录名

**背景事实（T5 已核验）**：`research/` 目录内住着 A/B/C/D 生产引擎本体，
被 `routes/opportunities.py` 与 `symbols.py` 实时调用——**在 research/ 目录
不等于研究用途**；反之 api/ 层也有纯观察用途。因此用途映射绑定**调用链与
契约**，不绑定路径：

| 调用链 | 用途 | 契约 | 接线后行为 |
|---|---|---|---|
| `scripts/daily_scan.py` → `run_opportunity_scan` | 收盘后正式买点扫描落库 | `production_signal_requires_final` | 非 final ⇒ 拒绝（§4） |
| `api/signal_scan.py::run_signal_scan(as_of=close)` → 同上 | 统一信号扫描（买+卖）落库 | `production_signal_requires_final` | 同上；含卖点提取（卖点同样吃最后一根 bar） |
| HTTP `GET /opportunities/scan` → `run_opportunity_scan` | 同正式扫描的 API 面 | `production_signal_requires_final` | 同上（与 CLI 共用纯函数，天然同口径） |
| `GET /symbols/{symbol}/buy-point-review`、详情页、看盘卡 | **盘中观察**：看当前形成中形态 | `observation_allow_partial`（新契约名，语义=允许 partial 但必须带显式标注） | 允许通过；结果标注完成度，不冒充收盘语义 |
| J1 golden 回放（`tests/golden/`） | 判定基准 | 样本显式 `completeness=final` | 基准输入钉 final，不在线判定 |
| 研究/回测脚本、PIT fixture | 研究 | `research_allow_partial` | 允许 + `research_view` 显式标注（W2-S1 已实现） |
| 既有五波预计算/宽度/板块任务 | 各自 | W2-S3 逐一登记，缺省**不改行为**（见 §5） |

要点：接线后**不悄悄取消原有合法用途**——盘中观察（buy-point-review、详情页）
继续可用且继续能看到形成中 bar，只是结果永远带完成度标注，下游/UI 不得把
非 final 展示成收盘信号。`as_of=intraday` 的扫描（若未来启用）也属观察用途，
不因「是扫描」就自动豁免或自动加严——按调用契约查表。

### 2.1 缓存命中路径表（实际调用点 × 命中情形 × 用途 × 检查位置，已读源码核实）

「检查位置」指接线后完成度判定发生处；现状=全链路无任何完成度检查。

| 调用点 | 缓存情形（实际函数与行为） | 用途 | 检查位置（接线后） |
|---|---|---|---|
| `scripts/daily_scan.py::main`（先 `service.get(symbols[0], refresh=True)` 预热，再 `run_opportunity_scan(..., refresh=True)`） | `refresh=True` 强制 `_run`（services.py:124-126），内存 TTL 不生效；帧级缓存仅两种：A股链直接在线抓（每次新 fetch），海外链 `CacheFirstProvider` 30min 磁盘命中（realtime.py:532-537） | 生产 close | `analyze()` 内策略判定（§3-1）；CLI 与 API 经 `run_opportunity_scan` 同一收敛点注入 |
| HTTP `GET /opportunities/scan`（routes/opportunities.py:645） | `refresh` 缺省 **False** ⇒ `service.get_many(refresh=False)`：内存 TTL 命中直接返回旧 entry（services.py:141-145），**不重抓、不刷新 fetched_at**；未命中才 `_run` | 生产 close（与 CLI 同纯函数 `run_opportunity_scan`，opportunities.py:568） | 同上；**且内存命中路径必须在 entry 上携带完成度结论复检**（§2.2） |
| HTTP `POST /opportunities/today/refresh`（opportunities.py:734） | `refresh=True`，同 CLI 情形 | 生产 close | 同 CLI |
| HTTP `POST /signals/today/refresh`（routes/signals.py:93，`as_of` 缺省 `"close"`）→ `run_signal_scan` | 两段：先 `run_opportunity_scan(refresh=True)` 强制重抓；随后 `service.get_many(wanted, refresh=False)` **纯读内存缓存**做卖点提取（signal_scan.py:51-56 注释明示）。注意：`as_of` 参数**只写进 signal_alerts 的 meta 行标签，不改变任何抓取/判定行为**（signal_scan.py:83）——`as_of=intraday` 与 `close` 现状行为完全相同 | 生产 close | 第二段是**典型「同一缓存被另一用途消费」点**：卖点提取消费的是前一段刚产生的 entry，其完成度结论必须随 entry 传递并在 require_final 下复检，不得因「不再调 analyze()」而免检 |
| `GET /symbols/{symbol}/buy-point-review`（opportunities.py:555）、详情页/看盘卡（dashboard.py、symbols.py） | `service.get(refresh=False)`：内存 TTL 命中常见（盘中短 TTL 持续刷新） | 观察（observation_allow_partial） | `analyze()` 内 observe_annotate 策略：只标注不拒绝 |

### 2.2 盘中观察缓存被生产消费的反例（锁死）

**反例**：同一 `AnalysisService` 实例被全部路由共享（app 级单例）。14:59 用户
看详情页产生 entry（observation 用途、partial 帧）；15:05 生产请求到达——
`GET /opportunities/scan` 缺省 `refresh=False`，走 `get_many(refresh=False)`：
A股因 `session.is_cache_fresh` 要求 `fetched_at ≥ last_close`（session.py:113）
会判过期重抓（该路径自洽）；**但海外指数走扁平 TTL**（services.py:106-107
只看 age），14:59 的盘中 entry 在 TTL 内被原样当作生产扫描结果消费——即使
不再调 `analyze()`，无检查的生产消费成立。`run_signal_scan` 的第二段
`get_many(refresh=False)` 同理。

**方案二选一（取舍）**：

- **方案 A（用途隔离缓存）**：entry 按用途分桶，生产请求不读观察 entry。
  彻底但代价高：两桶并发抓取同一标的会重复打网络、TTL 语义分叉、内存翻倍，
  且 `run_signal_scan` 第二段「买点刚刷新、卖点纯读」的设计被破坏（必须重抓）。
- **方案 B（复用但重检准入资格，本稿选定）**：entry 上携带该帧的完成度结论
  与观测时间（`AnalysisEntry` 增加旁侧字段，不改 `AnalysisResult` 结构）；
  生产消费点（`run_opportunity_scan`、`run_signal_scan` 卖点段）在消费前按
  `production_signal_requires_final` **复检 entry 的结论**，不满足即拒绝——
  与是否重新调 `analyze()` 无关。
  取舍理由：观察 entry 的帧在盘中必为 partial（观测时刻 < 收盘），生产复检
  必拒并触发该标的重抓（等效 A 的隔离效果），但零重复抓取成本、零 TTL 分叉；
  复检是纯内存字段比较，无 IO。

### 2.3 生产入口缺省=最严格

任何生产入口的用途参数**缺省值必须是 production_close/require_final**，
不得因调用方漏传参数而落到观察用途。具体：`run_opportunity_scan`、
`run_signal_scan` 的用途参数缺省 production；`analyze()` 的
`bar_completeness_policy` 缺省 `observe_annotate`（保护既有观察调用方），
但**生产收敛点必须显式传参覆盖**，且该显式传参由 §3-3 的单一注入点保证，
不依赖每个调用方自觉。缺省宽松=静默漏洞，方向上只允许「缺省更严」。

### 2.4 报告绑定实际参与计算的数据版本

扫描产出（ScanItemDTO / SignalAlertRow / 详情页完成度标注）必须携带
**实际参与计算的那一份帧的观测时间与完成度结论**（来自被消费的 entry，
而非响应生成时刻 `generated_at`）。验收反例：注入新帧重抓后，若 DTO 仍带
旧缓存的结论或旧观测时间 ⇒ 结果无效。J1 golden 与 S3 验收草案第 8 条据此
断言「结论字段与帧同源」。


---

## 3. 接线位置（G3）

**选定边界：`AnalysisService` 增加按调用的用途参数，策略穿透到
`analyze()` 内、规则引擎（`analyze_bars`）执行之前，对实际抓到的那一份帧
做判定；两个生产入口统一在 `run_opportunity_scan` 收敛点注入
production 契约。**

具体分层（W2-S3 实现蓝图）：

1. **判定发生点**：`compose/pipeline.py::analyze()` 增加可选参数
   `bar_completeness_policy`（缺省 `observe_annotate`——只标注不拒绝，保持
   既有观察用途零行为变化）。在 `price_provider.fetch` 返回/缓存兜底定帧
   **之后**、`analyze_bars`（规则层）**之前**，用 §1 口径对
   `price_data.bars` 最后一根 bar 判定；policy=require_final 时非 final 抛
   `PartialBarError`。**这保证「检查的帧」与「送入规则层的帧」是同一份
   DataFrame 对象**——检查一份、计算另一份 = 无效，此边界天然排除。
2. **观测时刻来源**：`AnalysisService._run` 把自己的 `fetched_at`（抓取前
   取的 now）传入 analyze；`analyze` 内部缓存兜底分支改传缓存 meta 的
   `fetched_at`（§1.3 的 W2-S3 改动点）。
3. **契约注入点（CLI/API 双路径唯一收敛处）**：
   `routes/opportunities.py::run_opportunity_scan`（纯函数，`daily_scan.py`
   CLI、HTTP `/opportunities/scan`、`signal_scan.py` 三方共用）在调用
   `service.get_many` 时传 `usage="production_close"` → `AnalysisService`
   选 require_final 策略。**任何一条生产路径想绕过，必须绕开
   run_opportunity_scan 本身，而三条路径已在 J1 双入口护栏下钉死共用该纯
   函数**——不新增可绕过面。
4. **不选的位置与原因**：
   - 不在 `analyze()` 内部无条件硬拒：会杀掉 buy-point-review 等合法盘中
     观察用途（§2）；
   - 不在 `run_opportunity_scan` 拿到 entry 后再判：那时规则已在帧上跑完，
     判定对象只能是结果不是帧，违反「同一份帧」红线；
   - 不在 provider 层：provider 不知道调用用途，且改 provider 适配器超出
     W2-S1 冻结边界。

---

## 4. 拒绝传播（G4）

- `PartialBarError` 在 `AnalysisService._run` 被捕获后转为**既有不可用表达**，
  不发明新状态：
  - `run_opportunity_scan`：该标的 `ScanItemDTO(verdict=none,
    error="收盘数据未走完（partial/unknown，bar 日期 X，观测时刻 Y）")`——
    与数据不可用同一展示通道；
  - `signal_scan.py`：写 `SIDE_UNAVAILABLE` 行，`kind="bar_not_final"`，
    error 带三态与日期明细——复用「数据不可用标的显式写 unavailable 行，
    不静默为无信号」的既有语义（signal_scan.py 模块头）。
- **非 final 的拒绝必须显式可见，禁止静默变「无信号」**：none-verdict 行带
  error 文案，unavailable 行带 kind，前端照既有 error 渲染。
- **禁止偷偷删掉最后一根 partial bar 再包装成完整扫描**：那是另一种产品
  策略（「用截至昨日的历史跑收盘语义」），收益与风险（当日触发条件系统性
  缺失、与 J1 基准口径分叉）需用户拍板，本稿与 W2-S3 均不做、不预留隐藏
  开关。若未来用户选择该策略，须单独立项并同步改 J1 基准预期。

---

## 5. 不受影响清单（G5-a）

1. **显式研究路径**：`research_allow_partial` 保持允许 + 标注（W2-S1 已实现，
   `research_view`）；golden 样本钉 final 不受在线判定影响。
2. **final 不替代既有数据质量判断**：`MIN_BARS=21`、`DATA_UNAVAILABLE`
   （17 处调用点）、validate_bars、trusted-provider 门全部原样；final 是
   「这根 bar 走完没有」，不是「数据好不好」——两轴正交，先过质量检查再谈
   完成度，互不豁免。
3. **观察用途零行为变化**：buy-point-review、详情页、看盘卡默认策略为
   只标注不拒绝；盘中看形成中形态的既有能力不取消。
4. **既有定时/预计算任务缺省不动**：宽度、板块、五波等任务不在
   production 契约注入名单内（§2 表），W2-S3 逐一登记、缺省不注入。
5. **守卫帧=计算帧**：§3-1 的判定点保证；列为 W2-S3 验收项。
6. **周线完成语义**（calendar.py）独立并存：周线完成仍走「本周最后交易日」
   日历判定，本契约只管单根日线 bar，不改 aggregate_weekly。

---

## 6. W2-S3 验收草案（G5-b）

1. **双路径不可绕过**：CLI 真子进程跑 `scripts/daily_scan.py` 与 API
   TestClient 走真实 HTTP 路由（沿用 J1 S2 的双入口测试形态），注入
   partial 帧夹具，两条路径都必须产出显式拒绝（error 行/unavailable 行），
   不得产出信号。
2. **非 final 显式拒绝、不静默无信号**：断言拒绝行带三态/日期明细文案；
   「verdict=none 且无 error」不算通过。
3. **合法标的零误伤**：final 样本（观测时刻 ≥ 收盘、交易日、无合成标记，
   含缓存命中路径：meta.fetched_at ≥ 收盘）在两条路径上判定与信号产出与
   接线前完全一致。
4. **J1 判定预期不变**：`tests/golden/` 全量（含 test_golden_completeness
   的 final 标注断言）在接线后原样通过；规则哈希不因接线变化（接线只在
   规则层之前增加准入，不改规则与样本）。
5. **14:59 反例回归测试**：帧观测时刻 14:59、15:01 分类 ⇒ partial ⇒ 拒绝；
   缓存 fetched_at=14:59 在 15:01 读 ⇒ 同样拒绝（防「读缓存当新证据」复发）。
6. **观察路径回归**：buy-point-review 盘中夹具照常返回结果且带完成度标注。
7. hygiene 全绿、无既不在名单内的新文件。
8. **写入时间升级反例回归**（GPT 第 27 轮增补）：(a) 模拟在线抓取 15:01
   落盘的收盘后帧 ⇒ final 合法通过（不得把「落盘晚」误判成 partial）；
   (b) 模拟 §1.1.3-② 的重写路径（CacheFirst 命中→叠加→重写缓存，
   meta.fetched_at 被刷新）⇒ 判定不得因刷新的 fetched_at 升 final，
   带 `+rt` 后缀判 partial、后缀被剥的重写帧判 unknown。
9. **缓存复用升级反例回归**（§2.2）：盘中观察 entry（partial）在 TTL 内
   被 `GET /opportunities/scan`（refresh=False）与 `run_signal_scan` 卖点段
   消费 ⇒ 必须拒绝且不产出信号，并触发该标的重抓；断言消费点复检的是
   entry 携带的结论而非重新抓取。
10. **缺省最严格回归**（§2.3）：生产收敛点不传用途参数（模拟调用方遗漏）
    ⇒ 行为与显式 production_close 完全一致；任何路径不得出现缺省宽松。
11. **报告绑定回归**（§2.4）：注入新帧重抓后，DTO/告警行携带的完成度结论
    与观测时间必须来自新帧（检查新帧返回旧结论=无效）。
12. **Yahoo v8 日期换算回归**（§1.5 修订三）：对 UTC 换算会跨日的市场
    （如 ^N225 类样本）断言换算前后 bar 日期差一天，且该变化随 W2-S3
    授权一并评审，不与接线混提。

---

## 7. 版本与状态

- v1.0（2026-09-20）：W2-S2 设计稿冻结。六点逐节覆盖（§1 证据口径含 A股
  §1.4 / 美股 §1.5 分节、§2 用途映射、§3 接线位置、§4 拒绝传播、§5 不受
  影响清单、§6 W2-S3 验收草案）。
- v1.1（2026-09-20）：GPT 第 27 轮 REVISE_REQUIRED 三处修订——
  §1.1.1-1.1.5 完成证据补实（三种时间事实、fetched_at 赋值位置源码核实、
  写入时间升级四反例、8 源逐源准入表、零误伤限定）；§2.1-2.4 缓存命中
  路径补实（路径表、盘中观察缓存被生产消费反例锁死、缺省=最严格、报告
  绑定数据版本）；§1.5 Yahoo v8 日期语义冻结并列入 S3 授权范围；
  §6 增补第 8-12 条验收反例。
- **状态：设计稿。任何实现/接线/测试代码需 W2-S3 独立小单与独立授权。**
