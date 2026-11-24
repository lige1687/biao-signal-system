# 原固定300股六日原始数据补取（2026-11-02）

**结论：**BaoStock 本轮第1次登录成功，原固定300股逐股日线和调整事件各查询一次，共 **600/600 次成功**。已取得 2026-10-26、27、28、29、30 与 11-02 六个交易日的不复权原始日线；每一天有 **280 股报价行**，其中 **279 股交易且成交额为正**、1 股停牌。其余20股在已核旧索引里均有缺口前的供应商退出日期，六日无报价行符合现有生命周期记录。这是可供主控续接的原始源，**还不是六日焦点动量值或交易机会**；原已验收序列仍截止 10-23。

- 固定名单沿原 `inputs.json → source_manifest.asset_sources`，manifest SHA-256 `5f3bd55994025442b5d7af416a8bd316f347b73ad61dcf134ac6040c9597cca6`。新响应未替换旧原件，先前4次续接及2次失败登录记录保留。
- 日线字段为 `date,code,open,high,low,close,preclose,volume,amount,adjustflag,tradestatus,pctChg,isST`，请求 `adjustflag=3`，即**不复权原价**；`amount` 为供应商报告的人民币元成交额，源字符串原样保存。调整事件单独请求 10-24 至 11-02，字段为 `code,dividOperateDate,foreAdjustFactor,backAdjustFactor,adjustFactor`；返回 **sh.601088 于 10-26 一条事件**。需由原适配器按有效 `foreAdjustFactor` 衔接价格，不直接拼不复权收盘价。
- `sz.002717` 六日均有 `tradestatus=0` 行、金额空白；按既有规则不可算有效交易报价。20个无行代码及各自旧索引退出日期见 `data-result.json.readback`，不能将它们补零。
- 新原始响应在外盘独立目录 `focus-recent-20261102-20261102T221933-461019228cc1/result/raw`。设备 UUID `DEBA1C85-6059-3865-B50A-A8EE1F80E4D9`，压缩原件总185,387字节；600件压缩及解压内容 SHA-256、字段、行数均已逐件读回。逐件路径和哈希在外盘 `acquisition-ledger.json`，本地 `data-result.json` 锁定该账本 SHA。旧 v8 索引 SHA `165a695612cfb4022b899d9c20ea5c85e1736994533974551685f58c3a7dd153` 也读回匹配其元数据。

**剩余边界：**尚未把新源送入原固定300模型、核因子事件接续或验证六日焦点值；主控独立复核后才能更新展示。供应商历史原件初次可得及事后修订时间未知；不存在用宽度缓存或其他供应商替换金额的步骤。
