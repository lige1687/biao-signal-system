export interface PortfolioTurn {
  id: string;
  role: "user" | "assistant";
  text: string;
  status?: "pending" | "complete" | "failed";
  cid?: string;
  fallback?: string;
  verifyNote?: string;
  questionId?: number | null;
  grounded?: boolean;
  retry?: { message: string; client_request_id: string; portfolio_holding_id: string | null };
}

export interface PortfolioChatState {
  sessionId: string | null;
  draft: string;
  turns: PortfolioTurn[];
}

export function portfolioScopeKey(holdingId: string | null): string {
  return `lei.portfolio.agent.v1:${holdingId === null ? "all" : `holding:${encodeURIComponent(holdingId)}`}`;
}

export function emptyPortfolioChat(): PortfolioChatState {
  return { sessionId: null, draft: "", turns: [] };
}

export function loadPortfolioChat(storage: Pick<Storage, "getItem">, holdingId: string | null): PortfolioChatState {
  try {
    const raw = storage.getItem(portfolioScopeKey(holdingId));
    if (!raw) return emptyPortfolioChat();
    const data = JSON.parse(raw);
    if (!data || !Array.isArray(data.turns)) return emptyPortfolioChat();
    return {
      sessionId: typeof data.sessionId === "string" ? data.sessionId : null,
      draft: typeof data.draft === "string" ? data.draft : "",
      turns: data.turns.filter((turn: unknown) => {
        if (!turn || typeof turn !== "object") return false;
        const candidate = turn as PortfolioTurn;
        return (candidate.role === "user" || candidate.role === "assistant") && typeof candidate.text === "string";
      }).map((turn: PortfolioTurn) => turn.status === "pending"
        ? { ...turn, status: "failed" as const,
          text: turn.text || "上次连接中断，可重试原问题。" } : turn),
    };
  } catch { return emptyPortfolioChat(); }
}

export function savePortfolioChat(storage: Pick<Storage, "setItem">, holdingId: string | null,
                                  state: PortfolioChatState): boolean {
  try {
    storage.setItem(portfolioScopeKey(holdingId), JSON.stringify(state));
    return true;
  } catch { return false; }
}

export function isCurrentScope(requestScope: string, currentHoldingId: string | null): boolean {
  return requestScope === portfolioScopeKey(currentHoldingId);
}
