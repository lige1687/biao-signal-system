# 宏观阅读与ERP预览已核验，待用户视觉验收

- task-id: portfolio-trends-20261013; owner: 01a1334f-1167-7752-8041-e22a5dc2213b; status: review; scope_released: true; updated_at: 2026-10-14T19:27:08.251973+08:00; checked_coordination_sha: f45070be66bd9161196a4e2007e205169a94a81e; checked_at: 2026-10-14T19:27:08.251973+08:00
- 已读COORDINATION1.1、自身、investor-workspace-simplification-20261012、investor-observation-map、research-dispatch-controller及最新变化research-utility-review-20261012（限定自己的报告/raw、单项登记，已释放）；原已读清单沿用。无共享文件冲突，未覆盖他人改动。
- 用户授权语雀宏观读法、ERP优先及指标展现改善；AI CapEx仅按需新闻。已落地12阅读目录，ERP先图后数/同日期两端分解/历史位置/反例/来源；宏观教学四情景不判当前周期。6历史序列真实可取，新增调查周图明确缺周与过期。
- 本轮增量精确范围沿用后文已登记的web/components/fundamentals、父页、client/vite、reading.py、reading-history路由、macro_history缓存键、单元测试及自有报告。client额外修复newsApi的from/to→date_from/date_to参数映射，组件北京时间再过滤；原近30日混入9月3日旧文，修复后0条如实。未改news后台。
- 验收：794模块构建、10pytest、前端算术及新闻日期边界、6真实GET、422/405异常输入、12目录/中美/期间/情景/新闻浏览器、390px无溢出；标准主仓归置及隔离树目录检查通过。无error日志；原大包和共享ECharts卸载warning记录，未改他人共享图表，不声称主动断网流程已测。
- 本地成果：仓内.codex/worktrees/portfolio-trends-20261013，分支codex/portfolio-trends-20261013，基础52b5083e；源码未提交未推送。预览5190+独立只读8190运行中，无调度器/自动通知。8000/5188源码与进程未改。远端只有协调摘要，不可称远端有本轮源码。
- 报告docs/experiments/fundamentals-reading-ARCHIVE-2026-10-14.md、自有work-progress/API收据及本轮reading-20261014.patch/manifest；隔离registry668→669原项不变，INDEX增本报告。8000报告库未同步。图片仅本机.codex/portfolio-trends-qa/erp-reading-20261014.png、erp-mobile-20261014.png。原目标okr-a4fed76c71c3仅note版本13→14，状态不变且读回成功。
- 仍缺期限结构、OI/COT、社融M1M2/新订单、同年度盈利预期连续数据，只提供读法/来源；不声称全部指标补齐，不改技术信号、仓位或交易，不做收益实验。用户视觉验收、仓外现用5188写入确认尚待；新数据接入要保持原口径与来源时间，未自动扩项。
- root集成/验收；Sol中等做独立数据/新闻/调查，Astra高做ERP方法复核；独审两个P2已修。实际token/费用未知。

---

# 范围增量：缺失趋势与宏观缓存（当前）

- status: active; updated_at: 2026-10-14T19:04:43.141373+08:00; checked_coordination_sha: 1d0c3790e03836273cdd236381023eb644102382; checked_at: 2026-10-14T19:04:43.141373+08:00
- 已读portfolio-trends-20261013及上次以来实际变化任务（命令回执）；原已读清单沿用。新增只触本任务隔离树，不覆盖共享后台；其他owner源码避让。
- 用户已授权补齐缺失指标。新增精确写范围：src/lei_signal/fundamentals/reading.py、src/lei_signal/api/routes/fundamentals.py中仅reading-history路由、src/lei_signal/fundamentals/service.py中仅macro_history缓存键、tests/unit/test_fundamentals_reading.py、web/vite.config.ts中独立预览代理、web/src/api/client.ts新增只读方法、web/src/components/fundamentals/既定组件。
- 根因证据：macro_history缓存键macro_hist:metric未含page_size，先请求3条会污染60条请求。修复只加缓存维度，不改历史数据/计算规则。
- Sol data_audit独占新增reading.py与test_fundamentals_reading.py（root负责路由、service小改与前端）。按需公共FRED3条实际利率/VXN/核心PCE及CN3条宏观源；不接付费，不改自动化。预览新只读API独立端口8190，仅挂本接口，其余继续8000；不启动业务调度器，不重启8000。
- 验收：离线日期/同比/缺失/缓存隔离/失败测试，真实API每条独立来源与所属日，浏览器切换及错误/缺失，构建/归置。盈利预测与COT现阶段仍明确未接数据，不用新闻/PE冒充。

---

# 宏观阅读与 ERP 展示扩展（本轮当前状态）

- task-id: portfolio-trends-20261013; owner: 01a1334f-1167-7752-8041-e22a5dc2213b; status: active; updated_at: 2026-10-14T18:52:17.812042+08:00
- checked_coordination_sha: b0093aebe33b5e4214eaf9db416953717452dfce; checked_at: 2026-10-14T18:52:17.812042+08:00
- 已读 COORDINATION1.1、portfolio-trends-20261013、investor-workspace-simplification-20261012、research-utility-review-20261012、investor-observation-map、research-dispatch-controller；后四项最新记录本轮开头已读取。
- 授权增量：用户要求整合语雀观察指标、前述十类指标、突出 ERP、说明如何读图和依据；AI CapEx 仅按需新闻，其他行业专项排除。基本面仍为叙事层，不改变信号/交易/仓位。
- 基线沿用本任务隔离工作树及已验证5190前端。工作分支codex/portfolio-trends-20261013，base 52b5083e870f2fb4a240d349b9346f7d022be239。未推代码部分仍仅本地。
- 本轮写范围：原6前端文件；新增web/src/components/fundamentals/组件与样式、web/scripts/test_fundamentals_reading.mjs；必要的web/src/api/client.ts与web/src/types.ts增量仅在核缺口后；docs/ops/work-progress/portfolio-trends-20261013*、docs/experiments/fundamentals-reading-ARCHIVE-2026-10-14.md、该报告registry/INDEX登记。backend目前只读，若必须扩API先更新具体范围。
- 唯一写者root；子代理只读审阅现有数据和ERP方法，不写源文件。避让TodayPage/today.css、IndexComparison/overlay/dashboard既有块、因子研究和他人文件。主仓web与仓外5188本轮不直接写。
- 验收：ERP真实公式与成分/日期、现有十类数据能力及缺口如实、宏观按频率读趋势、AI新闻可点读来源，无自动监控；构建、必要计算与异常边界、真实API、桌面/窄屏完整路径、来源报告、归置。
- 采用research-closure限定来源核对+UI实现，不开展收益实验。最多6次外部来源请求（失败计入），新财务/收益实验0，未证明收益增量。两份策略文档SHA与已确认值一致。
- 截至本节点：语雀已通过已登录浏览器读到，末尾交互待检查；匿名网页访问失败保留。具体实现与本轮验收尚未执行。不存在后台通知或新自动化。
- 原仓外同步确认仍未收到单独答复；本轮先交付仓内5190可用结果，不因此中断已授权工作。

---

# 预览已验证，现用页同步待用户确认

- status: blocked（仅仓外现用路径写入待确认）；updated_at: 2026-10-13T11:39:43.824818+08:00; checked_coordination_sha: 3bafc053c8dc63d747161d8c1ff8a425f764c5ee; checked_at: 2026-10-13T11:39:43.824818+08:00
- 已读本记录及最新协调变更路径：docs/coordination/tasks/investor-workspace-simplification-20261012.md
docs/coordination/tasks/research-utility-review-20261012.md。实现范围无扩大。唯一root，不改其他owner源码/后台。
- 6文件完成持仓状态色/选中层级、基本面首页8历史图及6/12/36月切换；build/边界计算/真实Web/390px/归置/diff通过。实际资料缺口保持。
- 预览127.0.0.1:5190/portfolio与/fundamentals，仓内.codex/worktrees/portfolio-trends-20261013，分支codex/portfolio-trends-20261013。源码仅本地未提交未推送，远端不可复现。
- 证据docs/ops/work-progress/portfolio-trends-20261013.md及同名patch/manifest；截图仅本机主仓.codex/portfolio-trends-qa，不上传私人账户。原目标仅note版本12→13读回。
- 尚未修改现用5188所在仓外checkout；用户AGENTS要求仓外修改先确认，具体6文件同步问题已提出。其他验收完成；无后台研究或新通知。
- 恢复：人类允许同步后核before_sha256，先备份再精确同步，浏览器读回；主观视觉待人类验收。

---

# 持仓重点与基本面趋势展示

- task-id: portfolio-trends-20261013; owner: 01a1334f-1167-7752-8041-e22a5dc2213b; status: active; updated_at: 2026-10-13T11:32:26.712393+08:00
- checked_coordination_sha: 76750f78e80d93f712d42cc04c08895b05986dbf; checked_at: 2026-10-13T11:32:26.712393+08:00
- 已读: COORDINATION1.1、research-dispatch-controller、investor-workspace-simplification-20261012、research-utility-review-20261012、investor-observation-map、market-observation、lei-technical-reader-research、sentiment-factor-research。
- 用户要求持仓颜色突出重点、基本面看趋势。服务既有策略展示/背景解释层，不改技术判定。
- 基线: 5188实际web（52b5083e及现有因子增量）；独立工作分支codex/portfolio-trends-20261013。仅本地，无已推源码。
- 唯一写者root。隔离修改web/src/pages/portfolio.css、web/src/components/portfolio/PortfolioToday.tsx、web/src/pages/FundamentalsPage.tsx、新FundamentalsTrendOverview.tsx及配套样式/数据整理测试；自己的work-progress与验收记录。已有指标/规则/API只读。
- 冲突决定: 原持仓与因子owner已明确释放。市场理解owner的IndexComparison/dashboard/navigation块避让；情绪原研究和冻结历史不动。不编辑其他owner记录、不重启后台。
- 验收: 有意义的状态色/选中层级；首页直接见日期轴趋势；切换市场/期间、缺失不足不补造、移动宽度、构建和归置、浏览器读回。
- 正在做: 复用实际web建立仓内隔离预览；无研究/真实账户写入。视觉待用户验收。
- 未运行: 本轮构建/浏览器验收；已完成协调只读/源定位。预算费用未知，0新金融实验。
- 下一步: 绘制已提供历史、验证用户路径、准确保存源码与证据。
