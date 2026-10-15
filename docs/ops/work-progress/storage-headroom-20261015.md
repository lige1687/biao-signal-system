# 双均线研究内盘余量恢复

更新时间：2026-10-15T20:45:49.390165+08:00。设备：本地Mac。负责人：01a13f90-f5ca-7111-ac4f-4afd655b71f3。

## 当前结果：已完成

20:58实际内盘可用16570871808B（15.433GiB）。主仓和主研究的factor-evidence-integration-20261012工作目录均通过原plan_output，内盘保留线仍5GiB，预检仅只读规划，0新研究或输出目录。

用户明确允许保存既有B站草稿、正常退出Chrome并清理Cache/Code Cache两处缓存。草稿3986516保存后，独立新标签草稿列表显示更新时间2026-10-15 20:55:00；未改内容、未发布。Chrome最终进程为0，两个目录已清空移除，个人资料/登录/扩展检查项未变。

Chrome两缓存共移除78465个条目，普通文件内容1069335567B（约1.07GB）。清理窗口实际可用14958858240→16603172864B，净增1644314624B（1.531GiB）；同期系统也回收空间，不能全部归因缓存删除。正常退出Chrome前20:49:40可用2406199296B，20:58为16570871808B；期间交换文件分配从20GiB降至12GiB，本任务未删swap或快照。

先前旧更新包已核验归档移除，但当时实测净变化-10498048B；这段失败保留，不能把旧包内容大小当作物理释放量。现已达到5GiB以上再留约1GiB的任务目标，不继续扩目录清理，不恢复Chrome造成缓存回写。

## 准确处理清单与恢复

唯一处理源：`/Users/yongbiaoli/Library/Caches/com.openai.codex/org.sparkle-project.Sparkle/Installation/0U9VRSSL6`，内部旧ZIP及解包的ChatGPT.app版本26.1007.21159/build20052，早于当前安装26.1007.30912/build20156。

归档TAR：`/Volumes/win+mac通用/个人资料归档/LeiSignal-内盘余量-20261015-01a13f90/obsolete-update-0U9VRSSL6.tar`，2458030080字节，SHA-256 `68fba3add9d8d63a79081d5fc41c149d3f3f2691cd9e1378fa82b9808c80cda8`。

共3978普通文件、5076目录/文件/符号链接条目，普通文件内容2449126654字节。逐文件内容SHA-256、大小、类型、权限和链接目标与TAR完整读回相符；扩展属性以base64另存manifest，未声称已完成实际应用恢复安装。

清单：`/Volumes/win+mac通用/个人资料归档/LeiSignal-内盘余量-20261015-01a13f90/manifest.json`，SHA-256 `1f897415cd51a3452b159bcf26ebd279a5020b23e37ee605e1967f10322548ce`；同目录`恢复说明.md`、`removal-receipt.json`保留。恢复先核TAR指纹，在有空间的新空目录解包后核每文件和元数据，禁止覆盖当前应用或安装旧版。

移除前完整源二次指纹相同、固定外盘UUID正确、lsof无句柄；同盘改名到本任务临时目录后再次核源，按5076个精确清单项移除。源和临时目录均已不存在。当前安装版与较新待安装版Info.plist的inode/内容未变。较新aNd8bPrCq、Sparkle Launcher/Updater全部保留。

## 首轮保留与待决定清单（历史，后续处理见末节）

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

## Chrome准确授权后接续：未保存草稿阻止退出（2026-10-15T20:53:09.608006+08:00）

- 人类在原研究对话明确答“允许退出Chrome并清理这两处缓存”；已登记并读回协调commit ee3e76e8。该许可持续有效，不重复询问缓存授权。
- 正常退出命令返回成功但进程仍在、Cache/No_Vary_Search/journal.baj仍有打开句柄；未据返回值执行清理。菜单正常退出与按住⌘Q后，实际出现“离开此网站？系统可能不会保存您所做的更改”。
- 选择取消保留页面后，定位到B站《美债收益率超过5%，美股为什么还没崩？》既有草稿编辑页。未点击“离开”、未存草稿、未投稿、未改表单内容。原授权未明确丢弃或改写视频草稿，已合并询问“保存草稿再退/放弃未保存更改/保留页面暂停”。
- 两缓存目录仍在，删除0文件；没有强杀进程或绕过占用检查。准确清理脚本已准备且仅语法检查，待Chrome真正退出并无句柄后才可运行；脚本会核个人资料/登录数据库/扩展目录保留。
- 2026-10-15T20:52:34.128217+08:00内盘可用3937689600B（3.667GiB），原plan_output仍拒绝5GiB保留要求。本轮退出前曾测得2406199296B，后来的自然变化不算清理释放。
- 当前阻塞：未保存草稿处理决定；恢复条件是用户选择保存或放弃，之后继续正常退出、无占用、准确两缓存清理和容量预检。现有缓存清理授权不撤回，其他资料/快照/swap/保留线仍保护。
- 小证据：data/cache/storage-headroom-20261015/chrome-before-quit.json、chrome-draft-blocker.json；本轮无缓存归档或成功移除回执，不冒称已完成。

## 最终完成：草稿保全、两缓存清理、原预检恢复（2026-10-15T20:59:16.673529+08:00）

- 人类最终批准“保存该草稿，再继续退出”，原研究对话另转达“只保存草稿、不发布，再退出清缓存”。只点击一次存草稿；通过独立新标签列表核同draft ID及20:55更新时间，原标签DOM短暂滞留不误判失败、不重复保存。没有投稿、话题/声明/标题/简介变更。
- Chrome正常退出请求后有延迟；最初仍有进程/占用，未清缓存。最终36→0 Chrome进程，重新执行完整lsof空输出/空错误验证后才处理。未强杀、未重启系统、未碰Codex会话或其他工作树。
- 两准确源：`/Users/yongbiaoli/Library/Caches/Google/Chrome/Default/Cache`和`/Users/yongbiaoli/Library/Caches/Google/Chrome/Default/Code Cache`。清单78465条，内容1069335567B；逐条inode/device/type/size/mtime与清理前一致，无符号链接外扩。两源均不存在。
- 保护核查22项，包括个人资料目录、Preferences、Secure Preferences、Login Data、Cookies、Extensions、Bookmarks、Sessions、Local Storage、IndexedDB；文件内容hash/大小及目录inode/device/mode前后相同。未重新打开网站验登录状态，结论是保存资料文件未改，不冒称各网站登录有效。
- 两浏览器缓存是用户明确同意丢弃的可再生成数据，无归档副本；恢复方式是下次打开Chrome/访问网页重新生成。旧更新包仍有前述完整外盘TAR恢复副本。
- 20:58真实storage固定UUID正确、4资源available、外盘559455928320B。主仓plan_output传外盘结果/日志1GiB、本机小记录1MiB，保留5GiB/外盘10GiB不变，通过；主研究工作目录实际同样通过，free16562909184B。只输出计划，execution_authorized=false、结果目录未创建，不把存储通过当研究完成。
- 本机完整证据：`data/cache/storage-headroom-20261015/bilibili-draft-saved.json`、`chrome-cleanup-receipt.json`、`chrome-final-preflight.json`、`research-worktree-preflight.json`。清单含私人路径仅本机，Git只此小进度摘要。`chrome-cleanup-receipt.json` SHA-256 `fd569cd510e7c98b9bc13d2e9d02b1585d0e5bc37cc0b9138d68a7f295ec9587`。
- 归置检查通过；状态completed，0后台清理/监控。新操作前需重核容量，不保障其他进程之后不写盘；主研究负责人自行按真实合同/估计重新预检即可继续。
- checked_coordination_sha `97c8d02b5f55e4418628e7d4fb59c7fee0d82276`；已读原5任务和treasury-yield-video-20261013，准确草稿保全由用户授权，不接管其制作或发布。成果只本进度，最新提交由对应分支git log定位，协调另记录远端成果SHA。无需向其他聊天发消息。
