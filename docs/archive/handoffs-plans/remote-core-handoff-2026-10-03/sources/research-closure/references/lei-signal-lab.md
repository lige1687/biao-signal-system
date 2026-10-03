# LeiSignal adapter (only in lei-signal-lab)

The global skill supplies lifecycle rules, not trading meaning or a new project controller. Read the current project's `AGENTS.md` and its required strategy documents first. Use these existing authorities with actual versions/fingerprints from the adopted protocol:

- `docs/research/experiment-backtest-principles.md` v1.1: research design/acceptance.
- `docs/research/ai-execution-contract.md` v1.0.1: execution/handoffs; controller's written review.
- `docs/research/definition-standard.md` and `definitions.v1.json`: exact `id@version`, not inferred color meanings.
- `docs/research/experiment-report-template.md`: project reports and minimal decision card for return experiments.
- `docs/research/research-question-method-standard.md`, `factor-increment-evidence-standard.md`: adopt explicitly for new relevant research; `src/lei_signal/research/question_contract.py` validates its question/evidence blocks only.
- Existing protocol, family trial ledger, manifest and output directory first. `scripts/run_factor_lab.py` and factor-lab runner run calculations, not a general agent-resume service. Do not alter the production engine for skill installation.
- `.agents/skills/lei-gpt-zcode-orchestrator/SKILL.md`: project delegation, callbacks and controller ownership when that workflow applies. This adapter does not call it recursively or mandate delegation/Pro.

Freeze existing protocols untouched. Put this lifecycle state in an optional `closure` member only for a newly adopted compatible manifest, or a small companion checkpoint under that experiment's raw directory. Never relabel old experiments as compliant or reset their budgets. The closure default budget cannot authorize an increase to an existing user/project budget.

Reports remain `docs/experiments/<topic>-YYYY-MM-DD.md` with `## 一句话结论（大白话）`, registry category from `registry.json`, and archive section when closing. Registry conclusions and execution status have different meanings: `mixed` may accompany `completed + inconclusive` or `paused`; record both explicitly. Existing raw paths must not move. Run repository hygiene at task close. No OKR completion or production authority is inferred from the report.
