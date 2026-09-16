import {planDraftFromArtifact} from './plan-card.mjs';
import fs from 'node:fs';
const artifact=JSON.parse(fs.readFileSync(new URL('./known-artifact.json',import.meta.url)));
const {draft}=planDraftFromArtifact(artifact);
const symbol="000001.SS",sessionId="sess_30064dfbb741",questionId=10,clientRequestId='controller-known-draft',rulesetVersion='test';
const payload=({
    symbol,
    module: draft.module,
    direction: draft.direction,
    ruleset_version: rulesetVersion,
    reason: "对话式建计划（agent 引导）",
    entry_rule_id: draft.entry_rule_id ?? null,
    entry_trigger_cn: draft.entry_trigger_cn ?? "",
    entry_price_ref: null,
    invalidation_price: draft.invalidation_price ?? null,
    valid_until: draft.valid_until ?? "",
    thesis_cn: draft.thesis_cn ?? "",
    invalidation_criteria_cn: draft.invalidation_criteria_cn ?? "",
    drawdown_playbook_cn: draft.drawdown_playbook_cn ?? "",
    take_profit_plan_cn: draft.take_profit_plan_cn ?? "",
    stop_plan_cn: draft.stop_plan_cn ?? "",
    target_b_price: draft.target_b_price ?? null,
    client_request_id: clientRequestId,
    source_session_id: sessionId ?? null,
    source_question_id: questionId ?? null,});
console.log(JSON.stringify({draft,payload}));
