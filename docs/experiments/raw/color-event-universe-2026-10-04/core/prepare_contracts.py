"""One-time pre-outcome qualification and finite four-branch draft construction."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from lei_signal.research.color_event_information import (
    ADDED_FEATURES, BASELINE_FEATURES, DEFINITION_REFS, build_qualification)
from lei_signal.research.question_contract import validate_workflow_contract

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
PANEL = ROOT / "docs/experiments/raw/volume-information-2026-09-30/execution/panel.json"
PRIOR = ROOT / "docs/experiments/raw/weekly-color-information-2026-10-04/return/accepted-freeze-01/contract.json"


def put(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if path.exists() and path.name == "qualification.json" else "x"
    with path.open(mode, encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def main():
    panel = json.loads(PANEL.read_text())
    previous = json.loads(PRIOR.read_text())
    panel_sha = sha256(PANEL.read_bytes()).hexdigest()
    assert panel_sha == "382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b"
    ledger = {"question": "daily20 adjacent color event, previous completed week context",
              "source_sha256": panel_sha, "all_history_seen": True,
              "branches": [], "maximum_real_fits": 16, "actual_real_fits_before_freeze": 0,
              "attempts_before_freeze": 0,
              "qualification_correction": "Independent black-event count initially omitted 588000.SS|2023-05-04 by requiring prior-day weekly120; prior-day daily252 alone is required. Corrected before outcomes and freeze."}
    for color in ("green", "black"):
        for target in ("forward_return", "mae"):
            c = deepcopy(previous)
            for key in ("bindings", "freeze", "rehearsal", "calendar"):
                c.pop(key, None)
            branch = f"{color}-{('return' if target == 'forward_return' else 'mae')}20"
            c["feature"].update(kind="color_event_information", event_color=color,
                                 definition_ref=DEFINITION_REFS[color])
            c["target"].update(kind=target, unit="percentage_point")
            q = c["question"]
            q.update(question_id="daily20-color-event-" + branch + "-2026-10-04",
                     hypothesis_family="daily20-color-event-" + branch + "-2026-10-04",
                     factor_refs=[DEFINITION_REFS[color]], sampling="event",
                     event_definition=f"252连续日内，前一日合格且日20由非{color}相邻变为{color}；当日上一完成周需120连续周",
                     added_information="当日可知的上一完成ISO周20绿/黑/灰；仅绿黑双指标，灰参照",
                     baseline="B0每ETF成熟训练均值；B1固定ret20/ret60/vol20/原文多头排列/ETF身份",
                     trial_history="黑绿两事件、收益/收盘下探两目标事前冻结，16主真实fit上限；全部历史已见",
                     decision_use=("绿色事件后收益/下探是否受上周状态额外影响，不构成完整入场" if color == "green" else
                                   "黑色事件后收盘下探/错失上涨是否受上周状态额外影响，不构成完整退出"),
                     method={"name": "prediction_ridge", "reason": "固定正则1；相同ETF日期、两个历史折；稀疏周色不作强排序"},
                     primary_metric={"name": "RMSE", "direction": "lower", "attention_threshold": None,
                                     "threshold_reason": "事前无可支持的有意义改善门槛，报告差额与不确定性"},
                     auxiliary_metrics=["5/10/20/60/120收益、上涨率、跌幅尾部、收盘MAE/MFE和路径峰谷",
                                        "原文多头/非多头分层、逐年ETF、去一ETF、周色分组成熟训练均值",
                                        "完整日历同步20/60日块1000次seed20261004；20日跌>5%组频率/Brier"],
                     dependence="同日ETF及20日结果重叠；完整日历同步20/60交易日块，不将稀疏事件行当连续日历")
            q["target"].update(kind=target, price_basis=("close_to_close" if target == "forward_return" else "close_to_close_path"))
            c["evaluator"] = {"kind": "prediction_ridge", "version": "1.0.0",
                              "baseline_features": list(BASELINE_FEATURES),
                              "added_features": list(ADDED_FEATURES), "lambda": 1.0,
                              "minimum_training_rows": 16}
            c["history"] = {"family": "daily20-color-event-" + branch + "-2026-10-04",
                            "changed_after_results_reason": "new bounded adjacent-event question; all historical observations already seen",
                            "ledger_path": ""}
            c["permissions"] = {"real_labels": True, "effect_authorized": True,
                                 "real_fits": 4, "paid_requests": 0, "production": False}
            c["budget"] = {"scientific_variants": 1, "execution_seconds": 7200, "max_rows": 6000}
            c["publication"] = {"report_path": f"docs/experiments/color-event-{branch}-2026-10-04.md",
                                "category": "模块与信号", "claimed_scope": "partial", "conclusion": "not_supported"}
            review_reasons = {
                "universe_fit": "四只已有经济价格重建的宽基ETF；来源到达与行动完整性限制仍在",
                "proxy_fidelity": f"日20相邻转{color}只是一段颜色变化，原文多头排列保留分组，周色延迟一完成周",
                "method_fit": "固定ridge1及2025、2026H1两折；同ETF日期配对，稀疏状态不强排序",
                "conclusion_scope": "只解释已见历史的局部事件预测误差，不能推出完整入场退出或账户收益",
            }
            for key, reason in review_reasons.items():
                c["controller_review"][key] = {"reason": reason,
                                                "source_refs": ["docs/experiments/raw/color-event-universe-2026-10-04/core/ledger.json"]}
            d = c["research_design"]
            d["claim_mapping"].update(original_statement="日20黑绿状态变化及上一完成周颜色是否有信息",
                proxy_definition=q["event_definition"] + "；上周颜色复用原周色定义",
                preserved_conditions=["原20判色", "原文多头排列保留为分组与模型背景", "完整周才可知", "严格颜色和未知分开"],
                omitted_conditions=["完整入场/退出", "小时信号", "账户资金动作"],
                decision_use=q["decision_use"], tested_scope="四国内宽基ETF已见经济日线局部事件")
            d["sample_fit"].update(unit="ETF×相邻颜色事件；按安排日保存资格排除", episodes=None,
                                   model_feature_count=len(BASELINE_FEATURES)+len(ADDED_FEATURES),
                                   dependence=q["dependence"], rationale="资格与方法事前固定；周绿稀疏须披露")
            qualification = build_qualification(panel, c, ROOT)
            qual_path = HERE / branch / "qualification.json"
            put(qual_path, qualification)
            qual_rel = qual_path.relative_to(ROOT).as_posix()
            d["sample_fit"].update(qualification_artifact=qual_rel,
                                   qualification_sha256=sha256(qual_path.read_bytes()).hexdigest(),
                                   assets=qualification["counts"]["assets"],
                                   observations=qualification["counts"]["observations"],
                                   dates=qualification["counts"]["dates"],
                                   paired_support=json.dumps(qualification["scientific_support"],ensure_ascii=False))
            c["history"]["ledger_path"] = "docs/experiments/raw/research-workflow-ledgers-2026-09-29/" + sha256(c["history"]["family"].encode()).hexdigest()[:24] + "/attempts.jsonl"
            validate_workflow_contract(c)
            put(HERE / branch / "draft.json", c)
            ledger["branches"].append({"branch": branch, "target": target, "event_color": color,
                                        "qualification": qual_rel, "draft": (HERE / branch / "draft.json").relative_to(ROOT).as_posix(),
                                        "planned_fits": 4,
                                        "qualified_events": qualification["coverage"]["eligible"],
                                        "folds": qualification["scientific_support"]["folds"]})
    put(HERE / "ledger.json", ledger)
    print(json.dumps({"branches": [{"branch": x["branch"], "qualified_events": x["qualified_events"],
                                     "folds": x["folds"]} for x in ledger["branches"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
