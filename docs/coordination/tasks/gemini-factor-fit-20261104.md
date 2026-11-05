# Gemini中美因子适用性审查

- task-id: gemini-factor-fit-20261104；owner: root/01a1a584-2813-7b42-8cd6-f181e79f1f8c；status: active；scope_released: false。
- updated_at: 2026-11-04T16:02:00+08:00；checked_coordination_sha: 7ea670559f127b4c2baf24fe9dad556315bac91a；checked_at: 2026-11-04T16:02:00+08:00。交付前已fetch核对，已读COORDINATION、classic-factor-research、research-dispatch-controller、market-increment-map-20261102及本任务；没有新增同写。
- 用户问题：Gemini所列中美因子是否已有、能否复刻、对个人低频宽基/ETF系统是否有增量。范围为七项资料/代码/旧证据审查；没有新行情下载、金融回测、生产或交易改动。
- 基线：codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，共享脏区保留。研究产物仅本地，未提交/推成果分支，远端不可完整复现；本记录仅为协调状态。
- 已完成：docs/experiments/gemini-factor-fit-2026-11-04.md、registry本键、INDEX本行及本任务research-notes小证据。root为唯一写者；Sol medium只读盘点已验收。registry既有条目/元数据与INDEX旧字节全部保留。
- 结论：隔夜/日内、FIP、宽度/拥挤已有研究；RSJ、精确量价秩相关、SUE全池及分析师修正宽度未找到精确效力实现。盈利预期类保留为不同信息资料候选，新增收益未知；不重建同类模块、不采用85/90阈值交易。
- 复用数值：最新精确算术隔夜/日内MSE14.7234398644→14.796657596（恶化0.4973%）；FIP赢家连续组相对全集六个月已知报价贡献−0.04447pp，范围跨零；行业高活跃半仓年化8.54%/回撤32.33%，买持10.51%/34.11%，EMA20半仓9.43%/25.23%。保留非完整FIP收益、假设行业价格账及未合格ETF边界。
- 原文和反例：FIP不识别每日幅度/先后；相同日线OHLC两路径的日内有符号半方差比例可反号；一般IC门槛/严格分层不证明有效；投资者身份不能由开收盘/成交量推定。
- 验收：主控独立读取当前报告及后续修订、代码、FIP图表数据、切割验收JSON、行业policy CSV；重新核核心差额；合成算例运行完成；归置检查与本次登记diff空白检查通过。无源码改动，无新金融测试。
- 预算：4/6公开文献工具请求（含访问失败），1批合成反例/保存汇总核验，0新行情/拟合/金融回测/付费，1名代理。旧研究预算与已看历史身份未重置。
- 失败留痕：预检绝对路径两次拒绝、否定network关键词一次拒绝，改为相对路径/明确local-only后ready才派发；FIP旧域跳转失败后作者新域成功；T&F/SSRN完整页403，没有冒称全文已读；猜测summary路径不存在，改读已存在原产物。
- 依赖：新效力研究仍需对应PIT财报/预测/名单/分钟数据和完整执行规则；本次采用问题已回答，无待执行必要核验，不存在后台任务。
- 历史：初始登记7ea670559f127b4c2baf24fe9dad556315bac91a已逐字读回；初始00:00日期占位在本版改为交付时点。本地状态含准确工具时间和来源指纹；没有上传用户附件或金融原件。

## 2026-11-05 盈利数据与候选接续

- checked_coordination_sha: 27aa9b5d689e78c98b3e09913eba7c726688671e；checked_at/updated_at: 2026-11-05T18:41:53.040488+08:00。已读COORDINATION、gemini-factor-fit-20261104、pro-advice-process-review-20261020、lowfreq-strategy-discovery-20261019、classic-factor-research、research-dispatch-controller。
- 授权：用户“可以的，开始吧”，接续盈利超预期与分析师预期修正的数据资格和可算候选；不改生产、交易或旧冻结。原审查仍为completed，本阶段active。
- 基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；脏区保留，成果尚未提交或推送，仅本地。
- 唯一写者root：docs/experiments/earnings-candidate-readiness-2026-11-05.md；docs/experiments/raw/earnings-candidate-readiness-2026-11-05/**；registry.json仅本键；INDEX.md仅本行；docs/ops/work-progress/gemini-factor-fit-20261104.md。仓外原任务earnings-stage-20261105和独立外盘输出属本任务。
- 重叠决定：季度财报旧负责人已完成释放；复用原件和验收，不改旧产物。唯一Sol只读原财报，network=false、write_paths=[]；不与其他研究重复运行。
- 验收：来源指纹、连续八个先前季度分母、同申报配对和保守SEC时点、预测财政期/历史版本/机构分母资格；可算和可回测分开；绩效与增量缺失明示；登记及归置读回。
- 新阶段预算6次来源工具请求、4批有目的核算、1名代理、0付费；旧阶段4来源/1合成/0收益实验保留，未重置。外盘身份已核；原件与新JSON留外盘，内盘小报告。
