"""统一数据门户（DataPortal）与物理闭卷考锁（Holdout Guard）。

设计目的：
1. 把散落在各处的 ETF 行情、ERP、市场宽度、焦点股热度、24 项市场观测面板统一到一个干净入口；
2. 默认 split="explore" 物理截断在 2023-12-31，平时试想法根本看不见 2024-2026 的数据，
   从源头上杜绝“把所有年份看光调参”，省掉繁琐的 19 字段事前 JSON 审批八股文。
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Literal
import numpy as np
import pandas as pd


HOLDOUT_START = "2024-01-01"
EXPLORE_END = "2023-12-31"

SplitMode = Literal["explore", "holdout", "full"]

# 常见场内 ETF 中文名映射（方便输出大白话表格与漏斗）
ETF_NAMES: dict[str, str] = {
    "510300.SS": "沪深300ETF",
    "510050.SS": "上证50ETF",
    "510500.SS": "中证500ETF",
    "512100.SS": "中证1000ETF",
    "159915.SZ": "创业板ETF",
    "588000.SS": "科创50ETF",
    "159901.SZ": "深100ETF",
    "512890.SS": "红利低波ETF",
    "512480.SS": "半导体ETF",
    "159995.SZ": "芯片ETF",
    "515880.SS": "通信ETF",
    "515050.SS": "5G通信ETF",
    "159819.SZ": "人工智能ETF",
    "512010.SS": "医药ETF",
    "512170.SS": "医疗ETF",
    "159992.SZ": "创新药ETF",
    "159928.SZ": "消费ETF",
    "512690.SS": "酒ETF",
    "515170.SS": "食品饮料ETF",
    "512400.SS": "有色金属ETF",
    "515220.SS": "煤炭ETF",
    "515210.SS": "钢铁ETF",
    "512660.SS": "军工ETF",
    "512800.SS": "银行ETF",
    "512000.SS": "券商ETF",
    "512200.SS": "房地产ETF",
    "515790.SS": "光伏ETF",
    "515030.SS": "新能车ETF",
    "159611.SZ": "电力基金",
    "159652.SZ": "有色50基金",
    "159865.SZ": "养殖基金",
    "159825.SZ": "农业ETF",
    "512980.SS": "传媒ETF",
    "515300.SS": "沪深300ETF易方达",
    "516010.SS": "游戏ETF",
    "562500.SS": "机器人ETF",
    "513100.SS": "纳指100ETF",
    "513500.SS": "标普500ETF",
    "513180.SS": "恒生科技ETF",
    "513030.SS": "德国ETF",
    "513520.SS": "日经ETF",
    "518850.SS": "黄金ETF",
    "SPY": "美股标普500",
    "QQQ": "美股纳指100",
    "IWM": "美股罗素2000",
    "SMH": "美股半导体",
    "GLD": "美股黄金",
}

# 本机股票池常见核心龙头中文名映射
STOCK_NAMES: dict[str, str] = {
    "000001.SZ": "平安银行", "000568.SZ": "泸州老窖", "000596.SZ": "古井贡酒", "000625.SZ": "长安汽车",
    "000661.SZ": "长春高新", "000698.SS": "沈阳化工", "000725.SZ": "京东方A", "000768.SZ": "中航西飞",
    "000831.SZ": "中国稀土", "000858.SZ": "五粮液", "000938.SZ": "紫光股份", "002008.SZ": "大族激光",
    "002049.SZ": "紫光国微", "002050.SZ": "三花智控", "002179.SZ": "中航光电", "002185.SZ": "华天科技",
    "002230.SZ": "科大讯飞", "002241.SZ": "歌尔股份", "002281.SZ": "光迅科技", "002304.SZ": "洋河股份",
    "002326.SZ": "永太科技", "002371.SZ": "北方华创", "002384.SZ": "东山精密", "002410.SZ": "广联达",
    "002415.SZ": "海康威视", "002460.SZ": "赣锋锂业", "002466.SZ": "天齐锂业", "002475.SZ": "立讯精密",
    "002555.SZ": "三七互娱", "002594.SZ": "比亚迪", "002747.SZ": "埃斯顿", "002812.SZ": "恩捷股份",
    "002821.SZ": "凯莱英", "300003.SZ": "乐普医疗", "300014.SZ": "亿纬锂能", "300059.SZ": "东方财富",
    "300073.SZ": "当升科技", "300122.SZ": "智飞生物", "300124.SZ": "汇川技术", "300136.SZ": "信维通信",
    "300223.SZ": "北京君正", "300274.SZ": "阳光电源", "300308.SZ": "中际旭创", "300347.SZ": "泰格医药",
    "300383.SZ": "光环新网", "300394.SZ": "天孚通信", "300474.SZ": "景嘉微", "300502.SZ": "新易盛",
    "300661.SZ": "圣邦股份", "300750.SZ": "宁德时代", "600030.SS": "中信证券", "600111.SS": "北方稀土",
    "600188.SS": "兖矿能源", "600196.SS": "复星医药", "600276.SS": "恒瑞医药", "600362.SS": "江西铜业",
    "600438.SS": "通威股份", "600460.SS": "士兰微", "600519.SS": "贵州茅台", "600584.SS": "长电科技",
    "600588.SS": "用友网络", "600600.SS": "青岛啤酒", "600660.SS": "福耀玻璃", "600703.SS": "三安光电",
    "600745.SS": "闻泰科技", "600760.SS": "中航沈飞", "600809.SS": "山西汾酒", "600850.SS": "电科数字",
    "600893.SS": "航发动力", "601012.SS": "隆基绿能", "601127.SS": "赛力斯", "601225.SS": "陕西煤业",
    "601238.SS": "广汽集团", "601318.SS": "中国平安", "601600.SS": "中国铝业", "601688.SS": "华泰证券",
    "601689.SS": "拓普集团", "601899.SS": "紫金矿业", "603160.SS": "汇顶科技", "603259.SS": "药明康德",
    "603288.SS": "海天味业", "603799.SS": "华友钴业", "603986.SS": "兆易创新", "603993.SS": "洛阳钼业",
}

ASSET_NAMES: dict[str, str] = {**ETF_NAMES, **STOCK_NAMES}


@dataclass(frozen=True)
class IndicatorSeries:
    """单条市场观测指标及其金融含义说明。"""

    id: str
    name_cn: str
    market: Literal["CN", "US"]
    plain_meaning: str
    expected_bottom_side: Literal["high", "low"]  # "high" 表示数值越高越像大底（如ERP、恐慌VIX）；"low" 表示数值越低越像大底（如宽度、情绪）
    series: pd.Series


# 系统已有核心市场指标的大白话金融含义登记
INDICATOR_META: dict[str, tuple[str, Literal["CN", "US"], str, Literal["high", "low"]]] = {
    "cn-erp": ("A股股债性价比", "CN", "买股票隐含收益率比国债多几个点：越高说明股票相对债券越便宜（赔率高）", "high"),
    "cn-breadth-b50": ("全场站上50日均线股票占比(%)", "CN", "全市场多少股票处于中期上升趋势：极低(<15%)代表泥沙俱下跌透，极高(>80%)代表普涨过热", "low"),
    "cn-breadth-b200": ("全场站上200日均线股票占比(%)", "CN", "全市场多少股票处于牛市年线上方：衡量牛熊大底与全面过热", "low"),
    "csi300-breadth-b50": ("沪深300成分股50日均线占比(%)", "CN", "大盘蓝筹内部真正在涨的比例：指数涨而它跌说明只拉权重掩护出货", "low"),
    "focus-momentum": ("最活跃5%焦点股近一月涨跌(%)", "CN", "市场上成交最火的一批票是在赚钱还是亏钱：衡量主线赚钱效应冷暖", "low"),
    "downside-price-impact": ("A股下跌价格冲击度", "CN", "每1亿元成交砸出多大跌幅：飙升说明场内买盘枯竭、稍微一卖就大跌（恐慌极值）", "high"),
    "salience-str": ("A股短期追涨热度", "CN", "近期暴涨日相对暴跌日的吸引眼球程度：过高说明散户追高情绪亢奋", "low"),
    "cn-daily-amount-top5": ("前5%头部股票成交集中度(%)", "CN", "全市场多少资金挤在最热的那5%股票里：过高(>50%)说明抱团极度拥挤易踩踏", "low"),
    "cn-index-futures-basis": ("股指期货升贴水基差", "CN", "期指相对现货升贴水：深度贴水往往反映机构极端悲观或对冲盘拥挤", "low"),
    "cn-financing": ("A股融资买入占比(%)", "CN", "杠杆资金活跃度：跌到冰点代表杠杆洗净，冲到高位代表散户加杠杆上头", "low"),
    "cn-300etf-pcr-volume": ("沪深300期权买跌与买涨比", "CN", "买下跌保护比买看涨期权多多少：飙高代表期权市场极度恐慌避险", "high"),
    "hv-cn": ("A股历史波动剧烈度(%)", "CN", "近期指数真实震荡剧烈程度：极低代表变盘前死水，极高代表恐慌宣泄或疯牛巨震", "high"),
    "vix": ("美股期权恐慌度", "US", "标普500期权隐含恐慌度：飙升代表机构恐慌抢购保险，往往对应黄金坑", "high"),
    "vxn": ("纳指科技股恐慌度", "US", "科技股期权隐含波动率：飙升代表纳指恐慌抛售极值", "high"),
    "vix-term-structure": ("美股近远月恐慌比", "US", "大于1代表眼前极度恐慌（近月期权比远月还贵），是经典的美股急跌见底信号", "high"),
    "hy-oas": ("美国企业高息债违约利差(%)", "US", "高风险企业债比国债多给多少利息：飙升代表实体企业违约风险恶化，不飙升说明美股回调只是虚惊", "high"),
    "aaii": ("美股散户看多看空差", "US", "看多散户减看空散户比例：深跌为负说明散户绝望割肉（反向见底信号）", "low"),
    "naaim": ("美股机构主动仓位(%)", "US", "机构真实股票仓位：砸到低位(<40)说明机构已砍仓完毕，顶格(>95)说明满仓缺乏后续买盘", "low"),
}


class DataPortal:
    """只读统一数据门户，默认开启探索期样本外锁。"""

    def __init__(
        self,
        repo_root: str | Path | None = None,
        lab_home: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
        self.lab_home = Path(lab_home) if lab_home else (Path.home() / ".lei_signal_lab")
        self.bp_cn = self.lab_home / "backtest_pool"
        self.bp_us = self.lab_home / "backtest_pool_us"
        self.live_bars_dir = self.lab_home / "strategy_lab_bars"
        self.pit_cache_dir = self.lab_home / "pit_cache"
        self._live_names_cache: dict[str, str] | None = None
        self._pit_fundamentals_cache: pd.DataFrame | None = None
        self._quality_source: str = "unloaded"

    def get_asset_name(self, symbol: str) -> str:
        """获取标的真实中文名称（优先取实时拉取缓存的官方中文简称，其次取内置字典）。"""
        if self._live_names_cache is None:
            names_file = self.live_bars_dir / "names.json"
            if names_file.exists():
                try:
                    self._live_names_cache = json.loads(names_file.read_text(encoding="utf-8"))
                except Exception:
                    self._live_names_cache = {}
            else:
                self._live_names_cache = {}
        if symbol in self._live_names_cache:
            return self._live_names_cache[symbol]
        return ASSET_NAMES.get(symbol, symbol.split(".")[0])

    @staticmethod
    def _slice_split(df_or_ser: pd.DataFrame | pd.Series, split: SplitMode):
        if split == "explore":
            return df_or_ser.loc[df_or_ser.index <= pd.Timestamp(EXPLORE_END)]
        if split == "holdout":
            return df_or_ser.loc[df_or_ser.index >= pd.Timestamp(HOLDOUT_START)]
        if split == "full":
            return df_or_ser
        raise ValueError(f"unsupported split mode: {split}")

    def load_latest_fundamentals_table(self) -> pd.DataFrame:
        """读取全市场最新一期季报好生意分层表（含行业、总市值、净资产回报率、净利增速、每股现金流、龙头/小巨人分层）。"""
        p = self.live_bars_dir / "fundamentals_latest.parquet"
        if not p.exists():
            return pd.DataFrame()
        return pd.read_parquet(p)

    def list_cn_etfs(self) -> list[str]:
        found: set[str] = set()
        for folder in (self.bp_cn, self.live_bars_dir):
            if not folder.exists():
                continue
            for p in folder.glob("*.bars.parquet"):
                sym = p.name.replace(".bars.parquet", "")
                if sym.startswith(("51", "15", "58", "56")):
                    found.add(sym)
        return sorted(found)

    def list_cn_stocks(self) -> list[str]:
        """列出本机行情池与增量池中的全部 A 股个股代码（排除指数与基金）。"""
        index_codes = {"000001.SS", "000016.SS", "000300.SS", "000688.SS", "000905.SS"}
        out: set[str] = set()
        for folder in (self.bp_cn, self.live_bars_dir):
            if not folder.exists():
                continue
            for p in folder.glob("*.bars.parquet"):
                sym = p.name.replace(".bars.parquet", "")
                if sym in index_codes:
                    continue
                if sym.endswith((".SS", ".SZ")) and sym[:3] in {
                    "000", "001", "002", "003", "300", "301", "600", "601", "603", "605", "688"
                }:
                    out.add(sym)
        return sorted(out)

    @staticmethod
    def normalize_cn_symbol(raw: str) -> str:
        """统一将 sh.600519 / 600519 / 000001.SZ 等代码规范为标准后缀代码。"""
        s = str(raw).strip()
        if not s:
            return s
        if s.startswith(("sh.", "SH.")):
            return s[3:] + ".SS"
        if s.startswith(("sz.", "SZ.")):
            return s[3:] + ".SZ"
        if s.endswith((".SS", ".SZ")):
            return s
        digits = "".join(ch for ch in s if ch.isdigit())
        if len(digits) == 6:
            return f"{digits}.SS" if digits.startswith(("5", "6", "9")) else f"{digits}.SZ"
        return s

    @staticmethod
    def _statutory_notice_fallback(report_date: pd.Timestamp) -> pd.Timestamp:
        """缺真实披露日时，按 A 股法定最晚披露截止日保守生效（杜绝提前偷看财报）。"""
        y, m = int(report_date.year), int(report_date.month)
        if m == 3:
            return pd.Timestamp(year=y, month=5, day=1)
        if m == 6:
            return pd.Timestamp(year=y, month=9, day=1)
        if m == 9:
            return pd.Timestamp(year=y, month=11, day=1)
        return pd.Timestamp(year=y + 1, month=5, day=1)

    def load_pit_fundamentals(self, *, split: SplitMode = "explore") -> pd.DataFrame:
        """从本机历史季报与年报资本纪律表构建严格按披露日生效的 PIT 基本面面板（零外盘依赖）。

        数据源（全部本地）：
        1. strategy_lab_bars/hist_q_reports/rpt_*.parquet（精确 NOTICE_DATE + ROE/毛利率/现金流/净利增速/行业）
        2. strategy_lab_bars/hist_capital_discipline/profit_*.parquet（2017+ 年报盈利与同业 ROE 分位，保守按次年 5 月 1 日生效）
        3. strategy_lab_bars/hist_capital_discipline/balance_*.parquet（资产增速与资产负债率，用于高债大扩张 PIT 排雷）
        4. strategy_lab_bars/hist_capital_discipline/dividend_*.parquet（每股分红）
        """
        if self._pit_fundamentals_cache is None:
            frames: list[pd.DataFrame] = []

            # 1) 本地历史季报（带精确公告日 NOTICE_DATE）
            q_dir = self.live_bars_dir / "hist_q_reports"
            if q_dir.exists():
                for pf in sorted(q_dir.glob("rpt_*.parquet")):
                    try:
                        qdf = pd.read_parquet(pf)
                    except Exception:
                        continue
                    if len(qdf) == 0 or "SECURITY_CODE" not in qdf.columns:
                        continue
                    sub = pd.DataFrame()
                    sub["symbol"] = qdf["SECURITY_CODE"].astype(str).str.zfill(6).map(self.normalize_cn_symbol)
                    rpt_dt = pd.to_datetime(qdf.get("REPORTDATE"), errors="coerce").dt.normalize()
                    ntc_dt = pd.to_datetime(qdf.get("NOTICE_DATE"), errors="coerce").dt.normalize()
                    fallback_dt = rpt_dt.map(
                        lambda d: self._statutory_notice_fallback(d) if pd.notna(d) else pd.NaT
                    )
                    sub["report_date"] = rpt_dt
                    sub["decision_date"] = ntc_dt.fillna(fallback_dt)
                    sub["industry"] = qdf.get("PUBLISHNAME", "").fillna("").astype(str)
                    sub["roe"] = pd.to_numeric(qdf.get("WEIGHTAVG_ROE"), errors="coerce")
                    sub["gross_margin"] = pd.to_numeric(qdf.get("XSMLL"), errors="coerce")
                    sub["ocf_ps"] = pd.to_numeric(qdf.get("MGJYXJJE"), errors="coerce")
                    sub["profit_yoy"] = pd.to_numeric(qdf.get("SJLTZ"), errors="coerce")
                    sub["rev_yoy"] = pd.to_numeric(qdf.get("YSTZ"), errors="coerce")
                    # 当期已知截面内同行业盈利能力百分位（绝不跨期偷看）
                    ind_grp = sub.groupby("industry")["roe"]
                    sub["quality_pct"] = ind_grp.rank(pct=True)
                    overall_pct = sub["roe"].rank(pct=True)
                    sub["quality_pct"] = sub["quality_pct"].fillna(overall_pct)
                    sub["source_kind"] = "q_report"
                    frames.append(sub.dropna(subset=["decision_date"]))

            # 2) 本地历史年报盈利表（补齐 2017–2020 早期历史）
            cap_dir = self.live_bars_dir / "hist_capital_discipline"
            if cap_dir.exists():
                for pf in sorted(cap_dir.glob("profit_*.parquet")):
                    try:
                        pdf = pd.read_parquet(pf)
                    except Exception:
                        continue
                    if len(pdf) == 0 or "symbol" not in pdf.columns:
                        continue
                    sub = pd.DataFrame()
                    sub["symbol"] = pdf["symbol"].astype(str).map(self.normalize_cn_symbol)
                    ry = pd.to_numeric(pdf.get("report_year"), errors="coerce")
                    sub["report_date"] = pd.to_datetime(ry.dropna().astype(int).astype(str) + "-12-31", errors="coerce").reindex(pdf.index)
                    sub["decision_date"] = pd.to_datetime((ry + 1).dropna().astype(int).astype(str) + "-05-01", errors="coerce").reindex(pdf.index)
                    sub["industry"] = pdf.get("industry", "").fillna("").astype(str)
                    sub["roe"] = pd.to_numeric(pdf.get("roe"), errors="coerce")
                    sub["gross_margin"] = pd.to_numeric(pdf.get("gross_margin"), errors="coerce")
                    sub["ocf_ps"] = pd.to_numeric(pdf.get("ocf_ps"), errors="coerce")
                    sub["profit_yoy"] = pd.to_numeric(pdf.get("profit_yoy"), errors="coerce")
                    sub["rev_yoy"] = np.nan
                    q_pct = pd.to_numeric(pdf.get("ind_roe_pct"), errors="coerce")
                    sub["quality_pct"] = q_pct.fillna(sub["roe"].rank(pct=True))
                    sub["source_kind"] = "annual_profit"
                    frames.append(sub.dropna(subset=["decision_date"]))

            if frames:
                merged = pd.concat(frames, ignore_index=True)
                merged = merged.sort_values(["symbol", "decision_date", "report_date"]).drop_duplicates(
                    subset=["symbol", "decision_date"], keep="last"
                )
            else:
                merged = pd.DataFrame(
                    columns=[
                        "symbol", "report_date", "decision_date", "industry",
                        "roe", "gross_margin", "ocf_ps", "profit_yoy", "rev_yoy",
                        "quality_pct", "source_kind",
                    ]
                )

            # 3) 按 PIT 披露日叠加资本纪律（资产增速、负债率）与分红
            bal_frames: list[pd.DataFrame] = []
            div_frames: list[pd.DataFrame] = []
            if cap_dir.exists():
                for pf in sorted(cap_dir.glob("balance_*.parquet")):
                    try:
                        bdf = pd.read_parquet(pf)
                    except Exception:
                        continue
                    if len(bdf) == 0 or "symbol" not in bdf.columns:
                        continue
                    bsub = pd.DataFrame()
                    bsub["symbol"] = bdf["symbol"].astype(str).map(self.normalize_cn_symbol)
                    ry = pd.to_numeric(bdf.get("report_year"), errors="coerce")
                    statutory = pd.to_datetime((ry + 1).dropna().astype(int).astype(str) + "-05-01", errors="coerce").reindex(bdf.index)
                    ntc = pd.to_datetime(bdf.get("notice_date"), errors="coerce").dt.normalize()
                    # 保守取较晚者，避免使用晚于法定披露日修订或提前泄露
                    bsub["bal_date"] = ntc.fillna(statutory)
                    bsub["asset_growth_yoy"] = pd.to_numeric(bdf.get("asset_growth_yoy"), errors="coerce")
                    bsub["debt_ratio"] = pd.to_numeric(bdf.get("debt_ratio"), errors="coerce")
                    bal_frames.append(bsub.dropna(subset=["bal_date"]))

                for pf in sorted(cap_dir.glob("dividend_*.parquet")):
                    try:
                        ddf = pd.read_parquet(pf)
                    except Exception:
                        continue
                    if len(ddf) == 0 or "symbol" not in ddf.columns:
                        continue
                    dsub = pd.DataFrame()
                    dsub["symbol"] = ddf["symbol"].astype(str).map(self.normalize_cn_symbol)
                    ry = pd.to_numeric(ddf.get("report_year"), errors="coerce")
                    dsub["div_date"] = pd.to_datetime((ry + 1).dropna().astype(int).astype(str) + "-05-01", errors="coerce").reindex(ddf.index)
                    dsub["bonus_per_share"] = pd.to_numeric(ddf.get("bonus_per_share"), errors="coerce")
                    div_frames.append(dsub.dropna(subset=["div_date"]))

            if len(merged) > 0 and bal_frames:
                bal_all = pd.concat(bal_frames, ignore_index=True).sort_values(["bal_date", "symbol"]).drop_duplicates(
                    subset=["symbol", "bal_date"], keep="last"
                )
                merged = merged.sort_values("decision_date")
                merged = pd.merge_asof(
                    merged,
                    bal_all,
                    left_on="decision_date",
                    right_on="bal_date",
                    by="symbol",
                    direction="backward",
                ).drop(columns=["bal_date"], errors="ignore")
            else:
                merged["asset_growth_yoy"] = np.nan
                merged["debt_ratio"] = np.nan

            if len(merged) > 0 and div_frames:
                div_all = pd.concat(div_frames, ignore_index=True).sort_values(["div_date", "symbol"]).drop_duplicates(
                    subset=["symbol", "div_date"], keep="last"
                )
                merged = merged.sort_values("decision_date")
                merged = pd.merge_asof(
                    merged,
                    div_all,
                    left_on="decision_date",
                    right_on="div_date",
                    by="symbol",
                    direction="backward",
                ).drop(columns=["div_date"], errors="ignore")
            else:
                merged["bonus_per_share"] = np.nan

            if len(merged) > 0:
                is_fin = merged["industry"].astype(str).str.contains("银行|保险|证券|电力|金融", regex=True, na=False)
                merged["reckless_debt"] = (
                    (~is_fin)
                    & (merged["asset_growth_yoy"] > 35.0)
                    & (merged["debt_ratio"] > 60.0)
                )
                merged = merged.sort_values(["symbol", "decision_date"]).reset_index(drop=True)
            else:
                merged["reckless_debt"] = pd.Series(dtype=bool)

            self._pit_fundamentals_cache = merged

        df = self._pit_fundamentals_cache.copy()
        if len(df) == 0:
            return df
        if split == "explore":
            df = df[df["decision_date"] <= pd.Timestamp(EXPLORE_END)]
        elif split == "holdout":
            df = df[df["decision_date"] >= pd.Timestamp(HOLDOUT_START)]
        elif split != "full":
            raise ValueError(f"unsupported split mode: {split}")
        return df.reset_index(drop=True)

    def load_stock_business_quality(self, *, split: SplitMode = "explore") -> pd.DataFrame:
        """加载严格按财报真实披露日对齐的 A 股‘好生意’指标（优先本地 PIT 面板与本地缓存，彻底解耦外盘）。

        返回列兼容旧接口（symbol, decision_date, gpa, cfoa, quality_pct），并附带 PIT 资本纪律字段。
        """
        local_cache = self.pit_cache_dir / "stock_business_quality.parquet"
        env_override = os.environ.get("LEI_QUALITY_CSV")
        ext_root = Path(os.environ.get("LEI_EXTERNAL_RESULTS_DIR", "/Volumes/win+mac通用/LeiSignal-新实验结果"))
        ext_csv = (
            Path(env_override)
            if env_override
            else ext_root
            / "profitability-price-correction-20261020"
            / "profitability-price-correction-20261020-20261020T135727-6742ff079a58"
            / "result/stock_weights.csv"
        )

        # 优先使用本机 PIT 财报面板（覆盖 2018–2026 全部 5000+ 股票，含高债大扩张标记）
        pit = self.load_pit_fundamentals(split="full")
        if len(pit) > 0:
            df = pd.DataFrame()
            df["symbol"] = pit["symbol"]
            df["decision_date"] = pit["decision_date"]
            # gpa 用毛利率或 ROE 小数口径代理，cfoa 用每股经营现金流，均保持与旧正负门槛完全兼容
            gm_dec = pit["gross_margin"] / 100.0
            roe_dec = pit["roe"] / 100.0
            df["gpa"] = gm_dec.fillna(roe_dec)
            df["cfoa"] = pit["ocf_ps"]
            df["quality_pct"] = pit["quality_pct"]
            df["roe"] = pit["roe"]
            df["profit_yoy"] = pit["profit_yoy"]
            df["asset_growth_yoy"] = pit["asset_growth_yoy"]
            df["debt_ratio"] = pit["debt_ratio"]
            df["reckless_debt"] = pit["reckless_debt"]
            df["industry"] = pit["industry"]
            df = df.dropna(subset=["decision_date", "quality_pct"]).sort_values(["symbol", "decision_date"])
            self._quality_source = "local_pit_fundamentals"
        elif local_cache.exists():
            df = pd.read_parquet(local_cache)
            df["decision_date"] = pd.to_datetime(df["decision_date"]).dt.normalize()
            self._quality_source = f"local_cache:{local_cache.name}"
        elif ext_csv.exists():
            raw = pd.read_csv(
                ext_csv,
                usecols=["scope", "decision_date", "code", "gpa", "cfoa", "financial_percentile"],
            )
            raw = raw[raw["scope"] == "gp"].copy()
            df = pd.DataFrame()
            df["symbol"] = raw["code"].astype(str).map(self.normalize_cn_symbol)
            df["decision_date"] = pd.to_datetime(raw["decision_date"]).dt.normalize()
            df["gpa"] = pd.to_numeric(raw["gpa"], errors="coerce")
            df["cfoa"] = pd.to_numeric(raw["cfoa"], errors="coerce")
            df["quality_pct"] = pd.to_numeric(raw["financial_percentile"], errors="coerce")
            df = df.dropna(subset=["decision_date", "gpa"]).sort_values(["symbol", "decision_date"])
            try:
                self.pit_cache_dir.mkdir(parents=True, exist_ok=True)
                df.to_parquet(local_cache, index=False)
            except Exception:
                pass
            self._quality_source = "external_synced_to_local_cache"
        else:
            self._quality_source = "missing"
            return pd.DataFrame(columns=["symbol", "decision_date", "gpa", "cfoa", "quality_pct"])

        if split == "explore":
            df = df[df["decision_date"] <= pd.Timestamp(EXPLORE_END)]
        elif split == "holdout":
            df = df[df["decision_date"] >= pd.Timestamp(HOLDOUT_START)]
        elif split != "full":
            raise ValueError(f"unsupported split mode: {split}")
        return df.reset_index(drop=True)

    def load_panel_bars(
        self,
        symbols: list[str],
        *,
        market: Literal["CN", "US"] = "CN",
        split: SplitMode = "explore",
        min_rows: int = 60,
    ) -> dict[str, pd.DataFrame]:
        """批量加载并对齐多标的日频宽表（行=日期，列=标的），供向量化面板因子与组合回测使用。"""
        fields = ("open", "high", "low", "close", "volume")
        buckets: dict[str, dict[str, pd.Series]] = {f: {} for f in fields}
        buckets["amount"] = {}
        turnover_bucket: dict[str, pd.Series] = {}

        for sym in symbols:
            try:
                bars = self.load_bars(sym, market=market, split=split)
            except FileNotFoundError:
                continue
            if len(bars) < min_rows:
                continue
            for f in fields:
                if f in bars.columns:
                    buckets[f][sym] = bars[f].astype(float)
            if "close" in bars.columns and "volume" in bars.columns:
                buckets["amount"][sym] = (bars["close"].astype(float) * bars["volume"].astype(float))
            if "turnover" in bars.columns:
                turnover_bucket[sym] = bars["turnover"].astype(float)

        panel: dict[str, pd.DataFrame] = {}
        for k, mapping in buckets.items():
            panel[k] = pd.DataFrame(mapping).sort_index() if mapping else pd.DataFrame()
        if turnover_bucket:
            panel["turnover"] = pd.DataFrame(turnover_bucket).sort_index()
        return panel

    def data_health_report(self) -> dict[str, object]:
        """透明汇报本地数据底座健康状态，杜绝外盘未挂载或数据过期导致的静默退化。"""
        etfs = self.list_cn_etfs()
        stocks = self.list_cn_stocks()
        pit = self.load_pit_fundamentals(split="full")
        inds = self.load_all_market_indicators(split="full")
        latest_ind_date = max((str(v.series.index[-1].date()) for v in inds.values() if len(v.series) > 0), default=None)
        ext_root = Path(os.environ.get("LEI_EXTERNAL_RESULTS_DIR", "/Volumes/win+mac通用/LeiSignal-新实验结果"))
        return {
            "cn_etf_count": len(etfs),
            "cn_stock_count": len(stocks),
            "pit_fundamentals_rows": int(len(pit)),
            "pit_fundamentals_symbols": int(pit["symbol"].nunique()) if len(pit) else 0,
            "pit_date_range": (
                f"{pit['decision_date'].min().date()} ~ {pit['decision_date'].max().date()}"
                if len(pit)
                else "missing"
            ),
            "market_indicators_count": len(inds),
            "market_indicators_latest_date": latest_ind_date,
            "quality_source": self._quality_source,
            "external_disk_mounted": ext_root.exists(),
            "local_offline_ready": len(etfs) > 0 and len(stocks) > 0 and len(pit) > 0,
        }

    @staticmethod
    def _clean_bars_df(path: Path) -> pd.DataFrame:
        df = pd.read_parquet(path).copy()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]
        cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
        return df[cols].astype(float)

    def load_bars(
        self,
        symbol: str,
        *,
        market: Literal["CN", "US"] = "CN",
        split: SplitMode = "explore",
    ) -> pd.DataFrame:
        folder = self.bp_cn if market == "CN" else self.bp_us
        base_path = folder / f"{symbol}.bars.parquet"
        live_path = (self.live_bars_dir / f"{symbol}.bars.parquet") if market == "CN" else None

        base_df = self._clean_bars_df(base_path) if base_path.exists() else None
        live_df = self._clean_bars_df(live_path) if (live_path is not None and live_path.exists()) else None

        if base_df is None and live_df is None:
            raise FileNotFoundError(f"行情文件不存在: {base_path}")
        if base_df is None:
            df = live_df
        elif live_df is None:
            df = base_df
        else:
            # 无缝拼接长历史与最新前复权行情：若重叠日因近期分红复权产生比例差，按重叠锚点对齐旧段价格（成交量保持不变）
            overlap = base_df.index.intersection(live_df.index)
            if len(overlap) > 0:
                anchor_dt = overlap[-1]
                b_cl = float(base_df.loc[anchor_dt, "close"])
                l_cl = float(live_df.loc[anchor_dt, "close"])
                if b_cl > 0 and l_cl > 0 and abs(l_cl / b_cl - 1.0) > 1e-4:
                    ratio = l_cl / b_cl
                    base_adj = base_df.copy()
                    for px_col in ("open", "high", "low", "close"):
                        if px_col in base_adj.columns:
                            base_adj[px_col] *= ratio
                else:
                    base_adj = base_df
                older = base_adj.loc[base_adj.index < live_df.index[0]]
                df = pd.concat([older, live_df]).sort_index()
            else:
                df = pd.concat([base_df, live_df]).sort_index()
                df = df[~df.index.duplicated(keep="last")]

        assert df is not None
        return self._slice_split(df, split)

    def load_all_market_indicators(self, *, split: SplitMode = "explore") -> dict[str, IndicatorSeries]:
        """加载系统已有的全部核心中美市场观测指标，并附带大白话金融含义。"""
        raw_series: dict[str, pd.Series] = {}

        # 1. A股股债性价比 (合并研究底表与 cache 实时更新)
        erp_candidates = [
            self.repo_root / "docs/experiments/raw/erp-trend-matrix-2026-11-07/erp-cn-reference.json",
            self.lab_home / "cache/erp_cn_reference_live.json",
        ]
        erp_ser_list: list[pd.Series] = []
        for erp_path in erp_candidates:
            if erp_path.exists():
                d = json.loads(erp_path.read_text(encoding="utf-8"))
                rows = list(d.get("points", [])) + list(d.get("dailySuccessors", []))
                if rows:
                    edf = pd.DataFrame(rows)
                    edf["date"] = pd.to_datetime(edf["date"]).dt.normalize()
                    edf = edf.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
                    erp_ser_list.append(edf["value"].astype(float))
        if erp_ser_list:
            combined_erp = erp_ser_list[-1]
            for s_prev in erp_ser_list[:-1]:
                combined_erp = combined_erp.combine_first(s_prev)
            raw_series["cn-erp"] = combined_erp.sort_index()

        # 2. 全A宽度 & 沪深300宽度 (合并历史底表与今日收盘实时缓存)
        br_all = self.repo_root / "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/breadth_all_a.parquet"
        if br_all.exists():
            bdf = pd.read_parquet(br_all)
            bdf.index = pd.to_datetime(bdf.index).tz_localize(None).normalize()
            raw_series["cn-breadth-b50"] = bdf["b50"].astype(float).sort_index()
            raw_series["cn-breadth-b200"] = bdf["b200"].astype(float).sort_index()

        br_live_path = self.lab_home / "cache/a_share_ma_breadth_history.json"
        if br_live_path.exists():
            try:
                bl = json.loads(br_live_path.read_text(encoding="utf-8"))
                b_rows = bl if isinstance(bl, list) else (bl.get("rows") or bl.get("history") or [])
                if b_rows:
                    bldf = pd.DataFrame(b_rows)
                    bldf["date"] = pd.to_datetime(bldf["date"]).dt.normalize()
                    bldf = bldf.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
                    if "ma50_pct" in bldf.columns:
                        s50 = pd.to_numeric(bldf["ma50_pct"], errors="coerce").dropna()
                        raw_series["cn-breadth-b50"] = (
                            s50.combine_first(raw_series["cn-breadth-b50"]).sort_index()
                            if "cn-breadth-b50" in raw_series
                            else s50
                        )
                    if "ma200_pct" in bldf.columns:
                        s200 = pd.to_numeric(bldf["ma200_pct"], errors="coerce").dropna()
                        raw_series["cn-breadth-b200"] = (
                            s200.combine_first(raw_series["cn-breadth-b200"]).sort_index()
                            if "cn-breadth-b200" in raw_series
                            else s200
                        )
            except Exception:
                pass

        br_300 = self.repo_root / "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/breadth_csi300.parquet"
        if br_300.exists():
            b3 = pd.read_parquet(br_300)
            b3.index = pd.to_datetime(b3.index).tz_localize(None).normalize()
            if "b50" in b3.columns:
                raw_series["csi300-breadth-b50"] = b3["b50"].astype(float).sort_index()

        # 3. 10年长历史 下跌价格冲击 & STR (2016-2026)
        da_path = self.repo_root / "docs/experiments/raw/douyin-observation-models-overlap-2026-10-31/observation-integration-20261101/compute/daily-aggregates.json"
        if da_path.exists():
            da = json.loads(da_path.read_text(encoding="utf-8"))
            for key in ("downside-price-impact", "salience-str"):
                pts = da.get("series", {}).get(key, {}).get("points", [])
                if pts:
                    sdf = pd.DataFrame(pts)
                    sdf["date"] = pd.to_datetime(sdf["date"]).dt.normalize()
                    sdf = sdf.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
                    raw_series[key] = pd.to_numeric(sdf["value"], errors="coerce").dropna()

        # 4. 11年长历史 动态焦点股动量（优先本机 pit_cache，外盘挂载时自动同步至本地缓存）
        local_focus = self.pit_cache_dir / "focus_momentum.parquet"
        ext_root = Path(os.environ.get("LEI_EXTERNAL_RESULTS_DIR", "/Volumes/win+mac通用/LeiSignal-新实验结果"))
        ext_focus = (
            ext_root
            / "focus-dynamic-zero-core-20261104"
            / "focus-dynamic-zero-core-20261104-20261104T224812-66497831abbf"
            / "result/observations.csv"
        )
        if local_focus.exists():
            try:
                fdf = pd.read_parquet(local_focus)
                fdf.index = pd.to_datetime(fdf.index).tz_localize(None).normalize()
                raw_series["focus-momentum"] = pd.to_numeric(fdf["focus"], errors="coerce").dropna().sort_index()
            except Exception:
                pass
        elif ext_focus.exists():
            fdf = pd.read_csv(ext_focus)
            if "horizon" in fdf.columns:
                fdf = fdf[fdf["horizon"] == 20]
            fdf["date"] = pd.to_datetime(fdf["date"]).dt.normalize()
            fdf = fdf.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
            ser_focus = pd.to_numeric(fdf["focus"], errors="coerce").dropna()
            raw_series["focus-momentum"] = ser_focus
            try:
                self.pit_cache_dir.mkdir(parents=True, exist_ok=True)
                ser_focus.to_frame(name="focus").to_parquet(local_focus)
            except Exception:
                pass

        # 5. 观察面板 panel.v1.json 补齐其余中美指标与最新读数
        panel_path = self.repo_root / "web/public/research/market-observation-panel/panel.v1.json"
        if panel_path.exists():
            panel = json.loads(panel_path.read_text(encoding="utf-8"))
            for cid, card in panel.get("cards", {}).items():
                pts = card.get("series") or card.get("points") or []
                if not isinstance(pts, list) or len(pts) < 60:
                    continue
                pdf = pd.DataFrame(pts)
                if "date" not in pdf.columns or "value" not in pdf.columns:
                    continue
                pdf["date"] = pd.to_datetime(pdf["date"]).dt.normalize()
                pdf = pdf.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
                ser = pd.to_numeric(pdf["value"], errors="coerce").dropna()
                if cid in raw_series:
                    raw_series[cid] = ser.combine_first(raw_series[cid]).sort_index()
                else:
                    raw_series[cid] = ser

        result: dict[str, IndicatorSeries] = {}
        for ind_id, ser in raw_series.items():
            if ind_id not in INDICATOR_META:
                continue
            sliced = self._slice_split(ser.dropna().sort_index(), split)
            if len(sliced) < 40:
                continue
            name_cn, mkt, meaning, bottom_side = INDICATOR_META[ind_id]
            result[ind_id] = IndicatorSeries(
                id=ind_id,
                name_cn=name_cn,
                market=mkt,
                plain_meaning=meaning,
                expected_bottom_side=bottom_side,
                series=sliced,
            )
        return result
