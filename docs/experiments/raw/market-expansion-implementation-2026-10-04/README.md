# 本批恢复与证据入口

先读../../market-expansion-implementation-2026-10-04.md，再读audit-summary.json、validation.json、live-check.json、ui-check.json、restore-check.json、source-ledger.json、manifest.json。本批基线48e2eadc918e4cf0c361c89d25f25a8c2fba524c；版本以本文件所在Git提交核准。原私人策略源只有指纹，原件/公司内网资料未外传。

原始PDF、FINRA工作簿/含数值审计、HTML、完整响应和截图只在原机器；audit-summary列大小与SHA，未交付不能假装可下载。服务按上游重新取得观察数据，不承诺获得相同历史版本或预测资格。旧结果不为新路径改写。

以下命令均从仓库根运行，权限和依赖先核；安装命令仅提供恢复方法，本轮未做洁净安装。Python>=3.11、Node22。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[api,dev]' akshare==1.18.49
cd web
npm ci
cd ..
.venv/bin/python -m pytest tests/unit/test_market_context.py tests/unit/test_fundamentals.py -q
cd web
npm run test:market-context
npm run build
cd ..
```

仅本题只读预览不导入完整app、不初始化账户数据库。先确认8045与5185空闲，不终止其他进程；已有端口占用可改为另一对并一致更新代理。

```sh
PYTHONPATH=src .venv/bin/python -m uvicorn preview_app:app --app-dir docs/experiments/raw/market-expansion-implementation-2026-10-04 --host 127.0.0.1 --port 8045
```

另一终端，从web目录运行（LEI_API_PROXY=8045用于独立市场预览；账户/完整应用端点不在此预览）：

```sh
LEI_WEB_PORT=5185 LEI_API_PROXY=http://127.0.0.1:8045 LEI_MARKET_CONTEXT_PROXY=http://127.0.0.1:8045 npm run dev -- --strictPort
```

若需复用已启动正式API，LEI_API_PROXY指向其地址，新context单独指8045。本机实际如此使用8000旧API；不意味着8000加载了新提交。

```sh
curl --fail 'http://127.0.0.1:8045/api/fundamentals/market-context?lookback_days=1095'
```

预期schema_version market-context/1，9个键；网络或源失败可以空序列且有明确错误，不能伪造通过。打开/market-understanding?market=cn#overview和美股、/agent?macro=1&market=us，核当前真实日期、来源、ETF/事件及追问。没有新权重、tokenizer、DB导出、密钥/登录态。跨机器环境/权限须重新核，不能仅凭通过清单启动旧金融研究。
