# 本轮叠加图恢复入口

先读../../market-price-indicator-overlay-2026-10-04.md，status.json / ui-check.json / live-check.json / restore-check.json，再核manifest.json与SHA256SUMS。源码/小证据版本以本文件所在Git commit为准；原始价格、context完整响应、截图、恢复副本和ETF原件仅本地，元数据有大小SHA。没有权重/私有数据库/凭证；未交的原件不能假装可从Git恢复。

在仓库根，复用已有依赖后最小检查：

```sh
node web/run-market-foundation-regression.mjs
node web/run-market-context-regression.mjs
npm --prefix web run build
```

预期17+15软件检查exit0、构建exit0；不是来源合格或投资效果。缺依赖时用项目已有lock/环境安装说明恢复，本轮未做洁净安装。独立副本只复用了本机esbuild；跨OS未验证。

真实用户流程需要现有只读API与本分支context。先确认空闲端口，不停止他人服务。从仓库根，用自己已核解释器：

```sh
PYTHONPATH=src python3 -m uvicorn preview_app:app --app-dir docs/experiments/raw/market-expansion-implementation-2026-10-04 --host 127.0.0.1 --port 8045
```

本机Python3.11.7/AkShare1.18.49曾原生库崩溃；实际通过的是项目已有Python3.13.12/AkShare1.18.91环境，不保证任意python3同结果。不要自动采购/升级全局库；先核版本和公开源权限。已有共享API8000实际代码版本未知，不宣称完整旧服务恢复。

在web目录，确认5185空闲：

```sh
LEI_WEB_PORT=5185 LEI_API_PROXY=http://127.0.0.1:8000 LEI_MARKET_CONTEXT_PROXY=http://127.0.0.1:8045 npm run dev -- --strictPort
```

打开/market-understanding?market=us&metric=us_10_2_spread#index-comparison，实际选指数/指标，看同图两线→悬停原值/日期→展开依据；切月频/A股/390px。网络失败/无输入保留缺图，不复制旧响应冒充当前。原金融实验禁止为恢复重跑。用户本人理解效果待验收；不接管原负责人。
