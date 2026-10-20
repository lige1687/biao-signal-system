# 资讯流（newsfeed）设计与排序系统 · 设计文档

日期：2026-08-27
状态：设计已获用户口头确认（方案 A），进入实施
分支：lei-signal-sync（data-sync 分支开发，运行时在 ~/Desktop/lei-signal-lab，落地路径见 §14）

## 1. 背景与目标

系统现有 `fundamentals/` 模块只有**数值指标**（PMI/CPI、利率、两融、VIX、板块资金流），没有任何新闻文本、政策数据、博主观点。本设计新增 `newsfeed` 模块：自动抓取宏观/系统性风险/政策/行业公司新闻 + B站 UP主视频（字幕总结）+ 微信公众号文章，统一入库、LLM 每日批量打分排序，前端提供筛选 + 关键词检索。

**目标**：每天早上打开 `/news` 页，一眼看到"昨天最重要的基本面消息 + 关注博主的最新观点"，并能按类别/关键词检索历史。

**非目标（红线沿用仓库哲学）**：
- 不做自动交易信号、不硬挡单标的信号；
- `newsfeed` 是参考层：LLM 只做"打分/归类/摘要"这类结构化工序，不做交易建议；
- 不追求实时（用户已确认每日一次批量整合即可）。

## 2. 用户已拍板的决策

| 决策点 | 结论 |
|---|---|
| 排序逻辑 | LLM 打分，**每天批量整合一次**控成本 |
| 公众号接入 | 全自动（wewe-rss 本地 docker 桥，不做手动投递） |
| B站总结 | 自研管线：UP主投稿 → CC 字幕 → LLM 摘要 |
| 检索形态 | 筛选 + 关键词搜索（SQLite FTS5），不做 RAG 问答 |
| 每日运行时间 | **20:30**（launchd） |
| 首批 UP主 | 趋势天哥、波段哥王安松、筹码小吕神、财经高一截（mid 实施期查证） |
| LLM 通道 | 复用 `plans/llm.py`（本机实测可用 ANTHROPIC_AUTH_TOKEN/BASE_URL/MODEL；DEEPSEEK/ARK 优先级更高，有则用） |

## 3. 分类体系

LLM 归类，浏览可筛，快讯入库时先按关键词规则预分类（未评分也能按类别浏览）：

| category | 含义 | 例子 |
|---|---|---|
| `macro` | 宏观基本面 | PMI/CPI 发布、美联储议息、LPR |
| `risk` | 系统性风险 | 债务上限、银行危机、地缘冲突、流动性事件、关税战升级 |
| `policy` | 政策 | 国务院会议、行业监管、产业政策、补贴 |
| `industry` | 行业与公司 | 英伟达财报、行业景气、龙头公司事件 |
| `blogger` | 博主观点 | 公众号文章、B站视频观点 |

## 4. 架构与数据流

```
[每日 20:30 launchd] 或 [前端"立即刷新"按钮 → POST /api/news/run]
  1. 抓取自上次水位以来的新条目：
     - 东财快讯 7x24、新浪 7x24   → 规则关键词粗筛（命中宏观/风险/政策/行业/关注标的才留）
     - Google News RSS            → 按配置的定制查询（如 "NVDA earnings"）
     - wewe-rss 公众号 RSS        → docker 本地 4000 端口（P2 期启用）
     - B站 UP主投稿列表（wbi 签名）→ 新视频抓 CC 字幕
  2. 归一化 + 去重（dedupe_key 唯一约束）→ 入库原始态
  3. LLM 批量整合（每批 ≤20 条）：类别 / 重要性 0-10 / 利多利空 / 涉及标的 / 一句话点评
  4. 生成"今日整合简报"（按类别归纳、同事件合并，结构化 JSON）
  5.（修订：放弃 FTS5，搜索用 LIKE 子串匹配，见 §6）
```

模块结构：`src/lei_signal/newsfeed/`
- `sources/`：`eastmoney.py`、`sina.py`、`gnews.py`、`rss.py`（通用 RSS，公众号复用）、`bilibili.py`（含 wbi 签名）
- `normalize.py`：统一 `NewsItem` dataclass + dedupe_key 生成
- `store.py`：SQLite 读写（迁移 016）+ LIKE 子串查询
- `llm_score.py`：批量打分 + 简报生成（复用 `plans/llm.py` 凭据体系）
- `pipeline.py`：编排（水位管理、错误聚合、单项降级）
- `service.py`：查询/触发 API 的服务层
- 路由：`api/routes/news.py` → `/api/news`，`app.py` 挂 `app.state.newsfeed_service`

## 5. 数据源规格（2026-08-27 实测可达）

| 源 | 端点要点 | 说明 |
|---|---|---|
| 东财快讯 | `np-listapi.eastmoney.com/comm/web/getFastNewsList`（biz=web_724，翻页用 sortEnd 游标） | ✅ 已验证；title+summary |
| 新浪 7x24 | `zhibo.sina.com.cn/api/zhibo/feed`（zhibo_id=152） | ✅ 已验证；rich_text |
| Google News RSS | `news.google.com/rss/search?q=<query>`（**必须带浏览器 UA**） | ✅ 已验证；标题+媒体名，不抓正文 |
| B站投稿 | `api.bilibili.com/x/space/wbi/arc/search`：**需 wbi 签名 + buvid cookie**（匿名 nav 可取 img/sub key，实测无签名返回 -352） | mid 列表来自配置 |
| B站字幕 | view API 取 cid → `player/wbi/v2` 取字幕列表 → 下载 json | CC 字幕匿名可取；**AI 字幕（ai_zh）通常需登录**，可选配 `BILI_SESSDATA` 提高命中率；无字幕视频降级为标题+简介 |
| 公众号 RSS | wewe-rss（docker，本地 4000）产出标准 RSS/Atom | P2 期部署；用户在微信读书订阅公众号；token 偶发失效需重新扫码（记运维手册） |

**水位管理**：每个源记 last cursor（东财 sortEnd / 新浪页内时间 / RSS entry id / B站 last bvid·pubdate），存 SQLite `news_watermarks` 表，重跑幂等。

## 6. 数据模型（迁移 016，只追加 + 幂等）

```sql
CREATE TABLE IF NOT EXISTS news_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,              -- eastmoney|sina|gnews|wechat|bilibili
  source_name TEXT,                  -- 公众号名 / UP主名 / 快讯频道名
  dedupe_key TEXT NOT NULL UNIQUE,   -- sha1(url)；无 url 时 sha1(source+title_norm)
  url TEXT,
  category TEXT,                     -- macro|risk|policy|industry|blogger（规则预分类，LLM 终裁）
  title TEXT NOT NULL,
  summary TEXT,                      -- 原始摘要 / 字幕前 N 字 / 正文前 N 字
  content TEXT,                      -- 全文（公众号正文 / B站字幕全文），可 NULL
  symbols TEXT,                      -- JSON array，LLM 涉及标的
  direction TEXT,                    -- bullish|bearish|neutral
  importance INTEGER,                -- 0-10，NULL=未评分
  llm_note TEXT,                     -- 一句话点评
  published_at TEXT NOT NULL,        -- ISO8601
  ingested_at TEXT NOT NULL,
  scored_at TEXT
);
CREATE INDEX idx_news_items_published ON news_items(published_at DESC);
CREATE INDEX idx_news_items_category ON news_items(category);

-- 修订（2026-08-27 实施前）：不建 FTS5 虚拟表。中文子串搜索用 LIKE '%kw%'（范围 title+summary+llm_note）。
-- 理由：LIKE 天然支持中文子串；日增 <300 条全表扫毫秒级；免去 trigram 版本兼容与触发器维护。

CREATE TABLE IF NOT EXISTS news_digests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  digest_date TEXT NOT NULL UNIQUE,  -- YYYY-MM-DD
  payload_json TEXT NOT NULL,        -- 结构化简报（见 §7）
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_watermarks (
  source_key TEXT PRIMARY KEY,       -- 如 bilibili:<mid> / eastmoney / rss:<url_hash>
  cursor_value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_runs (          -- 运行留痕（排障用）
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,              -- running|ok|partial|failed
  stats_json TEXT,                   -- 各源抓取/入库/评分计数
  errors_json TEXT
);
```

## 7. LLM 管线

**输入**：未评分条目分批（≤20 条/批），每条给 title + summary + content 截断（快讯 500 字、字幕截前 20000 字）。

**输出（严格 JSON 数组）**，逐条：
```json
{"id": 123, "category": "industry", "importance": 8,
 "direction": "bearish", "symbols": ["NVDA"],
 "note": "英伟达财报数据中心收入不及预期，指引下调"}
```

**简报生成**：当日已评分条目全量（title+note+importance 过一遍），输出结构化 JSON：
```json
{"digest_date": "2026-08-27",
 "sections": [
   {"category": "macro", "headline": "美联储放鸽", "bullets": ["...", "..."]}
 ],
 "top_events": [{"title": "...", "importance": 9, "why": "..."}]}
```
同事件多源条目在简报里合并为一个 bullet（简报层去重，列表层保留原始条目）。

**降级**：JSON 解析失败→原样重试 1 次→仍失败该批保持未评分（列表按时间排，管线继续）；LLM 完全不可用→入库照常、打分/简报跳过，`news_runs.status=partial`。沿用 `fundamentals/service.py` 单项降级哲学。

**成本预估**：快讯粗筛后 50~150 条/天 × ~400 token + B站 3~5 视频 × ~2 万 token（字幕）+ 简报 1 次 ≈ **<20 万 token/天**，deepseek-chat 折合 ¥1/天以内；Anthropic 通道略贵但量级相同。可控。

## 8. 配置 `config/newsfeed.json`（git 同步，仓库新增 config/ 目录）

```json
{
  "bili_ups": [
    {"mid": 0, "name": "趋势天哥"},
    {"mid": 0, "name": "波段哥王安松"},
    {"mid": 0, "name": "筹码小吕神"},
    {"mid": 0, "name": "财经高一截"}
  ],
  "rss_feeds": [],
  "gnews_queries": ["NVDA earnings", "Fed rate decision", "英伟达"],
  "symbols": ["NVDA"],
  "flash_keywords": {
    "macro": ["央行", "美联储", "LPR", "CPI", "PPI", "PMI", "GDP", "国债", "美债", "非农", "议息"],
    "risk": ["风险", "危机", "违约", "制裁", "地缘", "冲突", "流动性", "债务上限", "关税"],
    "policy": ["政策", "国务院", "证监会", "发改委", "财政部", "央行发布", "规划", "补贴", "监管"],
    "industry": ["财报", "业绩", "营收", "净利润", "发布", "产能", "涨价", "订单"]
  },
  "lookback_days": 3
}
```
- `symbols`：重点标的（含 watchlist 之外的美股，如 NVDA），用于快讯加分 + 生成 gnews 查询。
- `lookback_days`：首次运行回看天数（默认 3，之后走水位增量）。

## 9. API 契约（`api/routes/news.py`）

| 端点 | 说明 |
|---|---|
| `GET /api/news/items` | 参数：`category`、`q`（LIKE 子串，命中 title/summary/llm_note）、`source`、`from`/`to`、`scored`（`all`\|`scored`\|`unscored`，默认 all）、`min_importance`、`limit`（默认 50，max 200）、`offset`。排序：已评分按 importance DESC, published_at DESC，未评分条目排在已评分之后按时间倒序；`scored=unscored` 时纯时间倒序。返回含 total |
| `GET /api/news/digests` | 最近 N 天简报（默认 7） |
| `POST /api/news/run` | 手动触发整条管线（后台线程，立即返回 run_id） |
| `GET /api/news/status` | 最近 run 状态 + 各源水位 + 计数（前端刷新按钮用） |

## 10. 前端（`/news` 资讯流页）

- TopNav 加"资讯流"入口（无红点轮询，数据日更）。
- 页面结构：
  - 顶部：**今日简报卡**（最新 digest 的 sections + top_events，原生渲染结构化 JSON，不引 markdown 库）；
  - 筛选栏：类别 tabs（全部/宏观/风险/政策/行业公司/博主观点）+ 来源下拉 + 日期范围 + 搜索框（防抖 400ms）；
  - 列表：卡片含 类别标签、重要性星级（0-10 → 5 星制取半）、方向箭头（利多↑红/利空↓绿/中性—）、标的 chips、来源+时间、一句话点评、原文链接；未评分条目显示原始标题+摘要，角标"未评分"；
  - 右上角"立即刷新"按钮 → POST run → 轮询 status → 刷新列表。
- 接线照现有惯例：`client.ts` 加 `newsApi`、`types.ts` 加类型、`App.tsx` 加路由。

## 11. 调度

- `scripts/precompute_newsfeed.py`：CLI 入口（`--full` 忽略水位、`--no-llm` 只入库），供 launchd 与手动用。
- `scripts/com.lei.newsfeed.plist`：每日 20:30，PYTHONPATH=src，WorkingDirectory 照仓库惯例（部署机路径）。
- 安装走 `install_app_autostart.sh`（该脚本需追加新 plist）。

## 12. 错误处理

- 任一源失败：记入 `news_runs.errors_json`，其余源继续（partial）。
- 限速：B站每请求间 sleep ≥1s（防风控）；RSS/快讯每源整体超时 30s。
- 幂等：dedupe_key 唯一约束 + INSERT OR IGNORE，重跑不重复。

## 13. 测试策略（照 `tests/unit/test_fundamentals.py` 风格）

- 纯逻辑单测（HTTP mock）：normalize/dedupe_key、关键词粗筛、LLM JSON 解析容错（截断/夹杂 markdown 代码块）、LIKE 中文搜索、水位增量、简报 payload 校验。
- wbi 签名：给定已知 key+params 断言 w_rid（固定向量）。
- E2E（不进 CI）：`scripts/dev_run_newsfeed_once.py` 用 `LEI_SQLITE_PATH` 指向临时库真实抓 4 位 UP主 + 快讯 + LLM（凭据来自 Desktop .env 的 ANTHROPIC_*）。

## 14. 部署与分期

**P1（本次实施）**：B站（4 位 UP主）+ 东财/新浪快讯 + Google News RSS + LLM 打分/简报 + `/news` 页 + launchd 20:30 + 单测 + E2E 跑通"看看效果"。
**P2**：wewe-rss docker 部署 + 公众号 RSS 接入（需用户微信读书扫码，一次人工动作）；`BILI_SESSDATA` 可选配置。
**P3（可选）**：今日简报飞书推送（复用 `notify/feishu`）。

**落地路径**：本仓库（lei-signal-sync，data-sync 分支）开发 → 提交推送 → 用户合并到 Desktop 运行时克隆（该克隆当前在 feat/timing-backtest 分支，需用户决定合并顺序）→ `biao restart` + 装新 plist。运维手册增补 §12：newsfeed 数据源/水位/排障/wewe-rss 扫码。

## 15. 风险与开放问题

| 风险 | 缓解 |
|---|---|
| B站 AI 字幕需登录，无 SESSDA 命中率低 | 实施期用 4 位 UP主真实视频实测命中率；低则请用户提供 BILI_SESSDATA（P2） |
| wewe-rss 微信读书 token 失效 | 运维手册记录重扫码步骤；失效期间该源停更不影响其他源 |
| LLM JSON 输出不稳定 | 严格解析 + 重试 1 次 + 降级未评分态 |
| ~~trigram FTS 索引体积~~ | 已规避：改 LIKE 搜索，无索引膨胀问题 |
| 两克隆分支分叉（data-sync vs feat/timing-backtest） | 本设计只在 lei-signal-sync 实施；合并时机由用户决定 |
