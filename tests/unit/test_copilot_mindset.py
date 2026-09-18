"""认知/心态种子库加载器：校验/去重/降级 + 判定隔离红线双证。"""
from __future__ import annotations

import json

import pytest

from lei_signal.copilot import mindset as mm

#: 入仓种子文件的指纹（内容不改的锚点；变动须走规则账本流程）。
_EXPECTED_SHA256 = "4bff4b76c120b2ac429e479752606390402b578d1bb248a533def927151b03e4"


def _write_seed(tmp_path, items, comment=None):
    payload = {"items": items}
    if comment:
        payload["_comment"] = comment
    p = tmp_path / "mindset_seed.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


def _item(**over):
    base = {
        "category": "认知",
        "text": "先想亏到哪儿，再想赚多少。",
        "quote": "先想亏损的底。",
        "source": "测试来源 2026-09-19",
    }
    base.update(over)
    return base


def test_load_real_seed_file():
    pack = mm.load_mindset_seeds()
    assert pack["available"] is True
    assert pack["count"] == 26
    assert pack["sha256"] == _EXPECTED_SHA256
    assert pack["duplicates"] == 0
    for it in pack["items"]:
        assert set(it) == {"category", "text", "quote", "source", "seed_key"}
        assert all(it[f].strip() for f in ("category", "text", "source"))
        assert isinstance(it["quote"], str)  # quote 可选，缺失归一为空串


def test_seed_key_documented_dedup(tmp_path):
    # 自拟去重键 = sha256(category+\x00+text) 前 16 位：同类别同正文只留一条
    p = _write_seed(tmp_path, [_item(), _item(), _item(text="另一条正文")])
    pack = mm.load_mindset_seeds(p)
    assert pack["available"] is True
    assert pack["count"] == 2
    assert pack["duplicates"] == 1
    keys = [it["seed_key"] for it in pack["items"]]
    assert len(set(keys)) == 2


def test_invalid_entries_dropped(tmp_path):
    p = _write_seed(
        tmp_path,
        [
            _item(),
            {"category": "认知", "text": "缺 source"},  # 必需字段缺一
            {"category": "", "text": "x", "quote": "q", "source": "s"},  # 空串
            "不是对象",
        ],
    )
    pack = mm.load_mindset_seeds(p)
    assert pack["available"] is True
    assert pack["count"] == 1
    assert pack["dropped"] == 3


def test_quote_optional_normalised(tmp_path):
    # quote 可选：缺失/非字符串归一为空串，条目仍有效（实测 26 条仅 3 条带 quote）
    p = _write_seed(tmp_path, [_item(), _item(quote=None), _item(quote=123)])
    pack = mm.load_mindset_seeds(p)
    assert pack["count"] == 1  # 三条同键去重后剩一条（quote 不进键）
    assert pack["items"][0]["quote"] == "先想亏损的底。"


def test_missing_file_degrades(tmp_path):
    pack = mm.load_mindset_seeds(tmp_path / "nope.json")
    assert pack["available"] is False
    assert "seed_file_missing_or_corrupt" in pack["reason"]
    assert pack["items"] == []
    assert mm.seeds_available(tmp_path / "nope.json") is False


def test_corrupt_file_degrades(tmp_path):
    p = tmp_path / "mindset_seed.json"
    p.write_text("{broken json", encoding="utf-8")
    pack = mm.load_mindset_seeds(p)
    assert pack["available"] is False
    assert "seed_file_missing_or_corrupt" in pack["reason"]


def test_bad_structure_degrades(tmp_path):
    p = tmp_path / "mindset_seed.json"
    p.write_text(json.dumps({"no_items": 1}), encoding="utf-8")
    pack = mm.load_mindset_seeds(p)
    assert pack["available"] is False
    assert pack["reason"] == "seed_file_bad_structure"


def test_no_valid_items_degrades(tmp_path):
    p = _write_seed(tmp_path, [{"category": "认知"}])
    pack = mm.load_mindset_seeds(p)
    assert pack["available"] is False
    assert pack["reason"] == "seed_file_no_valid_items"


def test_seed_content_isolated_from_decision_paths():
    """红线双证之一（代码路径）：判定/评分/过滤/排序核心模块零 mindset 引用。

    逐个扫描判定层模块源码，确认没有 import 或符号引用种子库；种子只被
    copilot 叙事卡与 agent 话题块消费。
    """
    from pathlib import Path

    decision_modules = [
        "research_proxy", "recommend", "resolve", "sizing", "fit",
        "winrate", "breadth", "scout", "review", "sentiment",
    ]
    src = Path(mm.__file__).resolve().parents[1]
    for mod in decision_modules:
        f = src / f"{mod}.py"
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        assert "mindset" not in text.lower(), f"{mod}.py 引用了 mindset"
