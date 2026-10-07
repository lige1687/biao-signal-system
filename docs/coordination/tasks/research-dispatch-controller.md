# LEI 八目标研究调度（中控Git摘要）

- task-id：research-dispatch-controller
- 更新时间：2026-10-07T22:43:59+08:00
- 状态：active（研究执行分别在原四对话；本记录不代替其原负责人状态）
- 研究调度负责人：[本轮中控](codex://threads/01a116c7-3700-7062-a6c6-53af00ef60a0)；本记录唯一Git写者：[协调入口](codex://threads/01a10051-4db1-7490-b40f-c13243767fc6)。
- 原始目标：为个人周／月频趋势判断，推进可定位、可复算、可审查的八类成果；日／小时资料是辅助，周检查不意味着每周换仓。
- 用途及验收：每条线用已冻结问题、基准、代码／输入指纹及独立核验交付；区分计算正确、观察关联、稳定增量和可执行策略改善。研究流程优先，不用测试数量作成果。
- 适用规范：各执行分支AGENTS.md、current-standards.json实际版本、原合同和定义；本摘要不迁移旧冻结协议。Git规则COORDINATION.md 1.0；下一阶段补明确SHA查重。
- 本记录协调基线：24f40fc9131c86aec5ad5bb678743e3ca5868333。成果工作分支codex/lei-coordination-refresh-20261007，基线34b6435a915b7adeff8f8c04484fb75295e908c1；本轮成果未推。四线实际新成果分支／commit尚未交付，不能把旧分支SHA冒充本轮工作。
- 来源：本地docs/ops/work-progress/research-dispatch-controller-2026-10-07.md与用户交接；App四线快照均active/inProgress。源阶段记录尚未推送；原研究数据与成果是否远端可复现各线待交，未验证。

## 当前八目标

|目标|执行负责人／状态|本轮范围、依赖与验收|
|---|---|---|
|1 核心计算|[技术原对话](codex://threads/01a0e703-4c27-74e2-bf77-997e1879f967)，active|仅D—MAE真实消费链的结构／信号时点、价格、日历、截断与小例；复用旧审计，改动影响的旧结果才重核。|
|2 旧结论复用|[目录原对话](codex://threads/01a1074e-3d9d-70a2-a771-b079443ace18)，completed（已交，待中控独审）|对问题、资产池、代码／输入、基线／窗口、数字、局限、失效替代关系做证据目录；5211云端交接和本地旧82等结果分开。|
|3 D与未来不利幅度|技术原对话，active|D=(A−C)/ATR20_SMA，对照100×ATR/A；从t+1至t+21的21个收盘价衡量不利走势，不把C放进目标；75成熟／1未知，保留去重76案例与依赖；等准确原输入、实现独审和中控阶段批准才一次算标签。|
|4 个股资料资格|[数据原对话](codex://threads/01a101c1-ac35-70a3-8ecd-4a6179bb99ad)，completed（已交，待中控独审）|只补下一实验实际需要的成员／身份、退市、公司行动、交易可用性、行业；1944分类无需重做，价格修复仍0；5211名单不冒充历史全A池。|
|5 融合／仓位／退出|中控保留依赖，planned，执行者未指定|可靠特征和合格数据后再派简单同风险对照；资金、成本、换手和踏空均核，真实风险预算／集中／杠杆未知，模拟不是默认账户设置。|
|6 原生研究流程|[流程原对话](codex://threads/01a0e6d5-4bcf-7bd3-82e4-4961c963d20e)，active，优先|复用契约、账本、锁和回执，以D—MAE走真实链；唯一共享研究入口整合负责人；8项旧指纹失败保留，不改冻结证据凑绿。|
|7 外部增量／独审|[外部原对话](codex://threads/01a0cd21-07e5-7163-8f4e-72a4d5ebc32e)，planned／等中控派可审交付|先独立核准确合同、实现与数值；无明确缺口不新装平台；Qlib Ridge计算一致不证明收益增量。没有本輪新任务启动证据。|
|8 存储／恢复|各线测量，中控汇集，active（执行前义务）|开工重测实际空间和输入／输出预算；13.63GiB本机／602.17GiB SSD只是中控接管时测量；数据库、代码、锁留本机，SSD不算独立盘备份；403保持暂停。|

## 四线写入边界和依赖

|线／稳定子工作名|唯一执行写者|已登记可写路径|依赖／禁止事项|
|---|---|---|---|
|native-risk-d-mae|技术原对话|docs/experiments/raw/native-risk-d-mae-2026-10-07/；同题日期报告|共享入口和全局定义只读；原设计、输入SHA、独审、阶段批准缺失不算真实标签；与流程线共享接口先交候选，由流程线实现。|
|stock-data-qualification|数据原对话|docs/experiments/raw/stock-data-qualification-2026-10-07/；同题日期报告|现有资料资格进度由其原负责人维护；不改行情缓存、旧冻结输入或其他线代码；不重跑PPO/P26。|
|research-evidence-catalog|目录原对话|docs/experiments/raw/research-evidence-catalog-2026-10-07/；同题日期报告|只整理保存证据，不新增市场计算，不向执行线再派发，不覆写失效报告。|
|native-workflow-integration|流程原对话|docs/experiments/raw/native-workflow-integration-2026-10-07/；同题日期报告|共享入口是唯一整合角色，但具体src/scripts文件尚待其列出并推送查重；未登记准确路径不能写。原合同是设计提案非native_workflow_contract，不直接当执行合同。|

共同registry.json、INDEX.md、definitions.v1.json由中控串行安排登记，各线先交候选；目前四线只读。研究调度与本记录Git整合分工不改变原负责人归属。其他旧任务仍有范围，历史记录过期不代表可抢占。

## 输入、结果与停止边界

用户提供D—MAE设计ZIP，22485字节，SHA256=1f9841f63fd44794d4d20f3ee948dc6234251f496cc6cf1cbd381a43418b3025；原合同SHA=ace132ddb89de3e45951148d9673524fa9fe448f662f2576221d216bbe9717c6，中控已核，两条原对话已收到。此处引用中控回执，非本协调方再次独审；不上传包和原价格。PASS_IMPLEMENTABLE仅设计，原budget=0文件不改；新阶段许可须中控依据代码／来源／成员落准确执行记录。33组固定删除诊断使用同一已保存标签，0新拟合／重采样／新窗口。

已封存数值仅交接待原件核验：PPO 147周／626092有效行、平均排序关联−0.08272，对照20日涨幅−0.07870，差−0.00402；P26 142周／622658共同支持，高低持续性差−0.1701个百分点，年度不稳，残余PPO秩差约+8.47百分点。旧B1仅11对、差−9.09百分点且由1对驱动。现金回放仅6与4次往返，不能泛化；不因此重跑封存实验。1944键1601正常／339占位／4旧无返回，分类不是价格修复或真实停牌证明。

检查／预算：本协调0行情／0标签／0拟合；各线累计预算必须据原账本，当前未核完整用量。四线App运行已核，不代表成果验收。真实输入、独审与阶段预算等待技术／流程和中控回执；共同登记、真实交易、付费、部署、删除、403重试、仓外OKR数据库均未执行。Git目标摘要不冒充系统待升级数据库已同步。

## 可定位入口与最小接续

[技术旧权威记录](lei-technical-reader-research.md)、[资料旧权威记录](risk-shape-information.md)、[流程旧权威记录](classic-factor-research.md)、[外部旧权威记录](external-quant-resources.md)均保持原作者，只读。四线新产物链接与准确commit在交付后按本记录补；目前原机路径可在原对话读，尚未推送，Git不能复算，不能用空链接装作已交。

每轮开始、范围变化、交付前先fetch并读COORDINATION.md、本摘要和相关原任务，记录完整checked_coordination_sha、时间、相关task-id和冲突决定；先定唯一写者。网络失败先停可能冲突的修改，不影响已有授权的独立只读核查。下一操作：各线列准确共享文件并登记→实现与合成回调→中控独审／输入与阶段批准→真实一次计算→独审／归档。中控有实际心跳leisignal（每30分钟）回执，但离线／工具／额度不足不能保证继续跑。

较上一版新增：首次真实四线快照与本轮八目标、边界和原合同交接；未替其他任务宣布完成，未启动目标5或目标7新计算。

## 最新快照与同步失败（2026-10-07，Asia/Shanghai）

原先四线启动快照保留，不能视为永久运行状态。新续接已由中控说明gpt-6.1-sol请求HTTP400 model not supported，改用gpt-6-sol/high；这是请求配置，实际模型未独立核实，旧失败turn及部分产物保留。最新App快照：技术turn 01a116e8-7d52-70f3-8edb-4ea654aca288 active/inProgress，76案例／原D仍缺；数据turn 01a116e8-7e5f-7103-8ffb-9a0e62aa5db6 completed，属于交付者报告已完成，待中控独审；流程turn 01a116e7-dc94-70a2-9ac8-1d637e7c406c active/inProgress，合成复现停牌行MAE资格差异，不能套通用标签。目录线补核App：turn 01a116e8-7ee6-7c62-a392-46d7ddb2c616 completed，报告已交，待中控独审；此前未返回的快照不当作持续运行证明。

本轮Git尚未同步。远端最后实读为ccc290e9b1c13286252c77ff281fbada8c1206c1；待推开工提交c02c39bb10d6d0cc9755690a46b07eca210cfd99。普通SSH推两次Internal Server Error；线性重建与--no-thin传完整对象仍同错，四个失败request-id：EA15:207E18:2B71A:6BC71:6AC66018、E442:160914:2C517:6D86D:6AC66056、E4E4:3DC181:2C68B:6E4B4:6AC660EB、EFB0:30E70A:2C9FC:6E787:6AC6611E。HTTPS尝试无可用现有Git/API凭据且连接等待无进展，已结束该本次进程。fetch成功不等于push成功。未强推／删除／修改安全设置；共享冲突修改保持未准入。

原研究产物仍按各线独立推进，不以本协调失败宣布全部研究停止；本摘要及规则／工具是仅本地，远端不可复现。恢复条件是同仓库普通写入恢复，或提供对该仓库已有授权的可用写入通道；恢复先fetch并审阅最新范围，整合本地准确文件，普通推后核完整SHA和内容再开放涉及冲突的修改。

## 同文件的可检查分工（非权限或锁）

具体共享代码尚未登记；此处不声明其范围。依赖指交付前置，不强制所有准备工作等待。原负责人只有显式更新后才能成为更精确实时依据。

```lei-coordination-json
{
  "schema_version": 1,
  "record_id": "research-dispatch-controller",
  "checked_coordination_sha": "ccc290e9b1c13286252c77ff281fbada8c1206c1",
  "checked_at": "2026-10-07T23:18:13+08:00",
  "snapshot_only": true,
  "assignments": [
    {
      "task_id": "native-risk-d-mae",
      "owner": "01a0e703-4c27-74e2-bf77-997e1879f967",
      "status": "active",
      "write_paths": [
        "docs/experiments/raw/native-risk-d-mae-2026-10-07/",
        "docs/experiments/native-risk-d-mae-2026-10-07.md"
      ],
      "depends_on": [],
      "scope_released": false,
      "source": "controller allocation; implementer record remains authoritative; new output commits unverified"
    },
    {
      "task_id": "stock-data-qualification",
      "owner": "01a101c1-ac35-70a3-8ecd-4a6179bb99ad",
      "status": "completed",
      "write_paths": [
        "docs/experiments/raw/stock-data-qualification-2026-10-07/",
        "docs/experiments/stock-data-qualification-2026-10-07.md"
      ],
      "depends_on": [],
      "scope_released": false,
      "source": "controller allocation; implementer record remains authoritative; new output commits unverified"
    },
    {
      "task_id": "research-evidence-catalog",
      "owner": "01a1074e-3d9d-70a2-a771-b079443ace18",
      "status": "completed",
      "write_paths": [
        "docs/experiments/raw/research-evidence-catalog-2026-10-07/",
        "docs/experiments/research-evidence-catalog-2026-10-07.md"
      ],
      "depends_on": [],
      "scope_released": false,
      "source": "controller allocation; implementer record remains authoritative; new output commits unverified"
    },
    {
      "task_id": "native-workflow-integration",
      "owner": "01a0e6d5-4bcf-7bd3-82e4-4961c963d20e",
      "status": "active",
      "write_paths": [
        "docs/experiments/raw/native-workflow-integration-2026-10-07/",
        "docs/experiments/native-workflow-integration-2026-10-07.md"
      ],
      "depends_on": [],
      "scope_released": false,
      "source": "controller allocation; implementer record remains authoritative; new output commits unverified"
    },
    {
      "task_id": "factor-fusion-risk-exit",
      "owner": "01a116c7-3700-7062-a6c6-53af00ef60a0",
      "status": "planned",
      "write_paths": [],
      "depends_on": [
        "native-risk-d-mae",
        "stock-data-qualification"
      ]
    },
    {
      "task_id": "d-mae-independent-review",
      "owner": "01a0cd21-07e5-7163-8f4e-72a4d5ebc32e",
      "status": "planned",
      "write_paths": [],
      "depends_on": [
        "native-risk-d-mae"
      ]
    }
  ]
}
```

### 本地成果索引（未推，Git不可复现）

- [stock-data-qualification报告（本机）](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/stock-data-qualification-2026-10-07.md)：SHA256 e1f4a927df508e936734daccd778ae1f77d2088864b98ebcebe56da428b92c6c；位置已查存在，仅核定位，不替中控独立验收，准确成果分支／commit仍待交。
- [research-evidence-catalog报告（本机）](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-evidence-catalog-2026-10-07.md)：SHA256 6a7f23fa1fe6fa9f53e7e097dbfb76d017c52a7080166a5521f939a88ce4cef5；位置已查存在，仅核定位，不替中控独立验收，准确成果分支／commit仍待交。

本协调本地工具成果分支codex/lei-coordination-refresh-20261007完整commit 4a1bab7301c30b5e3d716a660ddc4df0617460d3（未推）。8项测试、目录检查、原AGENTS前缀保留通过；实际在线查询退出2，读到ccc290e9b1c13286252c77ff281fbada8c1206c1并拒绝尚未登记native-risk-d-mae；离线声明核对退出0但online_verified=false／work_clearance=false。
