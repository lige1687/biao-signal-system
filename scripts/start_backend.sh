#!/usr/bin/env bash
# 看板后端自启封装：优先用 WorkBuddy 管理的 venv(已含 fastapi/uvicorn/pandas/akshare)，
# 找不到则回退系统 python3。launchd 用 exec 直接托管 uvicorn 进程，便于 KeepAlive 重启。
set -euo pipefail
PROJ="/Users/yongbiaoli/Desktop/lei-signal-lab"
VENV_PY="$HOME/.workbuddy/binaries/python/envs/default/bin/python3"
if [ -x "$VENV_PY" ]; then PY="$VENV_PY"; else PY="$(command -v python3)"; fi
cd "$PROJ"
exec env PYTHONPATH="$PROJ/src" "$PY" -m uvicorn lei_signal.api.app:app --host 127.0.0.1 --port 8000
