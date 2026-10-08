# V8 制作记录

60秒六节点趋势交易编年史；无品牌、无旁白、无真实行情。4K和1080均完整解码通过。1080浏览器从头实播到60.011秒结束，无错误。

完整方法与史料见 docs/experiments/video-information-density-2026-10-08.md。媒体指纹见validation.json，源为studio/src，时间表为cue-plan.json。

磁盘不足导致两次制作记录写入失败，无删除；缓存清理待用户许可。当时归档和远端保存尚未完成；后续恢复见下文。

## 收尾恢复与验收
用户明确许可只删除v7/npm-cache后，删除该431MB可下载缓存；没有删除其他视频、源、素材或依赖。磁盘恢复563MiB，归档继续，原磁盘失败保留。

4K实际播放到38.186秒，3840×2160、readyState4、无error；1080从头到60.011秒ended。两文件均1800帧/30fps/AAC/60.011秒，完整解码。八处最终实际帧与10秒复杂段接触表均已查看。TypeScript、音画时间表和公开文案/页面品牌检查通过，品牌反例被拒绝；主观观感待用户。

复用V7 Remotion4.0.534/React19.2.3、系统Chrome与FFmpeg，没有新安装、付费媒体或子agent。studio/node_modules为本机符号链接，照片和音乐为硬链接，不覆盖源素材。进入studio运行remotion bundle src/index.ts，实际输出studio/build；用生产包URL/v8/studio/build渲染TrendChronicleV8，--scale=2 --crf=19 --jpeg-quality=92 --concurrency=2及系统Chrome路径。finish-media.py解码、转1080、抽帧。ffprobe工作目录为现有Remotion动态库目录。

静帧后书本标签修为书目信息示意，论文说明明确历史延续性，重新打包后再导出最终片；无失败全片重渲染。bundle第二位置参数未改变输出目录，改用实际build目录。原生4K文字与矢量，档案照片原始847×1229，照片不称原生4K。

音乐Oxygen Garden by Chris Zabriskie，Divider，CC BY4.0；官方录音42—102秒，截取、淡入淡出、响度调整和原创音效混音。片尾与播放页均署名。
https://chriszabriskie.com/divider/ · https://chriszabriskie.com/use/ · https://creativecommons.org/licenses/by/4.0/
实测−17.1LUFS、真峰−1.7dBFS、响度范围3.2LU，未完整主观听审。

利弗莫尔照片为1923年Financial World档案，作者不详，Commons标注美国公版；裁切、色调与遮罩处理。
https://commons.wikimedia.org/wiki/File:Jesse_Livermore_(c._1923).jpg

账号周额度43%→45%，显示变化2个百分点，账号共享且整数显示，单任务精确占用未知。
