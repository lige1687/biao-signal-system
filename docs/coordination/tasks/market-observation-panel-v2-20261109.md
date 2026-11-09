# 市场观察面板三层重构 · 本地开发验收

- task-id market-observation-panel-v2-20261109；owner 01a1c061-147b-7dc0-a226-ebc780c63117/root；status completed；scope_released=true；updated_at 2026-11-09T21:34:52+0800。
- checked_coordination_sha 97a024c740f261a242d628e9f41e51f2b1c32e01。交付前重新获取并读回本任务与上一同步点；相邻任务范围无变化。全部写者结束，本次阶段记录 docs/ops/work-progress/market-observation-panel-v2-20261109.md。
- 25张观察卡与三组诊断本地读回；四期指490日、A股PCR 271日到11/09，美股PCR 279日到11/06，NFCI 200周，焦点股/下跌冲击/STR/当前成员相关均至11/06。BW作者历史至2025-12，代理到11/09。510300 IV 仅8日，A股全截面11/09原件待取得，NAAIM近三周公开图表估读。
- 验收：独立统计复算、HTTP本地数据字节一致、真实桌面组合状态及小图/弹窗、Python/TS/Vite/归置通过。数据包SHA256 9ee8fe304262c7afa75db6c17e5ee489f51614e86515e47aad196f75c6922101；外盘固定UUID已核并保存114项小型证据。
- 基础18e64fa632dba5dbad0e5fcae09b4ccc75f119a9加共享本地改动。最近已推送本任务代码成果：无。本轮远端写入仅本任务协调元数据。用途是市场环境观察；原策略、交易和冻结研究源未修改。

---

# 市场观察面板三层重构

- task-id market-observation-panel-v2-20261109；owner 01a1c061-147b-7dc0-a226-ebc780c63117/root；status active；scope_released=false；updated_at 2026-11-09T20:58:01+0800。
- checked_coordination_sha 0965e5a1a54dea4f54d49a26dedd7341e0169278；已核 COORDINATION 1.1、market-observation、research-dispatch-controller、breadth-reading-aid-20261101、cross-market-risk-context-20261102、focus-stock-universe-20261024、microstructure-observations-20261108、trae-observation-integration-20261108、trae-sector-observation-20261108、hy-oas-card-20261109、erp-observation-clarity-20261107、erp-breadth-integration-review-20261108、market-increment-map-20261102、market-style-observation-20261020、sentiment-factor-research、investor-observation-map。邻接已完成或范围独立。保留各方未提交的实际工作区内容。
- 基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9 + 本地未提交；最近已推送本任务成果：无。市场环境叙事观察用途，两权威策略文档指纹一致。三组观察线不是策略参数或真实交易指令。
- 写范围：root 独占 web/src/components/market-observation-alerts/{index.tsx,indicatorCatalog.ts,selection.ts}、新 src/lei_signal/market_context/observation_panel*.py（源适配器除外）、scripts/launchd/build_market_observation_panel.py、新 web/public/research/market-observation-panel/**（源适配产物除外）、tests/unit/test_observation_panel*.py（来源专测除外）及本任务阶段记录。前端助手独占新 web/src/components/market-observation-panel/**。源助手独占现有 scripts/refresh_market_observation_history.py 与新 src/lei_signal/market_context/observation_panel_sources.py / tests/unit/test_observation_panel_sources.py；A股历史助手只读查证，结果先回传待主控另行登记。现有静态研究包、冻结输入、共享技术策略保持原归属。
- 用户授权四阶段数据覆盖/合并、窗口统计、阈值与大白话、三层诊断条。验收逐指标实际覆盖日期/样本与来源，校验统计窗口和跨日对齐，真实接口与桌面 UI 核验。源证据先复用、缺失不能用未来值或代替口径；未经验证的阈值只用于观察。当前预检策略与邻接记录已核对，尚未改源码/验收；未跑交易回测、未部署/启动新计划任务。最终记录数据缺口、来源和实测证据。

- 范围追加 2026-11-09T21:03:06+0800；checked_coordination_sha 9b9bf902f96ae05599ac14b5050fe456689a6b38。A股历史助手独占新 src/lei_signal/market_context/observation_panel_cn.py 与暂存目录 cn-update，复用已核 BaoStock 原件，重叠日期校验后接续；旧报价和冻结包只读。root 追加 scripts/check_repo_hygiene.py 一条已存在生产脚本登记（若脚本已在子目录则无需）。
