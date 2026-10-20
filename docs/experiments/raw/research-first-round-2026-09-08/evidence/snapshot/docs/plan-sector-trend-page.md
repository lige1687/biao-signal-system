# 行业板块趋势工作台 · 执行方案 v1

> 交付对象：执行 agent。本方案基于四路并行勘察（规则引擎复用面 / 预计算与缓存约定 / 前端可复用件 / 板块数据实测），所有关键断言均有实测数字支撑，标注【实测】的不要复核，直接照做；未标注的按方案执行。

## 0. 目标与定位

用户是**中期趋势交易者**（持仓数周~数月）。现有基本面页 `④ 行业` 区是"当日快照榜"（涨跌幅/当日主力净流入），与中期趋势需求正交。本方案新建独立页面 **`/sectors` 行业板块趋势工作台**，核心回答三个问题：

1. **哪些板块处于趋势确立/正在改善？**（阶段判定：筑底/上升/派发/下降）
2. **谁在相对变强、谁在相对变弱？**（RS 相对强度排名 + 排名变化 + RRG 轮动象限）
3. **板块内的趋势是否普遍？**（板块宽度：成分股站上 MA20/50/200 占比、新高扩散）

基本面页的 `④ 行业` 区保留不动（当日参考），两页互不替代。

## 1. 关键前提（全部已勘察确认）

| 前提 | 依据 |
|---|---|
| 东财 clist 板块列表 + `fs=b:{code}` 成分股可达 | 【实测】496 板块全量 560 请求/6并发/163s，0 失败 |
| 东财 fflow 资金流历史可达（五档齐全） | 【实测】`fetch_industry_flow` 正常 |
| 东财板块日 K 线**不可达**（代理白名单挡 push2his kline） | 【实测】ProxyError -> 板块指数必须本机合成 |
| 腾讯日K可用（含科创板 sh688；**北交所 bj 无历史**，只返当日 1 条） | 【实测】 |
| `a_share_klines.parquet`（4594 只 × 320 交易日 close，前复权）由 `com.lei.ashare.ma` 每交易日 16:30 维护 | 【实测】320 对齐窗口 2025-04-23~2026-08-14 |
| **阻塞项：代码 universe 缺科创板整段**（`a_share_breadth.py:132` 用 `ak.stock_info_sh_name_code()`，不含 sh68；616 只缺失 -> 现有全A宽度也失真） | 【实测】`a_share_codes.json` 4930 个代码无 sh68 |
| 申万层级 clist 无字段、名称后缀不可靠；唯一可靠判定 = 成分股集合严格包含 | 【实测】f1~f300 扫描 + 反例（`其他电源设备Ⅲ`⊂`其他电源设备Ⅱ`是真父子） |
| 38 组板块成分股集合完全相同（77 个板块），去重后 457；父==子并集 120/120 成立 | 【实测】 |
| `compute_features` 硬依赖 high/low/volume，缺则 KeyError；`open=high=low=close`+`volume=0` 补齐合法 | 【实测】 |
| `analyze_bars` 对合成指数能跑但不该跑：769 事件中大量语义无效（ATR/摆动点/颈线退化） | 【实测】 -> 只用 4 个轻入口 |
| MA200 在 320 日窗口内只有 121 天历史 | 【实测】 -> 宽度主看 b20/b50，b200 诚实标注"留痕中" |

## 2. 红线（全程遵守，逐条可验收）

1. **板块层一切判定标 `research_proxy`（研究代理）**，UI 常驻标注，不冒充 LEI 原始规则。
2. **不出买卖点**。列名/标签/文案只出现「趋势确立/走弱/强度增强/衰减/阶段」，禁 买入/卖出/建议买/加仓/减仓/抄底。
3. **MACD 必带盲区补齐**（沿用 `.claude/skills/macd-reading/SKILL.md`）：MACD 状态必须与 LEI 三色 + 均线斜率同屏出现，不得独立成结论列。
4. **不新造参数**：均线周期/MACD 12/26/9 从 `configs/rules.v1.yaml` 的 `indicators` 段读（`indicator_config()`），不硬编码。
5. **合成口径必须诚实标注**：等权指数（本机合成，非行情软件板块指数）；以当前成分回溯（含前视偏差，仅形态参考）；不含北交所（腾讯无历史）；MA200 留痕中。
6. **不可用字段不冒充**：合成指数的 `atr14`/`volume_ratio20` 等退化值不输出、不展示。
7. **斜率跨板块比较用百分比口径**（`ema_slope_accel_for_frame` 的 `ema20_slope_pct`），`*_slope`（绝对差）只取符号。
8. **原子写落盘**（照抄 `a_share_breadth._save_codes` 的 `tmp.replace(p)`），日志进 `logs/`（已 gitignore）。

## 3. 分阶段交付

```
P0 修 universe（含科创板）——阻塞项，顺带修好现有全A宽度
P1 预计算层（成分股映射 + 板块指数 + RS + 宽度 + 落盘）+ 单测
P2 后端 API（/api/sectors/*）+ 单测
P3 前端 /sectors 页（抽共享件 + 页面 + RRG 图）+ tsc/build 验证
P4 launchd 接线 + 运维文档
```

---

## P0 · 修 universe：补科创板（阻塞项）

### P0.1 `src/lei_signal/market_context/a_share_breadth.py`

- 修 `_fetch_sh_codes()`（约 L132）：`ak.stock_info_sh_name_code()` 返回不含科创板。**追加**调用 `ak.stock_info_sh_name_code(symbol="科创板")`（akshare 该接口的 `symbol` 参数支持 `"主板"`/`"科创板"`），两段 concat 去重。若 akshare 版本不支持该参数：回落到按代码段兜底——拉东财 clist `fs=m:1+t:23`（沪市A股，含科创板）取 6 开头全部代码，与 ak 结果并集。
- **验收**：重跑代码列表抓取，`a_share_codes.json` 含 `sh688xxx`/`sh689xxx`，总数 ≈ 5540±30（4930 + 616 − 部分重叠）。
- 落盘照抄现有 `_save_codes`（原子写）。`--limit` 调试参数行为不变。
- **不动**北交所：337 只腾讯无历史，剔除逻辑在预计算层做（P1），宽度层维持现状（bj 代码存在但腾讯只返 1 条，`_fetch_kline` 因 `len(out) >= 5` 不达标自动跳过，行为已正确【实测】）。

### P0.2 回补日K缓存

- 修完 universe 后跑一次 `python scripts/precompute_a_share_ma.py --force --no-save` 观察日志：科创板 616 只逐只拉腾讯 320 条并写入 parquet。首跑补科创板增量约 616 次请求 × 1.5s ≈ 15 分钟，可接受。
- 之后 `python scripts/precompute_a_share_ma.py` 正式跑，`a_share_klines.parquet` 增至 ≈5200 只。
- **验收**：`python3 -c "import pandas as pd; df=pd.read_parquet('$HOME/.lei_signal_lab/cache/a_share_klines.parquet'); print(df.symbol.str.startswith('sh68').sum())"` 输出 >0。

---

## P1 · 预计算层

### P1.1 新模块 `src/lei_signal/market_context/sector_trend.py`（全部逻辑在此，脚本只是 CLI 壳）

分层照抄 `a_share_breadth.py` 的结构：sources 在 `fundamentals/sources.py`（复用 `_get_json`/`_CLIST_URLS`），读盘写盘/纯计算在 `market_context/`，route 只读盘。

#### a) 成分股映射 `fetch_sector_members()`

- 板块列表复用 `fundamentals.sources.fetch_industry_boards()`（496 个，含 `f104/f105` 涨跌家数）。
- 每板块 `fs=b:{code}` 翻页拉成分（`pz=100` 硬上限【实测】，`fields=f12,f13,f14`）。**并发 6 线程 + 每请求 0.2s 抖动**，全量约 2.7 分钟【实测】。
- 市场前缀映射**不能用 f13**（北交所 920 段 f13=0 是错的【实测】），按代码前缀：
  ```python
  def _prefix(code: str) -> str:
      if code.startswith(("4", "8", "92")): return "bj"
      if code.startswith(("6", "9")): return "sh"
      return "sz"   # 0/3/2 开头
  ```
- 落盘 `sector_members.json`：`{"as_of", "date", "boards": {code: {"name": …, "members": [prefixed_symbol, …]}}}`，当日命中判定（读到的 `date == today` 即跳过，周末沿用周五）。原子写。

#### b) 层级判定与去重（纯函数）

```python
def classify_hierarchy(boards: dict[str, set[str]]) -> dict[str, dict]:
    """返回 {code: {"level": 1|2|3, "parent": code|None, "canonical_of": [alias codes]}}"""
```
- **去重**：`frozenset(members)` 为 key 分组，组内保留优先级 无后缀 > Ⅱ > Ⅲ 的为 canonical，其余记 alias（38 组【实测】，**不能按名称去后缀**——反例：`其他电源设备Ⅲ`⊂`其他电源设备Ⅱ` 是真父子）。
- **层级**：去重后 457 个里，没有真超集的 = L1（31 个，与申万一级完全一致【实测】）；其余的直接父 = 包含它且成分股数最小的板块。
- **交叉校验**（每次运行时执行，失败只 warning 不中断）：父板块成员集 == 子板块成员集之并（120/120 成立【实测】）。violation 打进快照 `warnings` 字段。

#### c) 等权指数合成（纯函数，单测重点）

```python
def build_equal_weight_index(member_prices: pd.DataFrame) -> pd.Series
```
- 输入：pivot 宽表（symbol 列 × date 行，值 close）。
- 算法（避坑全部来自【实测】）：
  1. `valid = wide.notna()`（**上市前是 NaN，不参与当日分母**）
  2. 停牌沿用前收：`wide_ff = wide.ffill()`，停牌日收益 = 0（正确）
  3. `ret = wide_ff.pct_change()`，用 `valid` 掩掉上市前（**不能 `fillna(0)` 后直接平均**，否则上市前被当"持平"压低波动）
  4. `daily_ret = ret.where(valid).mean(axis=1)`（**分母 = 当日有效成分股数**，不是固定分母——否则新股上市当天假跳空）
  5. `idx = 1000 × cumprod(1 + daily_ret.dropna())`
- **对齐窗口**：按"每日有效 ≥4000 只"裁 320 个交易日【实测】（union 365 天是假象，前 45 天每股数据残缺）。
- **有效性门槛**：命中成分股（在 parquet 中有 K 线）< 5 只的板块不生成指数（28 个板块 <3 只【实测】），趋势列显示"样本不足"，不参与 RS 排名。
- **全A等权基准** `bench_all`：parquet 全体按同法合成；沪深300 用已有 `000300.SS.bars.parquet`（1500 条，历史更长），作为参考列 `bench_hs300`，**不作为 RS 主基准**。

#### d) RS 相对强度（纯函数）

- 主基准 = `bench_all`（等权 vs 等权，同口径【方案决定】）。
- `rs(t) = idx/bench`，归一化 `rs(t0)=100`；`rs_above_ma20 = rs > MA20(rs)`；`rs_chg_20/60`；RS 百分位排名在同层级内算（L1 排 L1，L2 排 L2）。
- 排名变化 `rs_pctile_delta_20 = rs_pctile(t) − rs_pctile(t−20)`，首次运行为 null（前端显示"留痕中"）。
- **注意**：RS 排名基于等权指数全历史回溯，含前视偏差，仅作相对比较。

#### e) 板块宽度（纯函数）

- `b20/b50/b200`：成分股 `close > MA20/50/200` 占比（**只用当日有效成分**，分母同 c）；中期主看 `b50`。
- `nh60`：`close == rolling(60).max()` 的占比。
- 宽度背离：`idx` 创 60 日新高但 `b50` < 其 60 日均值 → `breadth_divergence: true`。
- b200 诚实标注：320 日窗口内 MA200 只有 121 天【实测】，首次不显示数值、显示"留痕中"（照抄 global-strip 对缺失宽度的处理：显式 null，绝不伪造）。

#### f) 趋势读出（复用规则引擎 4 个轻入口）

照抄本方案附带的代码骨架（勘察已实测字段名）：
```python
frame = compute_features(sector_bars_from_close(close), indicator_config())
frame = classify_colors(frame)
frame = compute_long_trend(frame)
macd = read_macd_strength(frame.iloc[-1], frame.iloc[-2])
```
- 补列：`open=high=low=close`，`volume=0.0`。
- 输出字段（snake_case，进快照）：`signal_color`、`signal_color_cn`、`ema20_slope_sign`、`sma60_slope_sign`、`sma120_slope_sign`、`ema20_slope_pct`（跨板块可排序）、`long_trend_cn`、`macd_status`、`macd_label_cn`、`macd_detail_cn`、`macd_dimension`、`alignment_cn`、各 `*_rule_version`、`provenance="research_proxy"`。
- 121 根以下（L3 新板块常见）只输出 color（21 根即可），其余 null；MACD warmup（前 34 根）自然为 None。

#### g) 阶段判定 Stage（纯函数，标 research_proxy）

| 阶段 | 条件（全部用 f) 的确定性输出） |
|---|---|
| ② 上升 | `idx > sma60` 且 `sma60_slope_sign > 0` 且 `rs_above_ma20` |
| ① 筑底 | 其余情形中 `rs_above_ma20` 且 `ema20_slope_sign ≥ 0` |
| ③ 派发 | `idx > sma60` 且（`sma60_slope_sign ≤ 0` 或 `breadth_divergence`） |
| ④ 下降 | `idx < sma60` 且 `sma60_slope_sign < 0` |

判定顺序 ②→③→①→④，判定依据字段（`stage_basis` 数组）写进快照，UI tooltip 展示——**阶段是合成结论，必须可追溯**。

#### h) 落盘产物（全部原子写，根目录 = `Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))`）

| 文件 | 内容 |
|---|---|
| `sector_trend_snapshot.json` | 当日全量：`{as_of, date, boards: [{code, name, level, aliases, member_count, hit_count, stage, stage_basis, rs_pctile, rs_pctile_delta_20, rs_chg_20, rs_chg_60, rs_above_ma20, b20, b50, b200, nh60, breadth_divergence, signal_color, …, main_flow_20_yi, pe_ttm, pct_change, up_count, down_count}], bench: {…}, warnings[]}` |
| `sector_trend_history.json` | list[dict] 逐日追加（同日覆盖再 append，照抄 `append_ma_breadth_history` 语义但 **today 用 trading_day 修正**勘察发现的瑕疵）：每日只存 `{date, boards: {code: {stage, rs_pctile, b50, close}}}`，控制体积 |
| `sector_members.json` | a) 的成分股映射（当日缓存） |

**PE 留痕**：每日快照顺带落 `pe_ttm`（clist 已有字段），页面不显示分位，显示"留痕中，N 个交易日后可用"。

#### i) 与现有 16:30 任务的关系

预计算流程：读 `sector_members.json`（当日有效则跳过成分股抓取，否则 6 并发拉全量 2.7 分钟）→ 读 parquet → 全部纯函数计算（秒级）→ 原子写三份 json。**不拉任何个股 K 线**（腾讯只被 16:30 任务使用）。

### P1.2 CLI `scripts/precompute_sector_trend.py`

照抄 `precompute_a_share_ma.py` 的壳（141 行）：sys.path 注入 / `--limit`（只算前 N 板块调试）/ `--no-save` / `--force` / 返回码 1=取数失败 / `⏱ 耗时` 打印。**不写 `--backfill`**（history 首日由快照自然生成，无需回溯分支）。

### P1.3 单测 `tests/unit/test_sector_trend.py`（`a_share_breadth` 至今零覆盖，这里立标准）

- 纯函数测试照 `test_market_breadth.py` 造数据风格：`_make_member_prices(...)` 造 5 只 × 300 日合成价。
- 必测用例：
  - 等权指数：停牌（某股中断后 ffill 收益=0）、新股中途上市（前段不进分母）、5 只中 1 只翻倍 → 指数涨 ≈20%；
  - 层级判定：构造 A⊃B⊃C 三层 + 一对同集合重复板块（验证 Ⅱ/Ⅲ 别名合并）+ `其他电源设备` 型反例（Ⅲ 是 Ⅱ 真子集 → 不合并）；
  - 阶段判定：四阶段各造一条满足/不满足的数据，断 `stage_basis` 可追溯；
  - RS：两板块一强一弱，断排名互换、`rs_above_ma20` 方向正确；
  - 落盘隔离：`monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))`；
  - 网络零依赖：全部 monkeypatch `fundamentals.sources` 相关函数（照 `test_fundamentals.py` 手法 A/C）。

---

## P2 · 后端 API

### P2.1 新路由 `src/lei_signal/api/routes/sectors.py`

照抄 `fundamentals.py` 风格（`router = APIRouter(prefix="/api/sectors", tags=["sectors"])`，普通 def 返回裸 dict，`_service(request)` 模式）。**不能叫裸 `/api/sectors`**（已被 `watchlist.py:65-91` 占用，前端 `api.sectors()` 在用）。

| 端点 | 行为 |
|---|---|
| `GET /api/sectors/trend?refresh=false&level=all\|l1\|l2` | 读 `sector_trend_snapshot.json`（miss → 404 body 带 `{"detail": "尚未运行预计算，请先跑 scripts/precompute_sector_trend.py"}`）；`level` 过滤在 service 层做 |
| `GET /api/sectors/{code}/history?days=250` | 读 `sector_trend_history.json`，取该板块 `{date, close, b50, rs_pctile, stage}` 序列 |
| `GET /api/sectors/{code}/members?limit=50` | 读 `sector_members.json` + 当日 clist 行情快照，返回成分股 `[{symbol, name, pct_change, market_value_yi}]`（行情用 `fetch_industry_boards` 同源 clist? 不——用 `fs=b:{code}` 成分股列表自带 f3/f20 字段一次拉齐） |
| `GET /api/ 行情叠加`（可选，见 P3 RRG） | RRG 数据 = trend 快照自带（rs_pctile + delta），无需单独端点 |

- service 层（新 `SectorsService`，挂 `app.state.sectors_service`，位置在 `app.py` L78 附近）：内存 `_TtlCache`（照抄 `fundamentals/service.py:29-52`，磁盘读也走 TTL 300s），`errors: []` 收集约定照抄。
- 流动性数据：`main_flow_20_yi` 由预计算层落进快照（fflow `lmt=60` 逐板块拉太贵——**只拉用户点开抽屉时**：`GET /api/sectors/{code}/flow?days=60` 实时走 `fundamentals` service 的 `industry_flow`（已存在，复用即可，前端直接调 `fundamentalsApi.industryFlow`，不新建）。
- 挂载：`app.py` import 列表（L25）+ `include_router`（L88 后）+ `app.state`（L78 后），三处。

### P2.2 单测 `tests/unit/test_sectors_api.py`

- 照 `test_api_endpoints.py` 的 `client(tmp_path, monkeypatch)` fixture：`monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))` + 写假快照 → 断 status/字段/404 文案。
- level 过滤、days 上限钳制（照 `fundamentals.py` 的 `max(1, min(...))` 风格）。

---

## P3 · 前端 `/sectors` 页

### P3.1 先抽共享件（纯重构，零行为变化，独立提交）

| 动作 | 从 | 到 |
|---|---|---|
| `fmt / fmtYi / pctClass` | `FundamentalsPage.tsx` L48-57 | `web/src/utils/format.ts`（**该文件现存全站零引用是死代码，正好激活，勿新建第二个 format 文件**）；FundamentalsPage 改 import |
| `MetricCard` | L121-157 | `web/src/components/trend/MetricCard.tsx` |
| `DrawerState` 类型 | L79-89 | `components/trend/TrendDrawer.tsx` 一并 export |
| `buildDrawer` | L92-117 | `components/trend/drawer.ts` |
| `alignTo / unionDates` | L176-185 | `web/src/components/trend/align.ts` |
| FundamentalsPage 全部改 import | — | 每步跑 `npx tsc --noEmit` |

抽完跑 `npm run build` 确认 FundamentalsPage 零回归（视觉无变化）。

### P3.2 类型 `web/src/types.ts` 末尾追加

```ts
// ---- 行业板块趋势工作台 (/api/sectors) ----
export interface SectorTrendRow {
  code: string; name: string; level: 1 | 2 | 3;
  aliases: string[]; parent: string | null;
  member_count: number; hit_count: number;
  stage: "accumulation" | "markup" | "distribution" | "decline" | null; // 筑底/上升/派发/下降/样本不足
  stage_basis: string[];
  rs_pctile: number | null; rs_pctile_delta_20: number | null;
  rs_chg_20: number | null; rs_chg_60: number | null; rs_above_ma20: boolean | null;
  b20: number | null; b50: number | null; b200: number | null; nh60: number | null;
  breadth_divergence: boolean;
  signal_color: string | null; signal_color_cn: string | null;
  ema20_slope_pct: number | null; long_trend_cn: string | null;
  macd_status: string | null; macd_label_cn: string | null; macd_dimension: string | null;
  alignment_cn: string | null;
  // 当日参考（来自 clist 快照）
  pct_change: number | null; pe_ttm: number | null; main_net_inflow_yi: number | null;
  up_count: number | null; down_count: number | null; total_mv_yi: number | null;
}
export interface SectorTrendResponse {
  as_of: string; date: string; trading_day: string;
  bench: { all_equal_close: number | null; hs300_close: number | null };
  boards: SectorTrendRow[];
  warnings: string[]; errors: string[];
  research_proxy_note: string;   // 「判定方式为研究代理……」常驻声明
}
export interface SectorHistoryPoint { date: string; close: number; b50: number | null; rs_pctile: number | null; stage: string | null; }
export interface SectorMembersResponse { as_of: string; code: string; name: string; members: { symbol: string; name: string; pct_change: number | null; market_value_yi: number | null; in_kline_cache: boolean }[]; }
```

### P3.3 API client `web/src/api/client.ts` L314 后追加

```ts
// ---- 行业板块趋势工作台 ----
export const sectorsApi = {
  trend: (refresh = false, level = "all") =>
    request<SectorTrendResponse>(`/sectors/trend?level=${level}${refresh ? "&refresh=true" : ""}`),
  history: (code: string, days = 250) =>
    request<{ points: SectorHistoryPoint[] }>(`/sectors/${encodeURIComponent(code)}/history?days=${days}`),
  members: (code: string, limit = 50) =>
    request<SectorMembersResponse>(`/sectors/${encodeURIComponent(code)}/members?limit=${limit}`),
};
```

### P3.4 页面 `web/src/pages/SectorsPage.tsx`

- **接线**：`App.tsx` import + `<Route path="/sectors" element={<SectorsPage />} />`；`TopNav.tsx` L28 后 `<NavLink to="/sectors">行业板块</NavLink>`。
- **骨架照抄** `FundamentalsPage.tsx` L876-1068（sortKey/sortAsc/keyword/selected/drawer 双抽屉状态、`useMemo` 过滤排序 null 沉底、`useMutation` 硬刷新直填缓存）。
- **页面结构（自上而下）**：
  1. `header`：标题「行业板块趋势」+ `generated` 时间 + 刷新按钮（trend 硬刷新 + invalidate history）。
 2. **口径声明条**（`.legend`）：等权本机合成 · 当前成分回溯含前视 · 不含北交所 · research_proxy。
 3. **RRG 轮动象限图**（页面主视觉）：echarts scatter。X=`rs_pctile`（0-100），Y=`rs_pctile_delta_20`，0-50-100 与 0 处虚线分四象限，右上领先/左上改善/右下走弱/左下落后；每个点 8 周**尾迹**（history 数据，`line` series + `scatter` 终点），默认只画 L1（31 个），toggle 切 L2；点 hover tooltip：名称/阶段/宽度 b50/成分数。**点板块点 → 开趋势抽屉**。
 4. **主表**（`event-table fund-table`，趋势列在前）：
     `板块(级别)` | `阶段` | `LEI色` | `RS百分位` | `RS 20日变化` | `RS 60日%` | `b50` | `nh60` | `均线状态` | `MACD` | `60日涨幅` | `当日涨幅` | `成分数` | `PE`
     - 排序按钮（照抄 SORTS 模式）：阶段 / RS百分位 / RS变化 / b50 / 60日涨幅 / 主力净流入。
     - `阶段` 用 `.macro-chip` + tone（②上升=opportunity，①筑底=neutral，③派发=caution，④下降=danger）；`LEI色` 用 `<ColorBadge>`（**必须圆点+中文字双通道**）；MACD 列只显示 status + 色调，hover 显示 `macd_label_cn`+`blind_spot`，**不独立成结论**。
     - 同产业链父子去重开关（默认开）：仅保留 L1+L2 或去掉被父板块完全包含的显示行——按 `parent` 字段过滤。L3 默认折叠，点父板块行展开（`level===3` 行 className 加 `dim`）。
     - 行点击 → 趋势抽屉；行尾 ★ 按钮 → 板块自选（localStorage，键 `lei.sector.stars`，**不接 watchlist**——主看板 providers 拉不到板块日K会报错）。
 5. **趋势抽屉 `SectorTrendDrawer`**（新建，包 `OverlayChart`——`TrendDrawer` 只吃单轴 TrendChart，不够用）：
     - 主图：板块等权指数（`axis:"left"`）+ 全A等权基准（`axis:"left"`，dashed）+ b50 宽度（`axis:"breadth"`，dashed，`breadthMarkLines={MARKLINES.breadth}` 15/50/85 线）——OverlayChart 三轴原生支持，零改动【勘察确认】。
     - 副信息：阶段 + `stage_basis` 逐条、MACD `label_cn`/`detail_cn`/`blind_spot_cn`、三色 `signal_reason`、`long_trend_cn`、`alignment_cn`、成分 n、命中 m/n。
     - 资金流段：`fundamentalsApi.industryFlow(code, 60)`，画 5/20/60 日主力累计 + 五档结构（超大/大/中/小）横向 bar（照抄 `IndustryFlowDrawer` L832-861 骨架）+ 量价同向性判定文案。
 6. **成分股抽屉**：`sectorsApi.members(code)` 列表 + `in_kline_cache` 标注 + 「加入自选」按钮（走现成 `api.addWatchlist`——成分股是股票，接 watchlist 完全合法）。
- **CSS**：几乎全复用（`fund-table/event-table/macro-chip/ColorBadge/drawer-*/btn/legend` 均已存在）；新原子（`dim` 级别弱化、RS 变化箭头、RRG 容器）追加在 `styles.css` L2512 后新段 `/* ---- 行业板块趋势工作台 ---- */`。

### P3.5 验收

```bash
cd web && npx tsc --noEmit && npm run build   # 零错误
```
- 手工验收：/sectors 打开无报错；RRG 点点开抽屉；主表排序/搜索/父子去重开关；★ 自选刷新后仍在；FundamentalsPage 视觉零变化。

---

## P4 · launchd 接线 + 运维

- 新 `scripts/com.lei.sector.trend.plist`：照抄 `com.lei.ashare.ma.plist`，Label=`com.lei.sector.trend`，**StartCalendarInterval 周一~五 16:45**（错开 16:30 的腾讯任务），日志 `logs/precompute_sector_trend.{out,err}.log`。
- `install_app_autostart.sh` 末尾加一行 `install_agent com.lei.sector.trend ...`；`biao-ctl.sh` 的 label 变量列表同步加。
- `运维手册.md` 追加一节：任务链（16:30 全A宽度/日K 维护 → 16:45 板块趋势）、故障排查（快照 date 停更、成分股拉取失败重跑 `--force`）、回补说明（首次运行无 RS 排名变化=留痕中属正常）。

---

## 交付顺序与提交节奏

```
P0.1 → P0.2 → 跑通全A宽度回归 → commit "fix(breadth): 代码 universe 补科创板"
P1.1 fetch_sector_members + 层级/去重纯函数 → 单测 → commit
P1.1 指数/RS/宽度/趋势读出纯函数 → 单测 → commit
P1.1 落盘 + CLI + 实跑落盘验证 → commit
P2 API + 单测 → commit
P3.1 抽共享件（零行为变化）→ commit
P3.2-3.4 页面 → tsc/build → commit
P4 launchd + 运维手册 → commit
```

## 验收门禁（全部满足才算交付）

1. `pytest tests/unit/test_sector_trend.py tests/unit/test_sectors_api.py tests/unit/test_fundamentals.py tests/unit/test_market_breadth.py -q` 全绿（P0 回归含在内）。
2. `cd web && npx tsc --noEmit && npm run build` 零错误。
3. 实跑 `precompute_sector_trend.py` 落盘成功：457 板块去重后无重复行、无"父子同榜"（同产业链只出最高层）。
4. 抽 2 个板块人工核对：稀土 BK1626 idx≈2275.76 / RS20 ≈ +10.79%（2026-08-14 口径【实测】），玻纤制造 BK1462 idx≈3993.21 / RS20 ≈ −1.51%。
5. 红线 2/3/5：页面 grep 不到「买入/卖出/加仓/减仓/抄底」；MACD 必与三色+斜率同屏；口径声明条常驻。
6. FundamentalsPage 视觉与行为零变化（P3.1 纯重构）。

## 不做（本期）

- PE 历史分位（只留痕）；板块市值加权指数；历史成分还原（不可得）；北交所（无数据源）；事件流/状态机跑板块（语义无效）；板块自选接 watchlist（providers 拉不到板块日K）；`precompute_a_share_ma` 串行改并发（另一个话题）。
