"""newsfeed 配置加载：仓库根 ``config/newsfeed.json``，缺文件/缺键用默认值兜底。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_PATH = _REPO_ROOT / "config" / "newsfeed.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "bili_ups": [],
    "rss_feeds": [],
    "gnews_queries": [],
    "symbols": [],
    "flash_keywords": {
        "macro": ["央行", "美联储", "LPR", "CPI", "PPI", "PMI", "GDP", "国债", "美债", "非农", "议息"],
        "risk": ["风险", "危机", "违约", "制裁", "地缘", "冲突", "流动性", "债务上限", "关税"],
        "policy": ["政策", "国务院", "证监会", "发改委", "财政部", "规划", "补贴", "监管"],
        "industry": ["财报", "业绩", "营收", "净利润", "产能", "涨价", "订单"],
    },
    "lookback_days": 3,
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """读配置并补默认键。文件损坏不炸：日志告警 + 全默认值（管线可空跑）。"""
    cfg_path = Path(path) if path else _CONFIG_PATH
    cfg: dict[str, Any] = {}
    if cfg_path.is_file():
        try:
            loaded = json.loads(cfg_path.read_text("utf-8"))
            if isinstance(loaded, dict):
                cfg = loaded
            else:
                logger.warning("newsfeed 配置 %s 顶层不是对象，用默认值", cfg_path)
        except (ValueError, OSError) as exc:
            logger.warning("newsfeed 配置读取失败(%s): %s，用默认值", cfg_path, exc)
    merged = {**DEFAULT_CONFIG, **cfg}
    # flash_keywords 半深合并：文件里通常只给部分类别。
    kw = dict(DEFAULT_CONFIG["flash_keywords"])
    kw.update(merged.get("flash_keywords") or {})
    merged["flash_keywords"] = kw
    return merged


__all__ = ["DEFAULT_CONFIG", "load_config"]
