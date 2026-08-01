"""规则账本加载器：所有阈值来自 configs/rules.v1.yaml，代码中不写死。"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

from lei_signal.domain.types import Provenance

_CONFIG_NAME = "rules.v1.yaml"


def _default_config_path() -> Path:
    # src/lei_signal/domain/rules_config.py -> 上溯三层到项目根
    root = Path(__file__).resolve().parents[3]
    return root / "configs" / _CONFIG_NAME


@functools.lru_cache(maxsize=4)
def load_ruleset(path: str | None = None) -> dict[str, Any]:
    """加载并缓存规则账本。"""
    config_path = Path(path) if path else _default_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"规则账本缺失: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict) or "rules" not in data:
        raise ValueError(f"规则账本格式错误: {config_path}")
    return data


class RuleSpec:
    """单条规则的来源、版本与参数。"""

    __slots__ = ("_spec", "rule_id")

    def __init__(self, rule_id: str, spec: dict[str, Any]) -> None:
        self.rule_id = rule_id
        self._spec = spec

    @property
    def version(self) -> str:
        return str(self._spec.get("version", "0.0.0"))

    @property
    def provenance(self) -> Provenance:
        return Provenance(str(self._spec.get("provenance", "research_proxy")))

    @property
    def note_cn(self) -> str:
        return str(self._spec.get("note_cn", ""))

    @property
    def formula(self) -> str:
        return str(self._spec.get("formula", "")).strip()

    def param(self, name: str, default: Any = None) -> Any:
        params = self._spec.get("params") or {}
        return params.get(name, default)

    @property
    def is_research_proxy(self) -> bool:
        return self.provenance is Provenance.RESEARCH_PROXY


def get_rule(rule_id: str, path: str | None = None) -> RuleSpec:
    """按 rule_id 取规则规格。缺失即报错，不静默使用默认值。"""
    ruleset = load_ruleset(path)
    spec = ruleset["rules"].get(rule_id)
    if spec is None:
        raise KeyError(f"规则账本中没有登记 rule_id={rule_id}")
    return RuleSpec(rule_id, spec)


def ruleset_version(path: str | None = None) -> str:
    return str(load_ruleset(path).get("ruleset_version", "0.0.0"))


def indicator_config(path: str | None = None) -> dict[str, Any]:
    return dict(load_ruleset(path).get("indicators") or {})


def risk_priority(path: str | None = None) -> list[str]:
    return list(load_ruleset(path).get("risk_priority") or [])


def state_machine_config(path: str | None = None) -> dict[str, Any]:
    return dict(load_ruleset(path).get("state_machine") or {})


__all__ = [
    "RuleSpec",
    "get_rule",
    "indicator_config",
    "load_ruleset",
    "risk_priority",
    "ruleset_version",
    "state_machine_config",
]
