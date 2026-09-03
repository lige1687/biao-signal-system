# 添加标的统一化设计（2026-08-27）

## 问题清单（均实测确认）

| # | 问题 | 根因 |
|---|------|------|
| P1 | 中证 93xxxx 指数全部不可添加（如 931160 中证通信设备） | `eastmoney_secid` 对 `.SS` 只生成 `1.` 前缀，而中证 93 系挂东财 market=2；腾讯 `sh/sz931160` 为空；Yahoo 无此 ticker |
| P2 | 裸 6 位沪市指数误路由（`000905` → `000905.SZ` 深市股票口径） | 0 开头一律 `.SZ`，且 probe 失败时不提示正确写法 |
| P3 | BKxxxx（东财概念/行业板块）/SWxxxx（申万）支持直输但选择器清单没有，不可发现 | 清单只覆盖 THS 881xxx 行业 + 策略指数 + 美股 ETF |
| P4 | 添加入口分裂：四个 tab、清单散落 labels.py 与 config.py | 历史演进产物，无统一目录 |
| P5 | probe 失败提示不指路 | 只报「行情暂不可用」，不给纠错建议 |

## 方案（用户已确认）

### 后端

1. **`eastmoney_secid()`**（symbols.py）：`93xxxx` → `2.{code}`。安全性：沪市 9 开头真实证券仅
   900xxx B 股，北交所为 82/43/87/92 开头，93 段无冲突。实测 `2.931160` 有完整日线与实时行情、
   `1.931160` 为空。
2. **`resolve_symbol()`**（symbols.py）：支持中证官方写法 `6位数字.CSI`（如 `931160.CSI`、
   `000905.CSI`），归一化为 `.SS` 后缀，与既有指数清单口径一致。
3. **`config.py`**：`STRATEGY_INDICES` 登记 `931160.SS 通信设备（中证）`；`INDEX_OVERRIDES`
   合并 STRATEGY_INDICES（显示名/市场标签「A股」正确生效，现状只含 DASHBOARD_INDICES）。
4. **概念板块进目录**（用户选择）：新增 `api/catalog.py` 拉东财概念板块
   （clist `fs=m:90+t:3+f:!50`，504 个，翻页拉全），内存 TTL 1h，失败降级空列表。
   `/api/sectors` 响应新增 `concepts` 键，旧键不动（向后兼容）。行业板块维持 THS 881xxx 口径
   不纳入 BK 行业（避免同名重复）；SW 不进目录（与 THS 重叠），两者保留代码直输。

### 前端

5. **AddSymbolDialog 重构为单入口**：一个搜索框 + 分类 chips（全部/行业板块/概念板块/指数/美股ETF）。
   输入即过滤统一目录（名称+代码），行内显示分类徽标，点击即加；输入非空时并排提供
   「按代码解析」动作（回车触发），走既有 resolve→确认添加流。目录渲染上限 200 行（约 666 条全量）。
6. **纠错提示**：probe 失败且输入为 0 开头裸 6 位码时，提示「带 .SS 后缀重试（如 000905.SS），
   中证指数也可用 .CSI 写法」。

### 不做的事（YAGNI）

- 不自动路由 000xxx 裸码到指数（与深市股票段真实冲突，只做提示）。
- 不把 BK 行业（496，与 THS 90 重叠）与 SW（54）纳入目录。
- 不动腾讯 quote 源（A 股指数盘口缺失显示「—」，与海外指数同口径，已有文档说明）。

## 测试

- `test_phase1.py`：`.CSI` 归一化、93xxxx secid 特判、900xxx/399xxx 不回归。
- `test_add_catalog.py`（新）：`/api/sectors` 返回四组清单（monkeypatch catalog）、
  INDEX_OVERRIDES 含策略指数、931160.SS 显示名。
- E2E：重启线上服务后 `GET /api/symbols/resolve?q=931160&probe=true` 应 probe_ok=true，
  添加后自选列表出现 K 线与中文名。

## 部署

线上服务跑在 `~/Desktop/lei-signal-lab`（feat/timing-backtest 分支）；本仓库（data-sync）与其
四个目标文件完全一致，改动可原样移植。流程：本仓库实施+测试 → 同文件移植 → `biao restart` → E2E。
