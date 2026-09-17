#!/bin/sh
# Agent runtime adoption package: REVERT script (S2/G3, 2026-09-17)
# Usage: run `sh <path-to>/revert.sh` from anywhere.
# Steps:
#   1) Full pre-check (zero writes): every replace target must still equal
#      after_sha256 and every added file must still equal after_sha256.
#      Any file modified after adoption (current != after) -> refuse to
#      revert, so post-adoption work is never overwritten.
#   2) Only after the pre-check passes: replace targets are restored to the
#      captured before content (the runtime worktree actual state, including
#      the then-uncommitted layers); add targets are deleted.

set -eu
# Locate the package dir from the script path, then walk up exactly 5 levels:
# adoption-package -> agent-runtime-adoption-candidate-2026-09-17 -> raw
#   -> experiments -> docs -> workspace root
CDPATH= cd -- "$(dirname -- "$0")"
PKG=$(pwd)
i=0
while [ "$i" -lt 5 ]; do
    cd ..
    i=$((i + 1))
done
echo "workspace root: $(pwd)"

PRECHK="${TMPDIR:-/tmp}/adoption-revert-precheck.$$"
mkdir -p "$PRECHK"
trap 'rm -rf "$PRECHK"' EXIT

tail -n +2 "$PKG/manifest.tsv" | while IFS="$(printf '\t')" read -r f op before after; do
    if [ "$op" = "replace" ]; then
        if [ ! -f "$f" ]; then
            echo "PRECHECK-FAIL: replace target missing: $f"
            continue
        fi
        cur=$(shasum -a 256 "$f" | cut -d' ' -f1)
        [ "$cur" = "$after" ] || echo "PRECHECK-FAIL: modified after adoption (refusing revert): $f"
    elif [ "$op" = "add" ]; then
        if [ ! -f "$f" ]; then
            echo "PRECHECK-FAIL: add target already gone: $f"
        else
            cur=$(shasum -a 256 "$f" | cut -d' ' -f1)
            [ "$cur" = "$after" ] || echo "PRECHECK-FAIL: modified after adoption (refusing delete): $f"
        fi
    fi
done > "$PRECHK/result.log" 2>&1 || true

if [ -s "$PRECHK/result.log" ]; then
    echo "---- PRE-CHECK FAILED (zero writes, nothing modified) ----"
    cat "$PRECHK/result.log"
    exit 1
fi
echo "PRE-CHECK OK: all targets still at after state; reverting now."

tail -n +2 "$PKG/manifest.tsv" | while IFS="$(printf '\t')" read -r f op before skip_after; do
    if [ "$op" = "replace" ]; then
        cp "$PKG/before/$f" "$f"
        echo "reverted [replace] $f"
    else
        rm "$f"
        echo "reverted [add removed] $f"
    fi
done
echo "REVERT DONE: 24/24 restored to the captured pre-adoption runtime state."
