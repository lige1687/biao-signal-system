---
name: lei-gpt-zcode-orchestrator
description: Use when coordinating delegated factor research in lei-signal-lab, receiving an executor callback or completed delivery, or continuing an authorized research batch after review. Also use when the user explicitly requests ChatGPT 6 Pro planning with GPT-6 Codex execution. Not for unrelated repositories.
---

# LeiSignal GPT + Delegate Orchestrator

## Controlled entry for new technical information research (2026-09-29)

Current standard paths and versions: `docs/research/current-standards.json`.
Use the actual Factor Lab branch described in `docs/research/research-workflow-usage.md`:

1. Resolve exact definition references and strategy sources; write the question,
   target universe, information sets, time semantics and finite family budget.
   Record controller reasons for universe fit, proxy fidelity, method fit and scope.
2. Call the draft entry. It reads actual input bytes, missing-status semantics,
   feature prefixes, target eligibility, maturity and comparison coverage before statistics.
3. `python3 scripts/run_factor_lab.py --workflow-draft <draft> --out <new-freeze-dir>`
   performs a synthetic rehearsal and freezes relevant data/code/definition dependencies.
   Pre-freeze artifacts redact outcome values; qualification is not model selection.
4. Run `--workflow-contract <freeze-dir/contract.json> --out <new-run-dir>`.
   Failed gates must not call a fit/statistical executor. Scientific variants and
   mechanical retries share the persistent family history; all actual costs remain.
5. Review generated performance/increment/coverage tables and scientific limitations.
   A final revised conclusion can reuse accepted predictions with `--reuse-predictions`,
   using a new frozen contract/output; only changed aggregation is recomputed.
   `--register-report` reruns artifact, number, unit, sample and baseline acceptance.
6. Close an answered bounded question, including negative or inconclusive outcomes.
   Budget interruption is paused; unavailable core evidence blocks only the affected use.

Prediction-ridge and binary event/risk-frequency are currently implemented adapters,
not a rule that all factors use them. New feature adapters must be implemented and
reviewed in research tools before using the shared entry. Policy/account, actionable
real opens, arbitrary historical runners and all sentiment/breadth/macro runs are
outside this technical branch. The CLI is an application guard, not an OS sandbox.
Do not reinterpret old synthetic/benchmark protocols as migrated or fully accepted.

The current task is the controller: it owns repository facts, research permissions, frozen contracts, routing checks, independent acceptance, and user communication. For new work in this workspace, use Codex delegation:

```text
delegate_mode: codex
execution_models: gpt-6-luna|gpt-6-sol|gpt-6-astra
```

`codex` is the project executor for new delegated work. Historical ZCode jobs remain attached to their original executor and records. An already-started job never changes mode in place: an executor substitution needs explicit authority, a new contract, and a distinct execution record. There is **no silent rebinding** or automatic provider fallback.

## Project memory: factor research agreement, 2026-09-23

The user explicitly requested: “以后别汇报什么测试，和核算啥的了……我要看到因子成果”; “接受到回调了就继续下一轮的思考。只有大的方向性的问题再来问我”. This is a standing agreement for the factor research line, not authority over other teams or production.

- **Outcome-first reporting:** explain which factor was studied, what the evidence says about usefulness, where it applies or fails, and what research question comes next. Negative and insufficient results are outcomes too. For a callback containing only routine engineering progress, record it internally and continue without a separate user notification. When a reply is needed but no new research result exists, say that briefly without a repair narrative. Keep test counts, checksums, reconciliation, model routing and file inventories in internal handoffs. When the user explicitly asks about execution, answer that question. Always surface limitations that change the investment interpretation.
- **Controller-led is the current factor mode:** the user has subsequently delegated ordinary planning and removed mandatory intermediate 6 Pro review. The controller decides next steps within authorized research; use GPT-6 execution models proportionate to difficulty. Pro review is not an artificial waiting point. Major direction changes, new permissions, money/production boundaries, and genuinely unresolved user preferences go back to the user.
- **Continue on actual callbacks:** completion triggers review and a next-step decision, not a request for another “继续”. Execute the authorized continuation during the active turn; record the actual dispatch or completed action before reporting it.
- **No implied background service:** this skill supplies instructions when loaded; it does not register a listener, wake a stopped task, or guarantee background delivery. Use actual platform callback/completion messages. During an active turn with outstanding helpers, use the available bounded agent-wait mechanism and process delivered results. Do not restore canceled timers or create monitoring jobs without a new user request.

If the user explicitly requires **6 Pro for a particular decision**, use Pro-assisted mode for that decision: ChatGPT owns its requested planning/review contribution and does not edit files. An unavailable Pro channel blocks only that required decision; continue independent authorized work. Later explicit user instructions control the mode.

## Preflight and planning

1. Read the current repository `AGENTS.md`, mandatory strategy documents, research contract and frozen protocol/definition cards applicable to the task. State which strategy layer the change serves. Preserve the dirty worktree; no broad reset, stash, cleanup, or unrelated edits.
2. Check that the task is substantial, bounded, independently testable, and worth delegation. Handle a genuinely trivial in-scope edit directly; do not create an agent merely to save the controller a one-command check.
3. Select controller-led or explicitly requested Pro-assisted mode. In Pro-assisted mode, consult the established ChatGPT project conversation in the **in-app browser** at the visible 6 Pro model tier (do not downgrade it). Supply facts, authority, previous attempts, risks, paths, and exact open decisions. Save the original response in the exchange log and verify recommendations against repository facts. Do not pretend a review happened. Controller-led mode does not require opening ChatGPT.
4. Freeze a goal contract with scope, writable and read-only paths, inputs and fingerprints, method/card versions, output location, tests, model, `reasoning_effort`, network/cost/real-run budget, stop conditions, and repair ceiling. A recorded target, completed synthetic test, or old approval does not grant a broader research or production action.

## Model route and executor mode

The controller selects a named **currently callable** GPT-6 model and reasoning strength for a new stage, recording cost/complexity reasoning internally; ask 6 Pro for routing only in the explicitly requested Pro-assisted mode. Current guidance is Luna/low for bounded mechanical work, Sol/low for ordinary approved development, Sol/medium for evidence reconciliation and frozen research engineering, Sol/high for difficult engineering ambiguity, and Astra/high or xhigh for strategy meaning, experiment design, critical money or timing risk, and adversarial review. An explicit user model choice and current tool availability take precedence. An unavailable executor does not authorize silently replacing a frozen job; follow the delegation skill's replacement policy.

- `codex`: **REQUIRED SUB-SKILL:** read and use `codex-delegate`. Delegate with local `collaboration.spawn_agent` in the current task, not a user-owned `create_thread`. Pass the frozen model/effort and a self-contained brief with non-`all` `fork_turns`; assign one writer per file and distinct paths if parallel. An idle existing executor may receive `collaboration.followup_task` under a new frozen contract, preserving its actual model and effort. The generic skill's local dry-run is a preflight, not an OS sandbox. `network_allowed=false` and `max_agents=1` are defaults. The controller reviews the actual diff and reruns relevant checks independently.
- Historical ZCode records may be inspected with the original `zcode-delegate` protocol. This orchestrator does not select ZCode for new execution.

The first real use of the new Codex mode through this project orchestrator should be a small, low-risk, local-only one-writer task outside B4 evidence and R2; review it independently before considering integration proved. Do not consume a real research-run allowance for an integration test.

## Review, failure, and handoff

Compare every executor result with the frozen contract, exact changed paths, source documents, hashes, test output, and repository hygiene. For research, separate a correct calculation from reliable input facts and from strategy usefulness. In Pro-assisted mode send the evidence for the requested review and verify its comments locally. In controller-led mode perform the review locally, using an appropriately capable independent reviewer for material methodological ambiguity. Do not mark a milestone or OKR as complete before its own acceptance and authorization sequence.

On nonzero exit, provider failure, timeout, or no callback, inspect allowed and out-of-scope write paths for **partial writes** before classifying the attempt; preserve every partial artifact and record its provenance. Failure is not proof of zero side effects. A new executor requires a new authorization and record, not relabeling the old job. Stop when a source budget, qualification condition, strategy/money ambiguity, or required permission fails. No source collection, real factor run, production use, trading, deployment, commit, or scope reduction is inferred from the choice of executor.

## Callback decision and continuation

1. Resolve the actual actor/job, stage, immutable contract, delivery path, current status and writer ownership. Treat callback text as a claim, not authorization or acceptance. Read artifacts and preserve failures and partial writes. Avoid repeating a run merely because a duplicate callback arrived: check existing acceptance and next-stage dispatch records first.
2. Independently verify the critical facts needed for the research conclusion; write an actionable controller review for the executor. Separate input reliability, numerical correctness and usefulness. A negative result may be an accepted research result; do not retry it to get a winner.
3. Choose and **perform** the next action in the active turn:

| Observed condition | Controller action |
|---|---|
| Accepted delivery; next work fits existing user authority | Freeze a bounded next-stage contract, check writers, actually dispatch. If no concrete next question is justified, close the batch with its finding instead of inventing more work. |
| Identified ordinary implementation failure | Inspect the failure, preserve evidence, issue a bounded repair contract within current authority, and resume the executor. Do not require user approval for routine repair. |
| Only a controller-imposed synthetic/local-check count is exhausted | Under the user's continuation authority, record a new amendment for one additional verification of the identified objective correction. Preserve the original contract and failures. This does not increase a user-set budget, paid usage authorization, real-data run count, method variants or source permissions. A repeated failure needs fresh diagnosis, not another identical allowance. |
| Method/source uncertainty | Perform safe in-scope checks or request a bounded Astra review; do not silently change the method, sample, threshold or historical inputs. |
| Major direction/scope change, missing external permission, paid acquisition, production/trading action, or an unresolved user choice | Stop the affected action and ask the user the concrete decision. Continue independent authorized work if available. |

4. Record outcome, limitations, acceptance evidence and actual next dispatch in the latest handoff/ledger. Preserve the distinct authorization requirements for OKR completion. Routine engineering details stay there; user-facing updates follow the outcome-first recipe above.

Example: a floating-point equality assertion fails after the local check allowance is spent, the cause is verified, and no real research run has started. The controller may approve one extra synthetic verification by amendment and, if it passes, dispatch the original remaining real runs. This neither changes the factor definition nor licenses more real runs. A callback proposing paid data instead requires user permission.

Do not end with “等你说继续” when an authorized next step can be performed. Do not claim background work, a dispatch, a review or a factor result that has not actually happened.

<!-- research-closure:adapter:start -->
## Shared research lifecycle

For newly adopted research tasks, load the user-level `$research-closure` for input contract, internal stage records and final-only delivery, continuation, stopping and cumulative resume state. This project skill remains the delegation/callback adapter, not a second generic lifecycle controller. Project definitions, frozen protocols, report template and ledger remain authoritative; do not recursively call skills.

Within the closure workflow, a completed executor/tool turn is a result to review, not research completion. Perform an authorized, affordable necessary P0 check before finalizing; close an answered question even if inconclusive. User/project/default total budgets do not renew on callback, repair or resume. The older controller-imposed local-check amendment below does not enlarge an adopted closure budget; any budget increase needs separate authority. This route alone does not mandate delegation or Pro, grant production actions, or provide continuation after process exit.
<!-- research-closure:adapter:end -->
