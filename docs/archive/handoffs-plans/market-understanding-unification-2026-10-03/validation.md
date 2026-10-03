# 实际验证记录

执行环境：任务隔离worktree，Darwin，Node22.22.1/npm10.9.4；2026-10-03 Asia/Shanghai。基础58baf916d14fbf536a024cced48edd3f118111f6，复用上轮预览5185及原市场服务8000。

| 实际检查 | 结果与边界 |
|---|---|
| npm run test:market-dashboard | exit0，14组合成边界；单位/日期/空值/未来/原阈值身份保持 |
| npm run test:market-understanding | exit0，33项原数据与目录边界 |
| npm run test:market-integration | exit0，5组：五旧深链/搜索参数/默认与未知分区、参考文字/颜色/身份、估值与收益差机会方向相反、VIX风险条件、旧模块与菜单保留/去重 |
| npm run build | exit0，751模块；大chunk提醒依旧，未扩大拆包工作 |
| git diff --check | exit0 |
| python3 scripts/check_repo_hygiene.py | exit1：旧检查器.git文件、用户要求docs/progress两项既存问题；未修改检查器，不冒称全绿 |
| 原/fundamentals入口 | 已打开的原页自动进入market-understanding#fund-sec-market；宽度、NAAIM/AAII、ETF缺项状态、情绪同窗/投影切换保留 |
| 旧深链 | /fundamentals?view=history#fund-sec-overlay 实际跳至 /market-understanding?view=history#fund-sec-overlay；刷新仍选长周期叠加 |
| URL往返 | 中国宏观→美国宏观→浏览器back/forward，URL与所选分区分别一致 |
| 五旧内容区 | 市场、利率/估值、长周期叠加、中国宏观、美国宏观均实际可达；卡与原控件保留；未冒称缺数源恢复 |
| 大图与色线 | 美国CPI旧抽屉仍可打开；2与0线改为经验/涨降价解释。总览CAPE大图绿≤12.4、蓝中位20.2、红≥27.4及配套文字实见 |
| 菜单 | 展开资讯与认知，仅因子/资讯/简报/心态，未见第二个基本面入口 |
| 390×844 | 统一六按钮、总览估值图例、旧美国宏观均scrollWidth=innerWidth=390；恢复默认尺寸 |

页面实际读取原服务，未强制刷新。A股总览7/9，美股16/16与上轮相同；旧利率区快照与历史差异保留，没有篡改或填齐值。中国宏观旧接口包含行业源错误，统一提示用缺项数量替代原始异常串，不把与该分区无关的源异常说成整页失败。

失败/发现：首次按旧/fundamentals URL取浏览器tab时未找到，因为开发预览已跳到新入口；读取实际tab清单后使用已有tab，无重复任务。一次按button角色找资讯菜单失败；该元素实际为summary，读回状态后通过可见文本展开成功。旧TrendDrawer仅在有zones时显示footnote，所以CPI窄修订在抽屉subtitle直接写经验线/非政策目标与配套判断，不修改共享组件。首次整合总览标题占空间较多，缩去重复副标题后重新构建。

未验证：全上游数据正确性/时点资格/许可、完整后台恢复、Linux/Windows、完整原页所有交互、投资收益或用户理解效果。此次颜色是对原参考数值的叙事解释，不是新的预测实验或策略条件。未触发刷新全源、情绪录入、下单、部署或付费操作。
