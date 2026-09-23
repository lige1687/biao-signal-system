# Lei Task Router Contract

Contract version: `2.0.0`

Read this reference only when a `lei-signal-lab` task needs a model or delegation route.
The current repository `AGENTS.md` and an explicit user choice always take precedence.

## Legal routes

| Route | Model and effort | Use |
|---|---|---|
| `direct_current_low` | active task, concise reasoning | A read-only check, one command, wording edit, or change too small to justify another model call. This does not change the active root model or effort. |
| `luna_low` | `gpt-6-luna`, low | A bounded small script, fixed format conversion, local mechanical patch, or already-defined test helper. Confirm availability first. |
| `sol_low` | `gpt-6-sol`, low | Ordinary feature work with an approved design, a few connected files, or a routine refactor. |
| `sol_medium` | `gpt-6-sol`, medium | Ordinary research adaptation, frozen experiment execution, general investigation, or evidence synthesis. |
| `sol_high` | `gpt-6-sol`, high | A difficult engineering investigation that survived earlier attempts or complex evidence reconciliation. |
| `astra_high` | `gpt-6-astra`, high | Strategy meaning, paper methodology, experiment design, system boundaries, or an important architecture decision. |
| `astra_xhigh` | `gpt-6-astra`, xhigh | Final judgment involving real money, a critical time point, or adversarial review spanning strategy, data, and execution. |

Choose the lowest route that is sufficient. Never lower the route for strategy, method, real-money, or critical-time risk merely to save cost.

## Jev candidate sets

Jev is permitted only when fixed rules leave two or three adjacent routes:

```text
direct_current_low,luna_low
luna_low,sol_low
sol_low,sol_medium
sol_medium,sol_high
sol_high,astra_high
astra_high,astra_xhigh
```

A three-route set must be three consecutive routes in the table. Do not ask Jev to reconsider a user override, a project hard rule, an obvious direct task, or a clearly classified task.

Version 2 replaces the former Spark and Terra route IDs. Old route packets are invalid, and the versioned fingerprint prevents old cached choices from being reused. Each recommendation returns the selected `model` and `reasoning_effort`; `direct_current_low` returns null for both because it keeps the active task unchanged.

## Adoption gate

A Jev answer is usable only when:

- the answer selects one supplied candidate;
- every probability is finite and between 0 and 1;
- probabilities sum to between 0.98 and 1.02;
- the selected route has the maximum probability;
- top probability is at least 0.60;
- the gap from first to second is at least 0.15.

Otherwise return a fixed-rule fallback. Never retry automatically.

## Sources and fallback reasons

Valid sources:

- `user_override`
- `project_rule`
- `jev`
- `cache`
- `fallback`

Valid fallback reasons:

- `key_unavailable`
- `network_error`
- `timeout`
- `http_error`
- `invalid_response`
- `low_confidence`
- `model_unavailable`

## Execution handoff

- Direct work stays in the current task.
- Bounded local delegation uses `$codex-delegate`.
- Use `$lei-gpt-zcode-orchestrator` only when the user requested Pro participation and the task is substantial enough to justify it.
- The old ZCode channel is outside this GPT-6 execution route. Historical jobs remain available for inspection through their original records.

The router recommends. The controller still freezes scope and permissions, dispatches, reviews the actual result, and communicates with the user.
