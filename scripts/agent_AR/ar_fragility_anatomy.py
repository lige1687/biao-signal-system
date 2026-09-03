# -*- coding: utf-8 -*-
"""
任务 AR：现役已验证组合的历史脆弱性解剖（系统 X 光片）
日期：2026-09-03 · 执行：agent AR · 会话纪律见 AGENTS.md

================ 跑前写死的协议（本 docstring 即预注册，跑完不改） ================

【组合口径】现役组合无单一权威定义（报告开头将如实陈述）。本解剖主口径取
最新认证版 = 合体 80/20 分账制（combined-certification-report-2026-08-31，
6/6 判定 PASS）：
  组合权益(t) = 0.8 * B9主仓腿(t) + 0.2 * LEI卫星腿(t)   [分账制数学恒等式]
参考口径：现金腿机械修正版 = cash_leg 报告 combo_cash_const_1.8（+1.8%/年
空仓计息，机械修正非策略）。防守版（hs300/spy/qqq_defense）与两只版、
终极组合均不在认证组合内，本解剖不纳入（无认证合并曲线，红线禁止拼造）。

【曲线来源（全部为归档 raw 复用，零复算零新回测）】
1) 主曲线 combo/b9/lei/hold：raw/combined_cert/combined_curves.csv
   （2017-03-24→2026-07-17，认证工件）拼接 raw/ultimate/ultimate_curves.csv
   同名列（2026-07-18→2026-08-18）。拼接前置校验：重叠区逐位差 = 0，
   若 |diff|>1e-9 立即中止。
2) 现金增强参考：raw/cash_leg/cash_curves.csv combo_cash_const_1.8。
3) B9 长窗上下文（2015-06-16 起，覆盖 2015 股灾/2016 熔断段）：raw/cash_leg/
   cash_curves.csv b9_cash0（portfolio_split 无现金计息口径；与认证 B9 日收益
   相关 0.999993、平均日差 0.008bp ≈ 2bp/年，口径差在报告注明）。
4) 市场宽度状态：raw/lei/a_share_breadth_33y_snapshot.json 的 ma200_pct
   （= B200 全A等权宽度读数），仅作状态标注，不参与任何计算判定。

【统计口径】年化 = (末值/首值)^(252/交易日数) - 1（与认证报告 9.43%/7.75%
口径一致，已复核）；回撤 = 1 - 净值/前高；Calmar = 年化/|最大回撤|。

【回撤时段定义与排序规则（核心，跑前写死）】
- 水下曲线 w(t) = 1 - equity(t)/cummax(equity)。
- 一个"回撤时段" = 相邻两次创历史新高之间的水下区间（互斥完备，天然分段，
  不做任何额外交并/拆分）。
- 深度 = 区间内 w 的最大值；峰日 = 区间起点前的高点日；谷日 = w 最大日；
  下跌持续 = 峰→谷交易日数；修复时长 = 谷→下一次创历史新的交易日数，
  窗口末仍未新高记"未修复"（right-censored，如实呈现）。
- 深度 < 2% 的时段不参与排名（写死阈值，防噪声；不影响前五结果）。
- 【5 大最差时段排序】按深度降序取前 5；深度并列时以下跌持续更长者为先。

【腿贡献分解规则】
- 分账制恒等式：combo(t) - combo(峰) = 0.8*[b9(t)-b9(峰)] + 0.2*[lei(t)-lei(峰)]。
  在谷日 t* 取值即得各腿对该时段最大深度的绝对贡献与占比（数学恒等，
  非近似；拼接曲线已验证恒等式残差 < 1e-6）。
- 时段内腿自身表现：腿在峰→谷区间的涨跌幅；正收益 = 对冲腿，负 = 拖累腿。
- 整窗贡献占比：0.8*(b9末-b9首) 与 0.2*(lei末-lei首) 占 (combo末-combo首)。
- 日收益相关矩阵：整窗与各前五时段内的 Pearson（引用认证归档 -0.003 交叉
  核对；LEI 为周频 ffill 日频口径，相关系数为低估其真实联动，报告标注）。

【红线遵守】描述性解剖：不提改进建议、不回测变体、不回答该不该继续用、
不使用买卖指令类词汇。所有数字可溯源到上述归档 raw 文件。

【随机性声明】本脚本无任何随机成分（纯归档曲线算术 + 排序）；双跑
（PYTHONHASHSEED=0/42）仅为流程纪律，两跑输出哈希必然一致，仍如实登记。
================================================================================
"""

import json
import hashlib
import numpy as np
import pandas as pd

BASE = "/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/"
OUT = BASE + "agent_AR/"
TRADING_DAYS = 252.0
MIN_DEPTH = 0.02  # 跑前写死


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def annualized(eq, dates):
    n = len(eq) - 1
    return float((eq.iloc[-1] / eq.iloc[0]) ** (TRADING_DAYS / n) - 1.0)


def max_drawdown(eq):
    cm = eq.cummax()
    w = 1.0 - eq / cm
    i = int(w.idxmax())
    peak_i = int(eq.loc[:i].idxmax())
    return float(w.loc[i]), int(peak_i), int(i)


def underwater_episodes(df, col):
    """按跑前写死规则：相邻两次历史新高之间的水下区间为一个回撤时段。"""
    eq = df[col]
    dates = df["date"]
    is_ath = eq >= eq.cummax() - 1e-12
    eps = []
    n = len(df)
    i = 0
    ath_idx = np.where(is_ath.values)[0]
    # 时段 = 两个相邻 ATH 之间非 ATH 的区间
    for a, b in zip(ath_idx[:-1], ath_idx[1:]):
        if b - a <= 1:
            continue
        seg = eq.iloc[a + 1:b]  # 区间内严格低于前高
        if seg.empty:
            continue
        w = 1.0 - seg / eq.iloc[a]
        depth = float(w.max())
        if depth < MIN_DEPTH:
            continue
        trough_off = int(w.values.argmax())
        trough_i = a + 1 + trough_off
        # 修复：谷后下一次新高（即 b，若 b 是 ATH 且谷在 b 前）
        recovered = bool(is_ath.values[b])
        rec_days = int(b - trough_i) if recovered else None
        eps.append(dict(
            peak_i=int(a), trough_i=int(trough_i), end_i=int(b),
            peak_date=str(dates.iloc[a].date()), trough_date=str(dates.iloc[trough_i].date()),
            end_date=str(dates.iloc[b].date()),
            depth=depth, fall_days=int(trough_i - a), rec_days=rec_days,
            episode_days=int(b - a), recovered=recovered,
        ))
    # 窗末未修复时段（最后一段 ATH 之后仍水下）
    last_ath = int(ath_idx[-1])
    if last_ath < n - 1:
        seg = eq.iloc[last_ath + 1:]
        if not seg.empty:
            w = 1.0 - seg / eq.iloc[last_ath]
            depth = float(w.max())
            if depth >= MIN_DEPTH:
                trough_off = int(w.values.argmax())
                trough_i = last_ath + 1 + trough_off
                eps.append(dict(
                    peak_i=last_ath, trough_i=int(trough_i), end_i=n - 1,
                    peak_date=str(dates.iloc[last_ath].date()),
                    trough_date=str(dates.iloc[trough_i].date()),
                    end_date=str(dates.iloc[-1].date()),
                    depth=depth, fall_days=int(trough_i - last_ath),
                    rec_days=None, episode_days=int(n - 1 - last_ath),
                    recovered=False,
                ))
    return eps


def main():
    # ---------- 曲线装配（附拼接校验） ----------
    cc = pd.read_csv(BASE + "combined_cert/combined_curves.csv", parse_dates=["date"])
    ult = pd.read_csv(BASE + "ultimate/ultimate_curves.csv", parse_dates=["date"])
    cl = pd.read_csv(BASE + "cash_leg/cash_curves.csv", parse_dates=["date"])

    # 列名对齐：认证文件 combo_20 vs ultimate 文件 combo20（同一定义，已先验证）
    ult = ult.rename(columns={"combo20": "combo_20"})
    ov = cc.merge(ult, on="date", suffixes=("_c", "_u"))
    checks = {}
    for c in ["combo_20", "b9", "lei", "hold"]:
        a = ov[f"{c}_c"].values
        b = ov[f"{c}_u"].values
        d = float(np.max(np.abs(a - b)))
        checks[c] = d
        assert d < 1e-9, f"拼接校验失败 {c}: {d}"
    main_df = pd.concat([cc, ult[ult["date"] > cc["date"].max()]], ignore_index=True)
    main_df = main_df[["date", "hold", "b9", "lei", "combo_20"]].rename(
        columns={"combo_20": "combo"})

    cash18 = cl[["date", "combo_cash_const_1.8"]].dropna().rename(
        columns={"combo_cash_const_1.8": "combo_cash18"})
    b9long = cl[["date", "b9_cash0"]].dropna().rename(columns={"b9_cash0": "b9_long"})

    bd = pd.DataFrame(json.load(open(BASE + "lei/a_share_breadth_33y_snapshot.json")))
    bd["date"] = pd.to_datetime(bd["date"])
    main_df = main_df.merge(bd[["date", "ma200_pct"]], on="date", how="left")

    # 恒等式校验（分账制）
    ident_err = float(np.max(np.abs(0.8 * main_df["b9"] + 0.2 * main_df["lei"] - main_df["combo"])))
    assert ident_err < 1e-5, ident_err

    # ---------- 全史统计 ----------
    stats = {}
    for col in ["combo", "b9", "lei", "hold"]:
        eq = main_df[col]
        dd, pi, ti = max_drawdown(eq)
        stats[col] = dict(
            start=str(main_df['date'].iloc[0].date()), end=str(main_df['date'].iloc[-1].date()),
            n_days=int(len(eq) - 1),
            ann=annualized(eq, main_df["date"]),
            maxdd=dd, maxdd_peak=str(main_df['date'].iloc[pi].date()),
            maxdd_trough=str(main_df['date'].iloc[ti].date()),
            calmar=annualized(eq, main_df["date"]) / dd,
            end_value=float(eq.iloc[-1]),
        )

    # 现金增强参考
    eq = cash18["combo_cash18"]
    dd, pi, ti = max_drawdown(eq.reset_index(drop=True))
    stats["combo_cash18"] = dict(
        start=str(cash18['date'].iloc[0].date()), end=str(cash18['date'].iloc[-1].date()),
        ann=annualized(eq, cash18["date"]), maxdd=dd,
        maxdd_peak=str(cash18['date'].iloc[pi].date()), maxdd_trough=str(cash18['date'].iloc[ti].date()),
        end_value=float(eq.iloc[-1]))

    # B9 长窗
    eq = b9long["b9_long"].reset_index(drop=True)
    dd, pi, ti = max_drawdown(eq)
    stats["b9_long_2015"] = dict(
        start=str(b9long['date'].iloc[0].date()), end=str(b9long['date'].iloc[-1].date()),
        ann=annualized(eq, b9long["date"]), maxdd=dd,
        maxdd_peak=str(b9long['date'].iloc[pi].date()), maxdd_trough=str(b9long['date'].iloc[ti].date()),
        end_value=float(eq.iloc[-1]))

    # ---------- 回撤时段（跑前写死规则） ----------
    eps = underwater_episodes(main_df, "combo")
    eps.sort(key=lambda e: (-e["depth"], -e["fall_days"]))  # 深度降序，并列取持续更长
    top5 = eps[:5]

    # ---------- 时段解剖 ----------
    def anatomy(e):
        d = main_df
        pk, tr, en = e["peak_i"], e["trough_i"], e["end_i"]
        # 恒等式分解（谷日相对组合峰日）
        combo_loss = d["combo"].iloc[tr] - d["combo"].iloc[pk]
        b9_contrib = 0.8 * (d["b9"].iloc[tr] - d["b9"].iloc[pk])
        lei_contrib = 0.2 * (d["lei"].iloc[tr] - d["lei"].iloc[pk])
        leg_b9_ret = d["b9"].iloc[tr] / d["b9"].iloc[pk] - 1
        leg_lei_ret = d["lei"].iloc[tr] / d["lei"].iloc[pk] - 1
        # 腿自身在整段（峰→修复/窗末）的表现
        leg_b7full = d["b9"].iloc[en] / d["b9"].iloc[pk] - 1
        leg_lei_full = d["lei"].iloc[en] / d["lei"].iloc[pk] - 1
        hold_ret_tr = d["hold"].iloc[tr] / d["hold"].iloc[pk] - 1
        hold_ret_full = d["hold"].iloc[en] / d["hold"].iloc[pk] - 1
        # B200 宽度状态
        w_seg = d["ma200_pct"].iloc[pk:tr + 1]
        w_full = d["ma200_pct"].iloc[pk:en + 1]
        # 时段内日收益相关（周频 ffill 标注）
        r_b9 = d["b9"].iloc[pk:tr + 1].pct_change().dropna()
        r_lei = d["lei"].iloc[pk:tr + 1].pct_change().dropna()
        corr_seg = float(np.corrcoef(r_b9, r_lei[:len(r_b9)])[0, 1]) if len(r_b9) > 30 else None
        return dict(
            depth_pct=e["depth"] * 100, fall_days=e["fall_days"], rec_days=e["rec_days"],
            episode_days=e["episode_days"], recovered=e["recovered"],
            peak_date=e["peak_date"], trough_date=e["trough_date"], end_date=e["end_date"],
            combo_loss_at_trough=float(combo_loss),
            b9_contrib=float(b9_contrib), lei_contrib=float(lei_contrib),
            b9_contrib_share=float(b9_contrib / combo_loss), lei_contrib_share=float(lei_contrib / combo_loss),
            b9_ret_peak_to_trough=float(leg_b9_ret), lei_ret_peak_to_trough=float(leg_lei_ret),
            b9_ret_peak_to_end=float(leg_b7full), lei_ret_peak_to_end=float(leg_lei_full),
            hold_ret_peak_to_trough=float(hold_ret_tr), hold_ret_peak_to_end=float(hold_ret_full),
            b200_mean_pt=float(np.nanmean(w_seg)), b200_min_pt=float(np.nanmin(w_seg)),
            b200_max_pt=float(np.nanmax(w_seg)), b200_at_trough=float(d["ma200_pct"].iloc[tr]),
            b200_mean_full=float(np.nanmean(w_full)),
            corr_b9_lei_seg=corr_seg,
        )

    top5_anat = [dict(rank=i + 1, **anatomy(e), ep_index=eps.index(e)) for i, e in enumerate(top5)]

    # ---------- 修复时长分布（所有 >=2% 时段） ----------
    rec = [e["rec_days"] for e in eps if e["rec_days"] is not None]
    unrec = [e for e in eps if not e["recovered"]]
    rec_dist = dict(n_episodes=len(eps), n_recovered=len(rec), n_unrecovered=len(unrec),
                    rec_median_d=float(np.median(rec)), rec_mean_d=float(np.mean(rec)),
                    rec_max_d=int(np.max(rec)),
                    underwater_frac=float(np.mean(1 - main_df["combo"] / main_df["combo"].cummax())))

    # ---------- 整窗腿贡献与相关 ----------
    b9_gain = 0.8 * (main_df["b9"].iloc[-1] - 1)
    lei_gain = 0.2 * (main_df["lei"].iloc[-1] - 1)
    total_gain = main_df["combo"].iloc[-1] - 1
    r = main_df[["b9", "lei", "combo", "hold"]].pct_change().dropna()
    corr_full = r.corr().round(4).to_dict()

    # 年度表（复算，供报告交叉核对）。口径：年收益 = 年末值/上年末值 - 1，
    # 首年（2017）基期 = 窗口起点 1.0。已验证该口径与认证 raw 的 yearly 表
    # 逐位一致（combo_20 2018=-22.0 / b9=-27.1 等），故沿用之。
    yrs = main_df.copy()
    yrs["year"] = yrs["date"].dt.year
    ylist = sorted(yrs["year"].unique())
    yearly = {}
    for c in ["combo", "b9", "lei", "hold"]:
        out = {}
        for i, y in enumerate(ylist):
            g = yrs[yrs["year"] == y]
            if len(g) <= 20:
                continue
            base = 1.0 if i == 0 else yrs[yrs["year"] == ylist[i - 1]][c].iloc[-1]
            out[int(y)] = round(float(g[c].iloc[-1] / base - 1) * 100, 1)
        yearly[c] = out

    # ---------- B9 长窗上下文（2015 段，不同口径，仅上下文） ----------
    pre2017 = b9long[b9long["date"] < main_df["date"].iloc[0]]
    seg = pre2017["b9_long"].reset_index(drop=True)
    pre_stats = None
    if len(seg) > 30:
        cm = seg.cummax()
        w = 1 - seg / cm
        i = int(w.idxmax())
        pk = int(seg.loc[:i].idxmax())
        dd, pi, ti = max_drawdown(seg)
        pre_stats = dict(
            window=f"{pre2017['date'].iloc[0].date()}~{pre2017['date'].iloc[-1].date()}",
            maxdd=dd, maxdd_peak=str(pre2017['date'].iloc[pi].date()),
            maxdd_trough=str(pre2017['date'].iloc[ti].date()),
            seg_ret=float(seg.iloc[-1] / seg.iloc[0] - 1),
            worst_dd_window=f"{pre2017['date'].iloc[pi].date()}~{pre2017['date'].iloc[ti].date()}",
        )
    # B9 长窗全史最大回撤与 2015 谷底日期（长窗自身口径）
    eqL = b9long["b9_long"].reset_index(drop=True)
    ddL, piL, tiL = max_drawdown(eqL)
    b9long_full = dict(maxdd=ddL, peak=str(b9long['date'].iloc[piL].date()),
                       trough=str(b9long['date'].iloc[tiL].date()))

    # ---------- 输出 ----------
    results = dict(
        experiment="AR system fragility xray",
        date="2026-09-03",
        protocol="见 scripts/agent_AR/ar_fragility_anatomy.py docstring（跑前写死）",
        curve_sources=dict(
            main="raw/combined_cert/combined_curves.csv + raw/ultimate/ultimate_curves.csv (bitwise-identical overlap)",
            cash18="raw/cash_leg/cash_curves.csv combo_cash_const_1.8",
            b9_long="raw/cash_leg/cash_curves.csv b9_cash0 (2015-06-16 起, 口径差≈2bp/年)",
            breadth="raw/lei/a_share_breadth_33y_snapshot.json ma200_pct"),
        splice_checks=checks,
        identity_check_max_err=ident_err,
        stats=stats,
        episodes_all=[{k: v for k, v in e.items()} for e in eps],
        top5=top5_anat,
        recovery_dist=rec_dist,
        whole_window_contrib=dict(b9_gain=float(b9_gain), lei_gain=float(lei_gain),
                                  total_gain=float(total_gain),
                                  b9_share=float(b9_gain / total_gain), lei_share=float(lei_gain / total_gain)),
        corr_full=corr_full,
        yearly_partial=yearly,
        b9_pre2017_context=pre_stats,
        b9_long_full=b9long_full,
        randomness="无随机成分（纯归档曲线算术）",
    )
    with open(OUT + "ar_fragility_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=1, default=float)

    pd.DataFrame(eps).to_csv(OUT + "ar_fragility_episodes_all.csv", index=False)
    pd.DataFrame(top5_anat).to_csv(OUT + "ar_fragility_top5.csv", index=False)

    print(json.dumps(dict(
        stats=stats, top5=[{k: t[k] for k in
                            ["rank", "peak_date", "trough_date", "end_date", "depth_pct",
                             "fall_days", "rec_days", "b9_contrib_share", "lei_contrib_share",
                             "b9_ret_peak_to_trough", "lei_ret_peak_to_trough",
                             "hold_ret_peak_to_trough", "b200_mean_pt", "b200_at_trough",
                             "corr_b9_lei_seg"]}
                           for t in top5_anat],
        rec_dist=rec_dist, whole_window_contrib=results["whole_window_contrib"],
        corr_full=corr_full, b9_pre2017=pre_stats, b9long_full=b9long_full,
        n_episodes=len(eps)),
        ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
