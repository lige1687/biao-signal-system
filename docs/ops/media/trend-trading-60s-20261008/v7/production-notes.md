# V7 重做记录 · 2026-10-08

## 当前状态
新版已完成实际导出：60 秒、1800 帧、4K 与 1080P 均完整解码通过，最终八处时间画面已检查。1080P浏览器从头实播至60.011秒结束、无错误；观感由用户验收。没有删除下载缓存或旧片。

## 本轮改变
参考原片的深色底、金色图形、宋体层级，重新制作画面；不复制原片的具体镜头内容。用真实历史照片、镜头拉远、价格突破和规则卡展开承担解释，不再使用 V6 的卡通人物与固定纸面讲义布局。无旁白，无真实行情案例。

## 参考证据
- 用户原参考：https://www.douyin.com/video/7691894559067910566 。浏览器实际可播放，查看约 30.85 秒“波动聚集”画面；没有完整听审，不能确认原音乐或全部剪辑节奏。公开解析接口本轮失败 douyin_api_forbidden，未改权限或绕过。
- 已有教程缓存复用，查看 main 教程 296—307 秒连续抽帧：问题、选项、翻页、年份、真实照片、局部推近、下划线依次发生。保存 reference-motion-contact.jpg；只代表这段视觉证据。
- 史实及 LEI 语义复用 docs/experiments/code-explainer-video-2026-10-08.md 的来源与核验，不把时间先后说成直接师承。

## 素材署名
“Oxygen Garden” by Chris Zabriskie, from the album Divider (2011).
Licensed under Creative Commons Attribution 4.0.
https://chriszabriskie.com/divider/ · https://chriszabriskie.com/use/ · https://creativecommons.org/licenses/by/4.0/
使用官方录音 42—102 秒片段，调整响度、淡入淡出，与本地原创短扫频/低频音效混音。未复制参考视频音轨，未进行完整主观听审。

利弗莫尔照片：Financial World，1923-11-03，摄影者不详；Wikimedia Commons 标注美国公版。影片裁切、加淡褐色和渐变遮罩。
https://commons.wikimedia.org/wiki/File:Jesse_Livermore_(c._1923).jpg

## 工具与约束
Remotion 4.0.534 / React 19.2.3 / 系统 Chrome / FFmpeg。官方 create-video blank 模板，本地依赖和 npm 下载缓存在 v7 内；npm 报告 10 项 high 依赖告警，未部署公网，未擅自升级依赖。没有调用付费视频或语音服务。

## 已知失败与修正
- 最初批量写入因同一路径同时 Add/Delete 被拒绝，未造成部分写入，改为正常编辑。
- TypeScript 首次检查有未使用 React 导入，已移除。
- 利弗莫尔实帧检查发现镜头平移裁到名字，已让名字补偿位移。
- 唐奇安预览发现图表平移裁切标签，改为保持左侧位置并缩小。
- Remotion 首次仍帧导出成功；多次影片导出遇 ENOSPC。相关错误保留 pilot-render.log。
- 将 Studio URL 直接用于 renderer 不兼容，返回 getStaticCompositions 未定义；不沿用该办法。

## 当时恢复条件（已解除）
以下为磁盘不足时的记录；21:16容量恢复后已解除，不再等待缓存删除许可。
先得到仅删除 v7/npm-cache 的用户许可（已提问，未收到回答），或用户自行释放磁盘。保留所有旧视频。再从 studio 执行本地 Remotion render src/index.ts，先导出 10 秒 LivermoreStudy，检查后导出 TrendHistoryV7，完整解码并实际播放。导出之前不得声称完成。

## 21:16 空间恢复
可用空间复查约2.5GiB，本agent未删除任何文件，原因未归因。缓存删除请求不再阻塞本轮。小样10秒已完整解码；pilot-motion.jpg实际导出接触表确认名字完整、价格线增长与镜头平移。正在导出60秒3840×2160版本。

## 成片检查中的局部修正
4K初版8处时间抽帧发现开头价格线与说明文字相交，已把说明移到独立底部区域，单独重渲染0—119帧，再接回4—60秒。其余镜头保留；FFmpeg重编码保证连续1800帧。opening-checked.jpg核对不再相交。首次修复命令因工作目录错误未改到源码，第一次短渲染未采用；随后修正并真实导出 opening-final-4k.mp4。
Remotion内附ffprobe最初缺动态库搜索目录；从其lib所在目录调用成功，无安装或系统配置变更。原失败日志保留finish-validation.log。

## 最终产物与复现
- 成片：trend-history-v7-4k-final.mp4，3840×2160@30fps；预览：trend-history-v7-1080-final.mp4，1920×1080@30fps；均1800帧，音频AAC，容器60.011秒，准确SHA见validation.json。
- 原生4K文字和矢量图形；档案照片原始847×1229，保留旧报刊颗粒，不将照片本身称为原生4K。
- 工具实际为Remotion4.0.534、FFmpeg及系统Chrome；字体使用macOS Songti SC / PingFang SC。源码包含全部确定性动画，音效sound.py固定随机种子。
- 音乐混音60秒完整解码，−17.0LUFS、真峰−1.6dBFS；这是技术音量核验，不冒充主观听审。
- 所有素材许可与改编署名在播放页；没有付费生成、TTS或发布。
- 完整重现：进入studio，使用本地remotion render src/index.ts TrendHistoryV7，设置--scale=2、--crf=19、--jpeg-quality=92和系统Chrome路径。最终开头修复已在源码，不需要再次分段拼接。照片和音频可从上方官方来源恢复；本机依赖/缓存/媒体未推送Git。
- npm下载缓存保留，删除请求因空间恢复不再需要处理；磁盘变化原因未确认。
- 本轮账号周额度显示40%→42%，变化2个百分点；账号共享且整数显示，不能精确归因本任务。

浏览器最终验收：1080P从0实播至60.011秒ended=true且无error；4K链接实际播放到14.939秒，3840×2160、readyState=4、无error。最终页面回到开头待播放，4K与1080下载链接均对应最终文件。
