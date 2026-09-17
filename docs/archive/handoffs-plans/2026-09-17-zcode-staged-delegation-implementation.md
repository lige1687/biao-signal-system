# ZCode Staged Delegation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the installed `$zcode-delegate` skill so Codex chooses any sensible number of planned stages while the whole job has a separate maximum of three repair dispatches.

**Architecture:** New jobs use protocol v2 with immutable `goals` plus immutable `stages`. `stage_index` tracks normal progress, `repair_count` tracks only dispatched repair attempts, and `execution_seq` uniquely identifies every ZCode call. Existing protocol v1 job records remain readable and retain their old round semantics.

**Tech Stack:** Node.js ESM, Node built-in test runner, ZCode bundled CLI 0.16.3, JSON state files, Codex `queue` CLI.

## Global Constraints

- Installed files live under `/Users/yongbiaoli/.codex/skills/zcode-delegate`; job state remains under `/Users/yongbiaoli/.codex/zcode-delegate/jobs`.
- This is development orchestration only. Do not modify trading rules, research definitions, UI, backtest data, or existing experiment records.
- Normal stage count is chosen by Codex before dispatch and has no protocol cap; every stage must have a meaningful deliverable.
- The whole job has `repair_budget: 3`; normal stage advancement never increments `repair_count`.
- A repair counts only when its execution is marked `dispatched`; static validation failure before launch does not consume the budget.
- Preserve exact ZCode session binding, authenticated callbacks, control transfer audit, no polling, highest ZCode CLI permission, and independent Codex verification.
- Preserve protocol v1 files and behavior for existing jobs. Never rewrite accepted job history.
- Personal skill files are outside this Git repository. Do not stage unrelated repository changes; validate each task immediately instead of pretending an external file was committed.
- Use `apply_patch` for edits and TDD for every behavior change.

---

### Task 1: Protocol v2 contract and initial state

**Files:**
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/jobctl.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/references/task-contract.md`

**Interfaces:**
- Consumes: `jobctl.mjs create --workspace --thread --request-file --contract-file`.
- Produces: `validateV2Contract(contract)`, protocol v2 `state.json`, and v2 `prompt-execution-1.md`.

- [ ] **Step 1: Add failing contract tests**

Add a v2 contract to the test helper with two stages and assertions equivalent to:

```js
assert.equal(state.protocol_version, 2);
assert.equal(state.stage_index, 0);
assert.equal(state.stage_count, 2);
assert.equal(state.current_stage_id, "S1");
assert.equal(state.execution_seq, 1);
assert.equal(state.current_attempt, "initial");
assert.equal(state.repair_count, 0);
assert.equal(state.repair_budget, 3);
assert.match(prompt, /execution=1/);
assert.match(prompt, /stage=S1/);
assert.match(prompt, /attempt=initial/);
```

Add rejection cases for a goal not covered by any stage, a dependency on a later stage, duplicate stage IDs, and a repair budget above three.

- [ ] **Step 2: Run the targeted tests and confirm RED**

Run:

```bash
node --test --test-name-pattern='protocol v2 contract|invalid stage plan' /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
```

Expected: FAIL because v2 stage fields and validation do not exist.

- [ ] **Step 3: Implement the minimal v2 schema**

Require `contract.stages` with this exact shape:

```js
{
  id: "S1",
  title: "non-empty string",
  goal_ids: ["G1"],
  deliverables: ["non-empty string"],
  acceptance: ["non-empty string"],
  depends_on: []
}
```

Write new jobs as protocol v2 with `executions["1"]`, fixed default `repair_budget: 3`, and `prompt-execution-1.md`. Keep `loadState()` able to read v1 records without migration.

- [ ] **Step 4: Run targeted and full tests**

Run:

```bash
node --test --test-name-pattern='protocol v2 contract|invalid stage plan' /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
node --test /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
```

Expected: targeted tests PASS; full suite may expose only expected legacy fixture adjustments, which must be corrected without changing v1 semantics.

### Task 2: Independent stage advancement and repair accounting

**Files:**
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/jobctl.mjs`

**Interfaces:**
- Produces: `record-stage-review`, `prepare-next-stage`, and v2-aware `prepare-repair` / `mark-dispatched`.
- Stage review JSON: `{stage_id, verified, summary, goal_ids_checked, evidence, limitations}`.

- [ ] **Step 1: Add failing state-transition tests**

Cover these exact invariants:

```js
assert.equal(afterAdvance.current_stage_id, "S2");
assert.equal(afterAdvance.repair_count, 0);
assert.equal(afterRepairPrepared.current_stage_id, "S1");
assert.equal(afterRepairPrepared.repair_count, 0);
assert.equal(afterRepairDispatched.repair_count, 1);
```

Also assert that `prepare-next-stage` rejects an unverified S1, verified S2 cannot advance past the final stage, and a fourth repair dispatch is rejected.

- [ ] **Step 2: Run tests and confirm RED**

```bash
node --test --test-name-pattern='stage review|next stage|repair budget' /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
```

Expected: FAIL because the commands do not exist.

- [ ] **Step 3: Implement stage review and next-stage prompts**

`record-stage-review` must validate exact stage identity and non-empty evidence. A passing review sets `status: "stage_verified"`; a failing review remains reviewable for repair. `prepare-next-stage` requires `stage_verified`, advances one stage, creates a new `initial` execution, and leaves `repair_count` unchanged.

- [ ] **Step 4: Implement repair accounting at dispatch**

`prepare-repair` creates `attempt: "repair"` for the current stage without incrementing the budget. `mark-dispatched` increments once only when that execution first receives `dispatched_at`; repeated marking is idempotent. Reject dispatch if `repair_count >= repair_budget`.

- [ ] **Step 5: Run full state tests**

```bash
node --test /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
```

Expected: all state and legacy tests PASS.

### Task 3: V2 dispatch, callback authentication, and v1 compatibility

**Files:**
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/dispatch-cli.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-stop-hook.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs`

**Interfaces:**
- V2 marker: `ZCODE_DELEGATE_DONE job_id=<uuid> nonce=<hex> execution=<n> stage=<S-id> attempt=<initial|repair> status=<...>`.
- V1 marker remains accepted for `protocol_version: 1` only.

- [ ] **Step 1: Add failing dispatch and hook tests**

Assert the fake ZCode call receives `--mode yolo`, resumes the exact bound session for S2 and repairs, writes `cli-execution-N-result.json`, and rejects callbacks with the wrong execution, stage, attempt, nonce, or session. Retain a v1 fixture that still accepts its old `round=` marker.

- [ ] **Step 2: Run tests and confirm RED**

```bash
node --test --test-name-pattern='v2 dispatch|v2 callback|v1 callback compatibility' /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
```

Expected: FAIL on the old round-only parser.

- [ ] **Step 3: Implement protocol-aware dispatch**

Branch on `state.protocol_version`. For v2, validate the prompt contains the exact execution/stage/attempt tuple, use the v2 result filename, and require a bound session after execution 1. Keep the v1 branch byte-compatible with existing records.

- [ ] **Step 4: Implement protocol-aware Stop Hook**

Use separate anchored marker patterns for v1 and v2. For v2, authenticate all routing fields before claiming `delivery-execution-N.lock`, write `callback-execution-N.json`, and queue a short notice showing `stage i/N` and `repairs used/3`.

- [ ] **Step 5: Run the full suite**

```bash
node --test /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
```

Expected: all tests PASS and fake credentials remain absent from stdout, stderr, and job files.

### Task 4: Acceptance, control transfer, and user-facing instructions

**Files:**
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/jobctl.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/SKILL.md`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/references/protocol.md`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/references/task-contract.md`
- Modify: `/Users/yongbiaoli/.codex/skills/zcode-delegate/agents/openai.yaml`

**Interfaces:**
- Acceptance requires every stage review to be verified and every G goal to have fresh Codex evidence.
- `transfer-control` is allowed only at `callback_received` or `stage_verified` checkpoints.

- [ ] **Step 1: Add failing acceptance and transfer tests**

Assert acceptance rejects a missing stage review even if all goals are listed. Assert a transfer from `dispatched` is rejected and a transfer from `stage_verified` preserves session, stage, execution, and repair counts.

- [ ] **Step 2: Run tests and confirm RED**

```bash
node --test --test-name-pattern='accept.*stage|transfer.*stage' /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
```

- [ ] **Step 3: Implement enforcement and update documentation**

Document in plain language: Codex chooses stages before dispatch, each stage has a user checkpoint by default, mechanical unattended repairs are optional, and `repair 0/3` is separate from `stage i/N`. Remove text that says three total executions.

- [ ] **Step 4: Validate all behavior and skill structure**

```bash
node --test /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
python3 /Users/yongbiaoli/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yongbiaoli/.codex/skills/zcode-delegate
```

Expected: all tests PASS and `Skill is valid!`.

### Task 5: Isolated two-stage end-to-end verification

**Files:**
- Create temporarily: `/tmp/zcode-staged-delegate-*/`
- Inspect only: `/Users/yongbiaoli/.codex/zcode-delegate/jobs/<test-job>/`

**Interfaces:**
- Uses the installed v2 CLI and existing ZCode provider.
- Must not touch the project working tree.

- [ ] **Step 1: Create a two-stage `/tmp` contract**

S1 creates `artifact.txt` with `alpha`; S2 resumes the exact session and appends `beta`. Both stages have deterministic file-content acceptance.

- [ ] **Step 2: Dispatch S1 and independently verify**

Expected file after S1:

```text
alpha
```

Record a passing S1 review and run `prepare-next-stage`; assert `repair_count` remains zero.

- [ ] **Step 3: Dispatch S2 and independently verify**

Expected file after S2:

```text
alpha
beta
```

Assert both CLI result files contain the same ZCode session ID and `repair_count` is still zero.

- [ ] **Step 4: Verify repair accounting without another real model call**

Use the test fake CLI to prepare and dispatch one repair; assert `repair_count` becomes one only at dispatch. Do not spend a real call merely to measure tokens.

- [ ] **Step 5: Run final verification**

```bash
node --test /Users/yongbiaoli/.codex/skills/zcode-delegate/scripts/zcode-delegate.test.mjs
python3 /Users/yongbiaoli/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yongbiaoli/.codex/skills/zcode-delegate
python3 scripts/check_repo_hygiene.py
```

Expected: full suite PASS, skill valid, repository hygiene PASS, project working tree unchanged except pre-existing user changes.
