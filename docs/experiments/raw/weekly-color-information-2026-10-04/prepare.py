"""Register this new weekly-state proxy; qualify before reading outcomes."""
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
    from lei_signal.research import weekly_color_information as weekly
    brief = json.loads((RAW / "brief.json").read_text())
    ref = brief["ref"]
    regpath = ROOT / "docs/research/definitions.v1.json"
    registry = json.loads(regpath.read_text())
    if any(x["id"] == ref.split("@")[0] for x in registry["objects"]):
        raise RuntimeError("Refuse overwrite; registration is append-only for this new object")
    common = [str((RAW / "brief.json").relative_to(ROOT)),
              "src/lei_signal/research/weekly_color_information.py",
              "tests/unit/test_weekly_color_information.py",
              "docs/experiments/raw/volume-information-2026-09-30/execution/source-manifest.json",
              "docs/research/strategy-source-snapshots/2026-09-30/LEI 技术交易体系.md",
              "docs/research/strategy-source-snapshots/2026-09-30/LEI 技术实现.md"]
    card = deepcopy(next(x for x in registry["objects"] if x["id"] == "research.trend.green_black60_state"))
    card.update(id=ref.split("@")[0], version="1.0.0", name="上一已完成周的20周绿黑灰状态",
                sources=common, local_alias="completed-week-color20", type="state_signal",
                spec_anchor=["桌面技术体系§2.7日周共振", "技术实现§3.2周线完成与§6多周期"],
                origin="原20周期判据应用于已完成交易周；上一ISO周才使用与120周暖启动为本轮保守代理，非完整共振事件或作者唯一标定",
                scope="四国内宽基ETF已见经济日线聚合的上一完成周背景信息")
    card["definition"] = {
        "formula": brief["feature"],
        "parameters": {"N_weeks": 20, "daily_warmup": 252, "weekly_warmup": 120, "primary_horizon_days": 20,
                       "week_policy": "previous_iso_week_only"},
        "unit": "categorical green/black/gray/unknown; green and black binary fields, gray reference",
        "direction": "颜色表达周道路方向；不预设同向就有新增收益",
        "transforms": "日线经济价每完整交易周最后报价；EMA20首20完整周SMA播种alpha2/21；周涨幅20/60作已有背景",
        "nan_policy": "缺报价或行动未知使该周失效并重置连续周；头部不完整周保守丢弃；当前周不用于信号；不造交易周",
        "endpoints": "在t收盘使用严格早于t所在ISO周的最后完成周；目标t+1..t+21共21收盘20间隔",
    }
    card["input"].update(frequency="daily_quote_aggregated_to_completed_trading_weeks",
                         calendar="源交易日历定义周内应有报价；整周无交易不伪造报价；ISO周边界")
    card["universe"].update(version="weekly-color-four-etf-20261004",
        eligibility="保留四固定ETF全部4340安排日；仅252连续日且120连续有效完成周及所需指标齐全进入效果比较",
        warmup="252连续日+120连续有效交易周；EMA20首20周SMA播种；周内缺失重置",
        missing="未知周、日不足和未成熟分别保留，不把unknown叫gray")
    card["time"].update(observation_time="t完整收盘后；周输入严格为上一ISO周或更早",
                        available_at="报价理论完成时间可核；历史供应商实际到达时间未认证",
                        effective_from="2026-10-04 completed-week color research registration")
    card["validation"].update(tests=[common[2]],
        method="人工周聚合/EMA/严格判据独立复算、前缀/缺失/权限及冻结演练；效果另用固定共同支持比较",
        limitations="周线为日线的确定表达；非新原始资料。保守晚到下一ISO周；不测日周同时变绿事件、三周期共振、小时扩散或资金动作；已见历史")
    card["status"].update(definition_clarity="fixed_explicit_completed_week_proxy", implementation="synthetic_checks_verified",
                          data_qualification="limited_retrospective_economic_ohlc", effectiveness="not_evaluated")
    card["lifecycle"] = {"state": "research_ready", "basis": common[:3],
                         "verification_scope": "合成口径/时点及无未来结果来源资格；研究结果由冻结合同和报告给出"}
    before = hashlib.sha256(json.dumps(registry["objects"], sort_keys=True).encode()).hexdigest()
    registry["objects"].append(card)
    for p in common:
        if p in registry["sources"] and registry["sources"][p]["sha256"] != sha(ROOT / p):
            raise RuntimeError("Existing authoritative source changed: " + p)
        registry["sources"][p] = {"path": p, "sha256": sha(ROOT / p)}
    put(regpath, registry)
    put(RAW / "registration.json", {"ref": ref, "existing_objects_sha256_before": before,
         "existing_objects_sha256_after": hashlib.sha256(json.dumps(registry["objects"][:-1], sort_keys=True).encode()).hexdigest(),
         "new_card_sha256": hashlib.sha256(json.dumps(card, sort_keys=True).encode()).hexdigest()})
    base = json.loads((ROOT / "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/risk/draft.json").read_text())
    payload = json.loads((ROOT / base["data"]["path"]).read_text())
    for slug, target in (("return", "forward_return"), ("risk", "mae")):
        c = deepcopy(base)
        for k in ("bindings", "freeze", "rehearsal", "calendar"):
            c.pop(k, None)
        ident = "weekly-color-" + slug + "-2026-10-04"
        q = c["question"]
        q.update(question_id=ident, hypothesis_family=ident, factor_refs=[ref],
                 baseline="B0较早成熟均值；B1固定日/周已知背景；并列每ETF成熟训练均值",
                 added_information=brief["feature"], decision_use=brief["decision_use"],
                 joint_structure="同日四ETF、周状态持续及20日重叠结果；每日完整安排，未知不填灰",
                 auxiliary_metrics=brief["auxiliary"], trial_history=brief["selection_history"],
                 dependence="同日ETF、持续周状态及20日重叠结果；同步20/60交易日块敏感性",
                 added_information_reason="周聚合为已知日线资料的表达，可能补充模型表达而非新增原始信息",
                 method={"name": "prediction_ols", "reason": "单候选两颜色字段、固定已知日周背景；不调参；合理简单均值并列"})
        q["target"].update(kind=target, price_basis="close_to_close" if slug == "return" else "close_to_close_path")
        c["feature"] = {"kind": "weekly_color_information", "lookback": 20, "bar_frequency": "daily_quote",
                        "warmup": 252, "missing_policy": "segmented", "definition_ref": ref,
                        "week_warmup": 120, "week_policy": "previous_iso_week_only"}
        c["target"].update(kind=target, path_field="close")
        c["evaluator"].update(baseline_features=brief["baseline"], added_features=brief["added"], minimum_training_rows=32)
        c["dependence"].update(seed=20261004)
        c["history"] = {"family": ident, "changed_after_results_reason": "新的周频表达，旧日20/日60状态保持封存；全部已见历史"}
        c["sources"] = [s for s in c["sources"] if not any(x in s["path"] for x in
            ("technical-multimethod", "technical_persistence", "test_technical_persistence"))]
        existing = {s["path"] for s in c["sources"]}
        c["sources"] += [{"path": p, "sha256": sha(ROOT / p)} for p in common if p not in existing]
        c["publication"].update(report_path="docs/experiments/weekly-color-" + slug + "-artifact-2026-10-04.md", conclusion="insufficient")
        qualification = weekly.build_qualification(payload, c, ROOT)
        folder = RAW / slug
        qp = folder / "qualification.json"
        put(qp, qualification)
        qrel = str(qp.relative_to(ROOT))
        c["research_design"] = {
            "claim_mapping": {"original_statement": "日K变绿与周K也变绿可做多周期共振；周线信号需该周完成后使用",
                "source_section": "技术体系§2.7；实现§3.2/6", "proxy_definition": card["origin"] + ": " + brief["feature"],
                "preserved_conditions": ["20周期黑绿判据", "实际周频聚合", "完整周才可知", "严格比较与灰/未知分开"],
                "omitted_conditions": ["日周同时变绿事件", "多头排列下完整黑色等待绿入场", "三周期同步标志动作", "小时扩散与账户操作"],
                "decision_use": brief["decision_use"], "observation_time": "t完整日收盘后，仅上一ISO周输入",
                "intended_action_time": "无交易；目标从t+1收盘开始", "application_scope": "trend_road_information",
                "tested_scope": card["scope"], "unresolved_uses": ["真正未见数据", "历史到达/行动完整性", "完整原文交易与资金收益"]},
            "sample_fit": {"qualification_artifact": qrel, "qualification_sha256": sha(qp), "outcome_values_used_for_design": False,
                "unit": "ETF×安排日；连续状态不是独立机会", **qualification["counts"],
                "paired_support": json.dumps(qualification["scientific_support"], ensure_ascii=False),
                "dependence": q["dependence"], "model_feature_count": 15,
                "rationale": "事前只核过去特征/来源/日期成熟与列秩；120周保守暖启动，日周涨幅防止只再表达上涨；两后期与简单对手",
                "decision": "estimate"}}
        reasons = {"universe_fit": "固定已有经济四ETF，历史来源实际到达和行动完整性有限，不扩大池",
                   "proxy_fidelity": card["origin"],
                   "method_fit": "分类状态不强排大小；固定共同支持、两历史折/零惩罚OLS及简单均值，周持续与20日重叠按日期核",
                   "conclusion_scope": "周状态背景表达的信息，不是完整日周变色事件或真实交易增量；全部已见资料"}
        for key in c["controller_review"]:
            c["controller_review"][key] = {"reason": reasons[key], "source_refs": [qrel, common[0]]}
        put(folder / "draft.json", c)
        print(slug, json.dumps(qualification["scientific_support"], ensure_ascii=False))


if __name__ == "__main__":
    main()
