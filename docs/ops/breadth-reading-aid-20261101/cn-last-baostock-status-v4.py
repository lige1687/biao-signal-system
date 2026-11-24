#!/usr/bin/env python3
"""Bounded BaoStock status probe for eight WeStock no-row symbols, 2026-10-26..30."""

import datetime as dt
import json
import os
import selectors
import signal
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEM = HERE / "cn-last-baostock-status-v4"
SYMBOLS = (
    "sh600621", "sh601326", "sh605258", "sh688121",
    "sh688496", "sz002717", "sz002827", "sz301468",
)
FIELDS = "date,code,close,volume,amount,tradestatus"
EVENT_PREFIX = "@@BAOSTOCK_PROBE@@"


def emit(event):
    print(EVENT_PREFIX + json.dumps(event, ensure_ascii=False), flush=True)


def worker():
    import baostock as bs

    socket.setdefaulttimeout(20)
    emit({"kind": "begin", "operation": "login"})
    try:
        login = bs.login()
        emit({"kind": "end", "operation": "login", "error_code": login.error_code,
              "error_msg": login.error_msg})
        if login.error_code != "0":
            return
        for symbol in SYMBOLS:
            code = symbol[:2] + "." + symbol[2:]
            emit({"kind": "begin", "operation": "query", "symbol": symbol})
            try:
                rs = bs.query_history_k_data_plus(
                    code, FIELDS, start_date="2026-10-26", end_date="2026-10-30",
                    frequency="d", adjustflag="3")
                rows = []
                if rs.error_code == "0":
                    while rs.next():
                        rows.append(rs.get_row_data())
                emit({"kind": "end", "operation": "query", "symbol": symbol,
                      "error_code": rs.error_code, "error_msg": rs.error_msg,
                      "fields": rs.fields, "rows": rows})
                if rs.error_code != "0":
                    return
            except Exception as exc:
                emit({"kind": "exception", "operation": "query", "symbol": symbol,
                      "exception_type": type(exc).__name__, "error": str(exc)})
                return
    except Exception as exc:
        emit({"kind": "exception", "operation": "login",
              "exception_type": type(exc).__name__, "error": str(exc)})
    finally:
        try:
            bs.logout()
        except Exception:
            pass


def main():
    # The supervising process imposes a separate wall-clock deadline on every SDK call.
    child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--worker"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             bufsize=1, start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ)
    events, extra_stdout = [], []
    pending = None
    timeout = None
    while True:
        ready = selector.select(timeout=25)
        if not ready:
            timeout = {"operation": pending, "seconds": 25}
            os.killpg(child.pid, signal.SIGKILL)
            break
        line = child.stdout.readline()
        if not line:
            break
        if line.startswith(EVENT_PREFIX):
            event = json.loads(line[len(EVENT_PREFIX):])
            events.append(event)
            if event["kind"] == "begin":
                pending = {k: event[k] for k in ("operation", "symbol") if k in event}
            else:
                pending = None
        else:
            extra_stdout.append(line.rstrip())
    _, stderr = child.communicate(timeout=5)
    # The qualification file is used only to identify the 33 requested pairs.
    q = json.loads((HERE / "qualify-cn-westock-v4.json").read_text())
    wanted = {(day, symbol) for day, info in q["unresolved_symbols_by_day"].items()
              if "2026-10-26" <= day <= "2026-10-30"
              for symbol in info.get("no_provider_row", []) if symbol in SYMBOLS}
    observed = {}
    for event in events:
        if event.get("kind") != "end" or event.get("operation") != "query":
            continue
        fields = event.get("fields", [])
        for row in event.get("rows", []):
            if len(row) == len(fields):
                data = dict(zip(fields, row))
                observed[(data["date"], event["symbol"])] = data
    classified = []
    for day, symbol in sorted(wanted):
        data = observed.get((day, symbol))
        status = "vendor_nontrading" if data and data.get("tradestatus") == "0" else "unknown"
        if data and data.get("tradestatus") == "1":
            status = "vendor_traded_conflict"
        classified.append({"date": day, "symbol": symbol, "classification": status,
                           "sdk_row": data})
    output = {"retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "source": "BaoStock Python SDK query_history_k_data_plus",
              "query": {"symbols": list(SYMBOLS), "start_date": "2026-10-26",
                        "end_date": "2026-10-30", "fields": FIELDS,
                        "frequency": "d", "adjustflag": "3"},
              "timeout": timeout, "worker_exit_code": child.returncode,
              "sdk_events": events, "sdk_stdout_other": extra_stdout,
              "sdk_stderr": stderr, "requested_missing_pairs": classified}
    (STEM.with_suffix(".json")).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    counts = {name: sum(x["classification"] == name for x in classified)
              for name in ("vendor_nontrading", "vendor_traded_conflict", "unknown")}
    lines = ["# BaoStock 定点交易状态核验", "", "仅查询 8 代码、2026-10-26 至 10-30；未拼接价格或修改正式缓存。",
             "", f"- SDK 请求：{sum(e.get('kind') == 'begin' and e.get('operation') == 'query' for e in events)} 次；登录 1 次。",
             f"- 33 个目标缺行：BaoStock 非交易 {counts['vendor_nontrading']}；有交易冲突 {counts['vendor_traded_conflict']}；未知 {counts['unknown']}。",
             f"- 超时：{timeout or '无'}；进程退出码：{child.returncode}。",
             "- `tradestatus=0` 仅作为 BaoStock 当日非交易状态证据，不自动解释停牌原因；无返回行仍为未知。", "",
             "| 日期 | 代码 | 状态 | BaoStock tradestatus |", "|---|---|---|---|"]
    lines += [f"| {x['date']} | {x['symbol']} | {x['classification']} | {(x['sdk_row'] or {}).get('tradestatus', '')} |" for x in classified]
    (STEM.with_suffix(".md")).write_text("\n".join(lines) + "\n")
    print(json.dumps({"counts": counts, "timeout": timeout, "worker_exit_code": child.returncode,
                      "json": str(STEM.with_suffix('.json'))}, ensure_ascii=False))


if __name__ == "__main__":
    worker() if sys.argv[1:] == ["--worker"] else main()
