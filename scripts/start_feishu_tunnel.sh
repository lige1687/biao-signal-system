#!/usr/bin/env bash
# 起 LEI 飞书回执隧道（本地 API + Cloudflare 临时隧道），并把公网域名自动写进 .env。
#
# 用法：
#   bash scripts/start_feishu_tunnel.sh
# 前台运行，Ctrl-C 停止（会自动杀掉后台 uvicorn）。
#
# 说明：
#   - 临时隧道每次重启域名都会变，脚本会自动更新 .env 的 FEISHU_ACTION_BASE_URL。
#   - 起好后重跑一次 daily_nag 让卡片按钮指向新域名（或等下一个交易日 15:30 自动跑）。
#   - 要稳定域名需改用命名隧道（cloudflared login + 自有域名），本脚本用临时隧道即可验证闭环。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

# 1) 确保 cloudflared 已装
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "[*] 未检测到 cloudflared，执行 brew install cloudflared ..."
  brew install cloudflared
fi

# 2) 起本地 API（若 8000 还没在跑）
if ! curl -fsS -o /dev/null http://127.0.0.1:8000/api/health 2>/dev/null; then
  echo "[*] 启动 uvicorn (127.0.0.1:8000) ..."
  mkdir -p "$REPO/logs"
  PYTHONPATH=src /opt/homebrew/bin/python3 -m uvicorn lei_signal.api.app:app \
    --host 127.0.0.1 --port 8000 >> "$REPO/logs/api.log" 2>&1 &
  API_PID=$!
  cleanup() { kill "$API_PID" 2>/dev/null || true; }
  trap cleanup EXIT
  for _ in $(seq 1 30); do
    curl -fsS -o /dev/null http://127.0.0.1:8000/api/health 2>/dev/null && break
    sleep 1
  done
else
  echo "[*] uvicorn 已在 127.0.0.1:8000 运行，跳过启动"
fi

# 3) 起 Cloudflare 临时隧道（后台），抽取公网域名写 .env
echo "[*] 启动 Cloudflare Tunnel ..."
TUNNEL_LOG="$(mktemp)"
cloudflared tunnel --url http://127.0.0.1:8000 >> "$TUNNEL_LOG" 2>&1 &
TUN_PID=$!

URL=""
for _ in $(seq 1 40); do
  URL="$(grep -oE 'https://[A-Za-z0-9._-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -n1 || true)"
  [ -n "$URL" ] && break
  sleep 1
done

if [ -n "$URL" ]; then
  BASE="${URL%%/*}"
  if grep -q '^FEISHU_ACTION_BASE_URL=' "$REPO/.env"; then
    sed -i '' -E "s#^FEISHU_ACTION_BASE_URL=.*#FEISHU_ACTION_BASE_URL=$BASE#" "$REPO/.env"
  else
    printf 'FEISHU_ACTION_BASE_URL=%s\n' "$BASE" >> "$REPO/.env"
  fi
  echo ""
  echo "[✓] 隧道已就绪：$BASE"
  echo "[✓] 已写入 $REPO/.env -> FEISHU_ACTION_BASE_URL"
  echo "[!] 重跑一次回执按钮才会指向新域名："
  echo "    /opt/homebrew/bin/python3 scripts/daily_nag.py --notifier feishu"
else
  echo "[!] 未在日志中检测到隧道域名，查看：$TUNNEL_LOG"
fi

# 4) 前台保持隧道，Ctrl-C 退出（trap 会清理 uvicorn）
echo "[*] 隧道运行中（Ctrl-C 停止）..."
wait "$TUN_PID"
