#!/bin/sh
# Agent runtime adoption package: REVERT script (S2 repair, 2026-09-17)
#
# Usage:
#   sh revert.sh --target /absolute/path/to/runtime-workspace-root
#
# The target is MANDATORY and must be an absolute path (same semantics as
# apply.sh). Package location and caller cwd never influence the target.
#
# Pre-checks (ALL must pass before the first write; any failure = zero writes):
#   1) manifest structure   : same checks as apply
#   2) package payloads     : before/ payloads must match before_sha256 (the
#                             revert input) AND after/ payloads must match
#                             after_sha256 (whole-package integrity)
#   3) required dependencies: same read-only fingerprints as apply — the
#                             baseline being restored to is designed against
#                             those exact dependency states
#   4) target state         : every replace target still equals after_sha256
#                             and every add file still equals after_sha256.
#                             Any file modified after adoption -> refuse, so
#                             post-adoption work is never overwritten.
#
# Restore materials: before reverting, every replace target's current content
# is backed up to KEEPDIR; on a mid-revert failure a restore-partial.sh that
# puts those files back (post-apply state) is generated and its path printed.

set -eu

usage() {
    echo "usage: sh revert.sh --target /absolute/path/to/runtime-workspace-root" >&2
    echo "  --target is required; the package will only touch that directory." >&2
    exit 1
}

TARGET=""
while [ $# -gt 0 ]; do
    case "$1" in
        --target)
            [ $# -ge 2 ] || usage
            TARGET="$2"; shift 2 ;;
        *) usage ;;
    esac
done
[ -n "$TARGET" ] || usage
case "$TARGET" in
    /*) ;;
    *) echo "REFUSED: --target must be an absolute path, got: $TARGET" >&2; exit 1 ;;
esac
if [ ! -d "$TARGET" ]; then
    echo "REFUSED: target is not an existing directory: $TARGET" >&2
    exit 1
fi
if [ ! -d "$TARGET/src/lei_signal" ] || [ ! -d "$TARGET/docs/experiments" ]; then
    echo "REFUSED: target does not look like a runtime workspace (missing src/lei_signal or docs/experiments): $TARGET" >&2
    exit 1
fi
echo "target (resolved): $TARGET"

PKG=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MANIFEST="$PKG/manifest.tsv"
DEPS="$PKG/dependencies.tsv"
RECOVERY_TOOL="$PKG/recovery.py"
[ -f "$MANIFEST" ] || { echo "REFUSED: manifest.tsv missing in package" >&2; exit 1; }
[ -f "$DEPS" ] || { echo "REFUSED: dependencies.tsv missing in package" >&2; exit 1; }
[ -f "$RECOVERY_TOOL" ] || { echo "REFUSED: recovery.py missing in package" >&2; exit 1; }

PRECHK="${TMPDIR:-/tmp}/adoption-revert-precheck.$$"
mkdir -p "$PRECHK"
KEEPDIR="${TMPDIR:-/tmp}/adoption-revert-keep-$(date +%Y%m%d%H%M%S)-$$"
mkdir -p "$KEEPDIR"
trap 'rm -rf "$PRECHK"' EXIT

# ---------- pre-check 1: manifest structure ----------
tail -n +2 "$MANIFEST" | while IFS="$(printf '\t')" read -r f op before after; do
    if [ -z "$f" ] || [ -z "$op" ] || [ -z "$before" ] || [ -z "$after" ]; then
        echo "STRUCT-FAIL: incomplete row: $f"
    fi
    case "$op" in
        replace|add) ;;
        *) echo "STRUCT-FAIL: unknown op: $op ($f)" ;;
    esac
done > "$PRECHK/struct.log" 2>&1 || true
rows=$(tail -n +2 "$MANIFEST" | wc -l | tr -d ' ')
[ "$rows" -eq 25 ] || echo "STRUCT-FAIL: expected 25 data rows, found $rows" >> "$PRECHK/struct.log"

# ---------- pre-check 2: package payloads (before/ is the revert input) ----------
tail -n +2 "$MANIFEST" | while IFS="$(printf '\t')" read -r f op before after; do
    bp="$PKG/before/$f"
    if [ "$op" = "replace" ]; then
        if [ ! -f "$bp" ]; then
            echo "PAYLOAD-FAIL: before payload missing: $f"
        else
            got=$(shasum -a 256 "$bp" | cut -d' ' -f1)
            [ "$got" = "$before" ] || echo "PAYLOAD-FAIL: before payload corrupt: $f (manifest=$before actual=$got)"
        fi
    fi
    ap="$PKG/after/$f"
    if [ ! -f "$ap" ]; then
        echo "PAYLOAD-FAIL: after payload missing: $f"
    else
        got=$(shasum -a 256 "$ap" | cut -d' ' -f1)
        [ "$got" = "$after" ] || echo "PAYLOAD-FAIL: after payload corrupt: $f (manifest=$after actual=$got)"
    fi
done > "$PRECHK/payload.log" 2>&1 || true

# ---------- pre-check 3: required dependencies ----------
tail -n +2 "$DEPS" | while IFS="$(printf '\t')" read -r df dh dsrc dwhy; do
    if [ ! -f "$TARGET/$df" ]; then
        echo "DEP-FAIL: required dependency missing at target: $df ($dwhy)"
    else
        got=$(shasum -a 256 "$TARGET/$df" | cut -d' ' -f1)
        [ "$got" = "$dh" ] || echo "DEP-FAIL: dependency drifted at target: $df (expected=$dh actual=$got)"
    fi
done > "$PRECHK/deps.log" 2>&1 || true

# ---------- pre-check 4: target still at post-apply state ----------
tail -n +2 "$MANIFEST" | while IFS="$(printf '\t')" read -r f op before after; do
    if [ ! -f "$TARGET/$f" ]; then
        echo "STATE-FAIL: target missing: $f"
        continue
    fi
    cur=$(shasum -a 256 "$TARGET/$f" | cut -d' ' -f1)
    [ "$cur" = "$after" ] || echo "STATE-FAIL: modified after adoption (refusing revert): $f (expected=$after actual=$cur)"
done > "$PRECHK/state.log" 2>&1 || true

cat "$PRECHK/struct.log" "$PRECHK/payload.log" "$PRECHK/deps.log" "$PRECHK/state.log" > "$PRECHK/result.log"
if [ -s "$PRECHK/result.log" ]; then
    echo "---- PRE-CHECK FAILED (zero writes, nothing modified) ----"
    cat "$PRECHK/result.log"
    rm -rf "$KEEPDIR"
    exit 1
fi
echo "PRE-CHECK OK: all targets still at post-apply state, package payloads and dependencies verified; reverting now."

# ---------- revert phase ----------
reverted_log="$KEEPDIR/reverted.list"
recovery_plan="$KEEPDIR/recovery-plan.tsv"
rows_file="$KEEPDIR/manifest-rows.txt"
tail -n +2 "$MANIFEST" > "$rows_file"
: > "$reverted_log"
printf 'path\taction\texpected_current\trestore_sha256\tpayload\n' > "$recovery_plan"
cp "$RECOVERY_TOOL" "$KEEPDIR/recovery.py" || { echo "REVERT-FAIL: cannot preserve recovery tool before target writes" >&2; exit 1; }

revert_fail() {
    # $1 = failed file, $2 = reason ; restores post-apply state for done files
    {
        echo '#!/bin/sh'
        echo 'set -eu'
        echo "exec python3 \"$KEEPDIR/recovery.py\" \"$TARGET\" \"$recovery_plan\""
    } > "$KEEPDIR/restore-partial.sh"
    chmod +x "$KEEPDIR/restore-partial.sh"
    echo "REVERT-FAIL: $2 ($1)"
    n=$(wc -l < "$reverted_log" | tr -d ' ')
    echo "files already reverted: $n (list: $reverted_log)"
    echo "recovery materials KEPT at: $KEEPDIR"
    echo "to restore already-reverted files to their post-apply state, run:"
    echo "  sh \"$KEEPDIR/restore-partial.sh\""
    exit 1
}

while IFS="$(printf '\t')" read -r f op before skip_after; do
    if [ "$op" = "replace" ]; then
        mkdir -p "$KEEPDIR/postapply/$(dirname "$f")"
        cp "$TARGET/$f" "$KEEPDIR/postapply/$f" || revert_fail "$f" "cannot back up post-apply content"
        # Recovery plan row recorded BEFORE the baseline rename (2026-09-18
        # interruption-window closure, mirrors apply.sh): a crash between the
        # record and the rename leaves the target at its post-apply content,
        # which recovery.py recognises as already-restored and skips; a crash
        # after the rename finds the row accounted. Per-file recovery, never
        # whole-package atomicity.
        printf '%s\tcopy\t%s\t%s\t%s\n' "$f" "$before" "$skip_after" "postapply/$f" >> "$recovery_plan"
        cp "$PKG/before/$f" "$TARGET/$f.tmp.adoption-revert" || revert_fail "$f" "cannot stage baseline content"
        got=$(shasum -a 256 "$TARGET/$f.tmp.adoption-revert" | cut -d' ' -f1)
        if [ "$got" != "$before" ]; then
            rm -f "$TARGET/$f.tmp.adoption-revert"
            revert_fail "$f" "staged baseline content mismatch"
        fi
        mv "$TARGET/$f.tmp.adoption-revert" "$TARGET/$f" || revert_fail "$f" "atomic baseline rename failed"
        printf '%s\t%s\n' "$op" "$f" >> "$reverted_log"
        echo "reverted [replace] $f"
    else
        mkdir -p "$KEEPDIR/postapply/$(dirname "$f")"
        cp "$TARGET/$f" "$KEEPDIR/postapply/$f" || revert_fail "$f" "cannot preserve added content"
        printf '%s\tcopy\tABSENT\t%s\t%s\n' "$f" "$skip_after" "postapply/$f" >> "$recovery_plan"
        rm "$TARGET/$f" || revert_fail "$f" "cannot remove added file"
        printf '%s\t%s\n' "$op" "$f" >> "$reverted_log"
        echo "reverted [add removed] $f"
    fi
done < "$rows_file"
echo "REVERT DONE: 25/25 restored to the captured pre-adoption runtime state."
rm -rf "$KEEPDIR"
exit 0
