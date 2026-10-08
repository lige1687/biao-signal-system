# V7 重做记录 · 2026-10-08

## 当前状态
60 秒 Remotion 时间线、音乐混音和七个场景已经制作。成片导出暂未成功，原因是磁盘空间不足；不能把 Studio 预览当作成片。用户质感验收待完成。

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

## 恢复
先得到仅删除 v7/npm-cache 的用户许可（已提问，未收到回答），或用户自行释放磁盘。保留所有旧视频。再从 studio 执行本地 Remotion render src/index.ts，先导出 10 秒 LivermoreStudy，检查后导出 TrendHistoryV7，完整解码并实际播放。导出之前不得声称完成。
