# 双均线研究内盘余量恢复

更新时间：2026-10-15T20:45:49.390165+08:00。设备：本地Mac。负责人：01a13f90-f5ca-7111-ac4f-4afd655b71f3。

## 当前结果

已将一个过期、无占用的应用更新下载包归档到外盘并移除内盘副本，但没有观测到正的空间释放，研究预检仍未恢复。本任务等待用户决定是否正常退出Chrome并处理其两处可重建缓存；不自动继续删除。

- 清理前后实测：3787653120 → 3777155072 字节，净变化-10498048字节。不能用删除文件总量代替物理释放量。
- 2026-10-15T20:44:07.012772+08:00内盘可用3590631424字节（3.344 GiB），外盘559455928320字节。既有plan_output使用1GiB外盘结果/日志估计及1MiB本机记录估计，保留5GiB内盘线，实际拒绝：insufficient internal capacity for metadata and 5 GiB reserve。
- 开工20:37内盘4937035776字节，此后持续下降。当前系统交换文件分配20GiB、存在20:42本地快照，无法隔离各项影响；未改快照、交换文件、备份设置或停止任何应用。

## 准确处理清单与恢复

唯一处理源：`/Users/yongbiaoli/Library/Caches/com.openai.codex/org.sparkle-project.Sparkle/Installation/0U9VRSSL6`，内部旧ZIP及解包的ChatGPT.app版本26.1007.21159/build20052，早于当前安装26.1007.30912/build20156。

归档TAR：`/Volumes/win+mac通用/个人资料归档/LeiSignal-内盘余量-20261015-01a13f90/obsolete-update-0U9VRSSL6.tar`，2458030080字节，SHA-256 `68fba3add9d8d63a79081d5fc41c149d3f3f2691cd9e1378fa82b9808c80cda8`。

共3978普通文件、5076目录/文件/符号链接条目，普通文件内容2449126654字节。逐文件内容SHA-256、大小、类型、权限和链接目标与TAR完整读回相符；扩展属性以base64另存manifest，未声称已完成实际应用恢复安装。

清单：`/Volumes/win+mac通用/个人资料归档/LeiSignal-内盘余量-20261015-01a13f90/manifest.json`，SHA-256 `1f897415cd51a3452b159bcf26ebd279a5020b23e37ee605e1967f10322548ce`；同目录`恢复说明.md`、`removal-receipt.json`保留。恢复先核TAR指纹，在有空间的新空目录解包后核每文件和元数据，禁止覆盖当前应用或安装旧版。

移除前完整源二次指纹相同、固定外盘UUID正确、lsof无句柄；同盘改名到本任务临时目录后再次核源，按5076个精确清单项移除。源和临时目录均已不存在。当前安装版与较新待安装版Info.plist的inode/内容未变。较新aNd8bPrCq、Sparkle Launcher/Updater全部保留。

## 保留与待决定清单

| 对象 | 大约大小 | 决定 |
|---|---:|---|
| Chrome Default/Cache | 707 MiB | Chrome运行中，未触碰 |
| Chrome Default/Code Cache | 377 MiB | Chrome运行中，未触碰 |
| Codex浏览器分区缓存 | 981 MiB | 当前应用环境，未触碰 |
| 较新Codex更新下载包aNd8bPrCq | 1.64 GiB | 更新器运行且版本高于当前，保留 |
| .cache/codex-runtimes | 1.52 GiB | 运行环境，保留 |
| 研究raw、数据库、会话、所有其他工作树 | 不按体积筛删 | 全部保护 |

已请求用户决定：是否正常退出Chrome，待无占用后仅处理Cache和Code Cache；这约1.06GiB，且快照/系统持续写入使实际释放不保证，不能许诺达到目标。用户未回复前不停止应用、不动相关缓存。若预检自然恢复，只需再次核实，不为凑量删除。

## 验证与失败

- 归档完整内容和清单：通过；源未变、无占用、固定设备：通过；精确移除及保留版本读回：通过。
- output_storage真实容量预检：未通过；0科研启动，未创建结果目录，未降低阈值。
- `python3 scripts/check_repo_hygiene.py`：通过。
- 首次归档准备因当前Python缺少os.listxattr而退出；尚未创建外盘目录、未删除源。改用macOS libc nofollow读取，完整扩展属性保留，无忽略错误。
- 运行中的一次预检仍低于5GiB，最终预检同样失败，保留实际回执；未将清理执行完写成目标完成。

## 交接与边界

跨任务当前状态：coordination/lei的`docs/coordination/tasks/storage-headroom-20261015.md`。checked_coordination_sha `5d33c483057ee70c20d8cd7010d2a23608cd88e3`；已读mac-local-storage-cleanup、daily-trading-system-audit、research-utility-review-20261012、research-dispatch-controller、investor-workspace-simplification-20261012。旧owner源码和记录只读，无重叠写入。

成果分支`codex/storage-headroom-20261015`，基础`18e64fa632dba5dbad0e5fcae09b4ccc75f119a9`；只发布此小进度文件，提交由git log --本路径定位。私有详细回执和本次操作脚本仅本机`data/cache/storage-headroom-20261015/`与外盘；无数据库、个人内容或大包入Git。主共享工作区原索引/分支未改、他人源码未触碰。

下一动作：等用户决定或用户完成其他任务后释放空间，再读storage及原plan-only。主研究负责人自行读取本记录；不发其他对话消息、不建定时器或长期监控。研究预算0，模型拟合0，真实交易0。
