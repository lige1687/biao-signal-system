# lei-signal-lab 微信小程序（Taro + React）

`lei-signal-lab` 的**只读看板小程序**：把本机运行的股票技术信号研究看板，搬到你手机上随时看。
**个人主体体验版自用**，不发布、不备案、不申请域名、不接登录/支付/订阅消息。

- 技术栈：**Taro 4 + React + TypeScript**，编译目标 `weapp`（微信小程序）。
- 数据来源：本机 FastAPI 后端的只读接口（`/api/*`，CORS 已开），所有判定都在 Python 后端，**前端不做任何信号计算**。
- 页面：今日信号（首页 tab）/ 自选看板（tab）/ 收盘简报（tab）/ 标的详情（从卡片进入）/ 监督待办（自选看板右上角进入，只读）。

---

## 硬红线（务必遵守）

1. **不改** `src/lei_signal/ui/`（Streamlit 冻结）、不改 `web/`、不改任何后端规则/判定逻辑。
2. 判定权在 Python 后端，小程序只展示；**不在前端重新计算任何信号**。
3. UI 用策略自己的语言：阶段、路牌、触发条件、失效位、机会/风险；不发明新概念，
   **不输出买卖建议、仓位、收益预测类内容**。
4. 后端标注 `research_proxy` 的数据**原样保留该标注**（详情页相关卡片显示「研究代理」徽标）；
   数据不可用时**显式展示 `DATA_UNAVAILABLE`**，不静默当成「无信号」。

---

## 工程结构

```
miniapp/
├── project.config.json        # 微信开发者工具工程配置（AppID 占位符 + 已关 urlCheck）
├── package.json               # Taro 4.2.1 + React 18
├── config/                   # Taro 编译配置（index/dev/prod）
├── babel.config.js / tsconfig.json
└── src/
    ├── app.config.ts         # 页面注册 + tabBar（3 tab）
    ├── app.tsx / app.scss    # 入口 + 全局深色样式
    ├── types/index.ts        # DTO 类型（从 web/src/types.ts 对齐后端复制）
    ├── store/settings.ts     # BASE_URL 持久化（本地 storage）+ 三种预设
    ├── utils/format.ts       # 格式化 / 涨跌色 / LEI 三色映射
    ├── api/client.ts         # Taro.request 封装（BASE_URL 可配置）
    ├── components/           # Tag / SectionTitle / LoadingState / Sparkline / CardItem / SignalItems / KLineView / MarketBreadthStrip / OpportunityPanel
    └── pages/                # signals / dashboard / brief / detail / settings / plans
```

---

## 本地运行（开发者工具）

1. **安装依赖**（首次）：
   ```bash
   cd miniapp
   npm install
   ```
2. **编译**（微信开发者工具会自己在导入时编译；也可手动 watch 构建）：
   ```bash
   npm run dev:weapp      # 监听构建到 dist/
   npm run build:weapp    # 一次性构建
   ```
3. **微信开发者工具** → 导入项目 → 选择 `miniapp/` 目录。
   - **AppID**：个人主体免费注册一个，填到 `project.config.json` 的 `appid` 字段（当前为占位符 `YOUR_APPID_HERE`）。
     或开发阶段直接选「测试号」（无需 AppID）。
   - **不校验合法域名**：导入后「详情 → 本地设置」勾选 **「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」**。
     （本仓库 `project.config.json` 已把 `urlCheck` 设为 `false`，但工具侧仍建议手动确认一次。）

> 首次构建若报 Taro 版本相关错，把 `package.json` 里所有 `@tarojs/*` 版本号改成你本机
> `taro --version` 对应的版本（**所有 @tarojs/* 必须一致**），再 `npm install`。

---

## 真机体验版步骤

1. 开发者工具里「上传」代码（上传时填个版本号如 `1.0.0`）。
2. 微信公众平台 → 该小程序「管理 → 版本管理 → 体验版」→ 选刚上传的版本「设为体验版」。
3. 生成体验版二维码，手机微信扫码。
4. 手机上打开后，进入「右上角 ··· → 开发调试 → 打开调试 / 打开 vConsole」
   （即**调试模式**），体验版才能访问任意域名（这正是体验版自用的意义）。

> 体验版本身仅限体验成员访问，但无需审核、无需备案域名，满足「自用」需求。

---

## 后端地址（BASE_URL）配置

小程序通过 `BASE_URL/api/...` 访问后端。`BASE_URL` 存于手机本地 storage，可在小程序内
「自选看板 → ⚙ 设置地址」里修改，改完即生效。

三种常用地址（设置页有快捷预设）：

| 预设 | 地址 | 适用 | 注意 |
|---|---|---|---|
| 开发者工具（本机） | `http://127.0.0.1:8000` | 开发者工具 / 模拟器 | 直连本机后端 |
| Mac 局域网 IP | `http://192.168.x.x:8000` | 同 Wi-Fi 真机 | **需先把 `start_backend.sh` 的 host 改为 `0.0.0.0`**（由你决定，**本小程序不改后端**） |
| Cloudflare 隧道 | `https://xxxx.trycloudflare.com` | 任意网络真机 | 运行 `scripts/start_feishu_tunnel.sh` 获得临时域名（每次重启会变） |

> 关键事实：后端 `start_backend.sh` 当前监听 `127.0.0.1`，手机真机**连不上**这个地址。
> 因此真机最稳的是用 `cloudflared` 隧道（脚本里有现成先例）；
> 或你自行把后端 host 改为 `0.0.0.0`（不在本任务范围）。本小程序一律不改后端。

后端存活校验（与开发者工具同机时）：
```bash
curl http://127.0.0.1:8000/api/dashboard/cards
```

---

## 用到的接口（与页面一一对应）

| 页面 | 接口 | 说明 |
|---|---|---|
| 今日信号 | `GET /api/signals/today` | 买点（daily_opportunity_scan）+ 卖点（signal_alerts） |
| 今日信号 · 重扫 | `POST /api/signals/today/refresh?as_of=close` | 手动重扫（收盘口径），下拉刷新则为重新读取 |
| 自选看板 · 市场宽度条 | `GET /api/market-context/global-strip` | 各市场面板（B20/B50/B200 + 阶段坑位 + 真全A涨跌家数）+ NAAIM/AAII 情绪 |
| 自选看板 · 机会雷达 | `GET /api/opportunities/today` / `POST .../refresh` | 读库快照（✅成立/🚫阻断/⏳等待），可立即重扫落库 |
| 自选看板 · 待办红点 | `GET /api/plans/summary` | 监督待办入口的未处理待办计数（onShow 刷新） |
| 收盘简报 | `GET /api/daily-brief/latest` | 1445 盘中预判 / 1645 收盘复核两槽位，接口 `slot` 字段区分 |
| 标的详情 | `GET /api/symbols/{symbol}/detail` | 三色判断依据、结构/B1、指标、风险摘要 |
| 监督待办（只读） | `GET /api/plans` + `GET /api/plans/{id}/alerts` + `GET /api/plans/{id}/actions?state=open` | 活跃计划（armed/entered）+ 当日提醒（block/remind/hint）+ 未处理待办；写操作去 web 端 |

所有 DTO 字段均来自 `web/src/types.ts`（与后端 `schemas.py` 对齐），**未臆造字段**。

---

## K 线说明

详情页 K 线用 **Canvas 2d 自绘**（`components/KLineView`，绘图逻辑在纯函数 `draw.ts`，可脱离小程序单测）：
- 默认 **红涨绿跌**（A股惯例）；可切换到 **LEI 三色模式**（按 `chart.states`/`stateColors` 给每日状态着色：绿/灰/黑）。
- **均线**：EMA/SMA × 20/60/120，同周期同色、EMA 实线 SMA 虚线（与 web 约定一致），chips 独立开关；默认开 EMA20 / SMA60 / EMA120。
- **结构标记**：底部确认 ◆（绿，灰=失效）、顶部确认 ◆（红，灰=失效）、结构失效 ✕、关键性波动竖线；参考线 B1/C 点/颈线带右端标签。
- **MACD 副图**（默认关）：DIF/DEA + 红绿柱，图例标注「研究代理」。
- 坐标轴（价格/日期网格）、最新价标签、量能 4 档色、60/120/250 根缩放；**点按 K 线出十字线**并在上方读出当日 OHLC/涨跌/量/均线值/命中结构。
- 所有数值均取自后端 `ChartPayload`（均线/标记/量能色都是后端算好的），前端只画不算。

---

## 验收自查（对应任务验收标准）

- [x] 开发者工具编译无报错（见 `dist/`）；三个 tab + 详情页浏览真实数据（服务存活时）。
- [x] 每个接口返回结构与页面渲染字段一一对应（字段均取自 `web/src/types.ts`，并 curl 核对真实返回）。
- [x] 后端与 `web/` 零改动（`git status` 仅新增 `miniapp/`）。
- [x] 红线 #2：前端不做信号计算（仅 `Taro.request` + 渲染）。
- [x] 红线 #3：只用策略语言（阶段/路牌/触发条件/失效位/机会·风险），无买卖建议/仓位/收益预测。
- [x] 红线 #4：`research_proxy` 原样保留（详情卡片显示「研究代理」徽标）；`DATA_UNAVAILABLE` 显式展示（信号页「数据不可用」区、详情页红色告警卡），不静默。

> 说明：本仓库所有 UI 文案仅描述「状态 / 路牌 / 失效位」，不构成任何买卖建议。
