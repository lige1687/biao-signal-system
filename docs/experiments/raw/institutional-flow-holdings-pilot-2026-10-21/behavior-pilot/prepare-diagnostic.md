# 准备阶段身份字段诊断（2026-10-22，未计算真实效果）

第一次 `prepare` 按自由文本 `ISSUER_TITLE` 字面相等来认跨基金同一证券，使 Parnassus Core Equity Fund 三期“有其他基金作同证券参照”的持仓数均为 0；初版状态文件保存在 [prepare-status-title-exact-initial.json](prepare-status-title-exact-initial.json)，SHA-256 `bfb55884a91bb969f4e299a9dda34e7e7806dd9e0ba1545f772baf0c9150afee`。原始两期同 CUSIP 交集并非零：2024-12-31 至 2025-03-31，Parnassus 与 Contrafund、Magellan、Dodge & Cox 分别有 19、17、6 个两端都出现的合格 CUSIP；初版跨基金标题比较把它们都挡掉。没有读取或计算真实申赎和持仓数量变化。

下表均取 2024-12-31 的 `FUND_REPORTED_HOLDING` 原行：同一 CUSIP、同一非空发行人 LEI、`UNIT=NS`、`CURRENCY_CODE=USD`、`ASSET_CAT=EC`，但各基金的自由文本名称、标题不同。Parnassus 的标题系统性带 `0.00000000` 后缀。

| CUSIP / 发行人 LEI | Parnassus `ISSUER_NAME` / `ISSUER_TITLE` | 另一基金 `ISSUER_NAME` / `ISSUER_TITLE` |
|---|---|---|
| `02079K305` / `5493006MHB84DD0ZWV18` | `ALPHABET INC-CL A` / `ALPHABET INC-CL A 0.00000000` | Contrafund：`ALPHABET INC` / `ALPHABET INC CL A`；Dodge：`Alphabet, Inc.` / `Alphabet, Inc., Class A` |
| `023135106` / `ZXTILKJKG63JELOEG630` | `AMAZON.COM INC` / `AMAZON.COM INC 0.00000000` | Contrafund：`AMAZON.COM INC` / `AMAZON.COM INC` |
| `037833100` / `HWUPKR0MPOU8FGXBT394` | `APPLE INC` / `APPLE INC 0.00000000` | Contrafund：`APPLE INC` / `APPLE INC` |
| `060505104` / `9DJT3UXIJIZJI4WXO774` | `BANK OF AMERICA CORP` / `BANK OF AMERICA CORP 0.00000000` | Contrafund：`BANK OF AMERICA CORPORATION` / `BANK OF AMERICA CORPORATION` |
| `11135F101` / `549300WV6GIDOZJTV909` | `BROADCOM INC` / `BROADCOM INC 0.00000000` | Contrafund：`BROADCOM INC` / `BROADCOM INC` |

这证实第一次零参照源于过严的跨基金自由文本比较；**不据此自行放宽真实发行人 LEI 冲突**。主控已在查看任何真实资金流或数量变化效果前，把澄清写入 `measurement-contract.json` 的 `identity_clarification_before_effects`：跨基金同 CUSIP、NS/USD 且双方有效发行人 LEI 完全一致时，标题差异只记录；LEI 缺失、无效或不同仍拒绝参照。同基金跨期和同一申报内重复行继续按原来的标题与 LEI 冲突规则保守排除。修正后的资格数见 [当前准备状态](prepare-status.json)，第一次零参照的状态保留不覆盖。正式效果运行仍未启动；外盘 `behavior-pilot` 结果目录尚不存在。
