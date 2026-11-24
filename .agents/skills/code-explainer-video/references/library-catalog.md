# 推文推荐素材、镜头与案例库

核对：2026-10-09，Asia/Shanghai。读了两原推文、下列七库README/目录/版本信息，额外读了三张shotcraft镜头卡、demos说明、音频署名表、角色动画指南、MV分镜及xilo两份参考文件。**本轮没有安装、运行或整库下载，不把能访问写成可直接出片。**

## 按任务选库

| 来源与入口 | 类型、何时用 | 先读什么 / 具体怎么取用 | 本轮核验与边界 |
|---|---|---|---|
| [HyperFrames launches](https://github.com/heygen-com/hyperframes-launches)（T2） | 完整发布片源码；研究场景衔接、材质和声音落点 | 找匹配项目后读其STORYBOARD.md、index.html、compositions；可从claude-paper-launch、texture-launch-video、sfx-music-launch目录选需求相关者，不直接套整片 | 目录与README已核；代码Apache-2.0，媒体/字体/品牌不在该授权内；LFS素材按需取，不整库拉大文件 |
| [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) / [画廊](https://vincentwei1021.github.io/video-shotcraft/)（T2） | 镜头配方及Remotion实现；先按语义选动作 | 画廊→references/shots具体卡→卡中精确demo路径→demos/README.md查依赖；声音读assets/audio/ATTRIBUTION.md | 当前主表157卡/214预览，另段称216 demo；旧推文152/209是旧值，不据此承诺完整数量。库代码Apache-2.0；音频逐文件核，部分旧SFX来源不明 |
| [awesome-claude-5-5-videos](https://github.com/athemeroy/awesome-claude-5-5-videos)（T1旧名awesome-opus-5-5-videos已重定向） | 来源索引；找类似题材和制作路径 | 从README案例/方法链接回原帖看条件、Prompt和演示；数量是不同统计单位，不等于独立可复制案例 | README与元信息已核；CC-BY-4.0不自动覆盖所链第三方作品；公开内容不含其全部原媒体 |
| [awesome-ai-motion](https://github.com/guanmo-ai/awesome-ai-motion) / [画廊](https://guanmo-ai.github.io/awesome-ai-motion/)（T1） | 中文动效发现库；按知识讲解/叙事/角色等找风格 | 看分类→案例详情→原作者Prompt/源码，记已编目/待完善状态 | README当前581作品/83提示词/27附源码是站方快照；未逐一复现。MIT仅原创脚本，案例素材须核原作者 |
| [ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase)（T1） | p5.js/p5.brush手绘角色起步；确实需要角色表演时 | ANIMATION_GUIDE.md→src与studio.html；先设计姿势/情绪/道具事件，再做中间动作 | MIT；读过指南，未运行。借姿势、错时跟随与阅读节奏，不把其Clawd角色/禁文字/每镜转场当本片默认 |
| [PDoomVideo](https://github.com/JohnHeibel/PDoomVideo)（T1） | 长MV工程与分镜学习；理解多场景如何贯穿同一主线 | STORYBOARD.md→对应src、ANIMATION_GUIDE；看反复出现的场景怎样升级、收尾怎样呼应开头 | 已读分镜片段及README；未核到仓库明确许可证，源码公开不等于可复制。只学组织方法，音乐与角色不搬入本片 |
| [xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video)（T1） | 作者原Skill；查Prompt结构与工程注意点 | skills/xilo-opus-video/references/brief-template.md、craft-rules.md；其他入口code-stack.md、plan-format.md | MIT；已读前两参考。仅按本项目需要整合，不安装覆盖我们Skill，不采用作者默认三方案/纯代码/自评分数作通过条件 |

## 三张实际读过的镜头卡

以下是用途判断与改编建议，不是效果已跑通。卡名不能替代查看实现，也不能把所有历史知识都塞进UI卡片。

- [row-embed](https://github.com/Vincentwei1021/video-shotcraft/blob/5ddbf521038b0a7accfb6dc1e0a9eb29c67277ab/references/shots/ui-entrance/row-embed.md)：适合规则逐条进入同一结构；必须核最后一条落定及阅读时间。可借错时归位，换成可编辑规则条目；不要每条都打音效。实现入口`demos/ui-entrance/row-embed/RowEmbed.tsx`。
- [deck-deal-flyin](https://github.com/Vincentwei1021/video-shotcraft/blob/5ddbf521038b0a7accfb6dc1e0a9eb29c67277ab/references/shots/ui-entrance/deck-deal-flyin.md)：表达大量信息汇入、加速后落定；不适合要求逐条阅读的史实名单，不机械搬26张卡或原节拍。实现入口`demos/ui-entrance/deck-deal-flyin/DeckDealFlyin.tsx`。
- [spotlight-hero-card](https://github.com/Vincentwei1021/video-shotcraft/blob/5ddbf521038b0a7accfb6dc1e0a9eb29c67277ab/references/shots/opening/spotlight-hero-card.md)：适合聚焦一个核心对象；可用在书页细节，但需要高清源与清晰标签。光效只为引导焦点，不能每镜都闪。实现入口`demos/opening/spotlight-hero-card/SpotlightHeroCard.tsx`。

移植时按demos/README核Fixtures、PageCam2D、Motion或纹理路径等实际import；文字、帧率、画幅和镜头时长重新核。带截图的demo要换成自己的素材，别把假UI当事实；只移植一个镜头需要的依赖。跨框架只能借动作关系，不能承诺源码直接兼容。

## 配乐与音效入口

- **本期默认仍是已登记leyan原声**，路径与限制见[music-candidates.md](music-candidates.md)。下列为备选，发现资源不自动换曲。
- **爱给网**（T2正文推荐）：[入口](https://www.aigei.com/)。本轮主页工具访问失败；没有取得具体曲目及许可，标为待核候选。不能把原文的“无版权”泛化为全站任意素材可商用。
- **Mixkit**（T1界面案例提到，shotcraft署名表亦引用）：[许可入口](https://mixkit.co/license/)。按音乐/音效类别及具体文件条件核，不把免费与可重新打包分发混同。
- **shotcraft音效索引**：[署名表](https://github.com/Vincentwei1021/video-shotcraft/blob/main/assets/audio/ATTRIBUTION.md)与references/sound-design.md。按纸张、界面、机械等实际动作找；若文件原始来源标待考就不作为已确认可发布音源。

## 每次挑选和归档

1. 输入镜头ID、对应文稿、关系类型、时长、已有风格和当前阶段；只看能补这镜缺口的资源。
2. 先查本地已批组件/素材清单，存在即复用；没有才走上表对应入口。候选和采用分开。
3. 候选卡记录：库URL、commit或查询日期、精确卡/实现路径、预览/原帖、适用理由、不合适处、拟改内容、依赖、许可与署名、是否真实渲过。拿不准的状态留未知。
4. 将采用项回填镜头表、素材清单、声音时间表。下载前核外盘；LFS先只取文本，再取所选项目所需资产；遵守原有工具安装边界。
5. 已实际验收的组件才登记“可复用”，保存版本、参数、预览和使用过的镜头。不同表现方式可以逐步累积，但不为了建库而生产一堆模板。

可直接使用[prompt-methods.md](prompt-methods.md)的P2。外部脚本先读后按本期范围执行，不通过安装另一个Skill绕过我们的确认顺序。

## 本次版本快照

以下为2026-10-09 GitHub默认分支API读回；后续采用源码时重新核版本与许可，不因旧记录锁死更新。

| 仓库 | commit |
|---|---|
| heygen-com/hyperframes-launches | d7ac35069d74a3a437780579b3b7fe2f3eeace5f |
| Vincentwei1021/video-shotcraft | 5ddbf521038b0a7accfb6dc1e0a9eb29c67277ab |
| athemeroy/awesome-claude-5-5-videos | 0b96ca1ec8e03fe72a1c349370ab5dad043c5a1b |
| guanmo-ai/awesome-ai-motion | e8df52d548fa6f15acc39098e6a0bf3df1651309 |
| JohnHeibel/ClaudeAnimationBase | 0ac8bf2b31942376cb6b8c4074715595d512acd2 |
| JohnHeibel/PDoomVideo | fa546a38092e75f2b079e6a86d6abc54dd525d17 |
| Kianzzz/xilo-opus-video | f2cd828e2692e7186186408ee01a936707c2c38d |
