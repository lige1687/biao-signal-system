"""Register two finite technical proxies and qualify without future outcomes."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def main():
    from lei_signal.research.technical_persistence_information import (
        BASELINE_PERSISTENCE, BASELINE_TRANSITION, build_qualification,
    )
    brief = json.loads((RAW / "brief.json").read_text())
    registry_path = ROOT / "docs/research/definitions.v1.json"
    registry = json.loads(registry_path.read_text())
    base = json.loads((ROOT / "docs/experiments/raw/technical-daily-risk-2026-10-03/slope/freeze-01/contract.json").read_text())
    payload = json.loads((ROOT / base["data"]["path"]).read_text())
    specs = [
        {"slug": "persistence", "kind": "ema_direction_persistence_information",
         "ref": "research.trend.ema_direction_persistence20@1.0.0", "type": "feature",
         "name": "EMA20最近20个交易日向上比例", "fields": BASELINE_PERSISTENCE,
         "added": "ema20_up_share20", "targets": ["forward_return", "mae"],
         "statement": "EMA稳定上行，随后SMA确认；趋势由20向60和120传导",
         "section": "技术体系§2.2", "formula": "sum(EMA20[j]>EMA20[j-1],j=t-19..t)/20",
         "unit": "fraction [0,1] in steps of0.05; equality counts0",
         "preserved": ["EMA20方向", "仅t及以前", "严格上行", "完整252连续日暖启动"],
         "omitted": ["稳定一词的作者唯一标定", "完整EMA→SMA传导与趋势五步骤", "交易动作"],
         "use": "检验持续程度在当前20/60颜色、EMA方向、涨跌及波动已知后是否提供收益或下探信息",
         "proxy": "固定20日方向比例是稳定上行的研究代理；不是原文唯一公式，也不是Q01连续等待年龄"},
        {"slug": "transition", "kind": "bull_green_transition_information",
         "ref": "research.signal.bull_green_adjacent_black20@1.0.0", "type": "state_signal",
         "name": "20组严格高于60组且当前绿色时的相邻黑转绿", "fields": BASELINE_TRANSITION,
         "added": "adjacent_black20", "targets": ["mae"],
         "statement": "20组高于60组的多头环境中，黑色等待绿色；灰色不动作",
         "section": "技术体系§2.7", "formula": "eligible=min(SMA20,EMA20)>max(SMA60,EMA60) AND color20(t)=green; X=1 iff color20(t-1)=black",
         "unit": "0/1 within fixed bull-green condition; other dates retained as ineligible",
         "preserved": ["20组高于60组", "当前严格绿色", "前一完整报价日严格黑色", "灰色和未知分开保留"],
         "omitted": ["经过灰色再转绿的等待路径", "趋势身份与转黑重置", "完整首次入场/再次入场", "持仓与账户规则"],
         "use": "在相同多头且绿色环境下，检验刚由黑转绿是否额外提示随后20日收盘下探",
         "proxy": "仅原文变色条件的相邻日子集；不是完整原文黑色等待绿色，也不是新增买入规则"},
    ]
    common = ["docs/experiments/raw/technical-multimethod-2026-10-03/brief.json",
              "src/lei_signal/research/technical_persistence_information.py",
              "tests/unit/test_technical_persistence_information.py",
              "docs/experiments/raw/volume-information-2026-09-30/execution/source-manifest.json",
              "docs/research/strategy-source-snapshots/2026-09-30/LEI 技术交易体系.md",
              "docs/research/strategy-source-snapshots/2026-09-30/LEI 技术实现.md"]
    for spec in specs:
        object_id = spec["ref"].split("@")[0]
        if any(card["id"] == object_id for card in registry["objects"]):
            raise RuntimeError("Refuse overwrite of existing definition: " + object_id)
        card = deepcopy(next(c for c in registry["objects"] if c["id"] == "research.trend.green_black60_state"))
        card.update(id=object_id, name=spec["name"], type=spec["type"], sources=common,
                    spec_anchor=[spec["section"], "技术实现§4.2"],
                    local_alias=spec["slug"], origin=spec["proxy"],
                    scope="四只国内宽基ETF已见日线；有限价格信息表达")
        card["definition"] = {"formula": spec["formula"], "parameters": {"lookback": 20, "warmup": 252, "horizon": 20},
                              "unit": spec["unit"], "direction": "方向及信息用途由冻结研究检验，不预设越大越好",
                              "transforms": "原生产EMA用前20收盘SMA播种，alpha=2/21；经济OHLC不改变",
                              "nan_policy": "缺价及未知行动分段重置；unknown不填gray；背景外保留理由",
                              "endpoints": "t及以前；目标从t+1至t+21，21个经济收盘20间隔"}
        card["validation"].update(tests=[common[2]], limitations=spec["proxy"] + "；既有价格表达，非新增原始信息；已见历史")
        card["status"].update(definition_clarity="fixed_explicit_research_proxy", implementation="synthetic_checks_verified", effectiveness="not_evaluated")
        card["lifecycle"] = {"state": "research_ready", "basis": common[:3], "verification_scope": "合成口径检查与无未来结果的来源/样本资格；效果由冻结合同"}
        registry["objects"].append(card)
    for p in common:
        registry["sources"][p] = {"path": p, "sha256": sha(ROOT / p)}
    put(registry_path, registry)
    for spec in specs:
        for target in spec["targets"]:
            name = "return" if target == "forward_return" else "risk"
            folder = RAW / spec["slug"] / name
            contract = deepcopy(base)
            for k in ("bindings", "freeze", "rehearsal", "calendar"):
                contract.pop(k, None)
            ident = "technical-" + spec["slug"] + "-" + name + "-2026-10-03"
            q = contract["question"]
            q.update(question_id=ident, hypothesis_family=ident, factor_refs=[spec["ref"]],
                     target={"kind": target, "horizon": 20, "start_offset": 1, "end_offset": 21,
                             "price_basis": "close_to_close" if name == "return" else "close_to_close_path"},
                     baseline="B0较早成熟均值；B1固定背景；另保留每ETF训练均值",
                     added_information=spec["formula"], decision_use=spec["use"],
                     joint_structure="同日四ETF、持续状态和重叠20日结果；背景外、未知及未成熟分开",
                     auxiliary_metrics=brief["studies"][0 if spec["slug"] == "persistence" else 1]["auxiliary"],
                     trial_history=brief["selection_history"] + "；Q01等待年龄与20/60旧颜色模型封存，本轮不是重跑",
                     method={"name": "prediction_ols", "reason": "同资产和同日期固定字段比較；零惩罚，不选最优参数；简单均值并列"},
                     dependence="同日四ETF及20日重叠结果；同步日期20/60日块作有限敏感性",
                     added_information_reason="既有价格的持续或事件表达是否帮助判断，不能把表达变换叫独立新数据")
            contract["feature"] = {"kind": spec["kind"], "lookback": 20, "bar_frequency": "daily_quote",
                                   "missing_policy": "segmented", "warmup": 252, "definition_ref": spec["ref"]}
            contract["target"] = {"kind": target, "start_offset": 1, "end_offset": 21, "entry_field": "close",
                                  "unit": "percentage_point", "price_measure": "economic_price"}
            if name == "risk":
                contract["target"]["path_field"] = "close"
            contract["evaluator"].update(baseline_features=list(spec["fields"]), added_features=[spec["added"]], minimum_training_rows=22)
            contract["history"] = {"family": ident, "changed_after_results_reason": "新持续程度/相邻事件代理，语义与固定用途事前登记；所有历史已见"}
            contract["sources"] = [s for s in contract["sources"] if not any(x in s["path"] for x in
                                     ("semantic-mining", "technical-daily-risk", "trend_slope_change", "test_trend_slope"))]
            existing = {s["path"] for s in contract["sources"]}
            contract["sources"] += [{"path": p, "sha256": sha(ROOT / p)} for p in common if p not in existing]
            contract["publication"].update(report_path="docs/experiments/technical-" + spec["slug"] + "-" + name + "-artifact-2026-10-03.md", conclusion="insufficient")
            qualification = build_qualification(payload, contract, ROOT)
            qp = folder / "qualification.json"
            put(qp, qualification)
            qrel = str(qp.relative_to(ROOT))
            contract["research_design"] = {
                "claim_mapping": {"original_statement": spec["statement"], "source_section": spec["section"],
                    "proxy_definition": spec["proxy"] + ": " + spec["formula"],
                    "preserved_conditions": spec["preserved"], "omitted_conditions": spec["omitted"],
                    "decision_use": spec["use"], "observation_time": "完整t日收盘后", "intended_action_time": "无交易；随后目标从下一收盘开始",
                    "application_scope": "trend_road_information", "tested_scope": card["scope"],
                    "unresolved_uses": ["完整LEI和资金增量未测量", "历史到达及全部行动完整性未认证", "真正未见数据缺失"]},
                "sample_fit": {"qualification_artifact": qrel, "qualification_sha256": sha(qp), "outcome_values_used_for_design": False,
                    "unit": "ETF×安排交易日；不是独立事件", **qualification["counts"],
                    "paired_support": json.dumps(qualification["scientific_support"], ensure_ascii=False),
                    "dependence": q["dependence"], "model_feature_count": len(spec["fields"]) + 1,
                    "rationale": "只以来源、过去特征、日期成熟与列秩审核资格；完整安排样本和背景外保留；新增一列、无调参；均值并列",
                    "decision": "estimate"}}
            reasons = {"universe_fit": "四固定国内宽基ETF经济价来源逐行可核；到达和行动完整性有限，不扩大池",
                       "proxy_fidelity": spec["proxy"],
                       "method_fit": "固定背景加一列，两时间折，不用结果定分组；样本/秩/稀少事件均先审，简单均值防止弱背景误导",
                       "conclusion_scope": "收益或收盘下探的信息用途；全部历史已见；不涉及账户、转黑重置或原文修改"}
            for key in contract["controller_review"]:
                contract["controller_review"][key] = {"reason": reasons[key], "source_refs": [qrel, common[0]]}
            put(folder / "draft.json", contract)
            print(spec["slug"], name, json.dumps(qualification["scientific_support"]["folds"], ensure_ascii=False))


if __name__ == "__main__":
    main()
