# Rebuild and rerun the accepted artificial workflow check

The passing check was assembled from several published Git sources. Commit `fe6e51e2c9d767ebd718f77b5de020b372e0a7db` contains the recovery receipts and the accepted CLI source, but it does **not** contain all 49 assembled baseline paths. For example, `docs/archive/handoffs-plans/dual-ma-information-2026-09-28/questions.json` is absent from that commit. Do not treat a checkout of the recovery branch by itself as a runnable project.

This procedure rebuilds only the accepted artificial X-to-Y engineering case. It does not restore all 108 files from the implementation-start inventory, install dependencies on a new machine, or establish real factor effectiveness.

## Published inputs

- Replay checkout: the passing recovery commit `fe6e51e2c9d767ebd718f77b5de020b372e0a7db`. It already contains `native_risk_d_mae_workflow.py`, both artificial-workflow tests, and the exact 4,889-byte CLI. The older project base `18e64fa632dba5dbad0e5fcae09b4ccc75f119a9` does not contain that adapter or those tests.
- The 19 locally preserved baseline files: `codex/native-workflow-baseline-20261008` at `dbd86bccf9ffe9ea9617a484bf8b96825880fb7d` (the 19 original bytes are the same as the first snapshot at `ec565b87f794541bfa6518a8675dce941390e3e8`).
- The other 30 baseline files: the exact commit/blob recorded for each path in `remote-baseline-inventory.json` at `ba106251577952bc35f5f865a76cd49d1c274773`. The recovery script checks the recorded remote refs and each source blob before writing.
- The accepted implementation and tests: `codex/native-workflow-integration-20261007` at `b2f45151128baa1fe387cda85862d71cb01e1206`, plus only the already accepted `shared-entry-changes.patch` and its recorded three-entry manifest from `ba106251577952bc35f5f865a76cd49d1c274773`.
- The CLI required by this test: `scripts/run_factor_lab.py` from `dbd86bccf9ffe9ea9617a484bf8b96825880fb7d`, 4,889 bytes, SHA-256 `eb38c3ce70a4331026ab1dc5d8f71eb5f2e1cbffda59ceac4abbaffb15820c52`. The project base has an older 842-byte version with SHA-256 `17a7bc63bc97893f24ee72861836d64e65298b18b4d53c67041ef999cc4613d5`, which rejects `--review-workflow-contract`.
- The complete first failure is preserved under `pure-git-recovery/`. The accepted rerun output is preserved under `pure-git-recovery-cli50/`. Treat both evidence directories as read-only.

## Rebuild in a fresh worktree

Use a clean, isolated checkout and the existing Python environment. The verified environment was Python 3.11.7 and pytest 8.4.2. Dependency installation on another machine was not tested; if the existing environment lacks a required package, record that as a separate recovery gap instead of installing or changing dependencies as part of this check.

From a clone with the stated commits available, run the following. Replace `REPLAY_ID` with a new unique value each time. Both the worktree and replay evidence directory must be absent. The replay directory is a sibling of the preserved evidence directories, and the script writes only there.

```bash
set -e
REPLAY_ID=replace-with-a-new-unique-token
replay_worktree=".codex/worktrees/native-workflow-replay-${REPLAY_ID}"
test ! -e "$replay_worktree" || { echo "replay worktree already exists" >&2; exit 1; }
git fetch origin refs/heads/codex/native-workflow-pure-git-recovery-20261008
git fetch origin refs/heads/codex/native-workflow-baseline-20261008
git fetch origin refs/heads/codex/native-workflow-integration-20261007
git worktree add "$replay_worktree" fe6e51e2c9d767ebd718f77b5de020b372e0a7db
cd "$replay_worktree"

test "$(wc -c < scripts/run_factor_lab.py | tr -d ' ')" = 4889
printf '%s  %s\n' eb38c3ce70a4331026ab1dc5d8f71eb5f2e1cbffda59ceac4abbaffb15820c52 scripts/run_factor_lab.py | shasum -a 256 -c -

replay_dir="docs/experiments/raw/native-workflow-integration-2026-10-07/pure-git-recovery-replay-${REPLAY_ID}"
test ! -e "$replay_dir" || { echo "replay evidence directory already exists" >&2; exit 1; }
mkdir "$replay_dir"
cp docs/experiments/raw/native-workflow-integration-2026-10-07/pure-git-recovery/recover.py "$replay_dir/recover.py"
python3 "$replay_dir/recover.py"
```

The copied recovery script is kept at the same repository-relative depth as the original, so its repository-root calculation remains valid. It reads the frozen inventory and accepted patch, assembles the 49 baseline files from their recorded Git blobs, applies the three accepted shared-entry changes, verifies the six implementation paths, **and runs the saved artificial integration node once**. It does not create the dedicated adapter or either test; those come from the starting commit. Its output location is the new replay directory containing `recover.py`; do not copy or run it from either preserved evidence directory, and do not run the test again by hand immediately afterward.

For reference, the script itself executes this one test command; do not run it separately after the script:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/integration/test_native_risk_d_mae_workflow.py::test_cli_x_then_one_y_restart_verify_and_repeat_rejection --tb=short
```

The recorded result was exit code 0, `1 passed in 3.40s`. The test creates artificial inputs and checks the X-only stage, the later Y stage, a fresh-process publication read, and rejection of repeated or tampered results. It does not use real market data or run a real research stage.

## What this result establishes

The exact bytes needed for this one artificial workflow node can be assembled from the listed remote Git commits in the verified Python environment. No single recovery commit contains the whole assembled source tree. The 108-file original environment has not been proven byte-identical: five runtime files differ from the old base, as listed in `five-runtime-static-audit.json`; three are loaded but their affected functions are not called by this node, and two are not imported by this path. Real inputs, source-time qualification, real X/V/Y, factor results, funding impact, production use, and fresh-machine dependency setup remain unverified.
