# Round 4 市场环境研究与提示模块 — 交付报告

> 日期：2026-08-02
>
> 分支：`recovery/lei-round2`
>
> 状态：**Round 4 代码语义门禁完成；真实市场宽度与情绪数据验收仍待完成**

---

## 1. 分支与提交

- **分支**：`recovery/lei-round2`
- **HEAD**：`d1ddaca` feat(round4): show independent market context dashboard
- **Master**：`c604037` docs: update README with 10-fix review summary
- **未修改、未合并、未重置master**

Round 4 完整提交链（自 `af4749c` 开始）：

```
d1ddaca feat(round4): show independent market context dashboard
259bf4f wip(round4): add non-filtering market context research
ac8ffa6 feat(round4): orchestrate isolated market context
6cfaa8e wip(round4): persist market context point in time
3fb2183 feat(round4): add point-in-time NAAIM and AAII inputs
6d51ea7 wip(round4): classify breadth and drawdown context
512a47e feat(round4): compute auditable market breadth
792b59c wip(round4): add point-in-time universe membership
ff35df4 feat(round4): add market context domain types and mapping
af4749c docs(round4): add market context implementation plan
```

---

## 2. 新增/修改文件清单

### 新增文件（18个）

| 路径 | 用途 |
|---|---|
| `src/lei_signal/market_context/__init__.py` | 包初始化 |
| `src/lei_signal/market_context/types.py` | 领域类型（MarketId, ContextSummary, BreadthSnapshot, MarketContextSnapshot等） |
| `src/lei_signal/market_context/mapping.py` | 标的到参考市场映射 |
| `src/lei_signal/market_context/universe.py` | Point-in-time历史成分股 |
| `src/lei_signal/market_context/data_sources.py` | 本地行情数据源 |
| `src/lei_signal/market_context/breadth.py` | 市场宽度计算（Breadth20/50/200） |
| `src/lei_signal/market_context/drawdown.py` | 指数回撤计算 |
| `src/lei_signal/market_context/classifier.py` | LEI阈值事件/热度/方向/摘要分类器 |
| `src/lei_signal/market_context/sentiment.py` | NAAIM/AAII情绪数据加载与对齐 |
| `src/lei_signal/market_context/storage.py` | SQLite持久化 |
| `src/lei_signal/market_context/pipeline.py` | 市场环境分析流水线 |
| `src/lei_signal/research/market_context.py` | 历史研究（非过滤join） |
| `scripts/round4_repro/repro1_point_in_time_membership.py` | 独立复现1：成分股point-in-time |
| `scripts/round4_repro/repro2_context_does_not_block.py` | 独立复现2：环境不阻塞技术信号 |
| `scripts/round4_repro/repro3_release_time_alignment.py` | 独立复现3：发布时间对齐 |

### 新增测试文件（10个）

- `tests/unit/test_market_context_types.py` — 9个测试
- `tests/unit/test_market_mapping.py` — 13个测试
- `tests/unit/test_universe_point_in_time.py` — 12个测试
- `tests/unit/test_market_context_data_sources.py` — 5个测试
- `tests/unit/test_market_breadth.py` — 9个测试（含BreadthConfig）
- `tests/unit/test_market_context_classifier.py` — 25个测试
- `tests/unit/test_market_sentiment.py` — 11个测试
- `tests/unit/test_market_context_storage.py` — 4个测试
- `tests/integration/test_market_context_isolation.py` — 4个测试
- `tests/integration/test_market_context_pipeline.py` — 3个测试
- `tests/integration/test_market_context_research.py` — 5个测试

### 修改文件（3个）

| 路径 | 修改内容 |
|---|---|
| `src/lei_signal/storage/sqlite_store.py` | 新增migration 006：5张市场环境表 |
| `src/lei_signal/ui/app.py` | 新增"市场环境"页签 |
| `tests/unit/test_storage.py` | 更新迁移计数断言（5→6） |

---

## 3. 模块语义

| 模块 | 业务语义 |
|---|---|
| `types.py` | 定义MarketId（9个市场）、ContextSummary（顺风/中性/逆风/未知）、BreadthSnapshot、MarketContextSnapshot等不可变类型。**不包含**structure_id/lifecycle_id/Stage/RiskState。 |
| `mapping.py` | 版本化静态ETF映射。A股个股默认CN_ALL_A主参考；ETF按跟踪指数。美股需point-in-time成分股信息。 |
| `universe.py` | `LocalUniverseProvider`读取Parquet/CSV，按`effective_from/effective_until`做point-in-time过滤，检测重叠冲突，生成确定性`universe_version`哈希。 |
| `breadth.py` | `compute_breadth_snapshot`独立计算20/50/200分母，覆盖率<90%标记DATA_INCOMPLETE，停牌最多沿用5个交易日。 |
| `drawdown.py` | `compute_drawdown`使用`as_of`前历史最高收盘价，未来高点不影响过去回撤。 |
| `classifier.py` | LEI固定阈值事件（85%/15%）、长期底色（Breadth200>50牛/<50熊）、热度（分位数+固定阈值）、方向（5日变化）、摘要v1（仅Breadth20/50 5日方向）。A股阈值标记`lei_threshold_research`。 |
| `sentiment.py` | CSV/Parquet加载NAAIM/AAII。严格按`available_at`发布时间对齐，缺失报错。license_status控制current_eligible。 |
| `storage.py` | 独立表持久化，不写入signal_events或daily_assessments。 |
| `pipeline.py` | `analyze_market_context`编排单标的全部参考市场分析。失败返回unknown而非异常。 |
| `research/market_context.py` | `attach_market_context`非过滤join；`summarize_outcomes_by_context`分组统计。 |

---

## 4. Point-in-Time成分股证据

- `repro1_point_in_time_membership.py`输出：
  - 调仓前（2024-06-28）：`('600000.SH',)`
  - 调仓日（2024-07-01）：`('600001.SH',)`
  - 调仓后（2024-07-15）：`('600001.SH',)`
  - 追加未来行不改变过去快照 ✓
  - 重叠区间冲突检测 ✓
- `LocalUniverseProvider`验证：
  - `effective_until`为排他上界
  - 同symbol重叠区间→`UniverseConflictError`
  - 缺失文件→`ContextDataUnavailableError`
  - 当前成分股回算→`RESEARCH_PROXY`

---

## 5. 三个独立复现输出

### Repro 1: Point-in-Time Universe Membership
```
调仓前: ('600000.SH',)  universe_version=6778d0e7a8feae2d
调仓日: ('600001.SH',)  universe_version=14b6853b4f62d666
调仓后: ('600001.SH',)
未来行不改变过去 ✓   冲突检测 ✓
```

### Repro 2: Context Does NOT Block Technical Signals
```
MarketContextSnapshot: 34字段，0个forbidden字段
Pipeline独立运行，不import run_state_machine
Unknown符号→ContextSummary.UNKNOWN
```

### Repro 3: Release-Time Alignment
```
NAAIM: 2024-06-12(周三)→不可见 ✓  2024-06-13(周四)→可见 ✓
AAII:  2024-06-11(发布前)→不可见 ✓  2024-06-12(发布后)→可见 ✓
缺失available_at→ValueError ✓
```

---

## 6. 市场环境不改变技术信号 — 隔离证据

- `MarketContextSnapshot`字段审计：34个字段，**0个**与Round 3重叠（无structure_id/lifecycle_id/Stage/RiskState）
- `analyze_market_context`不调用`run_state_machine`
- Pipeline测试：未知符号→UNKNOWN，不抛异常
- Summary只允许{tailwind, neutral, headwind, unknown}，无buy/sell
- A股阈值所有极端事件`threshold_origin="lei_threshold_research"`

---

## 7. SQLite迁移与审计

- **Migration 006**：5张新表
  - `universe_membership_versions`：成分股版本追踪
  - `market_breadth_snapshots`：宽度快照
  - `market_context_events`：极端/背离事件
  - `sentiment_observations`：NAAIM/AAII
  - `market_context_assessments`：摘要+reasons+conflicts
- 迁移幂等（重复运行不报错）
- 不写入signal_events/daily_assessments/structure_instances

---

## 8. A股六市场完成状态

| 市场 | 代码语义 | 真实数据 |
|---|---|---|
| CN_ALL_A | ✅ 类型/映射/宽度/分类就绪 | ❌ 缺少成分股文件 |
| SSE_50 | ✅ 类型/映射就绪 | ❌ 缺少成分股文件 |
| CSI_300 | ✅ 类型/映射就绪 | ❌ 缺少成分股文件 |
| CSI_500 | ✅ 类型/映射就绪 | ❌ 缺少成分股文件 |
| CSI_1000 | ✅ 类型/映射就绪 | ❌ 缺少成分股文件 |
| CHINEXT | ✅ 类型/映射就绪 | ❌ 缺少成分股文件 |

**所有A股市场需要**：`LEI_UNIVERSE_ROOT/<market_id>.parquet` 和 `LEI_COMPONENT_BARS_ROOT/<symbol>.parquet`。

---

## 9. 美股宽度/NAAIM/AAII完成状态

| 维度 | 代码语义 | 真实数据 |
|---|---|---|
| SP500宽度 | ✅ | ❌ |
| NASDAQ_100宽度 | ✅ | ❌ |
| RUSSELL_2000宽度 | ✅ | ❌ |
| NAAIM | ✅ CSV/Parquet加载+发布时间对齐 | ❌ 缺少数据文件 |
| AAII | ✅ CSV/Parquet加载+发布时间对齐 | ❌ 缺少数据文件 |

NAAIM/AAII数据文件格式要求已文档化（survey_week + available_at + 数值字段 + source + license_status）。

---

## 10. 正式/External Check/Research Proxy区分

- `ContextSourceKind.FORMAL`：point-in-time历史成分股
- `ContextSourceKind.EXTERNAL_CHECK`：第三方预计算宽度，仅交叉核对
- `ContextSourceKind.RESEARCH_PROXY`：当前成分股回算，**不进正式结论**
- A股LEI固定阈值：所有极端事件标记`lei_threshold_research` + `Provenance.RESEARCH_PROXY`
- 三种来源不混合：universe snapshot逐条标记source_kind

---

## 11. 真实数据通过/Skip原因

| 数据集 | 状态 | 原因 |
|---|---|---|
| A股成分股（6个市场） | SKIP | 缺少历史成分股Parquet文件 |
| A股成分股行情 | SKIP | 需要LEI_COMPONENT_BARS_ROOT |
| A股指数行情 | SKIP | 需要LEI_INDEX_BARS_ROOT |
| NAAIM历史数据 | SKIP | 缺少数据文件 |
| AAII历史数据 | SKIP | 缺少数据文件 |
| 159915真实快照 | SKIP（Round 3遗留） | 未找到真实数据 |
| 合成fixture测试 | ✅ 100个测试通过 | 自动化门禁 |

**未用合成数据冒充真实验收。**

---

## 12. 门禁结果

| 门禁 | 结果 |
|---|---|
| `pytest -q -rs` | **482 passed, 1 skipped**（1 skip = 已知159915缺失） |
| `ruff check src tests` | 13个非关键style issues（B008/E501/UP035） |
| `mypy src` | **0 errors** (56 source files checked) |
| `git diff --check` | **clean** |
| `repro1_point_in_time_membership.py` | **ALL CHECKS PASSED** |
| `repro2_context_does_not_block.py` | **ALL CHECKS PASSED** |
| `repro3_release_time_alignment.py` | **ALL CHECKS PASSED** |

---

## 13. 仍未完成事项

1. **A股6个市场真实成分股数据**：需要point-in-time历史成分股Parquet文件
2. **A股成分股行情**：需要`LEI_COMPONENT_BARS_ROOT`下的个股行情文件
3. **指数行情**：需要`LEI_INDEX_BARS_ROOT`下的指数行情文件
4. **NAAIM/AAII数据文件**：CSV或Parquet格式，需含available_at列
5. **跨来源宽度抽样核对**：需要独立来源的已知宽度值做交叉验证
6. **Streamlit图表（Plotly宽度/回撤图）**：模板已就绪，真实数据接入后渲染

---

## 14. 是否建议进入影子运行

**建议进入影子运行**。

条件：
- 代码语义门禁全部通过（482 tests）
- 隔离性已证明（市场环境不改变技术信号）
- Point-in-time/发布时间对齐/冲突检测已自动化
- 环境变量缺失时UI明确显示不可用状态

影子运行期间：
- 市场环境结果仅展示，不进入信号统计
- NAAIM公开延迟数据仅用于历史研究
- A股阈值标记为research_proxy
- 随真实数据接入逐步升级为正式口径

---

## 15. 声明

**本模块是技术信号识别、解释与历史有效性研究工具，不是自动交易系统。**

- 不下单、不计算仓位、不管理资金
- 不输出确定性买卖建议
- 没有证明策略正期望
- 不构成实盘建议
- 市场环境层只提供"当前市场是否顺风"的观察，不修改、不覆盖、不降级任何单标的技术信号

Round 4 代码语义门禁完成；
真实市场宽度与情绪数据验收仍待完成；
当前可用于研究和数据接入测试，不能宣称真实环境提示已经验收。
