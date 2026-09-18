# LeiSignal GPT + ZCode Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Do not dispatch subagents for this small local installation.

**Goal:** Install a local `lei-gpt-zcode-orchestrator` Skill that coordinates GPT-6 Pro review, ZCode execution, and Codex acceptance for `lei-signal-lab`.

**Architecture:** The Skill is a thin repository-specific orchestrator stored under `~/.codex/skills`. It does not duplicate either executor: it invokes `codex-with-chatgpt` for review and `zcode-delegate` for bounded execution, while the current Codex task owns repository checks and final acceptance. GPT recommends the ZCode profile for every new job, stage, and repair; Codex validates that the recommendation is supported and available.

**Tech Stack:** Codex Skill Markdown, YAML UI metadata, existing `codex-with-chatgpt`, existing `zcode-delegate`, Python Skill validator.

## Global Constraints

- Install only in `/Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator`; do not edit project business code.
- Preserve all unrelated dirty worktree changes in `/Users/yongbiaoli/Desktop/lei-signal-lab`.
- The Skill applies only to `lei-signal-lab`; it is not a generic cross-repository workflow.
- GPT recommends the ZCode model and reasoning profile; Codex performs only protocol, availability, scope, and safety validation.
- ZCode never decides strategy ambiguity, production adoption, real trading, funding, or final acceptance.
- The installed Skill must direct technical work to read the repository's current `AGENTS.md` and required domain documents rather than copying stale policy text.
- Automatic Skill discovery remains enabled.

---

### Task 1: Install the repository-specific orchestrator Skill

**Files:**

- Create: `/Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator/SKILL.md`
- Create: `/Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator/agents/openai.yaml`

**Interfaces:**

- Consumes: `$codex-with-chatgpt`, `$zcode-delegate`, and `/Users/yongbiaoli/Desktop/lei-signal-lab/AGENTS.md`.
- Produces: discoverable Skill `$lei-gpt-zcode-orchestrator`.

- [ ] **Step 1: Confirm the target is not already installed**

Run:

```bash
test ! -e /Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator
```

Expected: exit code `0`. If the directory exists, inspect it and update it narrowly instead of initializing over it.

- [ ] **Step 2: Initialize the Skill directory and UI metadata**

Run:

```bash
python3 /Users/yongbiaoli/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  lei-gpt-zcode-orchestrator \
  --path /Users/yongbiaoli/.codex/skills \
  --interface 'display_name=Lei GPT + ZCode Orchestrator' \
  --interface 'short_description=Review, delegate, and verify substantial LeiSignal work' \
  --interface 'default_prompt=Use $lei-gpt-zcode-orchestrator to review, execute, and independently verify this LeiSignal task.'
```

Expected: exit code `0`, with `SKILL.md` and `agents/openai.yaml` created.

- [ ] **Step 3: Replace the scaffold with the approved instructions**

Write this complete content to `SKILL.md`:

```markdown
---
name: lei-gpt-zcode-orchestrator
description: Coordinate GPT review, bounded ZCode execution, and independent Codex acceptance for substantial work in the local lei-signal-lab repository. Use when the user asks for the Lei collaboration workflow or wants GPT and ZCode to work together on that project; do not use for unrelated repositories.
---

# LeiSignal GPT + ZCode Orchestrator

Coordinate existing skills; do not replace them. The current Codex task owns the goal, repository state, permissions, strategy interpretation, and final acceptance. GPT reviews and recommends execution routing. ZCode performs only frozen, bounded work.

## Scope and required skills

Use this only when the target workspace is `/Users/yongbiaoli/Desktop/lei-signal-lab` or the user explicitly identifies that repository.

Read these skills completely before invoking them:

- `/Users/yongbiaoli/.agents/skills/codex-with-chatgpt/SKILL.md` for GPT planning or review;
- `/Users/yongbiaoli/.codex/skills/zcode-delegate/SKILL.md` before any ZCode dispatch.

Always read the repository's current `AGENTS.md`. Before technical changes, read every strategy document it marks mandatory. For research, backtests,收益解释, or work affecting real-money decisions, also read the current research contract, definition standard, applicable `id@version` cards, frozen protocol, and report/archive rules routed by `AGENTS.md`.

## Route by task size and risk

- Small, clear edit: Codex handles it directly. Add GPT review only when the user requests it or the change carries strategy or high-impact risk. Do not pay ZCode's fixed context cost.
- Substantial, bounded work: use the full flow below.
- Strategy ambiguity, parameter changes, timing or funding risk: GPT may identify options, but do not dispatch ZCode until Codex resolves repository facts and the user decides any meaning-changing ambiguity.

Do not infer production adoption, real trading, funding, OKR updates, or permission to change frozen research from a request to implement or study something.

## Full flow

1. **Preflight.** Restate the outcome and exclusions. Inspect Git state and existing implementation. Map the work to the repository's strategy layer, or explicitly state that it is engineering-only and does not change strategy. Preserve unrelated changes.
2. **GPT pre-review.** Invoke `codex-with-chatgpt` explicitly with ChatGPT/GPT, not its provider default. Give GPT the goal, exclusions, relevant repository rules, proposed paths, risks, acceptance evidence, and unresolved questions. Ask for an independent understanding, risks, alternatives, missing acceptance checks, and user decisions.
3. **Freeze the contract.** Record goals, non-goals, writable/protected paths, stages, evidence, commands, network/dependency/cost boundaries, stop conditions, and a three-repair maximum. For research, bind current document versions and fingerprints, object `id@version`, inputs, frozen protocol, research family, and known attempts.
4. **Decide whether to delegate.** Use ZCode only if the work is substantial, independently testable, free of unresolved strategy decisions, isolated from unrelated edits, and reviewable by Codex.
5. **Let GPT recommend routing.** Before every new ZCode job, normal stage, and repair, give GPT the actual work and evidence. Ask it to recommend one profile currently supported by `zcode-delegate` and explain the choice in plain language. A profile chooses both model and reasoning strength.
6. **Validate, do not silently override.** Codex checks that the recommended profile is supported, available, within the frozen scope, and permitted by the current `zcode-delegate` protocol. If it is invalid or unavailable, report the facts to GPT and ask it to choose again. If GPT cannot re-review, stop delegation instead of silently switching models. Record the recommendation, actual profile, reason, and any fallback.
7. **Dispatch and review stages.** Follow `zcode-delegate` exactly. Dispatch one closed stage at a time. A callback or completed marker is only a checkpoint. Inspect the real diff and artifacts and run fresh checks. Stage advances do not consume repair budget; the whole job has at most three dispatched repairs.
8. **Codex acceptance.** Verify every frozen goal using repository evidence. Check protected areas, strategy language, data timing, costs, funds, archive rules, and directory hygiene as applicable. A passing test proves only what that test covers; it does not prove research value or authorize production.
9. **GPT final review.** Give GPT the frozen contract, actual changes, independent test evidence, and known limits. Ask it to find omissions, counterexamples, strategy or permission overreach, future-data/timing/accounting problems, and unsupported completion claims. Codex verifies each comment against repository facts.
10. **Finish or stop.** Report completion only when artifacts exist, Codex checks pass, and GPT has no unresolved blocking issue. Otherwise report the exact failed goal, evidence, remaining repair budget, and required user decision.

## ZCode routing boundary

Use only profiles currently declared by `zcode-delegate`. At installation time they are:

- `flash-high`: mechanical work with GLM-5.3-Flash and high reasoning;
- `glm-high`: bounded diagnosis or implementation choices with GLM-5.3 and high reasoning;
- `glm-max`: genuinely difficult work or evidence-based escalation with GLM-5.3 and maximum reasoning.

Treat that list as a snapshot. The loaded `zcode-delegate` Skill is authoritative if profiles change. GPT recommends; Codex still performs the selection-and-recording step required by that protocol by adopting the valid recommendation.

## Failure handling

- GPT unavailable: preserve local state and pause only the GPT-dependent stage. Do not pretend a review occurred.
- ZCode dispatch or callback interrupted: inspect the existing job and bound session using `zcode-delegate`; never resend blindly or create a duplicate job.
- Overlapping workspace changes: stop writes to affected files and report the conflict. Do not reset, overwrite, or stage the whole repository.
- Missing or conflicting authority: stop the affected branch and ask the user. Continue only independent work.
- Failed checks: preserve evidence and separate new failures from pre-existing environment failures.

## User-facing updates

Use plain Chinese to say whether the work is in review, execution, verification, repair, or waiting for a decision. Final delivery names what GPT and ZCode actually did, what Codex independently verified, any fallback, what remains unauthorized, and clickable artifact paths.
```

After replacing the scaffold, keep `agents/openai.yaml` exactly as generated from the interface values above. Automatic invocation remains at its default enabled setting; do not add an explicit-only policy.

- [ ] **Step 4: Inspect the installed metadata**

Run:

```bash
sed -n '1,240p' /Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator/SKILL.md
sed -n '1,120p' /Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator/agents/openai.yaml
```

Expected: the frontmatter name matches the folder; `default_prompt` explicitly contains `$lei-gpt-zcode-orchestrator`; no scaffold placeholder remains.

### Task 2: Validate installation and decision boundaries

**Files:**

- Test: `/Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator/SKILL.md`
- Test: `/Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator/agents/openai.yaml`

**Interfaces:**

- Consumes: installed Skill from Task 1.
- Produces: validation evidence and scenario review for user handoff.

- [ ] **Step 1: Run the official Skill validator**

Run:

```bash
python3 /Users/yongbiaoli/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/yongbiaoli/.codex/skills/lei-gpt-zcode-orchestrator
```

Expected: exit code `0` and `Skill is valid!`.

- [ ] **Step 2: Review five routing scenarios against the installed instructions**

Read the installed Skill and confirm these observable outcomes:

1. A one-line display fix remains with Codex and does not invoke ZCode.
2. A substantial multi-file feature receives GPT pre-review, a frozen contract, GPT profile recommendation, ZCode stages, Codex checks, and GPT final review.
3. An undefined strategy threshold stops before ZCode and asks the user after checking repository authority.
4. A research task binds current research rules and does not treat passing code as production approval.
5. An unavailable GPT or invalid profile pauses the dependent stage and never silently swaps models or claims a review occurred.

Expected: every outcome is directly required by the installed Skill with no conflicting instruction.

- [ ] **Step 3: Confirm repository hygiene and untouched user changes**

Run:

```bash
cd /Users/yongbiaoli/Desktop/lei-signal-lab
python3 scripts/check_repo_hygiene.py
git status --short
```

Expected: hygiene passes; the status contains the user's pre-existing changes but no project business-code change from this installation.

- [ ] **Step 4: Report installation**

Report the installed name `$lei-gpt-zcode-orchestrator`, its absolute `SKILL.md` path, validation result, and one minimal invocation example. Note that a newly opened Codex task will discover it; the ChatGPT website and ZCode do not independently load the local Skill.
