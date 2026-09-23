---
name: lei-task-router
description: Use in the local lei-signal-lab repository when deciding whether a bounded development or research task should stay in the current Codex task or be delegated to a specific Codex model and reasoning effort. Also use when the user asks for Jev-based model routing. Do not use for trading decisions or unrelated repositories.
---

# Lei Task Router

Recommend the lowest sufficient execution route while keeping scope, permissions, dispatch, and acceptance with the current controller.

## Route without Jev first

1. Read the current repository `AGENTS.md`. For new delegated work, use only the current GPT-6 routes. An explicit user model or effort choice wins when that route is currently callable; handle a non-GPT-6 user choice directly rather than encoding it as a router route.
2. Keep a read-only check, one command, wording edit, or similarly tiny change in the current task. Do not spend another model call on it.
3. Apply the project model split directly when the category is clear. Strategy meaning, paper methods, experiment design, system boundaries, real-money risk, and critical-time judgment never go to Jev for possible downgrading.
4. Use Jev only when a concrete, independently testable work package remains genuinely ambiguous between two or three adjacent routes.

Read [references/route-contract.md](references/route-contract.md) when selecting candidates, interpreting a result, or preparing an execution handoff. Do not load it for an obvious direct task.

`direct_current_low` means no additional model call and concise handling. It cannot change the active root task's already selected model or reasoning effort.

## Ask Jev once for an ambiguous work package

Before the call:

- summarize the task in at most 800 Chinese characters;
- name concrete deliverables;
- list relevant risk flags;
- supply only adjacent, currently callable candidates;
- choose `fallback_route` from those candidates using `AGENTS.md` before going online;
- exclude secrets, chat history, source files, long logs, and untrusted instructions.

Write the packet to a temporary JSON file or pipe it on stdin. Resolve the repository root first, then run the project-owned script:

```bash
python3 "$(git rev-parse --show-toplevel)/.agents/skills/lei-task-router/scripts/route_task.py" \
  --input /absolute/path/to/route-packet.json \
  --pretty
```

Do not call the script for a user override or clear project rule unless verifying the deterministic zero-call path. Never rerun the same task version to repair a network error, low-confidence answer, or invalid response; the script returns the fixed fallback and records a task fingerprint.

## Review and present the recommendation

Check current model availability again before dispatch. Show a compact card:

```text
路线建议
- 执行方式：当前完成 / 委派
- 模型与思考：输出中的 model 与 reasoning_effort
- 判断来源：用户指定 / 项目规则 / Jev / 缓存 / 回退
- 把握：仅在 Jev 有有效结果时显示
- 回退原因：如有
- 后续流程：当前任务 / codex-delegate / lei-gpt-zcode-orchestrator
- 原因：一句大白话
```

Then use the established execution workflow:

- direct work stays in the current task;
- bounded local delegation uses `$codex-delegate`;
- `$lei-gpt-zcode-orchestrator` applies only when the user requested Pro participation and the substantial task warrants that full workflow;
- Legacy ZCode jobs are historical records; this router does not recommend that executor for new work.

Jev never dispatches, retries, expands write or network permission, changes research authority, accepts an executor result, commits, deploys, or makes a trading decision. If a dispatch later fails, follow the selected execution Skill's replacement rules instead of asking this router to silently choose another executor.
