"""全系统通用大白话智能提示引擎（universal_prompts）。

把经过 8~12 年逐年历史验证的硬规律沉淀为实时通用函数，彻底告别“只分析某一天快照”：
1. 任意单只股票/场内基金/场外基金实时提示 `evaluate_symbol_smart_prompt(symbol, entry_price=...)`：
   - 自动查财报排雷底色（真赚钱真现金流 vs 纸面利润流血雷区）；
   - 自动判当前买点与冷热（涨太猛禁追红灯 / 刚从大家成本区抬头好买点 / 跌超三成停跌一个月抬头可补仓 / 还在往下掉别伸手接）；
   - 自动算【两步拿住好股票】动态保护线（支持传入买进成本价，实时判断该盯“第一步20日均线保命线”还是“第二步60日均线与保本拿牛线”）。
2. 全账户持仓动态提示与自动待办 `evaluate_portfolio_smart_prompts(...)`：
   - 随用户持仓增删改与每日最新净值动态重算；
   - 平时没事不打扰；一旦任意持仓触发【涨疯破20日线减半锁利】、【跌透停稳一个月抬头可补新钱】、【假海外基回暖进入换美股指数窗口】，自动生成待办提醒。
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import numpy as np
import pandas as pd

from .chip_trend import compute_live_chip_metrics, rank_top_candidates
from .data_portal import DataPortal
from .fund_evaluator import evaluate_all_fund_opportunities
from .indicator_audit import render_market_weather
from .portfolio_doctor import _fetch_or_load_off_exchange_nav, diagnose_user_portfolio


def _normalize_symbol(raw_sym: str) -> tuple[str, str]:
    """将用户输入或路由传入的代码规范化，返回 (标准代码, 类别: stock/etf/us/off_fund)。"""
    s = raw_sym.strip().upper()
    if re.fullmatch(r"[A-Z.]{1,8}", s) and not s.endswith((".SS", ".SZ")):
        return s, "us"
    if s.endswith((".SS", ".SZ")):
        code6 = s[:6]
        if code6.startswith(("51", "15", "56", "58")):
            return s, "etf"
        return s, "stock"
    if re.fullmatch(r"\d{6}", s):
        if s.startswith(("51", "56", "58")):
            return f"{s}.SS", "etf"
        if s.startswith("15"):
            return f"{s}.SZ", "etf"
        if s.startswith(("600", "601", "603", "605", "688")):
            return f"{s}.SS", "stock"
        # 000/001/002/003/300/301 既可能是股票也可能是场外基金；优先看本地股票池与财报池是否存在该股票
        return s, "ambiguous_6digit"
    return s, "stock"


def _load_any_symbol_bars(portal: DataPortal, raw_sym: str) -> tuple[str, str, str, pd.DataFrame]:
    """加载任意股票、场内基金、美股或场外基金的历史日线，未缓存的A股在非测试环境下按需实时拉取。"""
    norm, kind = _normalize_symbol(raw_sym)
    fund_df = portal.load_latest_fundamentals_table()

    if kind == "ambiguous_6digit":
        cand_sz = f"{norm}.SZ"
        is_known_stock = (
            (portal.bp_cn / f"{cand_sz}.bars.parquet").exists()
            or (portal.live_bars_dir / f"{cand_sz}.bars.parquet").exists()
            or (len(fund_df) > 0 and cand_sz in set(fund_df["symbol"].astype(str)))
        )
        if is_known_stock:
            norm, kind = cand_sz, "stock"
        else:
            kind = "off_fund"

    if kind == "off_fund":
        off_dir = portal.lab_home / "strategy_lab_bars/off_exchange_funds"
        nav_obj = _fetch_or_load_off_exchange_nav(norm, off_dir)
        if not nav_obj.get("dates"):
            raise FileNotFoundError(f"未找到基金 {norm} 的净值数据")
        idx = pd.to_datetime(nav_obj["dates"])
        adj = pd.Series(nav_obj["adj_nav"], index=idx, dtype=float)
        unit = pd.Series(nav_obj["unit_nav"], index=idx, dtype=float)
        # 按最新单位净值等比例缩放复权序列，使展示价格与真实单位净值一致，同时保留分红再投资斜率
        scale = float(unit.iloc[-1] / adj.iloc[-1]) if adj.iloc[-1] > 0 else 1.0
        px = (adj * scale).loc[~adj.index.duplicated(keep="last")].sort_index()
        bars = pd.DataFrame(
            {"open": px, "high": px * 1.001, "low": px * 0.999, "close": px, "volume": 1_000_000.0},
            index=px.index,
        )
        clean_name = str(nav_obj.get("name", norm)).replace("(QDII)", "(海外)").replace("ETF", "指数")
        return norm, clean_name, "off_fund", bars

    if kind == "us":
        bars = portal.load_bars(norm, market="US", split="full")
        return norm, portal.get_asset_name(norm), "us", bars

    # stock or etf
    try:
        bars = portal.load_bars(norm, market="CN", split="full")
    except FileNotFoundError:
        if "pytest" in sys.modules:
            raise
        from lei_signal.data.providers import TencentPriceProvider

        provider = TencentPriceProvider(timeout=8.0, max_bars=650, attempts=2, backoff=0.6)
        fetched = provider.fetch(norm, min_rows=30)
        bars = fetched.bars.copy()
        bars.index = pd.to_datetime(bars.index).tz_localize(None).normalize()
        bars = bars.sort_index()
        portal.live_bars_dir.mkdir(parents=True, exist_ok=True)
        bars.to_parquet(portal.live_bars_dir / f"{norm}.bars.parquet")

    name = portal.get_asset_name(norm)
    if len(fund_df) > 0 and kind == "stock":
        hit = fund_df[fund_df["symbol"] == norm]
        if len(hit) > 0 and hit.iloc[0]["name"]:
            name = str(hit.iloc[0]["name"])
    return norm, name.replace("ETF", "基金"), kind, bars


def evaluate_symbol_smart_prompt(
    portal: DataPortal,
    symbol: str,
    *,
    entry_price: float | None = None,
) -> dict[str, object]:
    """对任意单只股票或基金实时计算大白话【排雷底色 + 买点补仓判断 + 两步拿牛保护线】。"""
    norm_sym, name_cn, kind, bars = _load_any_symbol_bars(portal, symbol)
    if len(bars) < 65:
        return {
            "symbol": norm_sym,
            "name": name_cn,
            "kind": kind,
            "available": False,
            "reason": "上市或净值记录不足三个月，暂不生成趋势与成本区提示。",
        }

    m = compute_live_chip_metrics(bars)
    cl_ser = bars["close"].astype(float)
    cl = float(cl_ser.iloc[-1])
    as_of = bars.index[-1].strftime("%Y-%m-%d")

    ma20_ser = m["ma20"]
    ema20_ser = m["ema20"]
    ma60_ser = m["ma60"]
    ma200_ser = cl_ser.rolling(200, min_periods=120).mean()
    hi250_ser = cl_ser.rolling(250, min_periods=100).max()
    atr_ser = m["atr20"]

    ma20 = float(ma20_ser.iloc[-1])
    ma20_prev3 = float(ma20_ser.iloc[-4]) if len(ma20_ser) >= 4 else ma20
    ema20 = float(ema20_ser.iloc[-1])
    ma60 = float(ma60_ser.iloc[-1])
    ma200 = float(ma200_ser.iloc[-1]) if np.isfinite(ma200_ser.iloc[-1]) else np.nan
    hi250 = float(hi250_ser.iloc[-1]) if np.isfinite(hi250_ser.iloc[-1]) else cl
    atr = float(atr_ser.iloc[-1]) if np.isfinite(atr_ser.iloc[-1]) else cl * 0.02

    poc = float(m["poc_price"].iloc[-1]) if np.isfinite(m["poc_price"].iloc[-1]) else ma60
    prof = float(m["profit_ratio"].iloc[-1]) if np.isfinite(m["profit_ratio"].iloc[-1]) else 0.5
    over10 = float(m["overhead_near10"].iloc[-1]) if np.isfinite(m["overhead_near10"].iloc[-1]) else 0.15

    dist_ma200 = (cl / ma200 - 1.0) if (np.isfinite(ma200) and ma200 > 0) else None
    dist_ma60 = (cl / ma60 - 1.0) if (np.isfinite(ma60) and ma60 > 0) else 0.0
    dd_1y = (cl / hi250 - 1.0) if hi250 > 0 else 0.0
    stopped_1m = bool(np.min(cl_ser.iloc[-20:]) >= np.min(cl_ser.iloc[-35:-5]) * 0.995) if len(cl_ser) >= 40 else False
    ma20_up = (cl >= ma20) and (ma20 >= ma20_prev3 * 0.999)

    vol60_ser = cl_ser.pct_change().rolling(60, min_periods=25).std()
    daily_vol_raw = float(vol60_ser.iloc[-1]) if (len(vol60_ser) > 0 and np.isfinite(vol60_ser.iloc[-1])) else 0.02
    daily_vol_pct = round(daily_vol_raw * 100.0, 2)
    if daily_vol_pct <= 1.6:
        volatility_note_cn = f"平时走得比较稳（近三月每天平均晃动约 {daily_vol_pct:.1f}%）"
    elif daily_vol_pct <= 2.6:
        volatility_note_cn = f"日常起伏适中（近三月每天平均晃动约 {daily_vol_pct:.1f}%）"
    else:
        volatility_note_cn = f"平时上蹿下跳波动大（近三月每天平均晃动约 {daily_vol_pct:.1f}%，单笔别买重）"

    # ── 1. 底色与财务排雷检查 ──
    quality_badge = "🟢 指数一篮子分散"
    quality_detail = "跟踪一篮子成分股，无单家公司暴雷退市风险。"
    is_landmine = False

    if kind == "stock":
        fund_df = portal.load_latest_fundamentals_table()
        hit = fund_df[fund_df["symbol"] == norm_sym] if len(fund_df) > 0 else pd.DataFrame()
        if len(hit) > 0:
            r = hit.iloc[0]
            roe = float(r["roe"]) if pd.notna(r["roe"]) else np.nan
            pyoy = float(r["profit_yoy"]) if pd.notna(r["profit_yoy"]) else np.nan
            ocf = float(r["ocf_ps"]) if pd.notna(r["ocf_ps"]) else np.nan
            ind = str(r["industry"] or "其他")
            tier = str(r["tier"] or "other")
            is_fin = any(k in ind for k in ("银行", "保险", "证券", "电力"))
            if (pd.notna(ocf) and ocf < -0.05 and not is_fin) or (pd.notna(roe) and roe < 0):
                is_landmine = True
                quality_badge = "🔴 财务排雷预警（少碰）"
                quality_detail = (
                    f"所属{ind}：最新季报每股经营现金流为 {ocf:.2f} 元、净资产回报率 {roe:.1f}%——"
                    "账面缺真金白银流入或处于亏损，历史检验此类公司一年内深跌超三成概率翻倍。"
                )
            else:
                # 补充核查最新年报是否有“借大钱瞎扩张”（总资产一年暴增超35%且负债率超60%）
                reckless_note = ""
                bal_dir = portal.lab_home / "strategy_lab_bars/hist_capital_discipline"
                bal_files = sorted(bal_dir.glob("balance_*.parquet")) if bal_dir.exists() else []
                if bal_files and not is_fin:
                    try:
                        latest_bal = pd.read_parquet(bal_files[-1])
                        bhit = latest_bal[latest_bal["symbol"] == norm_sym]
                        if len(bhit) > 0:
                            ag_v = float(bhit.iloc[0]["asset_growth_yoy"]) if pd.notna(bhit.iloc[0]["asset_growth_yoy"]) else np.nan
                            db_v = float(bhit.iloc[0]["debt_ratio"]) if pd.notna(bhit.iloc[0]["debt_ratio"]) else np.nan
                            if np.isfinite(ag_v) and ag_v > 35.0 and np.isfinite(db_v) and db_v > 60.0:
                                is_landmine = True
                                reckless_note = f" ⚠️ 年报总资产暴增 {ag_v:+.0f}% 且负债率高达 {db_v:.0f}%，属高债大扩张雷区（熊市极易深跌）。"
                    except Exception:
                        pass

                if is_landmine:
                    quality_badge = "🔴 高债大扩张预警（少碰）"
                    quality_detail = f"所属{ind}：{reckless_note.strip()}"
                elif tier == "leader":
                    quality_badge = "🟢 行业真龙头（底子硬）"
                    quality_detail = (
                        f"所属{ind}头部公司：三季报净资产回报率 {roe:.1f}%、净利同比 {pyoy:+.1f}%、"
                        f"每股经营现金流 {ocf:.2f} 元，赚钱能力与现金流均过关。"
                    )
                elif tier == "small_giant":
                    quality_badge = "🟢 细分小巨人（高成长）"
                    quality_detail = (
                        f"所属{ind}成长骨干：三季报净资产回报率 {roe:.1f}%、净利同比 {pyoy:+.1f}%、"
                        f"每股经营现金流 {ocf:.2f} 元，真金白银赚钱。"
                    )
                else:
                    quality_badge = "🟡 普通盈利公司"
                    quality_detail = (
                        f"所属{ind}：净资产回报率 {roe:.1f}%、每股经营现金流 {ocf:.2f} 元，财务尚无硬伤但未进同行顶尖前排。"
                    )
        else:
            quality_badge = "⚪ 暂无最新季报缓存"
            quality_detail = "运行收盘刷新后可自动补齐该公司最新现金流与盈利排雷结果。"
    elif kind == "us":
        quality_badge = "🟢 海外压舱石资产"
        quality_detail = "海外长牛市场：四十年历史验证长期持有最优，不宜频繁进出猜顶底。"

    # ── 2. 当前能不能买 / 能不能拿闲钱补 ──
    stage1_stop = round(min(ma20, ema20) - 0.55 * atr, 3)
    floor_20d = round(float(np.min(bars["low"].iloc[-20:])) * 0.985, 3)

    if is_landmine:
        buy_light = "🔴 财务雷区·不建议买"
        buy_advice = "现金流或盈利底子不过关，哪怕图形好看也容易踩坑，建议换看同行业真龙头。"
    elif (dist_ma200 is not None and dist_ma200 >= 0.55) or dist_ma60 >= 0.28:
        buy_light = "🔴 涨得太猛·严禁追高"
        over_txt = f"高出一年平均价 {dist_ma200*100:+.0f}%" if dist_ma200 is not None else f"高出近三月均价 {dist_ma60*100:+.0f}%"
        buy_advice = f"当前{over_txt}，处于人挤人的大涨沸腾区：12年历史里在这儿追高超六成会挨两成以上暴跌，千万别追。"
    elif dd_1y <= -0.30 and stopped_1m and ma20_up:
        buy_light = "🟢 跌透停稳抬头·可低吸/可补仓"
        buy_advice = (
            f"距一年高点已跌去 {abs(dd_1y)*100:.0f}%，且连续一个月没再破新低、刚重新站上近一月均价（{ma20:.3f}）："
            f"属于稳当低吸或拿新工资补一笔的位置，保护线设在近期最低点 {floor_20d}。"
        )
    elif dd_1y <= -0.30 and not ma20_up:
        buy_light = "🔵 深跌磨底·先别伸手接"
        buy_advice = (
            f"距一年高点已跌去 {abs(dd_1y)*100:.0f}%，目前还在近一月均价（{ma20:.3f}）下方："
            "手里原有的老仓千万别在地板上割肉，但新钱也等它停跌一个月并站上20日均线再补。"
        )
    elif kind != "off_fund" and ma20_up and cl >= poc and ((cl / poc - 1.0) <= 0.12) and prof >= 0.60 and over10 <= 0.14:
        risk_pct = max((cl - stage1_stop) / cl * 100.0, 1.0)
        buy_light = "🟢 刚过大家成本区·好买点"
        buy_advice = (
            f"股价刚站稳大多数人集中买进的成本价（{poc:.2f}）上方，场内 {prof*100:.0f}% 的人赚钱、头顶套牢卖压很轻；"
            f"往下离第一步保命线（{stage1_stop}）仅 {risk_pct:.1f}%，看错亏得少、看对空间大。"
        )
    elif ma20_up and cl > ma60:
        buy_light = "🟡 趋势向上但已离开底价·等回靠"
        buy_advice = (
            f"目前顺着均线往上走，但离底下成本密集区（{poc:.2f}）已有一定距离；"
            f"有仓位的继续拿着，空仓的别急追猛涨，等回靠近一月均价（{ma20:.2f}）附近再看。"
        )
    else:
        buy_light = "⚪ 走势偏弱·多看少动"
        buy_advice = f"当前在近一月均价（{ma20:.2f}）下方或趋势未理顺，耐心等站稳均线再动手。"

    # ── 3. 买进去之后怎么拿住不卖早（动态两步保护线）──
    stage2_wide_stop = round(max(ma60, entry_price * 1.02) if (entry_price and entry_price > 0) else ma60, 3)

    if kind == "us":
        hold_stage = "长期压舱石持有"
        active_stop_price = None
        hold_advice = "美股宽基属于长期压舱石：历史检验任何短线折腾都跑输拿着不动，忽略日常波动即可。"
    elif kind == "off_fund":
        recent_max_d200 = (
            float(np.nanmax(cl_ser.iloc[-15:] / ma200_ser.iloc[-15:] - 1.0))
            if (len(cl_ser) >= 200 and np.isfinite(ma200))
            else 0.0
        )
        if recent_max_d200 >= 0.55 and cl < ma20:
            hold_stage = "🔴 沸腾破线·立刻赎回一半锁利"
            active_stop_price = round(ma20, 3)
            hold_advice = "近期高出一年平均价超55%后跌破20日均线：立刻赎回一半锁住大波段利润（留一半防后续二波冲高）。"
        elif dd_1y <= -0.30:
            hold_stage = "🔵 深坑区·严禁地板割肉"
            active_stop_price = None
            hold_advice = "场外基金已深跌超三成：历史实测此时止损超半数卖在大底前夜，安心拿住等回暖，绝不在坑底割肉。"
        else:
            hold_stage = "🟢 常态持有·不到沸腾不折腾"
            active_stop_price = None
            hold_advice = "场外基金申赎费高，平时别按短线均线进出；只要没冲到高于一年均价55%的沸腾区，就稳稳拿着。"
    else:
        # 股票与场内基金：两步拿牛法！
        if entry_price is not None and entry_price > 0:
            gain_pct = (cl / entry_price - 1.0) * 100.0
            # 判断底下大部队成本是否已经明显搬到买进价高处(>15%)
            chips_moved_high = poc > entry_price * 1.15
            if gain_pct >= 15.0 and not chips_moved_high:
                hold_stage = f"🟢 第二步·放心拿住大涨（当前浮盈 {gain_pct:+.1f}%）"
                active_stop_price = stage2_wide_stop
                if cl < active_stop_price:
                    hold_advice = f"⚠️ 现价已跌破第二步宽保护线 {active_stop_price}，建议落袋保住胜果！"
                else:
                    hold_advice = (
                        f"你已赚超15%，且大多数人的买进成本（{poc:.2f}）还留在低位没跑！"
                        f"中途就算跌破20日均线（{ma20:.2f}）也只是小洗盘别卖早了，只盯宽保护线 {active_stop_price}（近三月均价与买进价+2%较高者）。"
                    )
            elif chips_moved_high and cl < poc and cl < ema20:
                hold_stage = f"🔴 高处换手破位·落袋锁利（当前浮盈 {gain_pct:+.1f}%）"
                active_stop_price = round(poc, 3)
                hold_advice = f"大多数人的持仓成本已搬到高处（{poc:.2f}）且现价跌破该成本区与均线，说明高处接盘资金被套，建议立刻落袋锁利！"
            elif gain_pct >= 15.0 and chips_moved_high:
                trail_high_stop = round(max(stage1_stop, min(poc * 0.985, ma20)), 3)
                hold_stage = f"🟢 第二步·抬高保护跟紧利润（当前浮盈 {gain_pct:+.1f}%）"
                active_stop_price = trail_high_stop
                hold_advice = (
                    f"你已赚超15%，近期高处换手增多使大家平均成本跟到了 {poc:.2f}（现价仍在上方健康运行）；"
                    f"把保护线抬高到 {trail_high_stop} 跟紧利润，跌破就落袋锁住大肉。"
                )
            else:
                hold_stage = f"🟡 第一步·严守保命线（当前盈亏 {gain_pct:+.1f}%）"
                active_stop_price = stage1_stop
                if cl < stage1_stop:
                    hold_advice = f"⚠️ 现价（{cl:.2f}）已跌破第一步保命线 {stage1_stop}，还没攒够利润垫时先出来避险，绝不让小亏拖成三四成大坑！"
                else:
                    hold_advice = (
                        f"目前还没攒够15%利润垫，先盯紧第一步保命线 {stage1_stop}；"
                        f"守住就继续拿，等涨过 {entry_price*1.15:.2f}（+15%）后自动切换为第二步拿住模式。"
                    )
        else:
            hold_stage = "两步拿住法（可填买进价自动算）"
            active_stop_price = stage1_stop
            hold_advice = (
                f"① 刚买进没赚够15%时：盯紧保命线 {stage1_stop}（跌破痛快走，防深套）；"
                f"② 赚够15%且大家的主成本（现为 {poc:.2f}）没搬到高处时：不怕破20日均线小洗盘，改盯近三月均价 {ma60:.2f} 与买进价+2%拿足大涨。"
            )

    # ── 4. 按波动与止损距离算单笔建议仓位上限（按风险定仓） ──
    if kind == "us":
        suggested_max_position_pct = 30.0
        sizing_advice_cn = f"底仓参考：海外宽基适合做长期压舱石，可逐步配到账户两到四成（{volatility_note_cn}）。"
    elif is_landmine:
        suggested_max_position_pct = 0.0
        sizing_advice_cn = "单笔建议仓位上限：0%（公司底子已触发排雷红灯，不花钱冒险）。"
    elif "严禁追高" in buy_light:
        suggested_max_position_pct = 0.0
        sizing_advice_cn = f"新买建议仓位上限：0%（当前处于涨太猛的沸腾红灯区，等降温回稳再按波动定仓；{volatility_note_cn}）。"
    else:
        raw_stop_dist = (cl - stage1_stop) / cl if (cl > 0 and stage1_stop < cl) else (2.0 * atr / max(cl, 1e-6))
        eff_risk_dist = float(max(raw_stop_dist, 2.5 * daily_vol_raw, 0.04))
        if kind == "stock":
            risk_budget = 0.010  # 单只股票看错止损，最多只亏总账户 1.0%
            lo_cap, hi_cap = 5.0, 15.0
        elif kind == "etf":
            risk_budget = 0.012  # 场内行业一篮子基金，最多只亏总账户 1.2%
            lo_cap, hi_cap = 8.0, 25.0
        else:
            risk_budget = 0.012
            lo_cap, hi_cap = 8.0, 20.0
        suggested_max_position_pct = round(float(np.clip((risk_budget / eff_risk_dist) * 100.0, lo_cap, hi_cap)), 1)
        sizing_advice_cn = (
            f"单笔建议上限：不超过总资金的 {suggested_max_position_pct:.0f}%"
            f"（现价离止损保护线约 {eff_risk_dist*100:.1f}%，按看错最多亏总账户 {risk_budget*100:.1f}% 倒推；{volatility_note_cn}）。"
        )

    return {
        "symbol": norm_sym,
        "name": name_cn,
        "kind": kind,
        "available": True,
        "as_of": as_of,
        "close": round(cl, 3),
        "ma20": round(ma20, 3),
        "ma60": round(ma60, 3),
        "ma200": round(ma200, 3) if np.isfinite(ma200) else None,
        "main_cost_peak": round(poc, 3),
        "profit_holders_pct": round(prof * 100.0, 1),
        "dist_ma200_pct": round(dist_ma200 * 100.0, 1) if dist_ma200 is not None else None,
        "drawdown_1y_pct": round(dd_1y * 100.0, 1),
        "daily_vol_pct": daily_vol_pct,
        "volatility_note_cn": volatility_note_cn,
        "suggested_max_position_pct": suggested_max_position_pct,
        "sizing_advice_cn": sizing_advice_cn,
        "quality_badge": quality_badge,
        "quality_detail": quality_detail,
        "buy_light": buy_light,
        "buy_advice": buy_advice,
        "hold_stage": hold_stage,
        "active_stop_price": active_stop_price,
        "stage1_stop_price": stage1_stop,
        "stage2_ma60_price": round(ma60, 3),
        "hold_advice": hold_advice,
    }


def _eval_single_harbor_asset(
    portal: DataPortal,
    *,
    symbol: str,
    code: str,
    display_name: str,
    gold_fallback_json: Path | None = None,
) -> dict[str, object]:
    """检查单只空仓过渡资产（黄金或高分红低波动基金）是否稳在近三月平均价（60日均线）上方。"""
    ser: pd.Series | None = None
    used_code = code
    used_sym = symbol
    try:
        bars = portal.load_bars(symbol, market="CN", split="full")
        if len(bars) >= 60:
            ser = bars["close"].astype(float).sort_index()
    except FileNotFoundError:
        ser = None

    if ser is None and gold_fallback_json is not None and gold_fallback_json.exists():
        try:
            raw = json.loads(gold_fallback_json.read_text(encoding="utf-8"))
            dates = raw.get("dates", [])
            vals = raw.get("nav", raw.get("unit_nav", []))
            if len(dates) >= 60 and len(dates) == len(vals):
                s = pd.Series(vals, index=pd.to_datetime(dates), dtype=float).sort_index()
                ser = s[~s.index.duplicated(keep="last")]
                used_code = "000216"
                used_sym = "000216"
        except Exception:
            ser = None

    if ser is None or len(ser) < 60:
        return {
            "code": used_code,
            "symbol": used_sym,
            "name": display_name,
            "available": False,
            "as_of": None,
            "close": None,
            "ma60": None,
            "dist_ma60_pct": None,
            "is_steady": False,
            "status_cn": "⚪ 暂无近期净值记录",
        }

    cl = float(ser.iloc[-1])
    ma60 = float(ser.rolling(60, min_periods=30).mean().iloc[-1])
    dist_pct = (cl / ma60 - 1.0) * 100.0 if ma60 > 0 else 0.0
    is_steady = bool(cl > ma60)
    as_of = ser.index[-1].strftime("%Y-%m-%d")
    status_cn = (
        f"🟢 稳在近三月均价上方（高出 {dist_pct:+.1f}%，可停放闲钱过渡）"
        if is_steady
        else f"🔴 跌破近三月均价（低于 {dist_pct:+.1f}%，暂不放，转货币理财）"
    )
    return {
        "code": used_code,
        "symbol": used_sym,
        "name": display_name,
        "available": True,
        "as_of": as_of,
        "close": round(cl, 3),
        "ma60": round(ma60, 3),
        "dist_ma60_pct": round(dist_pct, 1),
        "is_steady": is_steady,
        "status_cn": status_cn,
    }


def evaluate_idle_cash_harbor(portal: DataPortal) -> dict[str, object]:
    """实时给出空仓闲钱去向指示灯：检查黄金基金与高分红稳健基金是否稳在近三月均价上方。

    8 年逐年实测（2019–2026）：行业波段有超四成时间处于空仓等待，把闲钱交给走稳在近三月均价上方的黄金与高分红基金过渡
    （谁跌破近三月均价就撤回货币理财），比干放现金或货币每年多赚 4~5 个百分点，且 8 年中有 6 年跑赢闲放现金。
    """
    gold_fallback = portal.lab_home / "strategy_lab_bars/hist_capital_discipline/gold_000216.json"
    gold = _eval_single_harbor_asset(
        portal,
        symbol="518850.SS",
        code="518850",
        display_name="黄金基金",
        gold_fallback_json=gold_fallback,
    )
    high_div = _eval_single_harbor_asset(
        portal,
        symbol="512890.SS",
        code="512890",
        display_name="高分红低波动基金",
    )

    g_ok = bool(gold["available"] and gold["is_steady"])
    d_ok = bool(high_div["available"] and high_div["is_steady"])

    if g_ok and d_ok:
        headline_cn = "🟢 黄金与高分红基金都在近三月均价上方走稳：空仓闲钱可各放一半过渡，别干放活期。"
        allocation_cn = "空仓闲钱参考：50% 黄金基金 + 50% 高分红低波动基金（哪只跌破近三月均价就把那一半转回货币理财）。"
    elif g_ok and not d_ok:
        headline_cn = "🟡 黄金基金稳在近三月均价上方、高分红已跌破：空仓闲钱可优先放黄金基金过渡。"
        allocation_cn = "空仓闲钱参考：可放黄金基金过渡，高分红基金暂不碰；一旦黄金也跌破近三月均价，全部转回货币理财保本。"
    elif d_ok and not g_ok:
        headline_cn = "🟡 高分红基金稳在近三月均价上方、黄金近期已跌破：空仓闲钱可放高分红基金过渡，黄金先回避。"
        allocation_cn = "空仓闲钱参考：可放高分红低波动基金过渡，黄金等重新站稳近三月均价再看；若高分红也跌破均价，转回货币理财保本。"
    else:
        headline_cn = "⚪ 黄金与高分红基金目前均未站稳近三月均价：空仓闲钱老实放货币理财保本。"
        allocation_cn = "空仓闲钱参考：100% 放货币基金或银行活期理财保本，等哪只站回近三月均价再挪过去。"

    dates = [d for d in (gold.get("as_of"), high_div.get("as_of")) if isinstance(d, str)]
    as_of = max(dates) if dates else None

    return {
        "as_of": as_of,
        "headline_cn": headline_cn,
        "allocation_cn": allocation_cn,
        "gold": gold,
        "high_dividend": high_div,
    }


def evaluate_portfolio_smart_prompts(
    portal: DataPortal,
    *,
    portfolio_db_path: str | Path | None = None,
) -> dict[str, object]:
    """实时扫描用户当前持仓表，提取【必须动手的红黄灯待办 + 发工资补仓导航 + 每只持仓动态健康灯】。"""
    # 若测试或调用方指定了自定义 sqlite 路径，使用对应目录或临时只读连接
    lab_home = portal.lab_home
    if portfolio_db_path is not None:
        db_p = Path(portfolio_db_path)
        if db_p.parent != lab_home and (db_p.parent / "lab.db") == db_p:
            lab_home = db_p.parent

    diag = diagnose_user_portfolio(lab_home)
    items = diag.get("items", [])

    # 提取真正需要用户动手的动态事件（平时0打扰，触发才提醒！）
    urgent_actions: list[dict[str, str]] = []
    for it in items:
        light = str(it.get("health_light", ""))
        fname = str(it.get("fund_name", ""))
        codes = str(it.get("codes_display", "-"))
        if "减半锁利红灯" in light:
            urgent_actions.append({
                "level": "urgent",
                "code": codes.split("/")[0],
                "name": fname,
                "title": f"🔴 {fname}：涨疯后跌破20日均线，建议赎回一半锁住利润",
                "detail": str(it.get("action_advice_cn", "")),
            })
        elif "沸腾禁买红灯" in light:
            urgent_actions.append({
                "level": "warn",
                "code": codes.split("/")[0],
                "name": fname,
                "title": f"🔴 {fname}：高于年线55%以上极热区，严禁追高加仓",
                "detail": str(it.get("action_advice_cn", "")),
            })

    for add_name in diag.get("paycheck_add_ready", []):
        urgent_actions.append({
            "level": "opportunity",
            "code": "-",
            "name": str(add_name),
            "title": f"🟢 {add_name}：已跌超三成且停跌一个月重新站上20日均线，可拿闲钱补一笔",
            "detail": "满足12年验证的稳当补仓条件；补完后若跌破近期最低点2%，先把新补的钱撤回保命。",
        })

    for sw_name in diag.get("switch_window_ready", []):
        urgent_actions.append({
            "level": "switch",
            "code": "-",
            "name": str(sw_name),
            "title": f"🟡 {sw_name}：处于盈利或回暖窗口，可分批换成标普500/纳斯达克100指数",
            "detail": "这只基金美股占比偏低、波动大，趁现在不吃亏分两三次转入纯正低费率美股宽基压舱石。",
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "urgent_actions": urgent_actions,
        "portfolio_diagnosis": diag,
    }


def build_one_page_overview(portal: DataPortal, *, top_n: int = 8) -> dict[str, object]:
    """实时组装【一页看全】完整数据包：顶栏大盘极端警报 + 空仓闲钱去向灯 + 左屏持仓健康灯与工资投向 + 右屏基金与龙头尖子生。"""
    weather = render_market_weather(portal)
    idle_harbor = evaluate_idle_cash_harbor(portal)
    port_prompts = evaluate_portfolio_smart_prompts(portal)
    fund_opps = evaluate_all_fund_opportunities(portal)
    leaders = rank_top_candidates(portal, top_n=top_n, pool="leader", split="full")
    small_giants = rank_top_candidates(portal, top_n=top_n, pool="small_giant", split="full")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_weather": weather,
        "idle_cash_harbor": idle_harbor,
        "left_portfolio": port_prompts,
        "right_picks": {
            "right_side_sector_funds": fund_opps.get("right_side_sector_picks", []),
            "left_side_turnaround_funds": fund_opps.get("left_side_turnaround_picks", []),
            "crowded_warnings": fund_opps.get("crowded_no_chase_warnings", []),
            "broad_compass": fund_opps.get("broad_compass", []),
            "industry_leaders": leaders,
            "small_giants": small_giants,
        },
    }
