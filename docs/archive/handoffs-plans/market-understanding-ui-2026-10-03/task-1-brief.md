# Task1: Reviewed content promoted into application

Working directory: this repository root in an isolated checkout
Read the plan Global Constraints and Task1 only. Coordination already registered c4ec1ccd; do not fetch/update remote yourself.
Only write content.ts and content-data.json inside web/src/features/market-understanding/, plus this directory/task-1-report.md. No other file edits/commits; controller writes page/adapter/tests concurrently. No network or research. Preserve dirty files. Do not read credentials or strategy originals.

Export these interfaces and named constants from content.ts:
- type Market = "cn" | "us"; type Method = "trend" | "dca" | "value";
- type TopicId = "trend" | "position" | "leverage" | "volatility" | "economy" | "valuation" | "etf" | "method";
- topics: {id:TopicId,title:string,question:string,href:string}[];
- methods: {id:Method,title:string,goal:string,order:TopicId[]}[];
- roles: {title:string,goal:string,reads:string}[]; derive 10 from existing report table, explain not all institutions same.
- catalogue: {id:string,title:string,markets:Market[],topic:TopicId,frequency:string,reading:string,coverage:string,sourceUrl:string}[]; exactly 50 from density original_cells (retain original four cells in content-data.json source record), no speculative availability improvement. Parse market applicability manually from cells; A/美 both. Report uncertainties.
- cards: {id:string,title:string,markets:Market[],topic:TopicId,question:string,definition:string,frequency:string,rising:string,falling:string,level:string,combine:string[],counterexample:string,threshold:string,coverage:string,limitation:string,sourceIds:string[]}[]; exactly12 from originalcard payload; no latest numeric values, do not retain fake live fields. M12 event label not scalar. M01 live mapping controller only margin_balance. M11 shares both not actual feed.
- sources: {id:string,title:string,url:string,limitation:string}[]; resolve allcard sourceIds from ledger(s); when sourceID missing search existing atlas source ledger, no new browsing, report unresolved IDs (do not invent links).
- contentVersion:string; reportUrl:string; draftUrl:string pinned to d58a0740502207ca6dfeb9c9f18b1c135aa54632 on targetgithubrepo.

Use datajson as production-owned copy with provenance; content.ts typed exports and short explicit maps. Avoid opaque casts that hide missingfields. Separate high/low from rising/falling, don't add thresholds. All explanatory Chinese readable. No automated trading advice. Do not rewrite existing archived report.

Verify counts, duplicateIDs, source links, topicIDs. Runtime module cannot import archivedraw. Report exact checks+concerns to task-1-report.md and return concise summary. If unable to resolve critical source, markunknown rather than infer.
