"""策略与因子五态生命周期注册表与程序化准入门禁（lifecycle）。

状态流转：
  EXPLORE -> CANDIDATE -> SHADOW -> LIVE -> DEGRADED / RETIRED

强制制度红线：
1. 任何未经 L1/L2/L3 与无未来函数验漏的想法不得晋级 CANDIDATE；
2. 任何策略严禁绕过 SHADOW（前向真实新行情观察对账）直接升为 LIVE 生产规则；
3. 当 ForwardTracker 报出负漂移预警时，LIVE 策略可自动降级为 DEGRADED 并记录原因。
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal


LifecycleState = Literal["EXPLORE", "CANDIDATE", "SHADOW", "LIVE", "DEGRADED", "RETIRED"]
DEFAULT_REGISTRY_RELATIVE = Path("docs/research/strategy-lab-registry.v1.json")


class LifecycleRegistry:
    def __init__(self, repo_root: Path | None = None, path: Path | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
        self.path = Path(path) if path else (self.repo_root / DEFAULT_REGISTRY_RELATIVE)

    def load(self) -> dict:
        if not self.path.exists():
            return {
                "schema": "strategy-lab-lifecycle/1.0",
                "states": ["EXPLORE", "CANDIDATE", "SHADOW", "LIVE", "DEGRADED", "RETIRED"],
                "entries": [],
            }
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict) -> None:
        data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def get(self, item_id: str) -> dict | None:
        for e in self.load().get("entries", []):
            if e.get("id") == item_id:
                return e
        return None

    def register_explore(
        self,
        *,
        item_id: str,
        name: str,
        kind: str,
        financial_hypothesis: str,
        simple_baseline: str,
        code_fingerprint: str = "",
    ) -> dict:
        """在 EXPLORE 阶段登记新候选（开题必须先写清金融假说与简单对手）。"""
        if not financial_hypothesis.strip() or not simple_baseline.strip():
            raise ValueError("开题必须同时填写金融假说（financial_hypothesis）与简单对照对手（simple_baseline）")
        data = self.load()
        entries = list(data.get("entries", []))
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        existing = next((i for i, e in enumerate(entries) if e.get("id") == item_id), None)
        rec = {
            "id": item_id,
            "name": name,
            "kind": kind,
            "state": "EXPLORE",
            "financial_hypothesis": financial_hypothesis,
            "simple_baseline": simple_baseline,
            "code_fingerprint": code_fingerprint,
            "explore_evidence": {},
            "shadow_evidence": {"matured_obs": 0, "drift_status": "not_started"},
            "history": [{"at": now_str, "from": None, "to": "EXPLORE", "reason": "新研究立项"}],
        }
        if existing is not None:
            rec["history"] = list(entries[existing].get("history", [])) + [
                {"at": now_str, "from": entries[existing].get("state"), "to": "EXPLORE", "reason": "重新修订立项"}
            ]
            entries[existing] = rec
        else:
            entries.append(rec)
        data["entries"] = entries
        self.save(data)
        return rec

    def _update_entry(self, item_id: str, updater) -> dict:
        data = self.load()
        entries = list(data.get("entries", []))
        idx = next((i for i, e in enumerate(entries) if e.get("id") == item_id), None)
        if idx is None:
            raise KeyError(f"未登记的策略/因子ID: {item_id}")
        updated = updater(dict(entries[idx]))
        entries[idx] = updated
        data["entries"] = entries
        self.save(data)
        return updated

    def promote_to_candidate(
        self,
        item_id: str,
        *,
        no_lookahead_passed: bool,
        beats_simple_baseline: bool,
        plateau_pass_rate: float,
        evidence_summary: dict,
        reason: str,
    ) -> dict:
        """门禁 1：EXPLORE -> CANDIDATE（必须通过防未来函数、跑赢简单对手且参数非尖峰）。"""
        if not no_lookahead_passed:
            raise ValueError("准入拦截：未通过无未来函数前缀不变性检查，禁止晋级 CANDIDATE")
        if not beats_simple_baseline:
            raise ValueError("准入拦截：未相对简单对手产生有效净收益或风控增量，禁止晋级 CANDIDATE")
        if plateau_pass_rate < 0.60:
            raise ValueError(f"准入拦截：参数高原通过率仅 {plateau_pass_rate:.0%} (<60%)，存在过拟合尖峰风险")

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        def _apply(e: dict) -> dict:
            prev = e.get("state")
            if prev not in ("EXPLORE", "DEGRADED"):
                raise ValueError(f"非法状态流转：{prev} -> CANDIDATE")
            e["state"] = "CANDIDATE"
            e["explore_evidence"] = {
                **evidence_summary,
                "no_lookahead": True,
                "beats_simple_baseline": True,
                "plateau_pass_rate": round(float(plateau_pass_rate), 3),
            }
            e.setdefault("history", []).append({"at": now_str, "from": prev, "to": "CANDIDATE", "reason": reason})
            return e

        return self._update_entry(item_id, _apply)

    def promote_to_shadow(
        self,
        item_id: str,
        *,
        code_fingerprint: str,
        reason: str,
    ) -> dict:
        """门禁 2：CANDIDATE -> SHADOW（冻结代码指纹进入前向真实新行情观察期）。"""
        if not code_fingerprint.strip():
            raise ValueError("进入 SHADOW 必须绑定代码指纹")
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        def _apply(e: dict) -> dict:
            prev = e.get("state")
            if prev != "CANDIDATE":
                raise ValueError(f"必须先通过 CANDIDATE 门禁才能进入 SHADOW（当前: {prev}）")
            e["state"] = "SHADOW"
            e["code_fingerprint"] = code_fingerprint
            e["shadow_evidence"] = {"started_at": now_str, "matured_obs": 0, "drift_status": "accumulating"}
            e.setdefault("history", []).append({"at": now_str, "from": prev, "to": "SHADOW", "reason": reason})
            return e

        return self._update_entry(item_id, _apply)

    def promote_to_live(
        self,
        item_id: str,
        *,
        matured_shadow_obs: int,
        drift_ok: bool,
        min_required_obs: int = 15,
        reason: str,
    ) -> dict:
        """门禁 3：SHADOW -> LIVE（严禁绕过前向观察直接上线；需满样本且无负漂移预警）。"""
        if matured_shadow_obs < min_required_obs:
            raise ValueError(f"前向观察未满最低到期样本（当前 {matured_shadow_obs} < {min_required_obs}），禁止直通 LIVE")
        if not drift_ok:
            raise ValueError("前向观察存在负漂移预警，禁止晋级 LIVE")
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        def _apply(e: dict) -> dict:
            prev = e.get("state")
            if prev != "SHADOW":
                raise ValueError(f"严禁绕过 SHADOW 直通 LIVE（当前状态: {prev}）")
            e["state"] = "LIVE"
            e["shadow_evidence"] = {
                **e.get("shadow_evidence", {}),
                "matured_obs": int(matured_shadow_obs),
                "drift_status": "normal",
                "promoted_at": now_str,
            }
            e.setdefault("history", []).append({"at": now_str, "from": prev, "to": "LIVE", "reason": reason})
            return e

        return self._update_entry(item_id, _apply)

    def mark_degraded(self, item_id: str, *, reason: str, retire: bool = False) -> dict:
        """漂移触发降级或退役（LIVE/SHADOW -> DEGRADED 或 RETIRED）。"""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        target: LifecycleState = "RETIRED" if retire else "DEGRADED"

        def _apply(e: dict) -> dict:
            prev = e.get("state")
            e["state"] = target
            e.setdefault("history", []).append({"at": now_str, "from": prev, "to": target, "reason": reason})
            return e

        return self._update_entry(item_id, _apply)
