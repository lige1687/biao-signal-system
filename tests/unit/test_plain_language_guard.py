"""后端输出与新实验报告的大白话自动安检测试（与前端 plainLanguageGuard 配套形成全链路硬拦截）。"""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

from lei_signal.strategy_lab.cli import main as strategy_lab_cli
from lei_signal.strategy_lab.plain_language_guard import (
    audit_markdown_report,
    check_plain_chinese,
    plain_state_label,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_plain_language_guard_catches_jargon_and_invented_codes() -> None:
    """安检器必须准确拦截金融黑话、量化英文缩写和自造字母数字代号。"""
    bad_samples = [
        "本轮 L1 检验显示 Rank IC 达到 0.04，HAC t=2.55。",
        "采用 G4 熊市闸门后，进攻腿的卡玛和夏普大幅提升。",
        "策略 C2_M1 已晋级 CANDIDATE，等待 SHADOW 观察期。",
    ]
    for sample in bad_samples:
        hits = check_plain_chinese(sample)
        assert len(hits) >= 2, f"未能拦截黑话样例: {sample}"

    clean_sample = "行业基金改成每月换一次仓，大盘跌破半年线时降到两成半仓位，最惨回撤明显变小，目前处于模拟跟盘观察中。"
    assert check_plain_chinese(clean_sample) == []
    assert plain_state_label("SHADOW") == "模拟跟盘观察中"


def test_new_experiment_report_passes_plain_language_guard() -> None:
    """新产出的实验报告必须包含大白话一句话结论，且全篇零黑话、零自造代号。"""
    report_path = REPO_ROOT / "docs/experiments/strategy-lab-four-campaigns-2026-11-24.md"
    audit = audit_markdown_report(report_path)
    assert audit["has_plain_oneliner_heading"] is True, "实验报告缺少『## 一句话结论（大白话）』小节"
    assert audit["violations"] == [], f"实验报告混入禁用黑话或自造代号：{audit['violations']}"


def test_cli_user_facing_outputs_pass_plain_language_guard() -> None:
    """面向用户的核心命令行输出（生命周期清单、周度复盘）不得出现英文状态名与黑话。"""
    for argv in (["lifecycle-status"], ["weekly-review"]):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = strategy_lab_cli(argv)
        assert code == 0
        out = buf.getvalue()
        hits = check_plain_chinese(out)
        assert hits == [], f"命令 {argv} 输出混入禁用黑话：{hits}\n原文：\n{out}"
