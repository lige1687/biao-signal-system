#!/bin/sh
# Agent runtime adoption package: APPLY script (S2/G3, 2026-09-17)
# Usage: run `sh <path-to>/apply.sh` from anywhere.
# Steps:
#   1) Full pre-check (zero writes): all 14 "replace" targets must match
#      before_sha256 byte-for-byte (captured from the live runtime worktree
#      on 2026-09-17 11:44, including then-uncommitted layers); all 10 "add"
#      targets must not exist. Any mismatch -> refuse, nothing is written.
#   2) Only after the pre-check passes: each target is written to a .tmp
#      file, content-verified, then atomically moved into place.
# If any target drifted (runtime moved on), this script refuses by design.
# Re-run the diff audit and build a new package; do not force-apply.

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

PRECHK="${TMPDIR:-/tmp}/adoption-apply-precheck.$$"
WRITEDIR="${TMPDIR:-/tmp}/adoption-apply-write.$$"
mkdir -p "$PRECHK" "$WRITEDIR"
trap 'rm -rf "$PRECHK" "$WRITEDIR"' EXIT

tail -n +2 "$PKG/manifest.tsv" | while IFS="$(printf '\t')" read -r f op before after; do
    if [ "$op" = "replace" ]; then
        if [ ! -f "$f" ]; then
            echo "PRECHECK-FAIL: replace target missing: $f"
            continue
        fi
        cur=$(shasum -a 256 "$f" | cut -d' ' -f1)
        if [ "$cur" != "$before" ]; then
            echo "PRECHECK-FAIL: target drifted (refusing): $f"
            echo "  expected before=$before"
            echo "  actual         =$cur"
            continue
        fi
    elif [ "$op" = "add" ]; then
        if [ -e "$f" ]; then
            echo "PRECHECK-FAIL: add target already exists (refusing): $f"
            continue
        fi
    fi
done > "$PRECHK/result.log" 2>&1 || true

if [ -s "$PRECHK/result.log" ]; then
    echo "---- PRE-CHECK FAILED (zero writes, nothing modified) ----"
    cat "$PRECHK/result.log"
    exit 1
fi
echo "PRE-CHECK OK: all 24 targets match the before baseline; writing now."

tail -n +2 "$PKG/manifest.tsv" | while IFS="$(printf '\t')" read -r f op skip_before after; do
    mkdir -p "$(dirname "$f")"
    if [ "$op" = "replace" ]; then
        cp "$f" "$WRITEDIR/backup_$(echo "$f" | tr '/' '_')"
    fi
    cp "$PKG/after/$f" "$f.tmp.adoption"
    got=$(shasum -a 256 "$f.tmp.adoption" | cut -d' ' -f1)
    if [ "$got" != "$after" ]; then
        echo "WRITE-FAIL: after content mismatch: $f (aborting)"
        rm -f "$f.tmp.adoption"
        exit 1
    fi
    mv "$f.tmp.adoption" "$f"
    echo "applied [$op] $f"
done
echo "APPLY DONE: 24/24. Run the affected regressions from the report before"
echo "putting this into use; rollback with revert.sh in the same directory."
