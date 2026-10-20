#!/usr/bin/env bash
# 看板前端自启封装：直接调用 vite 二进制(等价于 npm run dev)，避免 npm 父进程干扰 KeepAlive。
# 优先用 WorkBuddy 管理的 node，找不到则回退系统 node。
set -euo pipefail
PROJ="/Users/yongbiaoli/Desktop/lei-signal-lab"
NODE="$HOME/.workbuddy/binaries/node/versions/22.22.2/bin/node"
[ -x "$NODE" ] || NODE="$(command -v node)"
cd "$PROJ/web"
exec "$NODE" "$PROJ/web/node_modules/.bin/vite"
