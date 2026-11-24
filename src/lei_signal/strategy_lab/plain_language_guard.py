"""后端输出与实验报告大白话自动安检门禁（plain_language_guard）。

把前端 `web/src/components/plainLanguageGuard.test.mjs` 的硬拦截机制扩展到：
1. `strategy_lab` 面向用户打印的文字、结论与表头；
2. `docs/experiments/` 新产出的实验报告正文与一句话结论。

原则：代码内部变量名可以留给程序用，但凡是展示给用户看的话，禁用金融黑话、英文缩写和自己编的字母数字代号。
"""
from __future__ import annotations

from pathlib import Path
import re


# 面向用户零出现的金融黑话、英文缩写与自造速记词 -> 建议大白话替代表
BANNED_JARGON_REWRITES: dict[str, str] = {
    # AGENTS.md 原有高频黑话
    "免疫": "没受影响",
    "走阔": "利差变大/借钱变贵",
    "传染": "一起跟着跌",
    "双低出清": "长短线都跌透",
    "存量出清": "融资盘降到位",
    "存量偏重": "融资盘偏重",
    "高赔率": "股票偏便宜",
    "无赔率垫": "股票不算便宜",
    "弱势底座": "大势偏弱",
    "多头底座": "大势向上",
    "牛市底座": "大势向上",
    "Contango": "恐慌回落恢复正常",
    "Vol Crush": "恐慌快速回落",
    "Washout": "大跌洗透",
    "W3范式": "按触发当天收盘价往后算",
    "W3 范式": "按触发当天收盘价往后算",
    "底峰锁仓": "底下便宜买的还没跑",
    "浮筹洗干": "想卖的差不多卖光了",
    "错配老仓": "买歪了的老持仓",
    # 近期新增的高发量化缩写与自造词
    "正交": "互相不重复/涨跌不同步",
    "闸门": "大盘弱时自动降仓开关",
    "进攻腿": "波段进攻那部分钱",
    "底仓腿": "稳健底仓那部分钱",
    "卫星腿": "波段进攻那部分钱",
    "多腿": "几块资金搭配",
    "各腿": "几块资金各自",
    "单腿": "单独一块资金",
    "三腿": "三块资金",
    "袖套": "独立模拟账户",
    "卡玛": "赚亏性价比",
    "Calmar": "赚亏性价比",
    "夏普": "每担一份波动多赚多少",
    "Sharpe": "每担一份波动多赚多少",
    "CAGR": "每年平均复利",
    "MDD": "历史最惨回撤",
    "Rank IC": "挑出来的品种后来涨得更靠前的把握度",
    "RankIC": "挑出来的品种后来涨得更靠前的把握度",
    "ICIR": "选品眼光稳不稳定",
    "HAC": "扣掉连续日期重复影响后的把握度",
    "DSR": "扣掉反复试错后的真实把握度",
    "Bootstrap": "打乱历史片段反复抽查",
    "Walk-Forward": "按时间一段段往后滚动检验",
    "走查": "按时间一段段往后滚动检验",
    "PIT": "严格按当年真实公告日",
    "ΔROE": "上季度盈利增速变快",
    "TopEx": "排最前面一组比平均多赚多少",
    "样本内": "2023年及以前用来想办法的历史数据",
    "样本外": "2024年以后封存用来考试的新数据",
    "分账制": "按各自账户分开算账",
    "等权篮子": "每只买一样多",
    "单因子": "只看这一项指标",
    "因果计算": "只用当时已经知道的数据来算",
}

# 禁止在给用户看的话里出现自造字母+数字代号（如 L1/L2/L3, G0~G4, C1/C2_M1, S0~S4, A0~A5）和全大写英文状态名
BANNED_CODE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bL[123]\b"), "不要用 L1/L2/L3 这种分层代号，直接说选品准不准、真实账户赚不赚钱、改参数稳不稳"),
    (re.compile(r"\b[GCSA][0-9](?:_M[0-9]|_[A-Za-z0-9]+)?\b"), "不要自己编 G4/C2/S3/A4 这类字母数字代号，直接用中文说清是什么办法"),
    (re.compile(r"\b(?:EXPLORE|CANDIDATE|SHADOW|DEGRADED|RETIRED)\b"), "不要用英文状态名，改用中文状态（试探中/待跟盘检验/模拟跟盘中/效果变差已降级/已停用）"),
]


STATE_LABEL_CN: dict[str, str] = {
    "EXPLORE": "试探打磨中",
    "CANDIDATE": "通过历史考验·待模拟跟盘",
    "SHADOW": "模拟跟盘观察中",
    "LIVE": "正式使用中",
    "DEGRADED": "效果变差已降级",
    "RETIRED": "已停用淘汰",
}


def plain_state_label(state: str) -> str:
    """把内部英文状态键翻译成普通人一眼能懂的中文状态。"""
    return STATE_LABEL_CN.get(str(state).upper(), str(state))


def check_plain_chinese(text: str) -> list[dict[str, str]]:
    """检查一段面向用户的中文文案是否混入了禁用黑话、英文缩写或自造代号。"""
    violations: list[dict[str, str]] = []
    for line_no, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        # 跳过纯链接路径里的文件名（不误伤 file:// 或 docs/... 路径引用）
        cleaned = re.sub(r"\[[^\]]*\]\([^)]+\)", lambda m: m.group(0).split("](")[0] + "]", line)
        cleaned = re.sub(r"`[^`]+`", "", cleaned)  # 行内代码标识另行检查（正文和表头不许出现）
        for term, hint in BANNED_JARGON_REWRITES.items():
            if term.lower() in cleaned.lower():
                violations.append({
                    "line": str(line_no),
                    "term": term,
                    "suggestion": hint,
                    "snippet": line[:90],
                })
        for pat, hint in BANNED_CODE_PATTERNS:
            m = pat.search(cleaned)
            if m is not None:
                violations.append({
                    "line": str(line_no),
                    "term": m.group(0),
                    "suggestion": hint,
                    "snippet": line[:90],
                })
    return violations


def audit_markdown_report(path: Path) -> dict[str, object]:
    """核查新实验报告是否满足归档与说人话双重要求：必含一句话大白话结论 + 全文零黑话零自造代号。"""
    content = Path(path).read_text(encoding="utf-8")
    has_oneliner = any(
        heading in content
        for heading in ("## 一句话结论（大白话）", "## 0. 一句话结论", "## 大白话总结", "## 一句话大白话")
    )
    violations = check_plain_chinese(content)
    return {
        "path": str(path),
        "has_plain_oneliner_heading": has_oneliner,
        "violations_count": len(violations),
        "violations": violations,
        "passed": has_oneliner and len(violations) == 0,
    }
