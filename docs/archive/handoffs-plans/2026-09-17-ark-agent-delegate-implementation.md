# Ark Agent Delegate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install `$ark-agent-delegate` as a personal Codex skill that sends staged work to Claude Code through `settings.ark-agent.json`, receives authenticated Stop-hook callbacks in the owning Codex task, and permits at most three repairs per job.

**Architecture:** The skill owns an independent job directory and protocol; it does not share state with ZCode. Codex freezes goals and stages, the first execution uses a new UUID session, later stages and repairs resume that exact session, and a user-level Claude Stop Hook queues a short authenticated callback to the owning Codex task. Codex independently verifies every stage before advancing or accepting.

**Tech Stack:** Node.js ESM, Node built-in test runner, Claude Code 2.1.258 CLI, Claude settings JSON, Codex `queue` CLI.

## Global Constraints

- Install under `/Users/yongbiaoli/.codex/skills/ark-agent-delegate`; job state lives under `/Users/yongbiaoli/.codex/ark-agent-delegate/jobs`.
- Load `/Users/yongbiaoli/.claude/settings.ark-agent.json` explicitly; preserve its provider/model/env values and never print credentials.
- Use `--dangerously-skip-permissions` exactly as the user requested. Highest tool permission does not broaden the frozen task scope.
- New stages are chosen by Codex before dispatch; the whole job has at most three repair dispatches.
- First execution uses a generated `--session-id`; every later execution uses exact `--resume`. Never use `--continue`.
- External work never authorizes merge, deploy, commit, trading, deleting important data, changing strategy definitions, or expanding scope.
- Default to a user checkpoint after each large stage. Only explicitly unattended, purely mechanical repairs may continue automatically.
- This is development orchestration only and must not modify trading rules, research definitions, UI, or experiment results.
- Use `apply_patch` for edits and TDD for every script behavior. Do not create a real model call merely to poll or measure usage.

---

### Task 1: Initialize the personal skill and freeze its public contract

**Files:**
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/SKILL.md`
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/agents/openai.yaml`
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/references/task-contract.md`
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/references/protocol.md`
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs`
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/jobctl.mjs`

**Interfaces:**
- Public invocation: `$ark-agent-delegate`.
- Job creation: `jobctl.mjs create --workspace --thread --request-file --contract-file --callback-review-effort <low|medium|high>`.
- Contract includes immutable `mission`, `goals`, `stages`, scope, protected paths, and stop conditions.

- [ ] **Step 1: Initialize the skill directory**

Run the system initializer for `ark-agent-delegate` with `scripts,references`, then replace scaffold content immediately. Do not create README or unused assets.

- [ ] **Step 2: Write failing creation tests**

The first test must assert:

```js
assert.equal(state.protocol_version, 1);
assert.equal(state.stage_index, 0);
assert.equal(state.current_stage_id, "S1");
assert.equal(state.current_attempt, "initial");
assert.equal(state.repair_count, 0);
assert.equal(state.repair_budget, 3);
assert.match(state.claude_session_id, /^[0-9a-f-]{36}$/);
assert.equal(state.callback_review_effort, "medium");
```

Add rejection tests for invalid stages, repair budget above three, empty goals, and unsupported callback effort.

- [ ] **Step 3: Run tests and confirm RED**

```bash
node --test /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
```

Expected: FAIL because `jobctl.mjs` has no implementation.

- [ ] **Step 4: Implement create and immutable contract validation**

Use atomic mode-0600 JSON writes. Generate job UUID, 128-bit nonce, and Claude session UUID separately. Write `prompt-execution-1.md` containing the exact completion marker fields and the frozen contract fingerprint.

- [ ] **Step 5: Make creation tests pass and validate the skill shell**

```bash
node --test /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
python3 /Users/yongbiaoli/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yongbiaoli/.codex/skills/ark-agent-delegate
```

Expected: creation tests PASS and skill structure valid.

### Task 2: Stage progression, repair budget, acceptance, and control transfer

**Files:**
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/jobctl.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/references/task-contract.md`

**Interfaces:**
- Commands: `mark-dispatched`, `record-stage-review`, `prepare-next-stage`, `prepare-repair`, `transfer-control`, `accept`, `cancel`, `status`.
- Stage review: `{stage_id, verified, summary, goal_ids_checked, evidence, limitations}`.
- Final report: every G goal verified plus every stage review verified.

- [ ] **Step 1: Write failing transition tests**

Assert normal S1→S2 advancement keeps `repair_count: 0`; a prepared repair keeps zero until first dispatch; the first repair dispatch sets one; duplicate marking stays one; and the fourth repair is rejected.

- [ ] **Step 2: Run tests and confirm RED**

```bash
node --test --test-name-pattern='stage|repair|accept|transfer' /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
```

- [ ] **Step 3: Implement transitions**

Use the same explicit state invariants as the approved design: only `stage_verified` may advance, only `callback_received` with a recorded failed review may prepare repair, and only callback/stage checkpoints may transfer control. Preserve session ID, nonce, contract fingerprint, stage position, execution number, and repair count through transfer.

- [ ] **Step 4: Implement acceptance enforcement**

Reject acceptance if any stage review is absent or false, any frozen goal is missing, evidence is empty, or verification commands are absent. Write `final-report.json` and its SHA-256 only after all checks pass.

- [ ] **Step 5: Run the full job controller suite**

```bash
node --test /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
```

Expected: all controller tests PASS.

### Task 3: Claude CLI dispatch with exact session and highest permission

**Files:**
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/dispatch-cli.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs`

**Interfaces:**
- First execution argv includes `-p --settings <path> --session-id <uuid> --dangerously-skip-permissions --output-format json`.
- Later execution argv replaces `--session-id` with `--resume <same uuid>`.
- Environment removes inherited Anthropic endpoint/model/key overrides; explicit settings supply the Ark provider.

- [ ] **Step 1: Add a fake Claude executable and failing argv tests**

The fake executable records argv and selected environment names, then emits:

```json
{"type":"result","subtype":"success","is_error":false,"session_id":"11111111-1111-4111-8111-111111111111","result":"done","usage":{"input_tokens":1,"output_tokens":1}}
```

Assert first and resumed argv, exact working directory, absence of `--continue`, presence of highest permission, and absence of secret values in output/job files.

- [ ] **Step 2: Run tests and confirm RED**

```bash
node --test --test-name-pattern='Claude CLI dispatch' /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
```

- [ ] **Step 3: Implement preflight and spawn**

Preflight checks executable, settings JSON, workspace, prepared state, exact prompt tuple, and session presence. Start Claude with an argv array, capture stdout/stderr, redact any secret values discovered in the settings `env` object, and write `cli-execution-N-result.json`.

- [ ] **Step 4: Handle failure truthfully**

Non-zero exit, invalid JSON, `is_error: true`, or mismatched returned session writes a redacted failed result and never fabricates a callback. A failure after dispatch still consumes a repair when `attempt=repair` because the real model invocation began.

- [ ] **Step 5: Run dispatch and full tests**

```bash
node --test /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
```

Expected: all tests PASS; no credential string appears in captured output.

### Task 4: Authenticated Claude Stop Hook and safe installer

**Files:**
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/claude-stop-hook.mjs`
- Create: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/install-hook.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/references/protocol.md`

**Interfaces:**
- Claude completion marker: `ARK_AGENT_DELEGATE_DONE job_id=<uuid> nonce=<hex> execution=<n> stage=<S-id> attempt=<initial|repair> status=<completed|needs_input|failed>`.
- Stop input uses official `hook_event_name`, `session_id`, and `last_assistant_message` fields.
- Codex callback uses `codex queue --thread <owner> -c model_reasoning_effort="<level>" --message <short notice>`.

- [ ] **Step 1: Write failing hook authentication tests**

Use a fake Codex binary and temporary delegate home. Valid input queues exactly once; wrong nonce, execution, stage, attempt, session, ordinary Stop, and duplicate Stop queue zero times. Assert callback JSON stores the full final response locally while the queued notice contains only job metadata and its path.

- [ ] **Step 2: Write failing installer tests**

Against a temporary copy of `settings.ark-agent.json`, assert the installer adds exactly one `hooks.Stop` command entry, preserves `env/model/theme`, creates a timestamped backup on change, and is byte-idempotent on the second run.

- [ ] **Step 3: Run tests and confirm RED**

```bash
node --test --test-name-pattern='Stop callback|hook installer' /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
```

- [ ] **Step 4: Implement hook and installer**

Use timing-safe nonce comparison, atomic callback/state writes, and a directory delivery lock. Configure Claude's documented settings shape:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {"type":"command","command":"/opt/homebrew/bin/node /absolute/claude-stop-hook.mjs","timeout":15}
        ]
      }
    ]
  }
}
```

The script itself filters the completion marker because Stop fires whenever Claude finishes responding.

- [ ] **Step 5: Run full tests and install the real hook**

```bash
node --test /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
node /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/install-hook.mjs --config /Users/yongbiaoli/.claude/settings.ark-agent.json
```

Expected: tests PASS; installer reports one change and a second run reports no change.

### Task 5: Skill instructions, effort routing, and failure recovery

**Files:**
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/SKILL.md`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/agents/openai.yaml`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/references/protocol.md`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/references/task-contract.md`
- Modify: `/Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs`

**Interfaces:**
- Callback effort: `low` for transport/config status, `medium` for ordinary implementation review, `high` for strategy, goal drift, security, money, or timing risk.
- Hook does not pass `-m` unless the user explicitly selected a callback model.

- [ ] **Step 1: Add failing instruction and effort tests**

Assert generated callback argv contains the job's effort override and no model override by default. Assert skill instructions require goal alignment, stage planning, independent review, maximum three repairs, exact-session resume, no polling, and evidence-backed final acceptance.

- [ ] **Step 2: Run tests and confirm RED**

```bash
node --test --test-name-pattern='effort|skill instructions' /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
```

- [ ] **Step 3: Complete instructions and recovery guide**

Document exact create/dispatch/review/advance/repair/accept commands, user checkpoint behavior, control transfer, missing callback diagnosis, permission truth, token-saving rules, and how to stop after the third repair without pretending success.

- [ ] **Step 4: Run full validation**

```bash
node --test /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
python3 /Users/yongbiaoli/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yongbiaoli/.codex/skills/ark-agent-delegate
```

Expected: all tests PASS and `Skill is valid!`.

### Task 6: One-time isolated real integration test

**Files:**
- Create temporarily: `/tmp/ark-agent-delegate-*/`
- Inspect only: `/Users/yongbiaoli/.codex/ark-agent-delegate/jobs/<test-job>/`
- Inspect without revealing secrets: `/Users/yongbiaoli/.claude/settings.ark-agent.json`

**Interfaces:**
- Real Claude Code session with Ark settings and highest permission.
- Fake Codex callback target for hook transport test; separate real Codex task only for per-turn effort persistence verification.

- [ ] **Step 1: Run a real `/tmp` write smoke test**

Create a one-stage contract whose only outcome is a fixed-content file. Dispatch once and verify the file, CLI result, exact session binding, callback, and delivery deduplication. Do not use the project workspace.

- [ ] **Step 2: Run a two-stage resume smoke test only if the first call succeeds**

Advance to S2, resume the exact session, and append a second fixed line. Verify both result records share one session and `repair_count` remains zero.

- [ ] **Step 3: Verify callback effort isolation**

Create an isolated projectless Codex task, queue one callback with `model_reasoning_effort="low"`, then inspect that a later manual/default turn does not persistently change its configured effort. If the override persists, stop and implement explicit restoration before release.

- [ ] **Step 4: Confirm Ark provider selection was not globally changed**

Compare a sanitized fingerprint of `env/model/theme` before and after. The only allowed real settings change is the installed Stop hook.

- [ ] **Step 5: Run final verification and repository hygiene**

```bash
node --test /Users/yongbiaoli/.codex/skills/ark-agent-delegate/scripts/ark-agent-delegate.test.mjs
python3 /Users/yongbiaoli/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yongbiaoli/.codex/skills/ark-agent-delegate
python3 scripts/check_repo_hygiene.py
```

Expected: tests PASS, skill valid, real smoke evidence recorded, repository hygiene PASS, and no project strategy or research file changed by installation.
