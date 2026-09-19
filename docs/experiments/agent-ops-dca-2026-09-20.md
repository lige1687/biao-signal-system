# 每日操作清单补定投状态位（GPT ITERATION:14 选点 A）——S1 接入与验证

- 日期：2026-09-20（任务派发 2026-09-19，报告按派发简报落 20260920）
- 阶段：S1（冻结目标 G1：dca 状态块接入每日操作清单，降级真实，既有块零影响）
- 分支：`codex/agent-runtime-adoption-20260917`（HEAD 7f8b0855 起步）
- 执行：ZCode 受派代理（只动本工作区；运行仓/sync 仓未触碰）

## 一句话结论（大白话）

**每天那份「今日操作清单」里，现在会多出一小格「定投状态」：它会如实显示
11 个跟踪标的当前处于什么状态（比如有没有跌进深超跌区）、中美市场宽度读数
是否可读；哪块数据读不到就明说哪块不可用，绝不编一个数出来。这次只是把
已经算好的状态搬到你每天必看的清单上（纯展示、纯只读），定投本身怎么算、
怎么下单，一律没动。**

## 0. 测的是什么、对用户意味着什么

- **测的是什么**：给 `build_ops_today`（每日操作清单的组装函数，网页
  `/ops` 页和每日推送共用同一份数据）新增一个「定投状态」区块。数据来自
  仓库里已有的定投只读服务，本阶段做的是「接线 + 如实降级」，不是新算
  任何东西。
- **结果是什么**：三态测试（有数据 / 证据账本缺失 / 宽度数据部分缺失）
  全部按预期表现；真实数据冒烟：证据账本（版本 2026-09-08-r2）可读、
  11 个跟踪池标的状态全部算出、中美宽度读数在（发布节奏未核实所以标
  「未知」，这是服务层既有口径）；情绪面区块逐字段零变化。
- **对用户实际有什么意义**：不用再单独翻定投页，每天打开操作清单就能
  看到定投标的的状态事实；数据缺了会看到明确原因，不会看到假状态。
  前端把这一格画出来是下一阶段的事，本阶段接口已就位。

## 1. 名词一句话说明（给不含量化背景的读者）

- **定投状态**：对 11 个跟踪标的（上证指数、沪深300、创业板指、黄金ETF、
  标普500 等）各算两个条件——「深超跌」（价格比 200 日均线低 20% 以上）
  和「底部区域」（跌得深 + 全市场上涨家数占比处于低位）。条件满足/不满足/
  数据不够没法判断，三种情况分开报，不混淆。
- **证据账本**：`configs/dca_evidence.json`，存放定投规则依据的文件；
  它读不到时，所有历史战绩引用都不可用——这属于「读不到依据」，
  不是「没有结论」。
- **市场宽度**：全市场有多少比例的股票站在 200 日均线上，衡量整体环境。
- **状态位（本阶段口径）**：只搬状态事实（可用性、读数、逐标的状态），
  不写解释文案、不加任何新判断；解释和页面呈现留下阶段。

## 2. 改动清单（213 行，全部纯新增；sentiment 块零改动）

| 文件 | 改动 |
|---|---|
| `src/lei_signal/api/schemas.py` | 新增 `DcaBlockDTO`（available/reason_cn/evidence_available/evidence_version/breadth/states 六个字段）；`OpsCardDTO` 加可选字段 `dca` |
| `src/lei_signal/copilot/ops.py` | 新增 `_build_dca_block()`（只读调既有 DCA 服务，注入参数仅供单测）；`build_ops_today` 加可选参数 `dca_reader`（生产调用方零改动）并在卡片上挂 `dca` 块 |
| `tests/unit/test_copilot_ops.py` | 新增 5 个测试：三态 + 端到端接线 + 读取器故障不阻塞清单 |

- **sentiment 块零改动证明**：`git diff` 中 `_build_sentiment_block` /
  `_sentiment_signal_lines` 两个函数的既有行零增删（diff 快照见 raw）；
  新增测试用「同库同参数两次组装、情绪面逐字段相等」锁住该性质。
- **纯只读证明**：对 diff 内容 grep 写操作关键词（insert/update/delete/
  commit/save/write 等）零命中；新代码路径只调 `load_evidence`（读账本）、
  `read_breadth`（读缓存）、`targets_state`（纯计算），零下单零记账。
- **形态对齐既有先例**：与 `api/routes/agent.py` 话题块 dca 分支、
  `api/routes/copilot.py` dispatch dca 分支、`api/routes/dca.py` 状态板
  三处一致——`symbols=None` 即服务默认跟踪池，缺数据=null 与
  未触发=false 的区分留在服务层，本层不改写。

## 3. 降级语义（不编数的具体规则）

1. 证据账本缺失/损坏 → `available=false` + `reason_cn`=账本错误详情；
   逐状态仍如实输出（价格算得出的照算，窗口不够的标
   `insufficient_data`、字段 null）。
2. 宽度读数缺失 → `breadth` 对应项为 null；依赖宽度的「底部区域」
   自动变 null（无法判定），不拖累只依赖价格的「深超跌」。
3. 逐状态计算抛异常 → `available=false` + 原因；整个读取器抛异常 →
   清单照常出，dca 块缺省为 null（与情绪面同一红线：区块缺席不阻塞清单）。

## 4. 验证记录（原始输出在同名 raw 目录）

- `tests/unit/test_copilot_ops.py`：8/8 通过（3 既有 + 5 新增）。
  - 有数据：available=true、账本版本、逐状态字段（state_status=ok、
    deep20=false、bottom_zone=false）、宽度引用卡齐全。
  - 缺数据（账本不存在）：available=false、reason 含「不存在」、
    跟踪池全部 `insufficient_data`（如实空态，不编数）。
  - 部分缺失（宽度缺席）：块整体 available=true（账本可读、价格可判），
    breadth 两项 null，deep20=false（仍可判）、bottom_zone=null（不可判）。
- 全量单测对照：当前树与干净树（HEAD 7f8b0855，改动 stash 后复跑）
  失败集合完全一致（14 failed / 13 passed / 8 errors，集中在 factor 契约
  指纹、write_tx_tracking、newsfeed push 等域）——全部为存量问题，
  与本次改动无关；ops 相关测试零破坏。
- 真实数据冒烟（临时 DB + 默认读取器，真实数据只读不写）：available=true、
  账本 2026-09-08-r2、11 标的状态齐、宽度 health=unknown（发布节奏未核实，
  服务层既有口径）、push_summary 文本不变。
- 真实数据禁碰：所有测试用 tmp_path 临时账本 + 构造行情/宽度注入；
  运行仓真实数据零写入。

## 5. 限制与边界

- **口径**：本阶段交付=状态位接入；不是「定投功能完成」，不含前端渲染、
  不含推送文案变化（push_summary 本次未动）、不含任何新判断或解释文案。
- web 端 `OpsCard` 类型与 `/ops` 页尚未消费 `dca` 字段（多出的 JSON 字段
  对现有页面无影响），渲染留下阶段。
- `dca_reader` 注入参数仅供单测；生产调用方（`/api/copilot/ops/today` 与
  `scripts/copilot_daily.py`）签名向后兼容，零改动。
- 全量单测存量失败清单（与本次无关）已留档 raw，供主控独立复核。

## 6. 复现路径

```bash
# 单测（三态 + 既有回归）
python3 -m pytest tests/unit/test_copilot_ops.py -v
# 生产默认路径冒烟（临时 DB，真实数据只读）
PYTHONPATH=src python3 - <<'EOF'
from lei_signal.copilot import ops
from lei_signal.storage.sqlite_store import connect
from lei_signal.api.opportunity_scan import today_date
import tempfile, os
conn = connect(os.path.join(tempfile.mkdtemp(), "s.db"))
card = ops.build_ops_today(conn, run_date=today_date(), recommend_card=None)
print(card.dca.available, len(card.dca.states), card.dca.evidence_version)
EOF
# diff 范围与只读性
git diff --stat
git diff src/lei_signal/copilot/ops.py | grep -iE "insert|update |delete|commit|save|write"  # 应零命中
```
