#!/usr/bin/env bash
# 简易情绪录入封装：每周花 1 分钟，把当周 NAAIM / AAII 读数写进 LEI_SENTIMENT_ROOT。
#
# 设计约束：lei-signal 禁止爬 AAII/NAAIM 网页，所以这是「离线手工录入」主路径，
# 数据质量最高、完全合规。官方文件（naaim.org 历史 xlsx / AAII 会员 CSV）可导出后
# 用 ingest_sentiment.py 的 from-naaim-xlsx / from-aaii-csv 转换。
#
# 前置（只需设一次，建议写进 ~/.zshrc）：
#   export LEI_SENTIMENT_ROOT=~/lei-sentiment-data
#   mkdir -p "$LEI_SENTIMENT_ROOT"
#
# 用法：
#   ./enter_sentiment.sh naaim <调查周 YYYY-MM-DD> <暴露指数>
#   ./enter_sentiment.sh aaii  <调查周 YYYY-MM-DD> <看多%> <中性%> <看空%>
#
# 例：
#   ./enter_sentiment.sh naaim 2026-08-10 72.5
#   ./enter_sentiment.sh aaii  2026-08-10 35 28 37
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/round5_repro/ingest_sentiment.py"
PY="${PYTHON:-python3}"

if [ "$#" -lt 3 ]; then
  echo "用法:" >&2
  echo "  $0 naaim <调查周 YYYY-MM-DD> <暴露指数>" >&2
  echo "  $0 aaii  <调查周 YYYY-MM-DD> <看多%> <中性%> <看空%>" >&2
  exit 1
fi

series="$1"; shift
case "$series" in
  naaim)
    survey="$1"; exposure="$2"
    "$PY" "$SCRIPT" append --series naaim --survey-week "$survey" --exposure "$exposure"
    ;;
  aaii)
    survey="$1"; bull="$2"; neutral="$3"; bear="$4"
    "$PY" "$SCRIPT" append --series aaii --survey-week "$survey" \
      --bullish "$bull" --neutral "$neutral" --bearish "$bear"
    ;;
  *)
    echo "未知 series: $series（用 naaim 或 aaii）" >&2
    exit 1
    ;;
esac
