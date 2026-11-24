# 任务运行台账诊断表（W1-S1，2026-09-19）

> 目的（大白话）：给每个自动定时任务建一本"运行流水账"——它什么时候跑的、
> 跑了多久、成没成功、用的是哪天的数据、结果写到了哪里。现在这些任务大多
> 只把日志扔在临时目录里，机器一重启就没了，任务悄悄失败也没人知道。

## 一句话结论（大白话）

19 个定时任务全部逐个查完：大多数任务的日志写在机器重启就丢的临时目录里，
而且"怎么算成功"全靠进程退出码（退出码 0 = 成功），没有统一的地方记录
"这次运行用了哪天的数据、结果写到了哪"。本阶段交付了一个独立的"台账小本"
模块（`src/lei_signal/jobledger/`）和一个命令包装器，先在不影响任何在办
改动的 3 个任务上做好了接线准备（只准备好方案，没有实际启用）。

## 记录字段规范（台账每行写什么）

| 字段 | 含义（大白话） |
|---|---|
| operation_id | 这次运行的唯一编号，防重复、可追溯 |
| operation_type | 怎么触发的（launchd_job=定时任务 / manual=手动 / test=测试） |
| started_at / finished_at | 开始/结束时间（带时区，精确到毫秒） |
| status | success=成功 / failed=失败 / partial=部分完成 |
| input_basis | 用的数据截至哪天哪个时点（如 close:2026-09-18） |
| output_reference | 结果写到了哪张表或哪个文件 |
| error_class | 失败原因归类（none=没失败 / exit_1=脚本异常退出 / killed_by_signal:SIGTERM=被杀） |
| job_name | 任务名（launchd 里的 label，如 com.lei.daily_scan） |

台账文件：仓库 `logs/job-ledger.jsonl`（`logs/` 已在 .gitignore，只追加不改写，
绝不写 `~/.lei_signal_lab/` 生产目录——代码里有红线检查）。

## 诊断表（19/19，全部来自实际读 plist 与脚本）

说明：**成功语义**指"怎么判定这次跑成功了"；**输入截止**指数据用到哪个时点；
**在办线**指该任务直接调用的脚本/模块当前正被另一条工作线修改（git Modified），
本轮不做接线试点。

### 常驻服务（3 个，KeepAlive，无排程）

| # | 任务 (Label) | 入口 | 排程 | 成功语义 | 输入截止 | 输出产物 | 在办线 |
|---|---|---|---|---|---|---|---|
| 1 | com.lei.backend | `python -m uvicorn lei_signal.api.app:app --port 8000` | 常驻 | 进程存活（KeepAlive 拉起即视为服务在）；崩溃看 logs/backend.err.log | 实时请求 | 不落盘（内存 API） | 是（app.py/routes 在办） |
| 2 | com.lei.frontend | `node web/node_modules/.bin/vite` | 常驻 | 进程存活 | — | 不落盘 | 是（web/ 大量在办） |
| 3 | com.lei.caffeinate | `/usr/bin/caffeinate -ims` | 常驻 | 进程存活（防睡眠） | — | 无 | 否 |

### 收盘后流水（11 个）

| # | 任务 | 入口 | 排程 | 成功语义 | 输入截止 | 输出产物 | 在办线 |
|---|---|---|---|---|---|---|---|
| 4 | com.lei.intraday | `scripts/intraday_check.py` | 交易日 14:45 | 退出码 0；有 actionable 才推送（腾讯 14:45 盘中价），只读判定 | 当日 14:45 盘中价（虚拟今日 bar） | 飞书/macOS 通知，不写业务表 | 部分（依赖 storage/sqlite_store 在办改动，脚本本身未改） |
| 5 | com.lei.watch_check | `scripts/watch_check.py` | 交易日 14:46 | 退出码 0；打印 active/触发/跳过统计 | 当日 14:45 盘中价 | 表 watch_subscriptions（triggered_* 字段） | 部分（同上 sqlite_store） |
| 6 | com.lei.daily_scan | `scripts/daily_scan.py` | 交易日 15:00 | 退出码 0（V8 teardown 用 os._exit(0)）；打印 scanned/actionable 统计 | 当日收盘价（15:00 后触发） | 表 daily_opportunity_scan（整体重写当日行） | 部分（同上 sqlite_store；试点候选，见下） |
| 7 | com.lei.supervisor | `scripts/daily_nag.py` | 交易日 15:30 | 退出码 0；催办节拍绑 last_bar_date 前进，DATA_STALE 不催 | 实时行情，失败回退 fixture 并标 DATA_STALE | 表 trade_plans 待办/催办 + 飞书/macOS 通知 | 部分（依赖 plans/copilot 模块在办） |
| 8 | com.lei.copilot.daily | `scripts/copilot_daily.py` | 每日 16:10 | 退出码 0；推荐落库+EXIT/actionable 才推送 | 当日收盘（复用 15:00 扫描结果） | 表 recommendation_journal、trade_reviews、ops 清单 + 通知 | **是**（copilot/* 全在办） |
| 9 | com.lei.ashare.ma | `scripts/precompute_a_share_ma.py` | 交易日 16:30 | 退出码 0；同交易日已算过自动跳过（幂等） | 当日全 A 收盘（腾讯日 K 增量） | `{LEI_CACHE_ROOT}/a_share_ma_breadth.json`（默认 `~/.lei_signal_lab/cache/`，下同）+ history.json + klines.parquet | 否（试点候选） |
| 10 | com.lei.daily.brief | `scripts/precompute_daily_brief.py --slot auto` | 交易日 14:45 与 16:45 各一次 | 退出码 0；按槽位原子写 JSON，LLM 失败模板降级 | 14:45=盘中预判 / 16:45=当日收盘 | `{LEI_CACHE_ROOT}/daily_brief/YYYY-MM-DD.json` 对应槽位 | 是（依赖 market_context/fundamentals/plans.llm 在办模块） |
| 11 | com.lei.sector.trend | `scripts/precompute_sector_trend.py` | 交易日 16:45 | 退出码 0；打印"✓ 已落盘"三份 json | 当日收盘 | `{LEI_CACHE_ROOT}/sector_trend_snapshot.json` + history + members | **是**（脚本本身在办 Modified） |
| 12 | com.lei.timing.daily | `bash scripts/timing_daily.sh` | 交易日 17:30 | **三步链任一步失败不阻断**、最终 exit 0 便于 launchd 观测（成功语义最弱的一个） | 16:30 MA 预计算 + 当日新浪/东财行情 | `~/.lei_signal_lab/cache/a_share_klines_full.parquet`、breadth_*.parquet、`~/.lei_signal_lab/timing_scorecard/scorecard.jsonl`+latest.json | 否（试点候选） |
| 13 | com.lei.paper.daily | `scripts/paper_account.py` | 交易日 18:00 | 退出码 0；生成当日简报 | 当日扫描结果（live 管线） | `~/.lei_signal_lab/paper/account.json` + `paper/brief_*.md` | 否 |
| 14 | com.lei.module.e.weekly | `scripts/check_module_e_signals.py` | 周五 18:10 | SP500 宽度缺数据时 return 1，否则 0；控制台+文件双输出 | lab.db SP500 宽度快照 as_of（回填滞后如实标注天数） | `~/.lei_signal_lab/paper/module_e_check_YYYY-MM-DD.md` | 否 |
| 15 | com.lei.portfolio.funds | `scripts/update_portfolio_funds.py --only nav` | 每日 20:05 | 退出码 0；净值未出沿用上次值（幂等） | 当日晚间国内基金净值（QDII T+1~T+2） | lab.db 持仓市值/收益字段 | 否 |

### 周末/每周与其余（3 个）

| # | 任务 | 入口 | 排程 | 成功语义 | 输入截止 | 输出产物 | 在办线 |
|---|---|---|---|---|---|---|---|
| 16 | com.lei.sentiment.weekly | `scripts/fetch_sentiment_weekly.py` | 周四 17:05、周五 10:05 | 单序列失败跳过，**两序列都失败才非零**（→ 对应 status=partial 的典型场景） | NAAIM 实时 / AAII 最新一期调查（survey_week 去重幂等） | `data/sentiment/`（LEI_SENTIMENT_ROOT） | 否 |
| 17 | com.lei.copilot.weekly | `scripts/copilot_weekly.py` | 周日 20:00 | 退出码 0；周复盘落库+推送 | 上一完整 ISO 周 | 表 trade_reviews + 飞书/macOS 通知 | **是**（copilot 在办） |
| 18 | com.lei.newsfeed | `scripts/precompute_newsfeed.py` | 每日 20:30 | **退出码 0 = ok 或 partial（部分源失败不致命）；1 = 全部源失败**（脚本自己已区分 partial） | 当日资讯抓取水位（增量） | lab.db newsfeed 表 + 今日整合简报 | 是（依赖 plans/llm.py 在办） |
| 19 | com.lei.signal.scan | `scripts/signal_scan.py` | 交易日 11:35 / 14:45 / 15:05 | 退出码 0（os._exit(0)）；as_of 按触发时刻自动定（≥15 点=close） | 11:35/14:45=盘中价，15:05=当日收盘 | 买点→daily_opportunity_scan；卖点/数据不可用→signal_alerts | 部分（依赖 sqlite_store 在办） |

### 诊断要点

1. **日志易失**：copilot.daily/weekly 写 `/tmp/lei-copilot-*.log`；其余多数写
   仓库 `logs/` 或 `scripts/logs/`（可保留，但无结构、无成败字段）。
2. **成功语义三种口径**：纯退出码（多数）；timing.daily 三步链"失败也 exit 0"
   （最弱，只能靠台账补）；newsfeed/sentiment 自带 partial 概念（与台账
   status=partial 天然对齐）。
3. **输入截止基本未显式记录**：as_of 逻辑散在各脚本内（signal_scan 按时刻、
   module_e 按快照 as_of、paper 按 T+N），接线时在 `--input-basis` 里人工声明。
4. 在办线任务（copilot.daily/weekly、sector.trend、daily.brief、newsfeed、
   backend/frontend）本轮**只进诊断表，不接线**。

## 口径修正与盲区声明（2026-09-20 补，GPT 第 20 轮终审条件）

### 证据分层：进程结果 ≠ 业务结果 ≠ 输入产物

| 层 | 是什么 | 大白话 | 不能当什么用 |
|---|---|---|---|
| 进程结果 | 退出码 / 致命信号（台账记的 status/error_class） | 这个程序进程本身跑完没有、怎么结束的 | 不能等同"业务做成了"：退出码 0 只代表进程正常结束 |
| 业务结果 | 任务内部各步骤的成败证据 | 里面每一步（取数、算信号、写表）各自成没成 | 台账**没有**步骤级证据时就是"未知"，不得用退出码 0 补成完整成功 |
| 输入产物证据 | input_basis / output_reference 指向的数据本身 | 事后去查表/文件，看数据真的在不在、新不新 | 只能证明"有产物"，推不出"全部步骤成功" |

推论：台账是**进程层**的流水账。业务层结论要么看任务自己的输出
（日志/表），要么等后续阶段给任务加步骤级记录；现阶段对只有退出码证据的
任务，只能说"进程正常结束"，不说"任务成功"。

### timing.daily 步骤事实的归属口径

诊断表里 timing.daily 一行写的"实际执行了哪些步骤"（如重算宽度、写表），
属于**执行结果扩展**信息——它描述"这次运行干了什么"，不是"这次运行
凭什么数据干活"。因此这类步骤事实**不进 input_basis 字段**：
input_basis 只写输入截止说明（数据截至哪天哪个时点），两者混写会让
"用了什么数据"没法单独审计。步骤事实留在诊断表文字与未来扩展字段里。

### SIGKILL 盲区声明（不得承诺所有中断都有终态行）

SIGKILL 无法被捕获。若包装器进程本身被 SIGKILL 杀死（而不是它包装的
子进程），包装器没有机会写终态行——此时台账表现为"有这次运行的开始
上下文但无终态"，正确读法是**未完成/未知**，不是"成功"也不是"失败"。
本包装器只承诺：子进程被信号杀死、或包装器收到可捕获信号（SIGTERM/
SIGINT）时，会落终态行。已知缓解：launchd 正常停任务发的是 SIGTERM，
先转发整组再记录（见下方孙进程清理），SIGKILL 只出现在强杀场景。

### 阶段完成口径修正

此前"19/19 完成"的说法修正为：**19 个任务完成诊断 + 3 个试点具备待激活
配置（未激活，HOLD 中）**。诊断完成不等于接线完成；激活需主控复审
GPT 复核通过后按 runbook 执行。

## 包装器用法（G3，已实现并测过）

```bash
python -m lei_signal.jobledger.wrap \
  --job-name com.lei.daily_scan \
  --input-basis close:$(date +%F) \
  --output-reference table:daily_opportunity_scan \
  -- /opt/homebrew/bin/python3 scripts/daily_scan.py
```

透传 stdout/stderr 与退出码；结束写一条台账（含 duration_ms、exit_code）；
被 SIGTERM/SIGINT 杀死也落 failed 记录（error_class=killed_by_signal:SIGTERM），
然后包装器以同信号自杀，launchd 观测语义不变。三种路径
（正常 / exit 3 / 被杀）已由 `tests/unit/test_jobledger_wrap.py` 覆盖，22 项全过。

## 试点接线 diff 样例（3 个非在办线任务，**只准备不执行**）

试点选择依据：脚本与其直接依赖（除公共 sqlite_store 外）不在在办 Modified
清单；timing.daily 成功语义最弱最需要台账；ashare.ma 是后续 17:30 链的上游。

### 样例 1：`com.lei.daily_scan.plist`

```diff
     <key>ProgramArguments</key>
     <array>
-        <string>/opt/homebrew/bin/python3</string>
-        <string>scripts/daily_scan.py</string>
+        <string>/opt/homebrew/bin/python3</string>
+        <string>-m</string>
+        <string>lei_signal.jobledger.wrap</string>
+        <string>--job-name</string>
+        <string>com.lei.daily_scan</string>
+        <string>--input-basis</string>
+        <string>close:launchd-15:00</string>
+        <string>--output-reference</string>
+        <string>table:daily_opportunity_scan</string>
+        <string>--</string>
+        <string>/opt/homebrew/bin/python3</string>
+        <string>scripts/daily_scan.py</string>
     </array>
```

同时给该 plist 增加（ wrap 需要能 import lei_signal）：

```xml
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>/Users/yongbiaoli/Desktop/lei-signal-lab/src</string>
    </dict>
```

### 样例 2：`com.lei.timing.daily.plist`

```diff
     <array>
-        <string>/bin/bash</string>
-        <string>/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/timing_daily.sh</string>
+        <string>/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3</string>
+        <string>-m</string>
+        <string>lei_signal.jobledger.wrap</string>
+        <string>--job-name</string>
+        <string>com.lei.timing.daily</string>
+        <string>--input-basis</string>
+        <string>close:ma-16:30+qq-sina-intraday</string>
+        <string>--output-reference</string>
+        <string>~/.lei_signal_lab/timing_scorecard/scorecard.jsonl</string>
+        <string>--</string>
+        <string>/bin/bash</string>
+        <string>/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/timing_daily.sh</string>
     </array>
```

（该 plist 原无 PYTHONPATH，同样需加 EnvironmentVariables 一段。）

### 样例 3：`com.lei.ashare.ma.plist`

```diff
     <array>
         <string>/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3</string>
+        <string>-m</string>
+        <string>lei_signal.jobledger.wrap</string>
+        <string>--job-name</string>
+        <string>com.lei.ashare.ma</string>
+        <string>--input-basis</string>
+        <string>close:qq-daily-kline-incremental</string>
+        <string>--output-reference</string>
+        <string>cache:a_share_ma_breadth.json</string>
+        <string>--</string>
         <string>/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/precompute_a_share_ma.py</string>
     </array>
```

（该 plist 原 ProgramArguments[0] 即 workbuddy python3，直接复用为 wrap 解释器，
本身已能 import lei_signal？——不能：它不带 `-m` 查 src；需同样补 PYTHONPATH。）

### 激活 runbook（主控审核后在安静窗口执行，本阶段零执行）

每个试点任务按同一套四步（以 daily_scan 为例）：

```bash
# 0) 前置确认：台账目录可写、gitignore 已覆盖
grep -n '^logs/$' .gitignore            # 应命中 logs/
mkdir -p logs && touch logs/job-ledger.jsonl

# 1) 手动演练一次（不经过 launchd，验证 wrap 与台账行）
PYTHONPATH=src /opt/homebrew/bin/python3 -m lei_signal.jobledger.wrap \
  --job-name com.lei.daily_scan --operation-type manual \
  --input-basis close:$(date +%F) --output-reference table:daily_opportunity_scan \
  -- /opt/homebrew/bin/python3 scripts/daily_scan.py --dry-run
tail -1 logs/job-ledger.jsonl | python3 -m json.tool   # 人工核对字段

# 2) 替换 plist（用上面 diff），然后热重载该任务（其余任务不动）
launchctl bootout gui/$(id -u)/com.lei.daily_scan     # 可能报「未加载」，忽略
launchctl bootstrap gui/$(id -u) scripts/launchd/com.lei.daily_scan.plist
launchctl print gui/$(id -u)/com.lei.daily_scan | head -20   # 确认 state=waiting

# 3) 回滚（如异常）：恢复原 plist 后重复 bootout/bootstrap 两步；
#    台账是只追加文件，回滚无需清理。
```

注意事项：
- 一次只接一个试点，观察一个完整交易日（含正常退出与台账行）再接下一个；
- `caffeinate` 等常驻服务与在办线任务本轮不接；
- 已知残留风险：daily_scan/signal_scan 尾部 `os._exit(0)` 跳过清理——对 wrap
  无影响（wrap 在子进程退出后由父进程写台账），已确认。

## 非干扰证据补强（2026-09-20，测试见 tests/unit/test_jobledger_nondisruption.py）

针对 GPT 第 20 轮六项条件逐项补齐，其中三项暴露并修复了 wrap.py 实现缺陷：

- **台账写失败降级（G1）**：原实现写台账失败会抛异常、改变退出码。已修：
  写失败只向 stderr 报"降级为不记录"，业务退出码、输出、执行次数不变，
  不换目录续写；禁止目录红线在降级路径下仍生效。
- **孙进程清理（G2，2026-09-20 第 22 轮修订）**：原实现让子进程另建
  会话（`start_new_session=True`）由包装器整组发信号——但这会让子进程
  脱离 launchd 监督的进程组，launchd 反而收不到尾。已按 GPT 第 22 轮
  裁决改为**同组**方案（见下节），整组清扫职责交回监督环境（launchd）。
- **子进程先被信号杀死（G3）**：原实现会把负返回码记成 `exit_-15` 这类
  数字退出错误。已修：负返回码按信号归类为 `killed_by_signal:<SIG>`。
- **启动上下文等价（G4）**：同命令有/无包装对比 stdout/stderr/退出码
  逐字节一致；env 未被替换（哨兵变量+环境规模一致）、cwd 与参数原样透传。
- **并发追加（G5）**：6 个包装器进程并发写同一 JSONL，逐行可独立解析、
  operation_id 不串写、无半行截断（单次完整行写入 + 追加模式）。
- **口径修正（G6）**：见上方"口径修正与盲区声明"一节。

## 同组修复与退出时序契约（2026-09-20，GPT 第 22 轮裁决落地）

### 改了什么（大白话）

之前包装器为了"自己管住所有子孙进程"，把任务进程挪到了一个独立的
进程组里。结果是 launchd（macOS 的任务管家）反而管不到这批进程：
任务被叫停后，管家按它自己记的那个进程组去收尾，收不到被挪走的
进程。现在改回去：任务和包装器放在同一个组里，由 launchd 统一收尾。
包装器收到停止信号时只做三件事：把信号转告直接子任务、最多等它几秒
（默认 5 秒，可调）、在流水账上记一笔后自己以同样的信号结束。

### 口径限定（不许过度宣称）

- 同组回收能力**仅在已验证的 launchd 启动拓扑下**成立：launchd 按
  进程组监督任务，包装器死后剩余同组进程由 launchd 清扫。
- 本包装器**不是通用 Shell 进程树监督器**，不保证自行脱离进程组的
  后代被回收。
- **试点任务不得启用 `AbandonProcessGroup=true`**（该选项会让 launchd
  放弃清扫进程组，直接破坏上述能力）。激活试点时此条作为红线检查项。

### 退出时序契约（冻结）

收到 SIGTERM/SIGINT → 转发仍存活的直接子进程 → 在停止预算内等待其
退出（默认 5 秒，对齐 launchd ExitTimeOut 默认语义；`--stop-budget`
或环境变量 `LEI_WRAP_STOP_BUDGET` 可调；不无限 wait）→ 尽力写一条
终态（预算耗尽时如实标注 `stop_budget_exhausted: true`，不伪装成
子进程已配合退出）→ 恢复默认信号处理器后向自身重发同信号终止
（直接父进程观察到 `returncode=-SIGTERM/-SIGINT`，而非 `exit(143)`）
→ 剩余同组进程交 launchd 清扫。台账写失败或子进程恰好先退出不破坏
此顺序、不产生重复终态。

### 真实 launchd 探针证据（双场景，2026-09-20 实测）

探针方法：临时 label（`com.lei.jobledger.probe.term.1789835949` /
`com.lei.jobledger.probe.kill.1789835982`，已全部 bootout 并删除
`/tmp` 探针目录），用**修复后的真实包装器**跑假任务，假任务再派生
一个孙进程（`/bin/sleep 300`），任务每 0.2 秒写一次心跳文件。

**场景 b：launchd 可处理信号（SIGTERM）**

- 拓扑记录：包装器 PID 41442 = 组长（PGID 41442），任务 PID 41444、
  孙进程 PID 41445 同组。
- `launchctl kill TERM` 后：心跳文件在 kill 时刻停止追加（33 行不再
  增长）；**测试清理之前**检查进程组——零遗留成员，孙进程 41445 已
  被 launchd 清扫；任务终态台账**恰好一条**：
  `status=failed, error_class=killed_by_signal:SIGTERM, exit_code=null`，
  未触发预算耗尽（子任务被转发信号后正常退出）。

**场景 c：launchd SIGKILL（强杀）**

- 拓扑记录：包装器 PID 41601 = 组长，任务 PID 41603、孙进程 PID
  41604 同组。
- `launchctl kill KILL` 后：心跳停止（13 行不再增长）；进程组零遗留，
  任务与孙进程均被监督环境回收；**台账无终态文件**——SIGKILL 不可
  捕获，按"未完成/未知"读法处理，不伪造终态（G4 语义保持）。

### 单测矩阵（G3a/G3d，tests/unit/test_jobledger_exit_contract.py）

- SIGTERM 转发 + 配合子进程完成清理标记 + 父进程断言 `-SIGTERM`；
- SIGINT 同序，断言 `-SIGINT`（注：前台等待中的 `/bin/sh` 会推迟 INT
  处理，属子进程不配合情形，由预算路径覆盖）；
- 忽略 SIGTERM 的子进程：0.5 秒预算耗尽后包装器照常退出不挂起，
  终态如实标注 `stop_budget_exhausted`；
- 停止预算解析（CLI > 环境变量 > 默认 5 秒，坏值回默认）；
- 被杀路径台账写失败：顺序不破坏、终态不重复、仍真实信号退出；
- 非干扰回归（G1 写失败降级 / G3 负返回码 / G4 环境输出 / G5 并发
  追加）复跑无回归；旧 G2 组清理测试改为"launchd 拓扑模拟 +
  监督者清扫"口径。

## 验收与边界声明

- 单测：`python3 -m pytest tests/unit/test_jobledger*.py -q` → 30 passed



- 单测：`python3 -m pytest tests/unit/test_jobledger*.py -q` → 36 passed
  （2026-09-20 第 22 轮修复后：22 既有 + 8 非干扰补强 + 6 退出契约新矩阵，
  旧 G2 组清理测试已改写为同组口径）。
- hygiene：`python3 scripts/check_repo_hygiene.py` 全绿（新文件只落
  `src/lei_signal/jobledger/`、`docs/ops/`、`tests/unit/`）。
- 零生产写入：未写 lab.db、未动 ~/.lei_signal_lab/、未执行任何 launchctl、
  未启动任何定时任务。
- 本诊断表信息全部来自本次实际读取 `scripts/launchd/*.plist` 与对应脚本
  源码，无猜测项。
