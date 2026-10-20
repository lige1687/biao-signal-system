# input-qualification — 沪深300宽度历史输入资格盘点（只读）

日期：2026-09-17。执行：GLM-5.3-Flash（ZCode 委派 round 1）。本轮只做本地读取与结构统计，
未重算任何宽度/状态/目标/收益，未联网。

## 一句话结论（大白话）

「宽度」= 一个指数的成分股里，有多少比例的股票价格站在自己的均线之上。本轮查清：
沪深300宽度有一条**用历史当天名单（不是拿今天的名单倒推过去）**构建的冻结序列，
2015-02-09 到 2026-06-30 之间约 85% 的交易日有合格数值，做「事后历史描述」基本够用；
但它是用**当前还上市的股票的前复权价格**算的（漏掉已退市老股票、协议里写的"后复权"
和实际不符），而且没有任何证据能证明"历史上每一天当时就能拿到这些数据"——所以
「当时可知的预测研究」资格**未核验**，不能直接开算。

## 1. 输入清单与哈希绑定

被审计的冻结实验：`docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/`
（2026-09-09 冻结，protocol.md 状态 FROZEN；registry 登记
`etf-breadth-source-and-confirmation-backtest-2026-09-09.md`）。

全部输入以 `prepared/input_fingerprints.json`（本身被 definitions.v1.json 钉哈希
`be140f67…`，实测匹配）绑定；本轮 2026-09-17 实测 **12 项全部存在且哈希全部匹配**：

| 输入 | 用途 | 实测 |
|---|---|---|
| `~/.lei_signal_lab/cache/a_share_klines_full.parquet`（49,432,584 B） | 沪深300与全A宽度的**价格底表** | ✓ 匹配 |
| first12 `actions.json` / `dated-restrictions.json` / 两 ETF nominal bars | 同实验 ETF 交易腿（与宽度序列无直接关系） | ✓ 匹配 |
| `prepared/breadth_csi300.parquet` | 冻结沪深300宽度序列（研究对象） | ✓ |
| `prepared/breadth_all_a.parquet` | 全A对照序列 | ✓ |
| `prepared/csi300_membership_daily.parquet` | 沪深300逐日名单（registry `csi_members`） | ✓ |
| `prepared/csi300_membership_probe_audit.json` | 名单探测审计 | ✓ |
| `prepared/chinext_*` 3 件 | 创业板链（C 档断链留证） | ✓ |
| `prepared/data_quality.json` | 质量自评（未被指纹清单钉住，实测 `f9b3b788…`） | 已记录 |

## 2. 成员名单资格（csi300 链）

- **来源与构建方式**：`prepare_data.py:231-291`。对 baostock
  `query_hs300_stocks(历史日期)` 在**历史日期上逐日查询**（不是拿当前名单倒算），
  20 个交易日间隔先探测、命中变化区间后二分定位首个生效日，共 272 次查询。
- **产物**：`csi300_membership_daily.parquet` = 843,900 行 = 2,813 个交易日 × 300 只整
  （每天恰好 300 只），2014-12-01 → 2026-06-30，累计 **682 个不同代码**（>300，
  直接证明含历史退出成员），31 个名单版本，无重复 (date,symbol) 键、无空值。
- **生效时间**：探测到的 30 个名单变更日全部落在 semi-annual 调整窗口附近
  （如 2016-06-13、2016-12-12、…、2026-06-15，全表见 probe audit）。
  变更在探测到的首个交易日整体切换，**名单内不保存公告日**——协议要求
  「公告日与生效日分别保存」，csi300 链只落实了生效日；`prepared/sources/` 的
  33 份中证指数公告原件是**创业板链**的证据，未逐条核对到 csi300 生效日。
- **已知盲区（audit 文件自带）**：若成分在同一个 20 日探测区间内"离开又回来"，
  端点比较检测不到——盲区存在但规模未知。
- **未知（保持未知）**：baostock 该接口返回的是"查询当日视角的名单"还是"事后修订
  过的名单"，无供应商认证；本轮未联网验证。

## 3. 日历

- 宽度序列的日期轴 = **510300 ETF 自己的交易日**（`prepare_data.py` main:
  `d300 = etf_dates("510300")`），不是交易所通用日历。ETF 长期停牌日会缺宽度观测
  （未逐一核对 510300 是否有停牌日，影响未知、预期极小）。
- 成员表与宽度序列同为 2,813 行，日期范围一致。

## 4. 价格数据资格（本轮最重要的发现）

**冻结的沪深300宽度序列是用「当前存续个股的前复权价格」算的**，证据链：

1. `prepare_data.py` main()（L341-351）：`panel = pd.read_parquet(ALL_A_PANEL)`，
   注释原话 "Reuse the already-audited long-history panel. **It is a current-list
   backfill**, so missing old constituents lower coverage and keep the result at
   grade B"；随后 `breadth_from_close_panel(panel…, csi300_membership)`。
2. `ALL_A_PANEL = ~/.lei_signal_lab/cache/a_share_klines_full.parquet`（L32），
   由 `scripts/backfill_breadth_full.py:88` 用 **`ak.stock_zh_a_daily(adjust="qfq")`
   （新浪源，前复权）** 构建。
3. `fetch_constituent_prices`（baostock 后复权，L294-305）在 main() 中**无任何调用**
   ——死代码。
4. 因此 protocol.md 的声明「指数逐股行情使用后复权连续价格」与实现**不符**：
   实际是前复权 + 当前存续回填。

**影响分层（如实区分，不夸大也不掩盖）**：

- 对"P 是否高于自身均线"这种**同日比值型比较**：前复权的整体回溯缩放对分子分母
  同乘同因子，P>SMA 判定不变——`verify_research_definitions.py` 的 breadth-scale
  检查正是这个不变性的形式化。因此该口径差异对宽度水平值的机理影响有限。
- 但两点是真实缺陷，不因不变性消失：
  ① **退市成员缺价**：已退市的历史成分不在底表中 → 计入当日名单总数（pool_total）
  却永远不合格 → 拉低覆盖率、缩窄 E200。名单是历史名单（682 只），价格是存续回填
  ——**分子分母的股票集合并不是同一套数据底表**。早年（2015 前后）影响最大：
  data_quality 实测 csi300 最低覆盖率 0.64、valid 率 2,378/2,813≈84.5%。
  ② **前复权底表不可当"当时价格"**：绝对价位、以及未来若复用该底表算价格类因子，
  会被"以今天为锚的回溯调整"污染。qfq 锚定抓取日（约 2026-08 前后重拉过），
  早于锚点的历史价格与当时真实价格不同。
- protocol/profile 声称"后复权连续价"（definitions.v1.json profiles.breadth
  price_basis 同样写"冻结后复权连续价"）——**设计声明与实现不一致**，本轮不改代码、
  不改登记表，提请主控裁定：是补数据重算，还是把声明修正为实际口径并评估影响。

## 5. 缺失、停牌、退市、公司行动

- 引擎层（`research_engine.py:16-62` + `_valid_quote_sma`）：缺失=显式 NaN，不前向
  填充；停牌日若无报价行即当日不合格；SMA 只用有效报价滚动（跳过 NaN，不补）；
  新股不足 200 个有效收盘不合格；当日合格集 E200 为空或覆盖 <0.90 → 当日宽度为
  缺失值并带原因（绝不把缺失当 0 或当弱）。
- 数据层：停牌日面板里到底是"缺行"还是"带标记行"未逐日核验（`fetch_constituent_prices`
  的 tradestatus 字段属死代码路径，实际底表是 akshare 新浪 qfq，其停牌呈现未知）。
- 公司行动：经前复权吸收（见 §4 机理讨论）；分红造成的价格跳跃对"是否高于均线"
  的影响被复权平滑，但供应商复权实现本身未独立复核。

## 6. 时间证据（观测/抓取/当时可得）

- **观测时间**：日收盘（profile.breadth.time：t 收盘观测，Asia/Shanghai）。
- **抓取时间**：2026-09-09 当天（文件 mtime 18:00-18:16 佐证；probe audit 记录
  272 次查询发生于一轮运行内）。
- **当时可得时间（available_at）**：**无任何证据**。verify 脚本生成的 manifest
  明文 `historical_available_at: "unknown: sources do not certify vendor arrival
  timestamps"`。历史每一天的名单/价格当时何时可得，供应商不认证，本轮也不伪造。
- 结论：该序列自带的资格证据只支持"2026-09-09 用历史查询视角重建"，不支持
  "历史上当时可知"。

## 7. 已知缺口（按集合与日期区间，不编统一合格起点）

| 集合 | 区间 | 缺口 |
|---|---|---|
| csi300 冻结序列 | 2014-12-01→2015-02-06 | 预热 + 覆盖不足，全缺（first_valid 2015-02-09） |
| csi300 冻结序列 | 2015 全年及早年 | 覆盖率最低 0.64（退市缺价+新股不足 200 日），中位数 0.9633；435/2,813 天无值 |
| csi300 冻结序列 | 2026-06-30 之后 | 序列止于 2026-06-30，**未维护到现在**；续到当下需新数据获取（本轮禁止） |
| 名单链 | 全期 | 20 日探测盲区（区间内进出往返）；公告日未保存 |
| 创业板 | 2017-10-09 | 链断（300075 不可逆），C 档，0 有效行——不得并入研究 |
| timing 展示线 | 1990→2026-08-18 | 当前成分倒算、生产脚本不在仓库、未登记——只能展示，不能研究 |
| 全A（两条线） | 各自全期 | 当前存续回算，早年幸存者偏差（协议预定 B 档） |

## 8. 三类用途分别裁定

| 用途 | 裁定 | 依据 |
|---|---|---|
| 仅展示（当前状态叙事） | **受限**：csi300 冻结序列止于 2026-06-30，不能冒充当下；当下展示实际由全A JSON 线承担（2021-06-17→2026-09-16） | `breadth_csi300.parquet` date_max；`a_share_ma_breadth_history.json` 结构统计 |
| 事后历史描述（retrospective description） | **证据支持（B 档，带缺口清单）**：历史名单+共同分母+显式缺失处理齐备，2,378 个有效日；限制=§4 价格底表缺陷、§7 区间缺口、探测盲区 | §2-§5 全部证据；data_quality.json 自评 B 档；protocol 预定等级一致 |
| 当时可知的预测研究（point-in-time predictive） | **未核验（不得默认可用）**：无到达时间证据；baostock 历史名单视角未经当时公告逐条核对；价格底表是后视锚定。三项都补齐前，只能做"假设当时可知"的描述性研究并如实标注 | §6；verify manifest `historical_available_at: unknown` |

生产在用 ≠ 研究合格：timing 展示线在生产页面挂着，但未登记、生产脚本不明，
研究资格为零。反之，csi300 冻结序列未进生产，却已有最强的研究底子。

## 9. 与相邻对象的辨认边界（防误用）

- **全A/创业板**：仅作辨认说明，不另开审计线。创业板 C 档断链留证；
  全A为对照与展示。若任何研究把全A序列、timing 缓存序列或生产 JSON 当作
  `breadth.csi300.*` 的实现或数据，均属误用（同名不同物的完整对照见
  definition-implementation-map.csv 补充线 1-3）。
- **三档分档（43.3/56.7 百分数 = 0.433/0.567 比例）**：已登记于
  `breadth.three_tier@1.0.0` 与冻结回测；`configs/rules.v1.yaml` 中**没有**任何
  宽度条目——宽度阈值不在规则账本内，动阈值不属于本轮也不属于任何未授权任务。
