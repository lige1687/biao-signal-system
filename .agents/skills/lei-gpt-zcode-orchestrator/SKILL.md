---
name: lei-gpt-zcode-orchestrator
description: Use when coordinating ChatGPT 6 Pro planning and GPT-6 Codex execution for substantial work in the local lei-signal-lab repository, especially factor-library and self-evolution work. Do not use for unrelated repositories.
---

# LeiSignal GPT + Delegate Orchestrator

The current task is the controller: it owns repository facts, research permissions, frozen contracts, routing checks, independent acceptance, and user communication. ChatGPT 6 Pro owns direction, architecture, difficult ambiguities, routing recommendations, and final review; it does not edit the repository. For new work in this workspace, use Codex delegation:

```text
delegate_mode: codex
execution_models: gpt-6-luna|gpt-6-sol|gpt-6-astra
```

`codex` is the project executor for new delegated work. Historical ZCode jobs remain attached to their original executor and records. An already-started job never changes mode in place: an executor substitution needs explicit authority, a new contract, and a distinct execution record. There is **no silent rebinding** or automatic provider fallback.

## Preflight and planning

1. Read the current repository `AGENTS.md`, mandatory strategy documents, research contract and frozen protocol/definition cards applicable to the task. State which strategy layer the change serves. Preserve the dirty worktree; no broad reset, stash, cleanup, or unrelated edits.
2. Check that the task is substantial, bounded, independently testable, and worth delegation. Handle a genuinely trivial in-scope edit directly; do not create an agent merely to save the controller a one-command check.
3. Consult the established ChatGPT project conversation in the **in-app browser** at the visible 6 Pro model tier (do not downgrade it). Supply repository facts, user authority, previous attempts, risks, paths, and exact open decisions. Record the original response in the repository exchange log, then verify each recommendation against local files before adopting it. If this channel is unavailable, pause the ChatGPT-dependent decision; do not pretend a review happened.
4. Freeze a goal contract with scope, writable and read-only paths, inputs and fingerprints, method/card versions, output location, tests, model, `reasoning_effort`, network/cost/real-run budget, stop conditions, and repair ceiling. A recorded target, completed synthetic test, or old approval does not grant a broader research or production action.

## Model route and executor mode

Ask 6 Pro for a named **currently callable** GPT-6 Codex model and reasoning strength per new stage or repair, with a plain-language cost/complexity reason. Validate its availability and the frozen scope locally. Current project guidance is Luna/low for bounded mechanical work, Sol/low for ordinary approved development, Sol/medium for evidence reconciliation and frozen research engineering, Sol/high for difficult engineering ambiguity, and Astra/high or xhigh for strategy meaning, experiment design, critical money or timing risk, and adversarial review. This is a routing heuristic, not a hard-coded model guarantee; an explicit user model choice and current tool availability take precedence. If a recommendation is unavailable, return the fact to 6 Pro instead of silently substituting.

- `codex`: **REQUIRED SUB-SKILL:** read and use `codex-delegate`. Delegate with local `collaboration.spawn_agent` in the current task, not a user-owned `create_thread`. Pass the frozen model/effort and a self-contained brief with non-`all` `fork_turns`; assign one writer per file and distinct paths if parallel. The generic skill's local dry-run is a preflight, not an OS sandbox. `network_allowed=false` and `max_agents=1` are defaults. The controller reviews the actual diff and reruns relevant checks independently.
- Historical ZCode records may be inspected with the original `zcode-delegate` protocol. This orchestrator does not select ZCode for new execution.

The first real use of the new Codex mode through this project orchestrator should be a small, low-risk, local-only one-writer task outside B4 evidence and R2; review it independently before considering integration proved. Do not consume a real research-run allowance for an integration test.

## Review, failure, and handoff

Compare every executor result with the frozen contract, exact changed paths, source documents, hashes, test output, and repository hygiene. For research, separate a correct calculation from reliable input facts and from strategy usefulness. Send the contract, actual diff/evidence, counterexamples and unresolved limits back to 6 Pro for final review; verify its comments against repository facts. Do not mark a milestone or OKR as complete before its own acceptance and authorization sequence.

On nonzero exit, provider failure, timeout, or no callback, inspect allowed and out-of-scope write paths for **partial writes** before classifying the attempt; preserve every partial artifact and record its provenance. Failure is not proof of zero side effects. A new executor requires a new authorization and record, not relabeling the old job. Stop when a source budget, qualification condition, strategy/money ambiguity, or required permission fails. No source collection, real factor run, production use, trading, deployment, commit, or scope reduction is inferred from the choice of executor.

Report to the user in plain Chinese: what 6 Pro decided, which mode/model/effort actually ran, what the controller independently checked, what remains unproven and unauthorized, and where the evidence is. Keep updates during lengthy work; never turn an executor's `completed` marker into a success claim.
