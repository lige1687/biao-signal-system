# 全球AI每日核验：2026-10-07

## 一句话结论（大白话）

本轮新增是Anthropic扩大专业安全研究的模型访问、Google发布可以本地检索代码及多媒体的轻量模型，以及iPhone查看电脑任务和剩余额度的组件。前两项分别改变行业能力开放和资料检索选择，第三项直接方便用户工作。没有证据建议购买新套餐或切换模型。

## 范围与验收

北京时间10月7日09:02触发。沿用research-closure和9月30日DevDay补核、10月4—5日已提醒信息；10月6日日报文件未找到，不假定已经扫描。窗口10月5—7日，并补看近七天。仅公开来源核验，不安装、不付费、不变更生产、不外发、不写外部台账。验收是日期、官方事实、可用条件、基准与限制、来源保存及归档检查；实际请求按raw保存，不设置任意六次停止点。

## 排序及增量

1. Anthropic CVP扩大（官方10月6日，时区/时刻未知）。此前Glasswing与CVP分别服务有限组织，现在合并成三级：Defense、Red Team、Specialized。合格安全人员申请可获得先进模型及较少误拦截；并非普通Claude套餐自动解锁。官方Opus5.5测试每档10种任务各5次：一般访问50次首提示全被挡；Defense46/50过程中被挡；Red Team无拦截，34/50成功。证据支持访问规则改变，不是新模型智力突增，也不等于所有安全任务成功率68%。排第一因影响专业软件安全工作方式。普通自有源码审查和已知问题修复仍可用一般模型；当前LEI无需申请。数据保留有要求和部分例外，未来EFS仍是预告。行动：若以后承担专项安全研究再核申请与资料处理条件。
来源：https://www.anthropic.com/news/cyber-verification-program

2. EmbeddingGemma 2（官方10月6日，时区/时刻未知）。把代码、文字、图像、音频和视频转换成可比较的表示，用来找相关资料；不是生成答案的聊天模型。740M参数，纯文字部分270M；Apache2.0，权重已提供。厂商MTEB Code从68.76至78.68，增加9.92分；Pixel11Pro量化权重活动内存文字约191MB、完整约567MB，不是整个应用内存或Mac实测。8K上下文。排名第二因为可以改变本地代码与文献检索的成本和隐私方式，但LEI增量尚未测试。行动：作为三天任务的检索候选，先与现有rg和目录检索比较找准资料的表现；本轮不安装、不把候选当已交付。
来源：https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/

3. ChatGPT iOS 1.2026.267（官方10月2日，时区/时刻未知；本轮补核）。主屏组件展示选定电脑最近任务；主屏/锁屏组件显示剩余额度和恢复时间。官方发布记录已列出，账户/设备实际显示未验。排名第三因为对用户直接方便，但不是模型或Cloud执行能力提升。行动：已有iPhone时查看组件是否可添加，本轮不自动更新或配置。CLI0.160.1的10月5日变化只针对远程Windows MCP启动环境变量，当前Mac用户无证据需采取动作。
来源：https://learn.chatgpt.com/docs/changelog

## 覆盖、反例和失败

四组检索涉及OpenAI、Anthropic、Google/DeepMind、DeepSeek、Qwen、Z.ai、Moonshot、MiniMax、Ai2、Meta。官网打开核对OpenAI新闻/Codex日志、Anthropic完整新CVP说明、Google目录及Embedding全文、DeepSeek目录；Qwen零行，MiniMax打开内部错误，国内完整覆盖未达到。Z.ai/Moonshot/Meta仅检索范围，不能称逐家完整官网核查。社区Dots额度讨论和浏览器默认行为只是用户反馈/请求，未作为新功能。
GoogleSuncatcher原型卫星线索只打开入口未完成正文证据核对，保留未验证，不当第三项已核重大消息。DevDay基线、Ai2和流感预测不重复；新发布日期不等于旧模型新发布。未独立复验厂商成绩，未检查所有服务状态。

## 结案与限制

以上三项官方发布核验完成；全球全面覆盖及Suncatcher候选仍未完成，不宣称全球无其他变化。execution_status=completed仅指上述限定交付，evidence_status=supported指发布事实；跨厂商完整覆盖保留缺口。raw五批工具资料保存，登记读回并运行目录检查。未提交、推送或修改策略。

