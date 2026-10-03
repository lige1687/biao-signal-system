"""Prepare one source-qualified risk study before reading any future labels."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.classic_volatility_risk_information import build_qualification


def dump(path, obj):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    c = json.loads((ROOT / "docs/experiments/raw/tsfresh-factor-validation-2026-10-02/freeze-joint/contract.json").read_text())
    for key in ("bindings", "freeze", "rehearsal", "stability_protocol"):
        c.pop(key, None)
    plan = json.loads((RAW / "scientific-plan.json").read_text())
    ref = plan["factor_ref"]
    family = "classic-risk-target-fit-2026-10-02"
    question = c["question"]
    question.update(question_id=family, hypothesis_family=family, factor_refs=[ref],
        baseline="简单历史平均、各ETF历史平均、当前波动延续；已有S/E确认与20日涨幅及ETF身份",
        added_information="既有20日简单日涨幅波动大小；不同于涨幅方向，非新增原始资料",
        decision_use=plan["question"], method={"name": "prediction_ridge", "reason": "固定lambda1，成熟训练资料拟合和标准化，较晚同观察比较；不是ARCH/GARCH复现"},
        primary_metric={"name": "MSE", "direction": "lower", "attention_threshold": None, "threshold_reason": "没有预先最低有用幅度，不补事后过关线"},
        auxiliary_metrics=["RMSE", "asset/year paired errors", "leave_one_asset_out_no_refit", "persistence", "asset_training_mean", "block120_saved_predictions"],
        dependence="20个未来间隔重叠；同日四ETF同步、连续60日期片段，固定120日辅助，不重拟合",
        trial_history="旧涨幅/同期解释研究已结案；本问题首次固定风险目标，历史全部已看过，当前未来风险值尚未计算")
    question["target"] = {"kind": "forward_volatility", "horizon": 20, "start_offset": 1, "end_offset": 21, "price_basis": "close_to_close_path"}
    c["feature"] = {"kind": "classic_volatility_risk_information", "definition_ref": ref, "lookback": 20,
        "warmup": 252, "missing_policy": "segmented", "bar_frequency": "daily_quote"}
    c["target"] = {"kind": "forward_volatility", "start_offset": 1, "end_offset": 21, "entry_field": "close", "unit": "percentage_point", "path_field": "close", "ddof": 1, "annualized": False, "price_measure": "economic_price"}
    c["evaluator"] = {"kind": "prediction_ridge", "version": "1.0.0", "baseline_features": plan["existing_information"], "added_features": ["volatility20"], "lambda": 1.0}
    c["split"]["folds"] = plan["folds"]
    c["dependence"] = {"block_length": 60, "draws": 1000, "seed": 20261002, "axis_scope": "evaluation"}
    c["budget"] = {"scientific_variants": 4, "execution_seconds": 7200, "max_rows": 6000}
    c["history"] = {"family": family}
    c["permissions"] = {"real_labels": True, "effect_authorized": True, "real_fits": 4, "paid_requests": 0, "production": False}
    c["publication"] = {"report_path": "docs/experiments/classic-risk-target-numeric-2026-10-02.md", "category": "方法论与验证", "claimed_scope": "full", "conclusion": "insufficient"}
    mapping = c["research_design"]["claim_mapping"]
    mapping.update(original_statement="经典波动大小的用途应与未来风险目标匹配；旧涨幅预测负结果不回答未来波动目标", source_section="etf.reference.volatility20@1.0.0；用户2026-10-02进一步增量研究授权", proxy_definition=plan["target"], preserved_conditions=["原波动20日简单收益标准差ddof1，无年化", "252连续有效经济报价", "全部四ETF同观察比较"], omitted_conditions=["涨跌方向预测", "完整LEI执行", "真实资料历史到达时间", "独立未见资料"], decision_use=plan["question"], intended_action_time="无交易；随后20间隔风险信息研究", application_scope="classic_risk_information", tested_scope="四只国内宽基ETF2022—2026H1已见历史")
    sample = c["research_design"]["sample_fit"]
    sample.update(qualification_artifact=str((RAW / "qualification.json").relative_to(ROOT)), model_feature_count=7,
        paired_support="全部四方法比较保留相同成熟观察，不以波动筛组或换ETF",
        rationale="先检查实际共同数量，六已有字段加一候选固定ridge1；同日四ETF相关，不能凭行数说独立验证。")
    reasons = {
        "universe_fit": "四只国内宽基ETF匹配用户主战场并复用已资格输入；同市场关联不能当独立四次重复，原六ETF定义仅测试此四只子范围。",
        "proxy_fidelity": "当前波动严格复用经典20个简单日涨幅样本标准差，不混用对数或年化旧变量；未来目标使用下一收盘后20个间隔，方向与买卖未研究。",
        "method_fit": "已有价格表达及产品身份与候选波动共同比较，训练结果必须在评价开始前成熟；固定惩罚和两折，另保留当前波动延续及逐产品历史平均。",
        "conclusion_scope": "全部已见历史、行动与报价重建资料，公开到达和未来修订未证；只比较限定风险目标误差，不推出盈利、账户回撤、完整策略或生产采用。",
    }
    c["controller_review"] = {key: {"reason": value, "source_refs": [str((RAW / "scientific-plan.json").relative_to(ROOT))]} for key, value in reasons.items()}
    panel_path = ROOT / c["data"]["path"]
    assert hashlib.sha256(panel_path.read_bytes()).hexdigest() == c["data"]["sha256"]
    payload = json.loads(panel_path.read_text())
    qualification = build_qualification(payload, deepcopy(c), ROOT)
    dump(RAW / "qualification.json", qualification)
    sample.update(qualification_sha256=hashlib.sha256((RAW / "qualification.json").read_bytes()).hexdigest(), **qualification["counts"])
    dump(RAW / "draft.json", c)
    print(json.dumps({"counts": qualification["counts"], "scientific_support": qualification["scientific_support"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
