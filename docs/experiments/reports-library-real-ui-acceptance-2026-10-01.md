# 报告库真实后端关键路径验收-2026-10-01

## 一句话结论（大白话）

已使用正常本地后端和486份现有真实报告补验：筛选刷新、正确正文、深链、返回、真实读取错误及重试恢复可以使用。真实手机场景暴露的加载后定位问题已最小修正，正文和返回按钮不再被吸顶导航遮挡。CI没有检查项，不能称CI通过。

## 版本与实际改动

原提交[6eaf0cd](https://github.com/lige1687/biao-signal-system/commit/6eaf0cdbd82525356eda9bea02827323f4e006fa)仅原两文件：`web/src/pages/ReportsLibraryPage.tsx`、`web/src/pages/reports-library-usability.css`。此次追加[最小定位修复](https://github.com/lige1687/biao-signal-system/commit/d0f34a2f400bcb08f468141df8d51e67d7101b3d)仅TSX一文件16行新增/2行替换；正文或错误加载完成后再次定位，并按当前吸顶导航实际高度留出可见空间。远端分支`codex/air-factor-parallel-20261001`与本地SHA一致，无强推、默认分支合并或部署，未夹带canonical研究dirty。

最终实际验收TSX SHA：`2fc4c774e91f8bb3dc90987b5e8c68136b4ca882c3f3a16001cfc76f5bdadfc0`。tsc+Vite构建通过，只有既有大chunk提示；git diff --check及仓库归置检查通过。没有追加研究、UI因子卡或改报告内容。

## 正常后端及真实资料

使用现有PID65822、cwd为原仓库的8000正常服务，未重启/重配；前端为隔离分支独占5204临时Vite，不用现有5173或OneAPI页面。后端版本未声明锁定到前端commit，验收限实际正常报告接口，不包办所有后端端点。

健康GET=200；首次报告列表20秒超时，唯一45秒上限复核在0.33秒返回200、282190字节、486份真实报告。没有证明首次超时具体原因，不以健康200冒称报告接口首次正常，也没重复等待或扩大后端架构。

实际读取`strict-bottom-first-description-2026-10-01.md`和`t03-double-ma-order-information-2026-10-01.md`，接口name/title/markdown与现有文件完全相同，正文SHA分别`03148d0b43992c8441986831548dc7d57b25f5c1e07288acc1e5e97032d7dad8`、`8df624140b2ed6fd0741442a17d24eda2db2560f24f3c761ab12127a51a540dc`。这里只验证显示身份，不重算任何金融效果。

## 浏览器关键路径及视觉检查

真实1440/390路径分阶段核验：类别/结论/关键词刷新保留，键盘选择、正文文件名与标题，第二报告深链与浏览器后退、显式返回、加载中不显示旧正文；不存在的真实报告API返回404，显示后端实际错误文案，重试确有正常后端新响应，返回后真实报告可恢复。

加载检查只是暂缓派发真实GET，随后正常继续，不填造数据；错误检查使用真实404，不制造500。除报告GET外的无关API及外部浏览器请求阻止，不伪造空JSON响应；不代表无关全站接口已验收。全新headless Chrome临时profile/独立contexts，未连接已有浏览器会话。最终查看了390正文/返回和1440错误截图，返回按钮位置及实际点击命中检查通过，两宽度无文档横向溢出；无页面JavaScript错误。

旧38项是此前合成验收，不复跑，也不拿它们代替本轮真实资料。本轮初版误要求错误消息带数字404、另一断言在重试响应到达前读计数，这两次测试错误保留；手机加载后定位失败是实际修正项。先前滚到页面零点会被吸顶导航遮挡，最终按导航高度留空间并用实际点击命中/截图复核，不把只有DOM存在叫可用。补丁后的阶段检查、剩余14项真实错误恢复检查及最终两宽度定位/点击检查分别留收据，未伪称一次全套首轮通过。200%缩放本轮未重新验收。

## CI的准确边界

[原提交Checks页](https://github.com/lige1687/biao-signal-system/commit/6eaf0cdbd82525356eda9bea02827323f4e006fa/checks)和[追加修复Checks页](https://github.com/lige1687/biao-signal-system/commit/d0f34a2f400bcb08f468141df8d51e67d7101b3d/checks)均明确显示“There are no checks for this commit”。Actions列表只有旧Dependency Graph且部分加载错误；提交树没有GitHub workflow文件。只能说这两提交未显示GitHub检查项，不能说CI测试通过或外部所有CI均无任务。没有登录、改权限、重试此前不可访问API、用替代方法绕过拒绝、CI重跑/dispatch。

## ARCHIVE

验收完成，证据在[raw目录](raw/reports-library-real-ui-acceptance-2026-10-01/)。只读UI资料，研究合同和结果原指纹保持；报告与登记留原仓库未推送。独占5204 Vite已按PID/cwd确认后停止，所有测试Chrome finally退出；现有8000/5173/OneAPI未触碰。不会继续泛化UI改版。

## 下一优先项

已在原技术交接追加：S01历史均线密集区的事前上涨空间仍缺区域形成边界、目标价、失效与多目标选择；A01个股资料仍缺历史成员生效、全段OHLC/行动/退出链。复用原资格盘点，不重扫库或重启旧弱结果。原线程实时状态unknown不等于未认领，两项条件未齐，本轮不执行。三项已完成研究保持封存。
