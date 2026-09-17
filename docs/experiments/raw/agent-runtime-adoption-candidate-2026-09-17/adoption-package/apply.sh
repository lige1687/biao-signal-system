#!/bin/sh
# Agent runtime adoption package: APPLY script (S2 repair, 2026-09-17)
#
# Usage:
#   sh apply.sh --target /absolute/path/to/runtime-workspace-root
#
# The target is MANDATORY and must be an absolute path. The package never
# guesses the target from its own location or from the caller's cwd.
# Target identity is verified: it must contain src/lei_signal and
# docs/experiments (runtime workspace layout).
#
# Pre-checks (ALL must pass before the first write; any failure = zero writes):
#   1) manifest structure   : 24 rows, 4 tab-separated columns, op in
#                             {replace, add}, sha256 fields well-formed
#   2) package payloads     : every after/<file> matches after_sha256 AND
#                             every before/<file> matches before_sha256
#                             (whole-package integrity, both directions)
#   3) required dependencies: every row of dependencies.tsv exists at the
#                             target and matches its required sha256. These
#                             are read-only fingerprints of runtime files the
#                             candidate depends on (trades.py idempotency API,
#                             client.ts, CopilotCards, AnswerText middle slot,
#                             App.tsx useAgentConsole store, AgentMarkdown
#                             bpLocatable, agent-workspace.css UX classes).
#                             They are NEVER copied or overwritten here.
#                             Missing or drifted -> refuse.
#   4) target state         : every replace target equals before_sha256
#                             (captured live runtime state), every add target
#                             absent.
#
# Write phase: each file is backed up, staged to a .tmp, content-verified,
# atomically renamed. KEEPDIR (backups + applied list + generated
# restore-partial.sh) is KEPT on a mid-write failure with the exact restore
# command printed. No claim of a single atomic transaction across 24 files;
# pre-checks make partial writes a deliberately hard-to-reach path, and if it
# happens anyway the recovery materials and an executable restore method
# remain.

set -eu

usage() {
    echo "usage: sh apply.sh --target /absolute/path/to/runtime-workspace-root" >&2
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
[ -f "$MANIFEST" ] || { echo "REFUSED: manifest.tsv missing in package" >&2; exit 1; }
[ -f "$DEPS" ] || { echo "REFUSED: dependencies.tsv missing in package" >&2; exit 1; }

PRECHK="${TMPDIR:-/tmp}/adoption-apply-precheck.$$"
mkdir -p "$PRECHK"
KEEPDIR="${TMPDIR:-/tmp}/adoption-keep-$(date +%Y%m%d%H%M%S)-$$"
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
    for h in "$before" "$after"; do
        case "$h" in
            ABSENT) ;;
            [0-9a-f]*) [ ${#h} -eq 64 ] || echo "STRUCT-FAIL: bad sha length: $h ($f)" ;;
            *) echo "STRUCT-FAIL: bad sha field: $h ($f)" ;;
        esac
    done
done > "$PRECHK/struct.log" 2>&1 || true
rows=$(tail -n +2 "$MANIFEST" | wc -l | tr -d ' ')
[ "$rows" -eq 24 ] || echo "STRUCT-FAIL: expected 24 data rows, found $rows" >> "$PRECHK/struct.log"

# ---------- pre-check 2: package payloads (after/ AND before/) ----------
tail -n +2 "$MANIFEST" | while IFS="$(printf '\t')" read -r f op before after; do
    ap="$PKG/after/$f"
    if [ ! -f "$ap" ]; then
        echo "PAYLOAD-FAIL: after payload missing: $f"
    else
        got=$(shasum -a 256 "$ap" | cut -d' ' -f1)
        [ "$got" = "$after" ] || echo "PAYLOAD-FAIL: after payload corrupt: $f (manifest=$after actual=$got)"
    fi
    if [ "$op" = "replace" ]; then
        bp="$PKG/before/$f"
        if [ ! -f "$bp" ]; then
            echo "PAYLOAD-FAIL: before payload missing: $f"
        else
            got=$(shasum -a 256 "$bp" | cut -d' ' -f1)
            [ "$got" = "$before" ] || echo "PAYLOAD-FAIL: before payload corrupt: $f (manifest=$before actual=$got)"
        fi
    fi
done > "$PRECHK/payload.log" 2>&1 || true

# ---------- pre-check 3: required dependencies (read-only fingerprints) ----------
tail -n +2 "$DEPS" | while IFS="$(printf '\t')" read -r df dh dsrc dwhy; do
    if [ ! -f "$TARGET/$df" ]; then
        echo "DEP-FAIL: required dependency missing at target: $df ($dwhy)"
    else
        got=$(shasum -a 256 "$TARGET/$df" | cut -d' ' -f1)
        [ "$got" = "$dh" ] || echo "DEP-FAIL: dependency drifted at target: $df (expected=$dh actual=$got)"
    fi
done > "$PRECHK/deps.log" 2>&1 || true

# ---------- pre-check 4: target state ----------
tail -n +2 "$MANIFEST" | while IFS="$(printf '\t')" read -r f op before after; do
    if [ "$op" = "replace" ]; then
        if [ ! -f "$TARGET/$f" ]; then
            echo "STATE-FAIL: replace target missing: $f"
            continue
        fi
        cur=$(shasum -a 256 "$TARGET/$f" | cut -d' ' -f1)
        [ "$cur" = "$before" ] || {
            echo "STATE-FAIL: target drifted (refusing): $f"
            echo "  expected before=$before"
            echo "  actual         =$cur"
        }
    elif [ "$op" = "add" ]; then
        [ -e "$TARGET/$f" ] && echo "STATE-FAIL: add target already exists (refusing): $f"
    fi
done > "$PRECHK/state.log" 2>&1 || true

cat "$PRECHK/struct.log" "$PRECHK/payload.log" "$PRECHK/deps.log" "$PRECHK/state.log" > "$PRECHK/result.log"
if [ -s "$PRECHK/result.log" ]; then
    echo "---- PRE-CHECK FAILED (zero writes, nothing modified) ----"
    cat "$PRECHK/result.log"
    rm -rf "$KEEPDIR"
    exit 1
fi
echo "PRE-CHECK OK: manifest structure, package payloads (after+before), 7 dependencies and 24 target states all verified; writing now."

# ---------- write phase ----------
applied_log="$KEEPDIR/applied.list"
rows_file="$KEEPDIR/manifest-rows.txt"
tail -n +2 "$MANIFEST" > "$rows_file"
: > "$applied_log"

write_fail() {
    # $1 = failed file, $2 = reason ; keeps KEEPDIR and emits a restore script
    {
        echo '#!/bin/sh'
        echo "# Restore files already written by the interrupted adoption apply."
        echo "# Target: $TARGET   Keep dir: $KEEPDIR"
        if [ -s "$applied_log" ]; then
            while IFS="$(printf '\t')" read -r dop df; do
                if [ "$dop" = "replace" ]; then
                    echo "cp \"$KEEPDIR/backup/$df\" \"$TARGET/$df\""
                else
                    echo "rm -f \"$TARGET/$df\""
                fi
            done < "$applied_log"
            echo "echo restored \$(wc -l < \"$applied_log\" | tr -d ' ') files to pre-apply state"
        else
            echo "echo nothing was written"
        fi
    } > "$KEEPDIR/restore-partial.sh"
    chmod +x "$KEEPDIR/restore-partial.sh"
    echo "WRITE-FAIL: $2 ($1)"
    n=$(wc -l < "$applied_log" | tr -d ' ')
    echo "files already written: $n (list: $applied_log)"
    echo "recovery materials KEPT at: $KEEPDIR"
    echo "to restore already-written files to their pre-apply state, run:"
    echo "  sh \"$KEEPDIR/restore-partial.sh\""
    exit 1
}

while IFS="$(printf '\t')" read -r f op skip_before after; do
    mkdir -p "$(dirname "$TARGET/$f")"
    if [ "$op" = "replace" ]; then
        mkdir -p "$KEEPDIR/backup/$(dirname "$f")"
        cp "$TARGET/$f" "$KEEPDIR/backup/$f" || write_fail "$f" "cannot back up current file"
    fi
    cp "$PKG/after/$f" "$TARGET/$f.tmp.adoption" || write_fail "$f" "cannot stage tmp file"
    got=$(shasum -a 256 "$TARGET/$f.tmp.adoption" | cut -d' ' -f1)
    if [ "$got" != "$after" ]; then
        rm -f "$TARGET/$f.tmp.adoption"
        write_fail "$f" "staged content mismatch"
    fi
    mv "$TARGET/$f.tmp.adoption" "$TARGET/$f" || write_fail "$f" "atomic rename failed"
    printf '%s\t%s\n' "$op" "$f" >> "$applied_log"
    echo "applied [$op] $f"
done < "$rows_file"
echo "APPLY DONE: 24/24 into $TARGET. Run the affected regressions from the report"
echo "before putting this into use; rollback with revert.sh --target <same target>."
rm -rf "$KEEPDIR"
exit 0
