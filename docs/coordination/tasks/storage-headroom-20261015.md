# 双均线研究内盘余量恢复

- task-id: storage-headroom-20261015
- owner: 01a13f90-f5ca-7111-ac4f-4afd655b71f3 / root
- status: active
- updated_at: 2026-10-15T20:39:17.224401+08:00
- checked_coordination_sha: 971cffd8c0f0d0bf233764ffe1d41a0c3f9db8f3
- read_task_ids: mac-local-storage-cleanup, daily-trading-system-audit, research-utility-review-20261012, research-dispatch-controller, investor-workspace-simplification-20261012
- rules: COORDINATION 1.1；AGENTS；codex-storage-management.md；research-output-storage.md。
- goal: 核验并整理可恢复且闲置的下载缓存，使既有output_storage固定5GiB预检恢复；争取额外约1GiB余量。若自然恢复则不为凑量删除。
- authorization: 用户明确要求分发Codex对话腾合适空间；准确白名单、恢复副本、源未变、无占用后移除；不动个人资料、运行环境、数据库、会话、他人工作树、冻结raw、系统快照或垃圾桶。
- baseline: 主仓18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；2026-10-15T20:37:34+08:00内盘4937035776B，外盘561918115840B，UUID正确。
- branches: codex/storage-headroom-20261015（成果待建立）；codex/storage-headroom-coordination-20261015（协调）。最近成果commit无。
- scope: 本任务docs/ops/work-progress/storage-headroom-20261015.md及data/cache/storage-headroom-20261015/小回执；外盘个人资料归档下新独立恢复目录。仓外只读盘点Library/Caches中下载缓存，候选为Codex Sparkle Installation两个旧包；准确处理白名单后续登记，当前尚未删除或迁移。
- conflict_decision: 旧mac-local-storage-cleanup及daily成果只读复用，不接管其源码/恢复清单；股票研究与机会页所有代码/证据保持。唯一写者本root；新增任务与旧负责人不同，不覆盖旧任务文件。
- verification: 当前容量/固定UUID、候选版本和进程依赖、逐文件SHA/类型、源未变/无句柄、精确删除后readback、既有plan-only实际通过、归置检查。
- completed: 已读规则/原负责人记录；当前空间仍不足，排除了环境和研究快照。
- next: 核旧下载包版本和占用，准确范围同步后归档核验再移除；如含活跃更新则保留并找其他合格缓存。
- blockers: 无；尚无已批准的准确删除白名单。
- research budget: 0研究、0新行情、0拟合；不降低预检、不启动他人研究、不创建定时器、不发送其他对话。
- data: 私有清单仅本机/外盘，未上传；尚无新归档。
- delta: 新独立受托空间恢复任务；不改旧清理owner状态。

## 准确闲置下载包范围 2026-10-15T20:40:24.218512+08:00
- checked_coordination_sha: b67d4d08dd5a7caf58184b4981c163dea5846235；已读上述5 task-id；增量研究owner确认本会话负责空间，无范围冲突。
- 唯一允许处理源：/Users/yongbiaoli/Library/Caches/com.openai.codex/org.sparkle-project.Sparkle/Installation/0U9VRSSL6。名义分配2459414528B；其中旧ZIP及解包的ChatGPT.app为26.1007.21159/build20052，当前/Applications/ChatGPT.app为26.1007.30912/build20156。旧目录2026-10-09修改，lsof完整扫描exit1且stdout/stderr空。
- 保留aNd8bPrCq（26.1007.71326/build20398）、Sparkle Launcher和当前Updater/Autoupdate进程；全部Codex运行环境/会话/浏览器缓存保留。初查/Applications/Codex.app不存在，已按实际进程纠正为ChatGPT.app，不据错误路径作判断。
- 新外盘恢复目录：/Volumes/win+mac通用/个人资料归档/LeiSignal-内盘余量-20261015-01a13f90/；精确TAR/全文件hash元数据清单/恢复说明，逐项核验后再复查源稳定和无占用，任一失败保留源。
- 该旧更新下载缓存符合用户已授权的闲置可恢复范围，不需停止当前应用。没有修改存储阈值、应用配置或研究源码。
