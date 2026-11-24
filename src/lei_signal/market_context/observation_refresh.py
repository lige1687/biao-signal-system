"""Append verified completed-market observations on a restart-safe daily clock."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from lei_signal.api.config import cache_root
from lei_signal.fundamentals.erp_refresh import ROOT, _atomic, refresh_cn_erp, refresh_us_erp
from lei_signal.market_context.us_breadth_refresh import closed_date, install_candidate, prepare

SHANGHAI = ZoneInfo("Asia/Shanghai")
SCOPES = ("erp-cn", "erp-us", "breadth-cn", "breadth-us", "funding-cn")


def completed_cutoffs(now: datetime) -> dict[str, str]:
    cn = now.astimezone(SHANGHAI)
    day = cn.date() if cn.hour >= 16 else cn.date() - timedelta(days=1)
    us = datetime.fromisoformat(closed_date(now)).date()
    while day.weekday() > 4:
        day -= timedelta(days=1)
    while us.weekday() > 4:
        us -= timedelta(days=1)
    return {"cn": day.isoformat(), "us": us.isoformat()}


def is_due(scope: str, record: dict, cutoff: str, now: datetime) -> bool:
    if record.get("as_of", "") >= cutoff:
        return False
    checked = record.get("checked_at")
    if not checked:
        return True
    age = (now - datetime.fromisoformat(checked)).total_seconds()
    # Source publication may lag its market. Retry later without an unbounded
    # loop, while allowing a new completed date to supersede yesterday's check.
    return record.get("cutoff") != cutoff or age >= 4 * 3600


def _scope_cutoff(scope: str, cutoff: dict[str, str], now: datetime) -> str:
    if scope == "breadth-cn":
        from lei_signal.market_context.cn_breadth_refresh import closed_cutoff as cn_breadth_cutoff

        return min(cutoff["cn"], cn_breadth_cutoff(now))
    return cutoff[scope[-2:]]


def _install_cn(output: Path, cache: Path) -> dict:
    receipt = json.loads((output / "receipt.json").read_text())
    if receipt.get("status") not in ("ready", "partial") or receipt.get("errors"):
        errs = "; ".join(str(e) for e in (receipt.get("errors") or []))
        raise ValueError(f"CN candidate is not qualified ({receipt.get('status')}): {errs}")
    cand_path = output / "candidate-history.json"
    if not cand_path.is_file():
        raise ValueError("CN candidate-history.json missing despite non-failed receipt")
    candidate = cand_path.read_bytes()
    target = cache / "a_share_ma_breadth_history.json"
    before = target.read_bytes()
    old, new = json.loads(before), json.loads(candidate)
    if hashlib.sha256(candidate).hexdigest() != receipt.get("candidate_sha256"):
        raise ValueError("CN candidate SHA differs from source receipt")
    if [row["date"] for row in new[len(old) :]] != receipt.get("new_dates"):
        raise ValueError("CN candidate dates differ from qualified dates")
    if any(
        receipt.get("daily_audit", {}).get(day, {}).get("unresolved", {"missing": True})
        for day in receipt.get("new_dates", [])
    ):
        raise ValueError("CN candidate contains unresolved stock sessions")
    if hashlib.sha256(before).hexdigest() != receipt["old_history_sha256"]:
        raise ValueError("CN live history changed during collection")
    if new[: len(old)] != old or len(new) <= len(old):
        raise ValueError("CN candidate did not preserve every old observation")
    if [p["date"] for p in new] != sorted({p["date"] for p in new}):
        raise ValueError("CN history contains duplicate or unordered dates")
    if any(
        any(
            not isinstance(row.get(f"ma{n}_pct"), (int, float)) or not 0 <= row[f"ma{n}_pct"] <= 100
            for n in (20, 50, 200)
        )
        for row in new[len(old) :]
    ):
        raise ValueError("CN candidate has invalid breadth values")
    _atomic(target, candidate)
    result = {
        "as_of": new[-1]["date"],
        "added_sessions": len(new) - len(old),
        "sha256": hashlib.sha256(candidate).hexdigest(),
        "target": str(target),
    }
    (output / "installation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def run(
    *, scopes: tuple[str, ...] = SCOPES, force: bool = False, now: datetime | None = None
) -> dict:
    from lei_signal.research.output_storage import OutputStorageError, plan_output

    cache = Path(cache_root())
    cache.mkdir(parents=True, exist_ok=True)
    with (cache / "market_observation_refresh.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "already_running"}
        now = now or datetime.now(UTC)
        cutoff = completed_cutoffs(now)
        state_path = cache / "market_observation_refresh_status.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        # Read installed files, rather than trusting a prior process's status.
        # This also avoids a second whole-universe collection after manual repair.
        for scope, filename in (
            ("breadth-cn", "a_share_ma_breadth_history.json"),
            ("breadth-us", "sp500_ma_breadth_history.json"),
        ):
            path = cache / filename
            if path.exists():
                rows = json.loads(path.read_text())
                if rows:
                    state[scope] = {**state.get(scope, {}), "as_of": rows[-1]["date"]}
        funding_path = cache / "cn_funding_live.json"
        if funding_path.exists():
            try:
                pkt = json.loads(funding_path.read_text(encoding="utf-8"))
                pts = [
                    p["date"]
                    for p in ((pkt.get("cards") or [{}])[0].get("points") or [])
                    if p.get("value") is not None and p.get("date")
                ]
                if pts:
                    state["funding-cn"] = {**state.get("funding-cn", {}), "as_of": pts[-1]}
            except Exception:  # noqa: BLE001
                pass
        due = [
            s
            for s in scopes
            if force or is_due(s, state.get(s, {}), _scope_cutoff(s, cutoff, now), now)
        ]
        if not due:
            temporary = state_path.with_suffix(".pending")
            temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            os.replace(temporary, state_path)
            return {"status": "up_to_date", "scopes": state}
        try:
            plan = plan_output(
                ROOT, "breadth-reading-aid-20261101", 250 * 1024**2, internal_bytes=2 * 1024**2
            )
            output = Path(plan["output"])
            if Path(plan["external_mount"]).stat().st_dev != plan["external_device"]:
                raise RuntimeError("external output device changed")
            output.mkdir(parents=True, exist_ok=False)
            (output.parent / "storage-plan.json").write_text(
                json.dumps(plan, ensure_ascii=False, indent=2)
            )
        except OutputStorageError:
            import shutil

            work_root = cache / "observation_work"
            work_root.mkdir(parents=True, exist_ok=True)
            old_runs = sorted(p for p in work_root.glob("run-*") if p.is_dir())
            for stale_dir in old_runs[:-2]:
                shutil.rmtree(stale_dir, ignore_errors=True)
            stamp = now.strftime("%Y%m%dT%H%M%SZ")
            output = work_root / f"run-{stamp}-{os.getpid()}" / "result"
            output.mkdir(parents=True, exist_ok=True)
        for scope in due:
            sub = output / scope
            record = {
                **state.get(scope, {}),
                "cutoff": _scope_cutoff(scope, cutoff, now),
                "checked_at": datetime.now(UTC).isoformat(),
                "output": str(sub),
            }
            try:
                if scope == "erp-cn":
                    result = refresh_cn_erp(sub, cutoff=record["cutoff"], cache=cache)
                elif scope == "erp-us":
                    result = refresh_us_erp(sub, cutoff=record["cutoff"], cache=cache)
                elif scope == "breadth-us":
                    receipt = prepare(sub)
                    if receipt.get("no_new_sessions"):
                        record.pop("error", None)
                        record.update(as_of=receipt["last_date"], status="no_new_sessions")
                        state[scope] = record
                        temporary = state_path.with_suffix(".pending")
                        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
                        os.replace(temporary, state_path)
                        continue
                    if not receipt.get("qualified"):
                        raise ValueError(receipt.get("error", "US breadth qualification failed"))
                    result = install_candidate(sub, cache / "sp500_ma_breadth_history.json")
                    result["as_of"] = result["last_date"]
                    (sub / "installation.json").write_text(json.dumps(result, indent=2))
                elif scope == "funding-cn":
                    from lei_signal.market_context.cn_funding_refresh import refresh_cn_funding

                    result = refresh_cn_funding(sub, cutoff=record["cutoff"], cache=cache)
                else:
                    from lei_signal.market_context.cn_breadth_refresh import refresh

                    cn_receipt = refresh(sub, cache=cache, cutoff=record["cutoff"])
                    if cn_receipt.get("status") == "no_new_sessions":
                        record.pop("error", None)
                        record.update(
                            as_of=cn_receipt.get("last_date", record.get("as_of")),
                            status="no_new_sessions",
                        )
                        state[scope] = record
                        temporary = state_path.with_suffix(".pending")
                        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
                        os.replace(temporary, state_path)
                        continue
                    result = _install_cn(sub, cache)
                record.pop("error", None)
                record.update(result, status="updated")
            except Exception as exc:
                record.update(
                    status="retry_pending", error=f"{type(exc).__name__}: {str(exc)[:350]}"
                )
            state[scope] = record
            # Small operational state, not a research input or a user alert.
            temporary = state_path.with_suffix(".pending")
            temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            os.replace(temporary, state_path)
            print(json.dumps({"scope": scope, **record}, ensure_ascii=False), flush=True)
        return {"status": "checked", "scopes": state}
