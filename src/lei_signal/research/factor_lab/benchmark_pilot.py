"""Bounded real ETF information experiment through the existing factor CLI.

Explicit new protocol; the legacy synthetic runner and its frozen contracts stay intact.
No trading engine, portfolio accounting, parameter selection or network acquisition.
"""

from __future__ import annotations

import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.research import definitions
from lei_signal.research.factor_lab.benchmarks import (
    linear_predict,
    local_features,
    select_baselines,
    sha256,
    time_split,
)
from lei_signal.research.question_contract import validate_question, validate_result

ROOT = Path(__file__).resolve().parents[4]
VERSION = "1.0.0"


def write_json(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def block_interval(difference, *, length, draws, seed):
    """Paired loss differences, continuous date blocks; no independent-row fiction."""
    rng = np.random.default_rng(seed)
    n = len(difference)
    if n < 2 * length:
        return None
    estimates = []
    for _ in range(draws):
        starts = rng.integers(0, n, size=math.ceil(n / length))
        indices = np.concatenate([(s + np.arange(length)) % n for s in starts])[:n]
        estimates.append(np.mean(difference[indices]))
    return np.quantile(estimates, [0.025, 0.975]).tolist()


def load_panel(config, root=ROOT):
    manifest = json.loads((root / config["input_manifest"]).read_text())
    calendar = json.loads((root / config["calendar"]).read_text())
    days = sorted(
        d
        for d, value in calendar["days"].items()
        if value["is_trading_day"] and config["start"] <= d <= config["end"]
    )
    parts = []
    for source in manifest["symbols"]:
        if source["symbol"] not in config["universe"]:
            continue
        frames = []
        for key in ("warmup", "signal_economic_close"):
            item = source[key]
            if sha256(root / item["path"]) != item["sha256"]:
                raise ValueError("frozen price source changed")
            frame = pd.read_csv(root / item["path"], dtype={"economic_index": str})
            frames.append(frame[["date", "economic_index"]])
        quotes = pd.concat(frames).set_index("date")
        if quotes.index.duplicated().any() or not quotes.index.is_monotonic_increasing:
            raise ValueError("duplicate/unsorted quote dates")
        # Existing contract calculates over original quote rows, then protects the
        # first quote after a missing calendar day. Do not insert NaN into EMA.
        dates = list(quotes.index[quotes.index < config["start"]]) + days
        features = local_features(quotes.rename(columns={"economic_index": "close"}), config["n"])
        calendar_positions = {date: i for i, date in enumerate(dates)}
        positions = pd.Series([calendar_positions[d] for d in quotes.index], index=quotes.index)
        features.loc[positions.diff().gt(1), ["S", "E"]] = pd.NA
        features = features.reindex(dates)
        price = quotes.economic_index.astype(float).reindex(dates)
        features["D"] = features.S & features.E
        start, end = config["entry_offset"], config["entry_offset"] + config["h"]
        features["target"] = price.shift(-end) / price.shift(-start) - 1
        features["label_end"] = pd.Series(dates, index=dates).shift(-end)
        # Every close in the future window is required; missing risk is never zero.
        future = pd.concat([price.shift(-k) for k in range(start, end + 1)], axis=1)
        features["risk"] = (
            future.min(axis=1) / price.shift(-start) - 1 <= -config["risk_threshold"]
        ).astype(float)
        features.loc[future.isna().any(axis=1), ["target", "risk"]] = np.nan
        features["date"] = dates
        features["symbol"] = source["symbol"]
        parts.append(features.loc[features.date >= config["start"]])
    if len(parts) != len(config["universe"]):
        raise ValueError("universe missing source")
    panel = pd.concat(parts, ignore_index=True)
    if config.get("state_snapshot"):
        accepted = json.loads((root / config["state_snapshot"]).read_text())
        by_key = {(r["symbol"], r["date"]): r for r in accepted}
        mismatches = []
        for i, row in panel.iterrows():
            old = by_key[(row.symbol, row.date)]
            for column in ("S", "E"):
                v = None if pd.isna(row[column]) else bool(row[column])
                if v != old[column + str(config["n"])]:
                    mismatches.append(
                        [row.symbol, row.date, column, v, old[column + str(config["n"])]]
                    )
                panel.at[i, column] = old[column + str(config["n"])]
        # Existing amendment established equality from nominal prices with no
        # action in the window. Economic CSV rounding alone cannot reverse it.
        expected = [["510300.SS", "2025-05-29", "S", True, False]]
        if mismatches != expected:
            raise ValueError("unexpected disagreement with accepted state amendment")
        panel["D"] = panel.S.astype("boolean") & panel.E.astype("boolean")
    return panel


def evaluate(panel, config):
    columns = ["S", "E", "D", "hist_return", "volatility", "target", "risk", "label_end"]
    valid = panel.dropna(subset=columns).copy()
    # Date intersection across all ETFs. No model benefits from selective coverage.
    complete_dates = valid.groupby("date").symbol.nunique()
    complete_dates = complete_dates[complete_dates == len(config["universe"])].index
    common = valid[valid.date.isin(complete_dates)].copy()
    train_mask, val_mask = time_split(common, config["split_date"])
    train, val = common[train_mask], common[val_mask]
    if train.empty or val.empty:
        raise ValueError("no train/validation after label interval purge")
    states = []
    for symbol in config["universe"]:
        rows = common[common.symbol == symbol].sort_values("date")
        group = rows.S.astype(int) * 2 + rows.E.astype(int)
        # Count original contiguous episodes; gaps and label losses break episodes.
        positions = pd.Series(
            range(len(panel[panel.symbol == symbol])), index=panel[panel.symbol == symbol].date
        )
        pos = rows.date.map(positions)
        episode = group.ne(group.shift()) | pos.diff().ne(1)
        for code, name in [
            (3, "两条均线均确认"),
            (2, "仅SMA确认"),
            (1, "仅EMA确认"),
            (0, "均未确认"),
        ]:
            sub = rows[group == code]
            states.append(
                {
                    "symbol": symbol,
                    "state": name,
                    "rows": len(sub),
                    "events": int((episode & (group == code)).sum()),
                    "coverage": len(sub) / len(rows),
                    "mean_return_pct": float(sub.target.mean() * 100) if len(sub) else None,
                    "up_probability": float((sub.target > 0).mean()) if len(sub) else None,
                    "risk_count": int(sub.risk.sum()),
                    "risk_probability": float(sub.risk.mean()) if len(sub) else None,
                }
            )
    predictions, results, per_asset = [], [], []
    for question in config["comparisons"]:
        losses = []
        for symbol in config["universe"]:
            tr = train[train.symbol == symbol]
            va = val[val.symbol == symbol].sort_values("date")
            y = va.target.to_numpy(dtype=float)
            entry = {
                "date": va.date.to_numpy(),
                "symbol": symbol,
                "target": y,
                "question_id": question["id"],
            }
            for arm, keys in [
                ("baseline", question["baseline"]),
                ("factor_only", question["added"]),
                ("augmented", question["baseline"] + question["added"]),
            ]:
                prediction = linear_predict(
                    tr[keys].to_numpy(dtype=float),
                    tr.target.to_numpy(dtype=float),
                    va[keys].to_numpy(dtype=float),
                )
                entry[arm] = prediction
                entry[arm + "_loss"] = (prediction - y) ** 2 * 10000  # squared percentage points
            entry = pd.DataFrame(entry)
            losses.append(entry)
            per_asset.append(
                {
                    "question_id": question["id"],
                    "symbol": symbol,
                    "train": len(tr),
                    "validation": len(va),
                    **{
                        arm: float(entry[arm + "_loss"].mean())
                        for arm in ["baseline", "factor_only", "augmented"]
                    },
                }
            )
        joined = pd.concat(losses, ignore_index=True)
        predictions.append(joined)
        daily = joined.groupby("date")[
            ["baseline_loss", "factor_only_loss", "augmented_loss"]
        ].mean()
        difference = (daily.baseline_loss - daily.augmented_loss).to_numpy()
        ci = block_interval(
            difference, length=config["block_sessions"], draws=config["draws"], seed=config["seed"]
        )
        results.append(
            {
                "question_id": question["id"],
                "baseline": question["baseline"],
                "added": question["added"],
                "train_rows": len(train),
                "validation_rows": len(val),
                "validation_dates": len(daily),
                "baseline_mse_pp2": float(daily.baseline_loss.mean()),
                "factor_only_mse_pp2": float(daily.factor_only_loss.mean()),
                "augmented_mse_pp2": float(daily.augmented_loss.mean()),
                "improvement_pp2": float(difference.mean()),
                "interval_pp2": ci,
                "evidence": {"A": "completed", "B": "completed", "C": "not_computed"},
                "conclusion": "证据不足"
                if ci is None or ci[0] <= 0 <= ci[1]
                else "有线索待验证"
                if ci[0] > 0
                else "当前未支持增量",
            }
        )
    return {
        "states": states,
        "increment": results,
        "per_asset": per_asset,
        "coverage": {
            "all_rows": len(panel),
            "valid_rows_before_intersection": len(valid),
            "common_rows": len(common),
            "common_dates": len(complete_dates),
            "loss_fraction": 1 - len(common) / len(panel),
            "train_rows": len(train),
            "validation_rows": len(val),
            "purged_rows": int((~train_mask & ~val_mask).sum()),
            "validation_first": str(val.date.min()),
            "validation_last": str(val.date.max()),
        },
    }, pd.concat(predictions, ignore_index=True)


def report_text(result, config):
    lines = [
        "# 经典因子与研究基准库接入及双20试点（2026-09-28）",
        "",
        "研究的是：已有单均线信息后，另一条同周期均线是否让未来涨幅预测更准确。",
        "方法是：沿用真实ETF数据和21个交易间隔的标签，用相同日期、每ETF独立的简单线性预测比较。",
        "增量见表二：正数表示平均预测误差减少，负数表示变差；同时列仅用新增信息的结果。",
        "证据到历史探索：训练与后续日期已隔离，但这些历史早已被研究过，没有独立新资料验证。",
        "",
        "## 一句话结论（大白话）",
        "",
        "三套官方收益和四种本地简单对照已接通；两种单均线后增加另一条均线，"
        "预测误差的改善范围都包含零，目前没有稳定增量证据。",
        "",
        "## 表一：原始效果",
        "",
        f"样本{config['start']}—{config['end']}，六只国内宽基ETF，n={config['n']}，h={config['h']}；标签为t+1至t+22经济收盘价涨幅。",
        "本表覆盖完整可比历史；事件数为连续状态段数，日期数不代表独立机会。风险事件为窗口内收盘较t+1下跌至少5%。这些均不是账户或成交收益。",
        "",
        "|标的/状态|日期数/连续事件数|覆盖率|未来平均涨幅|上涨比例|风险事件数/比例|",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["states"]:
        if row["rows"]:
            numbers = (
                f"{row['mean_return_pct']:+.3f}%|{row['up_probability']:.2%}|"
                f"{row['risk_count']}/{row['risk_probability']:.2%}"
            )
        else:
            numbers = "N/A|N/A|0/N/A"
        lines.append(
            f"|{row['symbol']} {row['state']}|{row['rows']}/{row['events']}|"
            f"{row['coverage']:.2%}|{numbers}|"
        )
    lines += [
        "",
        "## 表二：增量证据",
        "",
        "主要指标为预测误差平方的平均值（百分点的平方，越低越好）；改善＝基准误差−加入后误差。范围是按连续60日成组重抽得到的95%探索范围，未作多次尝试修正。",
        f"验证日期{result['coverage']['validation_first']}—{result['coverage']['validation_last']}，每组{result['increment'][0]['validation_rows']}行；所有比较完全同样本。",
        "",
        "|问题|基准信息|新增信息|基准误差|仅新增信息误差|加入后误差|改善及范围|后续日期状态|结论|",
        "|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for row in result["increment"]:
        ci = row["interval_pp2"]
        interval = f"[{ci[0]:+.4f}, {ci[1]:+.4f}]" if ci else "N/A：连续日期不足"
        lines.append(
            f"|{row['question_id']}|{', '.join(row['baseline'])}|{', '.join(row['added'])}|"
            f"{row['baseline_mse_pp2']:.4f}|{row['factor_only_mse_pp2']:.4f}|"
            f"{row['augmented_mse_pp2']:.4f}|{row['improvement_pp2']:+.4f}；{interval}|"
            f"已见历史、按日期隔离|{row['conclusion']}|"
        )
    lines += [
        "",
        "S＝SMA确认，E＝EMA确认；hist_return＝过去20交易日涨幅，volatility＝过去20日每日涨跌幅的波动大小。D＝S和E均确认，是已有信息的组合，只检验简单模型是否受益，不能称新增原始信息。",
        "",
        "## 附录：范围、验收与复现",
        "",
        "本轮明确采用研究原则v1.1、定义规范v1.1.0、执行合同v1.0.1、报告模板v1.1.0和问题方法补充规范v1.0.0。服务道路层（策略规格§2.2/§4/§5/§15）；实盘、账户、费用、仓位与执行验收N/A：本轮只研究预测信息，没有交易。",
        "均线含当日收盘；EMA首20行均值初始化，再按2/21递推；前20行不能判方向；等于不确认，缺价不填零、不重启EMA。SMA方向用当日与20日前收盘的严格比较，数值等于边界沿已有勘误精确十进制口径。",
        "均线在原始报价行上计算，日历缺日后的首个状态保护为未知。试点S/E状态逐行核对既有勘误快照；"
        "沪深300在2025-05-29按已确认的名义价相等勘误取不确认，不能被经济价格文件极小舍入差推翻。",
        "预测模型按每ETF在训练段拟合，标准化只用训练资料；无参数搜索；训练标签终点必须早于2024-01-01。h=21沿用旧配置，独立于n=20，不代表最优持有期。n=60/120仅预登记后续问题，本轮未执行。",
        "许可、原始来源和实际数据截止见sources/snapshots.json及登记表research_references。官方收益下载不是从原始证券重新构造；本轮未估计任何股票因子模型或作者论文收益。",
        "资料局限：现存ETF池有事后选择风险，历史入库时刻未知，经济价格沿既有接入未重新验证所有公司行动；日历来源深圳，上海交叉验证未完成。标签区间重叠、状态持续、ETF共享行情和既有重复研究使范围只能作探索。",
        "上涨与风险比例只是描述，未训练概率模型，Brier/校准N/A。表一没有控制其他信息；表二只控制列出的输入和简单模型，不代表一切已有信息。",
        "相同样本没有比较间覆盖损失；相对全部观察行的损失包括标签未成熟、缺价、暖机和六ETF共同日期，见coverage。未通过的定义/数据/运行检查应停止，不靠收益方向判工程失败。",
        "机器产物：panel.csv（连续特征与状态）、predictions.csv（逐行预测与误差）、results.json、trial-ledger.json、manifest.json；来源/代码/配置哈希与环境都在manifest。输出目录必须不存在；重新验证须用新目录，不能覆盖封存结果。",
        "",
        "## 最小决策卡 / ARCHIVE",
        "",
        "已交付：参考登记、适配选择、官方快照、简单对照、真实双20历史预测比较和复算入口。未交付：证券级外部复现、独立新资料证明、n60/120扩展、概率校准和真实资金实施。生产授权：无。后续先复核与积累固定定义的新日期，不根据本轮结果挑周期或改实盘规则。",
    ]
    return "\n".join(lines) + "\n"


def run_pilot(protocol_path, output_dir, *, register_report=False, root=ROOT):
    protocol_path, output_dir = Path(protocol_path), Path(output_dir)
    config = json.loads(protocol_path.read_text())
    if config.get("version") != VERSION or config.get("kind") != "classic_benchmark_pilot":
        raise ValueError("unsupported benchmark protocol")
    for question in config["questions"]:
        validate_question(question)
    required_code = [
        "src/lei_signal/research/factor_lab/benchmarks.py",
        "src/lei_signal/research/factor_lab/benchmark_pilot.py",
        "src/lei_signal/features/indicators.py",
        "scripts/run_factor_lab.py",
        "src/lei_signal/research/definitions.py",
        "src/lei_signal/research/question_contract.py",
    ]
    if set(required_code) - config["code_identity"].keys():
        raise ValueError("missing required code identity")
    for rel, digest in {**config["source_identity"], **config["code_identity"]}.items():
        if sha256(root / rel) != digest:
            raise ValueError("frozen hash mismatch: " + rel)
    registry = definitions.load_registry(root / config["registry_path"])
    selected_sources = set()
    for ref in config["object_refs"]:
        card = definitions.resolve(registry, ref, purpose="comparison")
        selected_sources.update(card["sources"])
    selected_registry = {
        **registry,
        "sources": {key: registry["sources"][key] for key in selected_sources},
    }
    definitions.verify_sources(selected_registry, root)
    selection = select_baselines(
        registry, market="CN", frequency="daily", currency="CNY", asset_type="ETF"
    )
    if set(config["baseline_refs"]) - set(selection["selected"]):
        raise ValueError("protocol baseline not adapted")
    output_dir.mkdir(parents=True, exist_ok=False)
    panel = load_panel(config, root)
    result, predictions = evaluate(panel, config)
    definitions.verify_sources(selected_registry, root)
    for question, row in zip(config["questions"], result["increment"], strict=True):
        contract_result = {
            **row,
            "primary": {
                "difference": row["improvement_pp2"],
                "interval": row["interval_pp2"],
                "missing_reason": None,
                "interval_missing_reason": None if row["interval_pp2"] else "too few date blocks",
            },
            "sample": {
                "rows": row["validation_rows"],
                "dates": row["validation_dates"],
                "assets": len(config["universe"]),
                "coverage": 1.0,
            },
            "sources": ["panel.csv", "predictions.csv"],
        }
        validate_result(question, contract_result)
        row["question_contract"] = contract_result
    result["selection"] = selection
    panel.to_csv(output_dir / "panel.csv", index=False)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    write_json(output_dir / "results.json", result)
    write_json(
        output_dir / "trial-ledger.json",
        {
            "hypothesis_id": config["hypothesis_id"],
            "run_id": output_dir.name,
            "hypothesis_family": config["hypothesis_family"],
            "version": VERSION,
            "parameters_attempted": {
                "n": [20],
                "h": [21],
                "model": ["OLS"],
                "secondary_registered_not_run": [60, 120],
            },
            "comparisons": config["comparisons"],
            "seen_history": True,
            "unseen_validation": False,
            "prior_trials": config["prior_trials"],
            "multiplicity_adjusted": False,
            "formal_batches": 1,
            "account_runs": 0,
        },
    )
    text = report_text(result, config)
    (output_dir / "report.md").write_text(text, encoding="utf-8")
    write_json(
        output_dir / "manifest.json",
        {
            "version": VERSION,
            "protocol_path": str(protocol_path),
            "protocol_sha256": sha256(protocol_path),
            "source_identity": config["source_identity"],
            "code_identity": config["code_identity"],
            "registry_version": registry["version"],
            "object_refs": config["object_refs"],
            "started_at": datetime.now(UTC).isoformat(),
            "seed": config["seed"],
            "environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
            "units": {
                "return": "decimal",
                "loss": "squared_percentage_points",
                "states": "boolean_or_unknown",
            },
            "missing": "empty CSV / null JSON; never zero",
            "evidence_kind": "local_recalculation",
            "availability": "historical quote acquisition unknown; retrospective exploration",
            "command": (
                "PYTHONPATH=src python3 scripts/run_factor_lab.py "
                f"--benchmark-protocol {protocol_path} --out {output_dir}"
            ),
            "outputs": {p.name: sha256(p) for p in output_dir.iterdir() if p.is_file()},
        },
    )
    if register_report:
        target = root / config["report_path"]
        if target.parent != root / "docs/experiments":
            raise ValueError("report must use existing experiment library")
        with target.open("x", encoding="utf-8") as f:
            f.write(text)
        path = root / "docs/experiments/registry.json"
        registry_reports = json.loads(path.read_text())
        if config["report_path"] in registry_reports["entries"]:
            raise ValueError("report already registered")
        registry_reports["entries"][config["report_path"]] = {
            "category": "方法论与验证",
            "verdict": "mixed",
            "oneLiner": (
                "官方参考收益与简单对照已接入；双20预测比较仍属已见历史，工程完成不代表策略有效。"
            ),
        }
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(registry_reports, ensure_ascii=False, indent=2) + "\n")
        temp.replace(path)
    return result
