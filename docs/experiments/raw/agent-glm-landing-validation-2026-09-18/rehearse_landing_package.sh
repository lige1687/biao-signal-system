#!/bin/bash
# S2 落地验证演练驱动：对新采用包（25行，含S1 subjects.py）复跑
# 采用/回退/拒绝场景 + 应用后S1复现脚本（原字节副本）对准已采用树。
# 目标全部为独立临时目录（从运行目录只读拷出），绝不写真实运行目录。
set -u
RUNTIME=/Users/yongbiaoli/Desktop/lei-signal-lab
WS=/Users/yongbiaoli/lei-agent-runtime-adoption-20260917
RAW="$WS/docs/experiments/raw/agent-glm-landing-validation-2026-09-18"
PKG="$RAW/adoption-package"
REH="$RAW/rehearsal"
S1RAW="$WS/docs/experiments/raw/agent-glm-symbol-binding-fix-2026-09-18"
PY=/opt/homebrew/bin/python3.11
PASS=0; FAIL=0
say() { echo "[$1] $2"; }
ok()  { say PASS "$1"; PASS=$((PASS+1)); }
bad() { say FAIL "$1"; FAIL=$((FAIL+1)); }

mktarget() { # $1 = dir name ; minimal faithful copy of runtime adoption surface
    local t="$REH/$1"; rm -rf "$t"; mkdir -p "$t/docs/experiments"
    rsync -a --exclude '__pycache__' "$RUNTIME/src/" "$t/src/"
    rsync -a "$RUNTIME/configs/" "$t/configs/"
    mkdir -p "$t/tests/integration" "$t/tests/unit"
    cp "$RUNTIME/tests/integration/test_agent_chat_e2e.py" "$t/tests/integration/"
    cp "$RUNTIME/tests/unit/test_agent_name_resolve.py" "$t/tests/unit/"
    rsync -a --exclude node_modules --exclude dist "$RUNTIME/web/" "$t/web/"
    ln -sfn "$WS/web/node_modules" "$t/web/node_modules"
    echo "$t"
}

snap() { # $1=target -> sha table for all manifest paths + deps
    local t="$1"; tail -n +2 "$PKG/manifest.tsv" | cut -f1
    tail -n +2 "$PKG/dependencies.tsv" | cut -f1
}

verify_applied() { # $1=target : every manifest path == after sha
    local t="$1" badn=0
    while IFS="$(printf '\t')" read -r f op b a; do
        got=$(shasum -a 256 "$t/$f" 2>/dev/null | cut -d' ' -f1)
        [ "$got" = "$a" ] || { badn=$((badn+1)); say detail "mismatch $f"; }
    done < <(tail -n +2 "$PKG/manifest.tsv")
    [ "$badn" -eq 0 ]
}

rm -rf "$REH"; mkdir -p "$REH"

# ---------- act1: clean apply -> 25/25, shas verified ----------
T=$(mktarget act1-target)
sh "$PKG/apply.sh" --target "$T" > "$REH/act1-apply-ok.log" 2>&1 \
    && grep -q "APPLY DONE: 25/25" "$REH/act1-apply-ok.log" \
    && verify_applied "$T" && ok "act1 apply 25/25 shas verified" \
    || bad "act1 apply (see act1-apply-ok.log)"

# ---------- act1b: S1 repro (byte-identical copy) against APPLIED tree ----------
# 复现脚本按自身位置推源码根（脚本目录上溯4层），reprodock 伪根下放4层目录。
RD="$REH/reprodock"
rm -rf "$RD"; mkdir -p "$RD/d1/d2/d3/d4"
cp "$S1RAW/repro_symbol_binding_fix.py" "$RD/d1/d2/d3/d4/repro_symbol_binding_fix.py"
ln -sfn "$T/src" "$RD/src"
( cd "$RD" && $PY d1/d2/d3/d4/repro_symbol_binding_fix.py fixed ) \
    > "$REH/act1b-repro-fixed-on-applied.log" 2>&1 \
    && grep -q "全部案例通过" "$REH/act1b-repro-fixed-on-applied.log" \
    && ok "act1b S1 repro fixed ALL PASS against applied candidate" \
    || bad "act1b repro on applied tree (see act1b log)"

# ---------- act8: double apply must refuse (targets at after state) ----------
sh "$PKG/apply.sh" --target "$T" > "$REH/act8-double-apply-refused.log" 2>&1 \
    && bad "act8 double apply NOT refused" \
    || { grep -q "PRE-CHECK FAILED" "$REH/act8-double-apply-refused.log" \
         && ok "act8 double apply refused (zero writes)" \
         || bad "act8 refusal reason unexpected"; }

# ---------- act3: revert -> byte-identical restoration ----------
sh "$PKG/revert.sh" --target "$T" > "$REH/act3-revert-ok.log" 2>&1 \
    && grep -q "REVERT DONE: 25/25" "$REH/act3-revert-ok.log" \
    && ok "act3 revert 25/25" || bad "act3 revert"
T2=$(mktarget act3-pristine)
diffn=0
while IFS= read -r f; do
    # 双方都不存在 = 一致（add 行回退后应被删除）
    if [ ! -e "$T/$f" ] && [ ! -e "$T2/$f" ]; then continue; fi
    cmp -s "$T/$f" "$T2/$f" || { diffn=$((diffn+1)); say detail "post-revert diff: $f"; }
done < <(snap "$T")
[ "$diffn" -eq 0 ] && ok "act3 revert byte-identical to runtime state ($diffn diffs)" \
    || bad "act3 revert left $diffn files different"

# ---------- act4: post-adoption edit -> revert refuses ----------
T=$(mktarget act4-target)
sh "$PKG/apply.sh" --target "$T" > /dev/null 2>&1 || bad "act4 setup apply"
echo "# later edit" >> "$T/web/src/utils/agentUx.ts"
sh "$PKG/revert.sh" --target "$T" > "$REH/act4-postedit-refused.log" 2>&1 \
    && bad "act4 revert NOT refused after later edit" \
    || { grep -q "modified after adoption" "$REH/act4-postedit-refused.log" \
         && ok "act4 revert refused, later edit protected" \
         || bad "act4 refusal reason unexpected"; }

# ---------- act2: target drift -> apply refuses ----------
T=$(mktarget act2-target)
echo "drift" >> "$T/src/lei_signal/plans/llm.py"
sh "$PKG/apply.sh" --target "$T" > "$REH/act2-drift-refused.log" 2>&1 \
    && bad "act2 apply NOT refused on drifted target" \
    || { grep -q "STATE-FAIL" "$REH/act2-drift-refused.log" \
         && ok "act2 drifted target refused (zero writes)" \
         || bad "act2 refusal reason unexpected"; }

# ---------- act5/act6: dependency drift / missing -> refuse ----------
T=$(mktarget act5-target); echo "x" >> "$T/web/src/api/client.ts"
sh "$PKG/apply.sh" --target "$T" > "$REH/act5-dep-drift.log" 2>&1 \
    && bad "act5 NOT refused on dep drift" \
    || { grep -q "DEP-FAIL" "$REH/act5-dep-drift.log" && ok "act5 dep drift refused" \
         || bad "act5 refusal reason unexpected"; }
T=$(mktarget act6-target); rm "$T/src/lei_signal/copilot/trades.py"
sh "$PKG/apply.sh" --target "$T" > "$REH/act6-dep-missing.log" 2>&1 \
    && bad "act6 NOT refused on missing dep" \
    || { grep -q "DEP-FAIL" "$REH/act6-dep-missing.log" && ok "act6 missing dep refused" \
         || bad "act6 refusal reason unexpected"; }

# ---------- act7: package corruption -> refuse (scratch package copy) ----------
SCP="$REH/scratch-package"; rm -rf "$SCP"; cp -R "$PKG" "$SCP"
printf '\n# tamper\n' >> "$SCP/after/src/lei_signal/plans/llm.py"
T=$(mktarget act7-target)
sh "$SCP/apply.sh" --target "$T" > "$REH/act7-package-corrupt.log" 2>&1 \
    && bad "act7 NOT refused on corrupt payload" \
    || { grep -q "PAYLOAD-FAIL" "$REH/act7-package-corrupt.log" && ok "act7 corrupt payload refused" \
         || bad "act7 refusal reason unexpected"; }

# ---------- act9: recovery probes (adapted to new package) ----------
sed 's#agent-runtime-adoption-candidate-2026-09-17#adoption-package-pointer#' \
    "$WS/docs/experiments/raw/agent-adoption-recovery-protection-2026-09-17/recovery_probe.py" \
    > /dev/null  # placeholder check only
cp "$WS/docs/experiments/raw/agent-adoption-recovery-protection-2026-09-17/recovery_probe.py" \
    "$RAW/recovery_probe_new_package.py"
/opt/homebrew/bin/python3.11 - "$RAW/recovery_probe_new_package.py" <<'PYEOF'
import sys
from pathlib import Path
p = Path(sys.argv[1])
t = p.read_text()
t = t.replace(
    'REPO = Path(__file__).resolve().parents[4]\nSOURCE_PACKAGE = REPO / "docs/experiments/raw/agent-runtime-adoption-candidate-2026-09-17/adoption-package"',
    'REPO = Path(__file__).resolve().parents[4]\nSOURCE_PACKAGE = REPO / "docs/experiments/raw/agent-glm-landing-validation-2026-09-18/adoption-package"')
t = t.replace('RESULTS = Path(__file__).with_name("recovery-probe-results.json")',
              'RESULTS = Path(__file__).with_name("recovery-probe-results-new-package.json")')
p.write_text(t)
print("probe adapted")
PYEOF
( cd "$WS" && $PY "$RAW/recovery_probe_new_package.py" ) > "$REH/act9-recovery-probes.log" 2>&1 \
    && ok "act9 six recovery scenarios pass on new package" \
    || bad "act9 recovery probes (see act9 log)"

# ---------- act11: rename-window recovery probes (S2 指定中断窗口) ----------
( cd "$WS" && $PY "$RAW/recovery_window_probe.py" ) > "$REH/act11-window-probes.log" 2>&1 \
    && ok "act11 rename-window recovery scenarios pass" \
    || bad "act11 window probes (see act11 log)"

# ---------- act10: frontend build + agent regressions in APPLIED tree ----------
TW="$REH/act1-target/web"
( cd "$TW" && npm run build ) > "$REH/act10-web-build.log" 2>&1 \
    && ok "act10 vite build OK on applied web tree" || bad "act10 web build"
for s in test:agent-ux test:agent-workspace test:agent-prices test:agent-markdown test:evidence-card test:agent-tasks; do
    ( cd "$TW" && npm run "$s" ) > "$REH/act10-${s//:/-}.log" 2>&1 \
    && ok "act10 $s OK" || bad "act10 $s"
done

echo "=========================================="
echo "REHEARSAL SUMMARY: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
