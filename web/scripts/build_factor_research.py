#!/usr/bin/env python3
"""Build a read-only research display snapshot from pinned, existing evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research import definitions, factor_access  # noqa: E402

BINDINGS = Path("web/src/pages/factor-research/display-bindings.json")
OUTPUT = Path("web/src/pages/factor-research/catalog.generated.json")
INCLUDED_TYPES = {"feature", "state_signal", "risk_metric", "factor_return"}
STAGES = {
    "unresearched",
    "calculation_only",
    "historical",
    "in_progress",
    "insufficient",
    "unbound",
}
RESULTS = {"not_evaluated", "insufficient", "no_help", "conditional", "supported", "unknown"}
USE_LABELS = {
    "description": "描述已有读数",
    "ranking": "比较相对位置",
    "research_signal": "观察研究条件",
    "attribution": "解释收益或风险",
    "comparison": "作为对照",
    "diagnostic": "核对计算或资料",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(root: Path, path: str, expected: str | None = None, role: str | None = None) -> dict:
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
    ):
        raise ValueError(f"unsafe source path: {path!r}")
    base = root.resolve()
    real = (base / path).resolve(strict=True)
    if not real.is_file() or not real.is_relative_to(base):
        raise ValueError(f"source outside repository or not a file: {path}")
    digest = sha(real)
    if expected is not None and digest != expected:
        raise ValueError(f"source fingerprint drift: {path}")
    record = {"path": path, "sha256": digest}
    if role is not None:
        record["role"] = role
    return record


def pinned(root: Path, spec: dict, role: str | None = None) -> dict:
    if (
        not isinstance(spec, dict)
        or not isinstance(spec.get("sha256"), str)
        or len(spec["sha256"]) != 64
    ):
        raise ValueError("pinned source requires path and sha256")
    return source(root, spec["path"], spec["sha256"], role)


def read_json(root: Path, spec: dict) -> dict:
    pinned(root, spec)
    data = json.loads((root / spec["path"]).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {spec['path']}")
    return data


def finite(value, where: str):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"non-finite or invalid number: {where}")
    return value


def text_part(value) -> str:
    if value is None:
        return "未记录"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def category(ref: str, card: dict) -> str:
    id_ = card["id"]
    if id_.startswith("breadth."):
        return "宽度"
    if id_.startswith("risk.") or "rv" in id_ or "volatility" in id_:
        return "风险"
    if "momentum" in id_ or "rank" in id_:
        return "相对强弱"
    if "pullback" in id_ or "distance" in id_ or "bias" in id_:
        return "回调位置"
    if "volume" in id_:
        return "量能"
    if id_.startswith(("trend.", "etf.trend.")):
        return "趋势"
    return "其他研究读数"


def asset_classes(card: dict) -> list[str]:
    words = " ".join(
        (text_part(card.get("scope")), text_part(card.get("universe", {}).get("version")))
    )
    out = []
    if "ETF" in words or "etf" in words.lower():
        out.append("ETF")
    if "股票" in words or "个股" in words or "全A" in words or "成分股" in words:
        out.append("个股")
    return out or ["其他"]


def purpose_for(card: dict) -> str:
    """Explain the registered formula in plain Chinese; never assess effectiveness."""
    name = card["id"]
    if name == "mixed.momentum.raw":
        return "比较过去约一年、扣除最近一个月的涨幅，观察强弱是否延续。"
    if name == "mixed.momentum.rank":
        return "把合格产品按普通动量从强到弱完整排序，便于检查相对位置。"
    if name == "mixed.rv20":
        return "量出最近20次有效报价的日涨跌波动幅度，描述价格是否颠簸。"
    if name == "mixed.rv_percentile":
        return "把当前波动放回自身历史中比较，观察它处于偏高还是偏低位置。"
    if name == "mixed.volatility_allowed":
        return "记录历史波动位置是否低于既定筛选水平；这是研究条件，不是买卖许可。"
    if name.startswith("breadth."):
        if name == "breadth.three_tier":
            return "把宽度水平对应到三档研究目标，记录规则会如何改变投入比例。"
        if name.startswith("breadth.production."):
            return "记录既有生产宽度口径下，各周期有资料的股票中多少站上各自均线。"
        if name.startswith("breadth.daily_all_a."):
            return "记录日常全A宽度口径下，各周期有资料的股票中多少站上各自均线。"
        pool = (
            "全A股票"
            if ".all_a." in name
            else "沪深300历史成分股"
            if ".csi300." in name
            else "创业板历史成分股"
        )
        length = "50" if "50" in name else "200"
        if ".delta" in name:
            return f"比较{pool}站上{length}日均线的比例与20个观察值前的变化。"
        if ".legacy_percent" in name:
            return f"按冻结旧百分数口径，描述{pool}中站上{length}日均线的占比。"
        return f"在共同合格股票分母内，计算{pool}有多少站上各自{length}日均线。"
    if name.startswith("risk."):
        if name == "risk.product_account_weight":
            return "量出某产品市值占完整账户的比例，观察是否过度集中。"
        if name == "risk.direction_account_weight":
            return "合并同一经济方向的持仓，量出它占完整账户的比例。"
        if name == "risk.product_invested_weight":
            return "量出某产品占已投入资产的比例，不含账户中的现金。"
        return "量出某经济方向对账户净盈亏的占比，说明盈亏集中在哪里。"
    if name.startswith("etf.trend."):
        length = "200" if "200" in name else "50"
        if ".sma" in name:
            return f"计算ETF连续价格最近{length}次有效报价的平均线，作为趋势位置参照。"
        return f"记录ETF连续价格是否站上{length}日均线；这是状态描述。"
    if name.startswith("trend."):
        if name == "trend.cost_basis_distance20":
            return "比较今天收盘价与20次有效报价前的价格，描述抵扣价距离。"
        if name == "trend.ma_cluster_width":
            return "量出六条均线最高与最低之间的相对距离，描述均线是否密集。"
        length = "200" if "200" in name else "50"
        if ".sma" in name:
            return f"计算最近{length}次有效报价的简单平均价，作为趋势位置参照。"
        if ".distance" in name:
            return f"量出当前价格离{length}日均线有多远，描述偏离程度。"
        if ".cross_up" in name:
            return f"记录本次价格是否由均线下方或线上穿到{length}日均线上方。"
        if ".recovered" in name:
            return "记录价格是否重新站回或等于200日均线。"
        return f"记录当前价格是否严格站上{length}日均线。"
    if name == "mixed.bias_ema120_pct":
        return "量出价格偏离120日指数均线的程度，描述位置是否远离长期道路。"
    if name == "mixed.pullback_ma_distance":
        return "在20、60、120日指数及简单均线中，找出价格离哪条线最近、相距多少。"
    if name == "mixed.swing_rr_distance":
        return "比较价格离已确认高点和低点的距离，仅描述当前位置与结构空间。"
    return "；".join(USE_LABELS[u] for u in card.get("uses", []) if u in USE_LABELS) or "用途未记录"


def item_from_card(
    root: Path, reference: str, card: dict, access: dict, registry_source: dict
) -> dict:
    lifecycle = card.get("lifecycle") or {}
    status = card.get("status") or {}
    stage = "unbound"
    result = "unknown"
    summary = "本页尚未绑定这张定义卡的真实市场效果材料；这不代表全仓没有研究。"
    item_sources = [registry_source]
    material_error = None
    display_name = card["name"]
    if reference in access.get("definitions", {}) or reference in access.get("bindings", {}):
        try:
            material = factor_access.read_materials(access, reference, root=root)
            item_sources.extend(material.get("sources_verified", []))
            if material.get("binding"):
                display_name = material.get("label") or display_name
                stage = "calculation_only" if material.get("evidence") else "unbound"
                result = "not_evaluated" if stage == "calculation_only" else "unknown"
                summaries = [e.get("summary", "") for e in material.get("evidence", [])]
                summary = "；".join(s for s in summaries if s) or summary
        except factor_access.AccessError as exc:
            material_error = str(exc)
            summary = "展示材料来源核验未通过，本对象材料暂不可用；正式定义卡仍可查看。"
    if material_error is not None:
        stage, result = "insufficient", "insufficient"
    return {
        "reference": reference,
        "id": card["id"],
        "version": card["version"],
        "name": display_name,
        "formal_name": card["name"],
        "object_type": card["type"],
        "category": category(reference, card),
        "purpose": purpose_for(card),
        "scope": text_part(card.get("scope")),
        "formula": text_part(card.get("definition", {}).get("formula")),
        "unit": text_part(card.get("definition", {}).get("unit")),
        "input": "；".join(
            filter(
                None,
                [
                    text_part(card.get("input", {}).get("fields")),
                    text_part(card.get("input", {}).get("price_basis")),
                ],
            )
        ),
        "time": "；".join(
            filter(
                None,
                [
                    text_part(card.get("time", {}).get("observation_time")),
                    text_part(card.get("time", {}).get("available_at")),
                ],
            )
        ),
        "asset_classes": asset_classes(card),
        "calculation": {
            "status": lifecycle.get("state", "unknown"),
            "scope": lifecycle.get("verification_scope", "未记录逐卡验证范围"),
        },
        "research": {"stage": stage, "result": result, "summary": summary, "evidence_date": None},
        "limitations": [
            text_part(card.get("validation", {}).get("limitations")),
            text_part(status.get("data_qualification")),
        ]
        + ([material_error] if material_error else []),
        "next_steps": [],
        "experiment_ids": [],
        "sources": item_sources,
        "source_error": material_error,
    }


def metric(label, value, unit, meaning):
    return {"label": label, "value": finite(value, label), "unit": unit, "meaning": meaning}


def make_momentum(root: Path, binding: dict) -> dict:
    specs = binding["sources"]
    protocol, stats, independent, run = (
        read_json(root, specs[k]) for k in ("protocol", "summary", "independent", "run")
    )
    if stats != independent:
        raise ValueError("momentum formal and independent summary disagree")
    if binding["reference"] not in protocol.get("definitions", []):
        raise ValueError("experiment reference absent from frozen protocol")
    if run.get("status") != "completed":
        raise ValueError("experiment run is not completed")
    passed = stats["predeclared_screen"]["positive_clue_screen_passed"]
    if type(passed) is not bool:
        raise ValueError("missing predeclared boolean result")
    overall, anchor = stats["overall"], stats["fixed_nonoverlap_anchor"]
    years = stats["by_period"]
    rows = [
        {
            "period": key,
            "dates": finite(value["rank_ic_valid_dates"], key),
            "relation": finite(value["rank_ic_mean"], key),
            "difference": finite(value["high_minus_low_mean"], key),
        }
        for key, value in years.items()
    ]
    return {
        "id": binding["id"],
        "title": binding["title"],
        "kind": binding["kind"],
        "run_status": "completed",
        "review_status": binding["review_status"],
        "review_summary": binding["review_summary"],
        "conclusion": binding["summary"],
        "result": "conditional" if passed else "no_help",
        "baseline": "六只平均及固定低二；只比较后续表现，没有交易账户。",
        "costs": "未计算费用、成交或持仓。",
        "references": [binding["reference"]],
        "products": [{"code": code, "name": code} for code in protocol["symbols"]],
        "period": {"start": protocol["window"][0], "end": protocol["window"][1]},
        "data_cutoff": protocol["window"][1],
        "run_at": run["completed_at"],
        "reviewed_at": binding["reviewed_at"],
        "sample": [
            metric(
                "有效排名日期",
                overall["rank_ic_valid_dates"],
                "日",
                "六只齐全且后续目标可用的共同交易日",
            ),
            metric(
                "固定不重叠日期", anchor["rank_ic_valid_dates"], "日", "预定每21个共同交易日取一次"
            ),
        ],
        "metrics": [
            metric(
                "全期平均排名关系",
                overall["rank_ic_mean"],
                "ratio",
                "六只当期与后续表现名次关系，非胜率",
            ),
            metric(
                "高二减低二后续表现差",
                overall["high_minus_low_mean"],
                "fraction",
                "21日后续平均涨幅差，非账户利润",
            ),
            metric("不重叠日期排名关系", anchor["rank_ic_mean"], "ratio", "固定日期子集的平均关系"),
            metric(
                "不重叠日期高低差",
                anchor["high_minus_low_mean"],
                "fraction",
                "固定日期子集的后续平均涨幅差",
            ),
        ],
        "result_tables": [
            {
                "title": "按观察时期",
                "columns": [
                    {"key": "period", "label": "时期", "unit": ""},
                    {"key": "dates", "label": "有效日期", "unit": "日"},
                    {"key": "relation", "label": "平均排名关系", "unit": "ratio"},
                    {"key": "difference", "label": "高二减低二", "unit": "fraction"},
                ],
                "rows": rows,
                "note": "按观察期分组；这些不是年度投资收益。",
            }
        ],
        "limitations": binding["limitations"],
        "next_steps": binding["next_steps"],
        "sources": [pinned(root, spec, role) for role, spec in specs.items()],
        "report_registration": None,
    }


def make_dual_ma(root: Path, binding: dict) -> dict:
    specs = binding["sources"]
    protocol, stats = (read_json(root, specs[k]) for k in ("protocol", "summary"))
    registered = json.loads((root / "docs/experiments/registry.json").read_text())
    report_path = specs["report"]["path"]
    registration = registered.get("entries", {}).get(report_path)
    if not isinstance(registration, dict) or registration.get("verdict") != "mixed":
        raise ValueError("dual-MA report registration or verdict changed")
    if protocol.get("object_ref") != binding["reference"]:
        raise ValueError("dual-MA candidate reference differs from protocol")
    symbol = protocol["symbol"]
    values = stats["symbols"][symbol]
    true, false = values["true_group"], values["false_group"]
    years = values["by_year"]
    rows = [
        {
            "period": year,
            "true_n": finite(v["true"]["n"], year),
            "true_mean": finite(v["true"]["mean"], year),
            "false_n": finite(v["false"]["n"], year),
            "false_mean": finite(v["false"]["mean"], year),
        }
        for year, v in years.items()
    ]
    return {
        "id": binding["id"],
        "title": binding["title"],
        "kind": binding["kind"],
        "run_status": "completed",
        "review_status": binding["review_status"],
        "review_summary": binding["review_summary"],
        "conclusion": binding["summary"],
        "result": "conditional",
        "baseline": "同一510300历史中双均线状态未成立的观察。",
        "costs": "未计算交易费用或账户收益。",
        "references": [binding["reference"]],
        "products": [{"code": symbol, "name": symbol}],
        "period": {
            "start": protocol["evaluation_window"]["start"],
            "end": protocol["evaluation_window"]["end"],
        },
        "data_cutoff": None,
        "run_at": None,
        "reviewed_at": binding["reviewed_at"],
        "sample": [
            metric("成立组观察", true["n"], "次", "状态成立且后续目标可用"),
            metric("未成立组观察", false["n"], "次", "状态未成立且后续目标可用"),
        ],
        "metrics": [
            metric(
                "成立组后续均值",
                true["mean"],
                "return_fraction",
                "之后21个价格变化区间，非账户利润",
            ),
            metric(
                "未成立组后续均值",
                false["mean"],
                "return_fraction",
                "之后21个价格变化区间，非账户利润",
            ),
        ],
        "result_tables": [
            {
                "title": "按观察年",
                "columns": [
                    {"key": "period", "label": "观察年", "unit": ""},
                    {"key": "true_n", "label": "成立次数", "unit": "次"},
                    {"key": "true_mean", "label": "成立组均值", "unit": "return_fraction"},
                    {"key": "false_n", "label": "未成立次数", "unit": "次"},
                    {"key": "false_mean", "label": "未成立组均值", "unit": "return_fraction"},
                ],
                "rows": rows,
                "note": "逐年方向不一致，价格变化比例不是年度账户收益。",
            }
        ],
        "limitations": binding["limitations"]
        + ["协议中的目标成熟截止不是输入资料截止日；本展示没有可核实的输入资料末日。"],
        "next_steps": binding["next_steps"],
        "sources": [pinned(root, spec, role) for role, spec in specs.items()],
        "report_registration": {
            "category": registration.get("category"),
            "verdict": registration.get("verdict"),
            "oneLiner": registration.get("oneLiner"),
        },
    }


def make_project(root: Path, binding: dict) -> dict:
    return {
        "id": binding["id"],
        "title": binding["title"],
        "stage": binding["stage"],
        "summary": binding["summary"],
        "review_status": binding["review_status"],
        "references": binding["references"],
        "evidence_date": binding["evidence_date"],
        "sources": [pinned(root, s) for s in binding["sources"]],
        "limitations": binding["limitations"],
        "next_steps": binding["next_steps"],
    }


def blocked_experiment(binding: dict, reason: str) -> dict:
    """Preserve a visible card without exposing unverified historical numbers."""
    return {
        "id": binding["id"],
        "title": binding["title"],
        "kind": binding["kind"],
        "run_status": "unknown",
        "review_status": "pending",
        "review_summary": "展示来源核验失败；此状态不表示原历史研究运行失败。",
        "conclusion": "来源未通过核验，当前无法展示这项研究的数字或结论。",
        "result": "insufficient",
        "baseline": "未核明",
        "costs": "未核明",
        "references": [binding["reference"]] if binding.get("reference") else [],
        "products": [],
        "period": {"start": None, "end": None},
        "data_cutoff": None,
        "run_at": None,
        "reviewed_at": None,
        "sample": [],
        "metrics": [],
        "result_tables": [],
        "limitations": [reason],
        "next_steps": ["复核原来源身份与预期指纹后重建展示快照。"],
        "sources": [],
        "report_registration": None,
    }


def blocked_project(binding: dict, reason: str) -> dict:
    return {
        "id": binding["id"],
        "title": binding["title"],
        "stage": "insufficient",
        "summary": "来源未通过核验，当前无法展示项目进度。",
        "review_status": "pending",
        "references": [],
        "evidence_date": None,
        "sources": [],
        "limitations": [reason],
        "next_steps": ["复核原来源身份与预期指纹后重建展示快照。"],
    }


def attach_experiments(items: list[dict], experiments: list[dict]) -> None:
    """Derive scoped research text only from successfully verified records."""
    by_reference: dict[str, list[dict]] = {}
    for exp in experiments:
        if exp["run_status"] == "completed" and exp["sources"]:
            for ref in exp["references"]:
                by_reference.setdefault(ref, []).append(exp)
    for item in items:
        if item["research"]["stage"] == "insufficient":
            continue
        matches = by_reference.get(item["reference"], [])
        if not matches:
            continue
        item["experiment_ids"] = [exp["id"] for exp in matches]
        descriptions = []
        for exp in matches:
            period = exp["period"]
            span = f"{period['start'] or '时期未记录'}至{period['end'] or '未记录'}"
            description = f"{exp['title']}（{span}）：{exp['conclusion']}"
            descriptions.append(description + " " + exp["review_summary"])
        item["research"] = {
            "stage": "historical",
            "result": matches[0]["result"] if len(matches) == 1 else "unknown",
            "summary": "；".join(descriptions),
            "evidence_date": max(
                (exp["reviewed_at"] for exp in matches if exp["reviewed_at"]), default=None
            ),
        }


def load_experiments(root: Path, bindings: list[dict]) -> tuple[list[dict], list[str]]:
    experiments: list[dict] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    adapters = {"rank_summary_v1": make_momentum, "dual_ma_description_v1": make_dual_ma}
    for binding in bindings:
        if binding["id"] in seen_ids:
            raise ValueError(f"duplicate experiment id: {binding['id']}")
        seen_ids.add(binding["id"])
        adapter = adapters.get(binding.get("adapter"))
        if adapter is None:
            raise ValueError(f"unrecognized experiment adapter: {binding.get('adapter')}")
        try:
            exp = adapter(root, binding)
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            reason = f"{binding['id']}: {exc}"
            errors.append(reason)
            exp = blocked_experiment(binding, reason)
        experiments.append(exp)
    return experiments, errors


def build(root: Path, bindings_path: Path = BINDINGS) -> dict:
    root = root.resolve()
    bindings = json.loads((root / bindings_path).read_text())
    if bindings.get("schema_version") != "factor-display-bindings/1":
        raise ValueError("unsupported display bindings")
    access = factor_access.load_access_catalog(root=root)
    registry = access["registry"]
    all_cards = definitions.validate_registry(registry)
    excluded = set(bindings["excluded_references"])
    registry_src = source(root, "docs/research/definitions.v1.json")
    items = [
        item_from_card(root, ref, card, access, registry_src)
        for ref, card in all_cards.items()
        if card["type"] in INCLUDED_TYPES and ref not in excluded
    ]
    experiments, source_errors = load_experiments(root, bindings["experiments"])
    projects = []
    for binding in bindings["projects"]:
        try:
            projects.append(make_project(root, binding))
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            reason = f"{binding['id']}: {exc}"
            source_errors.append(reason)
            projects.append(blocked_project(binding, reason))
    attach_experiments(items, experiments)
    source_errors.extend(
        f"{i['reference']}: {i['source_error']}" for i in items if i["source_error"]
    )
    if any(
        i["research"]["stage"] not in STAGES or i["research"]["result"] not in RESULTS
        for i in items
    ):
        raise ValueError("invalid item research state")
    objects = len({i["id"] for i in items})
    source_map = {}
    for entry in [
        source(root, str(bindings_path)),
        registry_src,
        source(root, "configs/factor-access.v1.json"),
        source(root, "docs/experiments/registry.json"),
        *[s for i in items for s in i["sources"]],
        *[s for e in experiments for s in e["sources"]],
        *[s for p in projects for s in p["sources"]],
    ]:
        old = source_map.setdefault(entry["path"], entry["sha256"])
        if old != entry["sha256"]:
            raise ValueError(f"conflicting source hashes: {entry['path']}")
    return {
        "schema_version": "factor-research/1",
        "generated_at": datetime.now(UTC).astimezone().isoformat(),
        "registry_version": registry["version"],
        "sources": [{"path": p, "sha256": h} for p, h in sorted(source_map.items())],
        "counts": {
            "factor_objects": objects,
            "definition_versions": len(items),
            "executed_experiments": sum(e["run_status"] == "completed" for e in experiments),
        },
        "limitations": [
            "目录只统计展示范围内的正式研究读数与状态；基础价格、选择动作、基准和策略另有身份，不计作因子。",
            "未绑定展示证据不等于全仓未研究；计算核验不等于真实市场有效。",
            "量能方向目前没有本展示目录中可直接确认的正式对象，保留为空缺。",
        ],
        "source_errors": source_errors,
        "items": items,
        "experiments": experiments,
        "projects": projects,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="check pinned sources and generated contents"
    )
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.root.resolve()
    generated = build(root)
    out = root / OUTPUT
    if args.check:
        if generated["source_errors"]:
            raise SystemExit("source verification failed: " + "; ".join(generated["source_errors"]))
        old = json.loads(out.read_text())
        for item in old["sources"]:
            source(root, item["path"], item["sha256"])
        old.pop("generated_at", None)
        generated.pop("generated_at", None)
        if old != generated:
            raise SystemExit(
                "generated snapshot differs from verified sources; rebuild after review"
            )
        print("factor research catalog: source fingerprints and generated content match")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(generated, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(f"wrote {out}: {generated['counts']}")


if __name__ == "__main__":
    main()
