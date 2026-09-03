"""收盘简报（14:45 盘中预判版 / 16:45 收盘版）· 确定性构建层 + 表达层。

用户拍板（2026-08-23）：
- 结构：① 环境异常（A+美宽度，异常驱动）→ ② 自选重点变化 → ③ 板块观察池。
- 环境的宏观指标（两融/VIX/中美利差）与行业基本面做一行背景，不做判定。
- 优先级**不写死**：继承机会扫描 verdict 档位（actionable > waiting > blocked/none），
  同档按「条件变化数」排——档位语义来自规则账本，不新造参数。
- 板块观察池：近 ``POOL_LOOKBACK`` 日出现在「临近升级 / 资金印证 / 动能前五」
  任一清单的板块，标连续天数；附 PE_TTM 与 20 日主力净流入（单据规模代理）。
- LLM 只做表达（照 plans/llm.py 表达层模式）：禁用词校验 + 模板降级，
  判定权在 Python；LLM 不可用时简报永远出模板版。
- 变化基线 = 上一份已落盘简报（昨收盘版优先）；盘中版标注「预判，未收盘」。

落盘：``{LEI_CACHE_ROOT}/daily_brief/YYYY-MM-DD.json``，
形如 ``{"date", "versions": {"1445": {...}, "1645": {...}}}``（幂等覆盖同槽位）。
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from lei_signal.api.labels import RISK_STATE_CN, RULE_CN
from lei_signal.data.cache import DEFAULT_CACHE_DIR
from lei_signal.domain.types import COLOR_CN, STAGE_CN

logger = logging.getLogger(__name__)

ROOT = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
BRIEF_DIR = ROOT / "daily_brief"

SLOT_INTRADAY = "1445"  # 盘中预判版（用户指定 14:45）
SLOT_CLOSE = "1645"     # 收盘复核版

POOL_LOOKBACK = 5          # 观察池连续天数回看窗口（展示口径，非策略参数）
BREADTH_PCT_WINDOW = 250   # 宽度分位回看窗口（统计描述）
BREADTH_EXTREME = 90.0     # 极端分位阈值：≥90 或 ≤(100-90) 视为异常（统计描述）

_BANNED_WORDS = ("买入", "卖出", "建议买", "该买", "加仓", "减仓", "抄底")

RESEARCH_NOTE = "research_proxy 研究代理，非买卖建议"


# ── 落盘 ─────────────────────────────────────────────────────────────────────
def brief_path(day: str) -> Path:
    return BRIEF_DIR / f"{day}.json"


def load_brief(day: str) -> dict | None:
    p = brief_path(day)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def save_brief_version(day: str, slot: str, brief: dict) -> None:
    """幂等合并同日多槽位，原子写。"""
    doc = load_brief(day) or {"date": day, "versions": {}}
    doc.setdefault("versions", {})[slot] = brief
    p = brief_path(day)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def load_baseline_before(day: str, slot: str) -> dict | None:
    """取 (day, slot) 之前最近一份简报（跨日：昨收盘 > 昨盘中 > …）。"""
    order = {"1445": 0, "1645": 1}  # 同日内收盘版更晚
    import datetime as _dt

    try:
        cur = (_dt.date.fromisoformat(day), order.get(slot, 0))
    except ValueError:
        return None
    best: dict | None = None
    best_key: tuple | None = None
    if not BRIEF_DIR.exists():
        return None
    for f in sorted(BRIEF_DIR.glob("*.json"), reverse=True):
        try:
            d = _dt.date.fromisoformat(f.stem)
        except ValueError:
            continue
        doc = load_brief(f.stem)
        if not doc:
            continue
        for s in doc.get("versions", {}):
            key = (d, order.get(s, 0))
            if key < cur and (best_key is None or key > best_key):
                best, best_key = doc["versions"][s], key
    return best


# ── ① 市场环境 · 异常检测（纯函数）──────────────────────────────────────────
def percentile_of(value: float, hist: list[float]) -> float | None:
    """value 在 hist 中的百分位（0~100）。hist 为历史序列（不含当日亦可）。"""
    if not hist:
        return None
    below = sum(1 for v in hist if v <= value)
    return round(below / len(hist) * 100.0, 1)


def _breadth_series_points(path: Path, keys: tuple[str, ...]) -> list[dict]:
    if not path.exists():
        return []
    try:
        hist = json.loads(path.read_text(encoding="utf-8"))
        return hist if isinstance(hist, list) else []
    except Exception:  # noqa: BLE001
        return []


def detect_breadth_anomalies(
    a_hist: list[dict], us_hist: list[dict]
) -> tuple[list[dict], list[dict]]:
    """返回 (异常清单, 常驻背景行)。异常 = 近 250 日分位 ≥90 或 ≤10。

    只做统计描述，不给方向判断（环境层不硬挡单标的，Round 4 原则）。
    """
    anomalies: list[dict] = []
    context: list[dict] = []
    for market, hist, fields in (
        ("A股", a_hist, (("b20", "ma20_pct"), ("b50", "ma50_pct"), ("b200", "ma200_pct"))),
        ("美股", us_hist, (("b20", "breadth_20"), ("b50", "breadth_50"), ("b200", "breadth_200"))),
    ):
        if len(hist) < 2:
            continue
        for label, field in fields:
            raw = [p.get(field) for p in hist[:-1][-BREADTH_PCT_WINDOW:]]
            vals: list[float] = [v for v in raw if v is not None]
            last, prev = hist[-1].get(field), hist[-2].get(field)
            if last is None or not vals:
                continue
            pct = percentile_of(last, vals)
            chg = None if prev is None else round(last - prev, 1)
            context.append(
                {
                    "market": market,
                    "metric": label,
                    "date": hist[-1].get("date"),
                    "value": round(last, 1),
                    "day_change": chg,
                    "pctile_250d": pct,
                }
            )
            if pct is not None and (pct >= BREADTH_EXTREME or pct <= 100 - BREADTH_EXTREME):
                anomalies.append(
                    {
                        "market": market,
                        "metric": label,
                        "value": round(last, 1),
                        "pctile_250d": pct,
                        "day_change": chg,
                        "note_cn": (
                            f"{market}宽度 {label} 报 {last:.0f}%，处于近一年 "
                            f"{pct:.0f}% 分位（{'高位' if pct >= BREADTH_EXTREME else '低位'}）"
                        ),
                    }
                )
    return anomalies, context


# ── ② 自选 · 状态抽取与 diff（纯函数）───────────────────────────────────────
def _color_cn(color: object) -> str | None:
    v = getattr(color, "value", color)
    return COLOR_CN.get(v) if isinstance(v, str) else None


def _rule_names(rule_ids: set[str]) -> str:
    """规则 ID →「、」连接的中文名（账本未登记的保留原 ID，不冒充翻译）。"""
    return "、".join(sorted(RULE_CN.get(r, r) for r in rule_ids))


def extract_symbol_state(assessment) -> dict:
    """从 analyze 判定结果抽确定性状态（只取规则引擎输出，不新增判断）。"""
    sup = getattr(assessment, "supports", []) or []
    con = getattr(assessment, "conflicts", []) or []
    stage = getattr(getattr(assessment, "stage", None), "value", None)
    risk_state = getattr(getattr(assessment, "risk_state", None), "value", None)
    return {
        "color": getattr(getattr(assessment, "color", None), "value", None),
        "color_cn": _color_cn(getattr(assessment, "color", None)),
        "stage_cn": STAGE_CN.get(stage, stage),
        "risk_state_cn": RISK_STATE_CN.get(risk_state, risk_state),
        "dimensions": dict(getattr(assessment, "dimensions", {}) or {}),
        "support_rules": sorted({f.rule_id for f in sup if getattr(f, "rule_id", None)}),
        "conflict_rules": sorted({f.rule_id for f in con if getattr(f, "rule_id", None)}),
        "new_event_count": len(getattr(assessment, "new_events", []) or []),
    }


def diff_symbol_state(prev: dict | None, curr: dict) -> dict:
    """与基线对比：色变 > 维度翻转 > 条件增删。返回变化描述（无可考字段为空）。"""
    changes: list[str] = []
    if prev is None:
        return {"is_new": True, "changes": ["首次纳入简报（无基线）"], "n_changes": 1}
    if prev.get("color") != curr.get("color"):
        changes.append(
            f"趋势颜色变化：{prev.get('color_cn') or prev.get('color')} → "
            f"{curr.get('color_cn') or curr.get('color')}"
        )
    for dim, val in curr.get("dimensions", {}).items():
        old = (prev.get("dimensions") or {}).get(dim)
        if old is not None and old != val:
            changes.append(f"维度翻转：{dim} {old} → {val}")
    add_s = set(curr["support_rules"]) - set(prev.get("support_rules") or [])
    rm_s = set(prev.get("support_rules") or []) - set(curr["support_rules"])
    add_c = set(curr["conflict_rules"]) - set(prev.get("conflict_rules") or [])
    rm_c = set(prev.get("conflict_rules") or []) - set(curr["conflict_rules"])
    if add_s:
        changes.append(f"新增支持条件：{_rule_names(add_s)}")
    if add_c:
        changes.append(f"新增冲突条件：{_rule_names(add_c)}")
    if rm_s:
        changes.append(f"支持条件消失：{_rule_names(rm_s)}")
    if rm_c:
        changes.append(f"冲突条件消除：{_rule_names(rm_c)}")
    if curr.get("new_event_count"):
        changes.append(f"当日新增标志性事件 {curr['new_event_count']} 条")
    return {"is_new": False, "changes": changes, "n_changes": len(changes)}


#: verdict 档位（继承机会扫描语义；不新造参数，只做展示排序）
_VERDICT_TIER = {"actionable": 0, "waiting": 1, "blocked": 2, "none": 3, "": 3}


def rank_watchlist_changes(items: list[dict]) -> list[dict]:
    """排序：verdict 档位 → 条件变化数 → 标的代码。稳定、确定性。"""
    return sorted(
        items,
        key=lambda it: (
            _VERDICT_TIER.get(it.get("verdict") or "", 3),
            -it.get("n_changes", 0),
            it.get("symbol", ""),
        ),
    )


# ── ③ 板块观察池（纯函数，基于 /sectors 快照）──────────────────────────────
def today_sector_pool(snapshot: dict | None) -> dict[str, dict]:
    """当日池成员：临近升级 / 资金印证(confirm) / 动能前五（顶层板块）。"""
    pool: dict[str, dict] = {}
    if not snapshot:
        return pool
    boards = [b for b in snapshot.get("boards", []) if b.get("parent") is None]

    def put(b: dict, tag: str) -> None:
        code = b.get("code")
        if not code:
            return
        entry = pool.setdefault(
            code,
            {
                "code": code,
                "name": b.get("name"),
                "stage": b.get("stage"),
                "rs_pctile": b.get("rs_pctile"),
                "rs_pctile_delta_20": b.get("rs_pctile_delta_20"),
                "pe_ttm": b.get("pe_ttm"),
                "flow_20d_main_yi": b.get("flow_20d_main_yi"),
                "flow_vs_stage_cn": b.get("flow_vs_stage_cn"),
                "next_watch": b.get("next_watch"),
                "tags": [],
            },
        )
        if tag not in entry["tags"]:
            entry["tags"].append(tag)

    def unmet(b: dict) -> int:
        return sum(1 for c in b.get("checkpoints") or [] if not c.get("met"))

    for b in boards:
        if b.get("stage") in ("accumulation", None) and unmet(b) <= 1:
            put(b, "临近升级")
        if b.get("flow_vs_stage") == "confirm":
            put(b, "资金印证")
    momentum = sorted(
        (b for b in boards if (b.get("rs_pctile_delta_20") or 0) > 0),
        key=lambda b: -(b.get("rs_pctile_delta_20") or 0),
    )[:5]
    for b in momentum:
        put(b, "动能前五")
    return pool


def pool_streaks(
    today_pool: dict[str, dict], recent_pools: list[dict]
) -> dict[str, int]:
    """连续在榜天数：逐日往回数，某日不在池即断（今日恒为 1）。

    ``recent_pools`` 按日期升序传入（缺失日不在其中，同样视为断档——保守口径）。
    """
    streaks: dict[str, int] = {}
    for code in today_pool:
        s = 1
        for prev in reversed(recent_pools):
            if code in set(prev.get("codes") or []):
                s += 1
            else:
                break
        streaks[code] = s
    return streaks


# ── 表达层：模板（确定性兜底）+ LLM（可选增强）─────────────────────────────
def render_template(payload: dict) -> str:
    """确定性模板版：LLM 不可用/不过校验时使用，信息密度优先。"""
    env = payload.get("env", {})
    lines: list[str] = []
    slot_cn = "盘中预判（未收盘）" if payload.get("slot") == SLOT_INTRADAY else "收盘复核版"
    lines.append(f"【LEI 收盘简报】{payload.get('date')} · {slot_cn}")
    lines.append("")
    lines.append("① 市场环境")
    anomalies = env.get("anomalies") or []
    if anomalies:
        for a in anomalies:
            line = f"  ⚠ {a['note_cn']}"
            if a.get("day_change") is not None:
                line += f"；较前日 {a['day_change']:+.1f} 个百分点"
            lines.append(line)
    else:
        lines.append("  环境无异常变动（宽度均在正常分位区间）")
    macro = env.get("macro") or {}
    if macro:
        lines.append(f"  背景：{macro.get('line_cn', '')}")
    lines.append("")
    lines.append("② 自选重点变化")
    wl = payload.get("watchlist", {})
    changed = [it for it in wl.get("items", []) if it.get("n_changes")]
    if changed:
        for it in changed:
            tier = it.get("verdict_cn") or it.get("verdict") or "-"
            lines.append(f"  [{tier}] {it.get('display_name') or it.get('symbol')}")
            for ch in it.get("changes", [])[:4]:
                lines.append(f"    · {ch}")
    n_unchanged = wl.get("unchanged_count", 0)
    if n_unchanged:
        lines.append(f"  其余 {n_unchanged} 项无变化")
    lines.append("")
    lines.append("③ 板块观察池（近几日持续上榜）")
    pool = payload.get("pool", {})
    if pool.get("items"):
        for it in pool["items"]:
            tags = "·".join(it.get("tags", []))
            pe = it.get("pe_ttm")
            pe_s = "亏" if pe is not None and pe < 0 else (f"{pe:.0f}" if pe is not None else "-")
            flow = it.get("flow_20d_main_yi")
            flow_s = f"{flow:+.0f}亿" if flow is not None else "-"
            head = f"  {it.get('name')}（连续{it.get('streak', 1)}天｜{tags}"
            lines.append(f"{head}｜强弱百分位 {it.get('rs_pctile') or '-'}｜市盈率 {pe_s}｜20日主力净流入 {flow_s}）")
            if it.get("next_watch"):
                lines.append(f"    ↳ {it['next_watch'].replace('SMA60', '60日线')}")
    else:
        lines.append("  当前无持续上榜板块")
    lines.append("")
    lines.append(f"④ {RESEARCH_NOTE}。完整细节见看板。")
    return "\n".join(lines)


def check_banned(text: str) -> bool:
    return any(w in text for w in _BANNED_WORDS)


DAILY_BRIEF_SYSTEM_PROMPT = """你是 LEI 交易系统的收盘简报表达层。
把给定 JSON（已由确定性 Python 层算好）组织成简洁高密度中文日报。

铁律（违反即丢弃）：
1. 只引用给定 JSON 的事实与数值，禁止外部信息与推算。
2. 禁用词：买入、卖出、建议买、该买、加仓、减仓、抄底。
3. 自选按 verdict 档位排序（actionable > waiting > blocked/none），不得跨档提权。
4. 固定三段：市场环境（只讲异常，无异常一句带过）→ 自选重点变化 → 板块观察池；每段不超 6 行。
5. 结尾固定一句「research_proxy 研究代理，非买卖建议」；slot=1445 时保留「预判（未收盘）」。
6. 面向普通用户写通俗中文：不出现 pct、verdict、RS、SMA 等英文缩写
   （百分比写「个百分点」，相对强度写「强弱百分位」，均线写「60日线」等）。
"""


def summarize_with_llm(payload: dict, config) -> str | None:
    """LLM 表达层调用（复用 plans.llm 的底层投递）。失败返回 None → 模板。"""
    from lei_signal.plans.llm import _post_user_content  # 项目内复用表达层投递

    content = (
        "以下是确定性构建层产出的简报数据（只许引用其中事实与数值）：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n\n请按系统指令输出三段式日报。"
    )
    try:
        out = _post_user_content(
            content, config,
            system_prompt=DAILY_BRIEF_SYSTEM_PROMPT, thinking_budget=1024,
        )
    except Exception as exc:  # noqa: BLE001 - LLM 失败一律走模板
        logger.warning("简报 LLM 调用失败（走模板）: %s", exc)
        return None
    if not out or check_banned(out):
        logger.warning("简报 LLM 输出为空或含禁用词（走模板）")
        return None
    return out
