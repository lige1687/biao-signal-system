# CheckCC 与 Claude 封号风险：公开证据核查

## 一句话结论（大白话）

CheckCC（https://checkcc.org）及开源项目 yacuo/check-cc 确实存在，能检查浏览器语言、时区、字体和网络相关信息。但本次看到的是作者自定的环境评分，没有找到能证明使用后封号率下降的对照数据。可以用于排查环境，不能把低分当作账号安全保证；不支持地区的使用限制也不会因评分低而消失。

## 问题、范围与判断

用户要求找出记忆中的检测网站及 GitHub 项目，判断是否真能降低 Claude 封号风险。本轮仅核公开资料与部分源码，不安装、不执行修复、不登录 Claude、不采集用户网络，不涉及交易系统改造。

| 问题 | 已有参照 | 新证据 | 判断及边界 |
| --- | --- | --- | --- |
| 项目是否存在 | 用户记忆名称 | 网站及对应 GitHub 仓库 | 存在，名称 CheckCC |
| 检测是否有实现 | README 功能宣称 | client-engine.ts、config/signals.ts | 浏览器信息采集与按权重计分确有代码；未全面审计线上部署 |
| 分数是否等于封号概率 | 作者风险标签 | 权重固定在配置中：时区26、语言20、中文字体16 | 未见概率校准或真实封号对照；不能解释成百分比 |
| 修改环境能否降低封号率 | 项目宣传 | 官方封号原因包括使用政策、注册地点、服务条款 | 效果无法估计；没有经过跟踪的账号样本 |
| 浏览器能否代表 Claude Code | 浏览器采集 | navigator、Intl、canvas 字体检测 | 浏览器与终端可能走不同网络；不能据此确认 CLI 的实际请求环境 |

本次新增信息主要是：评分具体由作者配置，代码对中文语言、中文字体、若干亚洲时区赋分；这些条件可以出现在受支持地区的正常中文用户身上。因此“检测到地区相关信号”不能直接变成“账号会被封”。这是一项逻辑反例，未实际运行账号实验。

## 同类工具与官方边界

- [stormzhang/ipcheck](https://github.com/stormzhang/ipcheck)：终端网络诊断，README 列出 IP、DNS、代理、时区、Claude 端点等；读取过 cli.py 的部分内容。其风险标签同样不等于 Anthropic 官方决定。未安装或完整安全审计。
- [check-cc.oaker.io](https://check-cc.oaker.io/)：另一个相似名字的网站。页面明确说明只测访问本站的出口 IP；如果本站与 Claude 分流不同，看到的 IP 就不代表 Claude 所见。未确认其源码归属。
- [Anthropic 封号与申诉说明](https://support.claude.com/en/articles/8241253-safeguards-warnings-and-appeals)：列出多种封号原因，包括从不支持地点创建账号；未公开完整权重，也未认可上述评分。
- [Claude 支持地区](https://support.claude.com/en/articles/8461763-where-can-i-access-claude)：中国大陆不在本次读取的支持列表中。环境检测不能提供额外使用资格。

实用判断：可把检测结果用于网络和配置排查，不根据“低风险”标签购买账号或高价网络，也不在未审计脚本的情况下使用“一键修复”。项目 README 宣称无需 Claude 登录、密码或 Cookie，但这不构成对当前线上站点全部代码的安全保证。

## 核查记录与不确定性

读取日期：2026-09-30。GitHub API 返回 main 对应树 SHA：`078e7baa1d2a08df28da3f25dacb90e687f4c79f`。

关键代码：[信号权重](https://github.com/yacuo/check-cc/blob/078e7baa1d2a08df28da3f25dacb90e687f4c79f/src/detection/config/signals.ts)、[浏览器采集与加分](https://github.com/yacuo/check-cc/blob/078e7baa1d2a08df28da3f25dacb90e687f4c79f/src/detection/client-engine.ts)。只核这两个关键文件，不宣称完成整仓审计。scoring.ts 的网页读取失败。

过程记录：公开检索和页面/目录阅读共7次 web 批次，包含 GitHub API 不可访问、一次误点广告链接（未购买或提交资料）、固定版本 scoring.ts 读取失败。补充 curl 目录读取：首次因 URL 未引用被 shell 拒绝；第二次沙箱 DNS 失败；经用户批准后成功。未进行封号实验，未调整规则、系统时区或网络。资料检索超过通用 Skill 的默认6次上限，是本次过程偏差，后续不追加检索。已取得的信息足以回答项目身份与公开证据的能力边界，不能量化封号风险降幅。

## 2026-09-30 实机补查（同日追加，不改原结论）

用户授权先检测、找开源工具诊断、再检测。Chrome 上 CheckCC 自动检测基线为 89 分，高风险；此前同环境曾为 97 分，期间没有修复，故分数本身存在波动。只读运行开源 [ipcheck](https://github.com/stormzhang/ipcheck) 后，重新用 CheckCC 自动检测仍为 89 分、高风险。ipcheck 从临时目录执行，未全局安装，也未改浏览器、网络或系统设置。该前后比较是诊断工具运行前后，不是修复实验，不能用于估计防封效果。

ipcheck 与 CheckCC 均看到香港出口；ipcheck 检出本机直连和浏览器出口不同、系统代理开启，公开 IP 情报把同一出口分别标为住宅与 VPN，CheckCC 则标为数据中心。各家的类型标签不一致。ipcheck 看到当前 Claude Code CLI 端点配置为 DeepSeek，因而它的“Claude 使用中风险”不代表 Claude Pro/Max 订阅网页。报告不记录完整 IP、账号或付款信息。

进一步查看项目公开的 [Detector.tsx](https://github.com/yacuo/check-cc/blob/main/src/components/detector/Detector.tsx)：公开代码只显示浏览器端和基础服务端信号的组合，未找到线上页面展示的 WebRTC 检测文字；本次线上页展示 49 项，公开版本与线上版本的对应性未获证实。因此未执行线上“一键修复”脚本，不把分数降低等同于账号风险降低。官方[支持地区](https://support.claude.com/en/articles/8461763-where-can-i-access-claude)目前未列香港或中国大陆；环境工具不能改变账号适用地区。结案状态：限定诊断完成；真正降低订阅封号率的效果仍证据不足。

## ARCHIVE

限定公开证据与实机诊断完成，结案原因为证据边界：检测功能有支持，降低封号率的因果效果证据不足。没有账号样本、跟踪期限、处理组或对照组，不给出虚构成功率。整仓安全审计及真实账号效果实验未开展，属于新的任务范围。
