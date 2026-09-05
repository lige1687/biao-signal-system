import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type {
  RecommendCard,
  ReviewCard,
  SizingAdvice,
  TradePreview,
} from "../../types";

/** 推荐卡：前5标的+前3板块，symbol 可点击跳详情；「让AI讲讲」按需一次调用。 */
export function RecommendCardView({ card }: { card: RecommendCard }) {
  const [narrative, setNarrative] = useState<string | null>(null);
  const explain = useMutation({
    mutationFn: () => api.copilotRecommendExplain(""),
    onSuccess: (r) => setNarrative(r.reply),
  });
  return (
    <div className="cp-card">
      <div className="cp-label">
        今日推荐 · {card.run_date}（排序仅影响展示，不构成新判定）
      </div>
      {card.items.length === 0 && <div className="muted">今日无上榜标的。</div>}
      {card.items.map((it) => (
        <div key={it.symbol} className="cp-row">
          <Link to={`/symbol/${it.symbol}`} className="cp-sym">
            {it.display_name}
          </Link>
          <span className={`badge v-${it.verdict}`}>{it.verdict_cn}</span>
          {it.sentiment_cn && (
            <span className="cp-chip" title="散户情绪叙事标注（不参与判定）">
              {it.sentiment_cn}
            </span>
          )}
          <span className="muted">{it.reasons.slice(0, 3).join("；")}</span>
        </div>
      ))}
      {card.sectors.length > 0 && (
        <div className="cp-row">
          板块：
          {card.sectors.map((s) => (
            <span key={s.code} className="cp-chip">
              {s.name}·{s.stage_cn}
            </span>
          ))}
        </div>
      )}
      <div className="muted" style={{ fontSize: 11 }}>{card.disclaimer_cn}</div>
      {narrative && (
        <div className="cp-narrative">
          <span className="muted">AI讲解：</span>
          {narrative}
        </div>
      )}
      <button
        className="btn small"
        disabled={explain.isPending || !!narrative}
        onClick={() => explain.mutate()}
      >
        {explain.isPending ? "生成中…" : narrative ? "已讲解" : "让AI讲讲"}
      </button>
    </div>
  );
}

/** 报单确认卡：字段可改，确认后才落库（设计定稿 D1 红线）。 */
export function TradeConfirmCard({ preview }: { preview: TradePreview }) {
  const qc = useQueryClient();
  const [code, setCode] = useState(preview.fund_code ?? "");
  const [name, setName] = useState(preview.fund_name ?? "");
  const [amount, setAmount] = useState(
    preview.amount != null ? String(preview.amount) : "",
  );
  const [date, setDate] = useState(preview.trade_date);
  const create = useMutation({
    mutationFn: () =>
      api.copilotTradesCreate({
        fund_code: code.trim(),
        fund_name: name.trim() || code.trim(),
        side: preview.side,
        amount: Number(amount),
        trade_date: date,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["copilotTrades"] });
      qc.invalidateQueries({ queryKey: ["opsToday"] });
    },
  });
  const missingHint = preview.missing.length
    ? `待补：${preview.missing.join("、")}`
    : "信息已抽全，请核对";
  return (
    <div className="cp-card">
      <div className="cp-label">报单确认（{preview.side_cn}）· 确认后记入基金台账</div>
      <div className="muted" style={{ fontSize: 11 }}>
        {missingHint}。金额单位为元；定价按报单日基金净值（ETF按单位净值）。
      </div>
      <div className="cp-form">
        <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="基金代码（6位）" />
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="基金名称" />
        <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="金额（元）" />
        <input value={date} onChange={(e) => setDate(e.target.value)} placeholder="日期 YYYY-MM-DD" />
      </div>
      <button
        className="btn small primary"
        disabled={
          create.isPending ||
          create.isSuccess ||
          !/^\d{6}$/.test(code.trim()) ||
          !(Number(amount) > 0) ||
          !/^\d{4}-\d{2}-\d{2}$/.test(date)
        }
        onClick={() => create.mutate()}
      >
        {create.isPending ? "记账中…" : create.isSuccess ? "已记账" : "确认记账"}
      </button>
      {create.error && (
        <div className="cp-error">
          {create.error instanceof Error ? create.error.message : String(create.error)}
        </div>
      )}
    </div>
  );
}

export interface HoldingsData {
  active_plans: Array<{
    plan_id: string;
    symbol: string;
    state: string;
    valid_until: string;
  }>;
  fund_positions: Array<{
    fund_code: string;
    fund_name: string;
    shares: number;
    realized_pnl: number;
    market_value: number | null;
    unrealized_pnl: number | null;
  }>;
  hint_cn: string;
}

/** 持仓速览卡（计划 + 基金台账持仓）。 */
export function HoldingsCardView({ data }: { data: HoldingsData }) {
  return (
    <div className="cp-card">
      <div className="cp-label">持仓速览</div>
      {data.fund_positions.map((p) => (
        <div key={p.fund_code} className="cp-row">
          <span className="cp-sym">{p.fund_name}</span>
          <span className="muted">
            份额 {p.shares.toFixed(2)}
            {p.market_value != null && <> · 现值 {p.market_value.toFixed(0)} 元</>}
            {p.unrealized_pnl != null && (
              <> · 浮动 {p.unrealized_pnl >= 0 ? "+" : ""}{p.unrealized_pnl.toFixed(0)}</>
            )}
            {p.realized_pnl !== 0 && (
              <> · 已实现 {p.realized_pnl >= 0 ? "+" : ""}{p.realized_pnl.toFixed(0)}</>
            )}
          </span>
        </div>
      ))}
      {data.active_plans.map((p) => (
        <div key={p.plan_id} className="cp-row">
          <Link to={`/symbol/${p.symbol}`} className="cp-sym">{p.symbol}</Link>
          <span className="muted">
            计划 {p.state} · 有效期至 {p.valid_until}
          </span>
        </div>
      ))}
      {data.active_plans.length === 0 && data.fund_positions.length === 0 && (
        <div className="muted">暂无进行中的计划与基金持仓。</div>
      )}
      <div className="muted" style={{ fontSize: 11 }}>{data.hint_cn}</div>
      <Link to="/portfolio" className="cp-link">去「我的持仓」页</Link>
    </div>
  );
}

/** 复盘卡（单笔/周报共用）。 */
export function ReviewCardView({ review }: { review: ReviewCard }) {
  return (
    <div className="cp-card">
      <div className="cp-label">{review.title_cn}</div>
      {review.sections.map((s) => (
        <div key={s.heading_cn} className="cp-section">
          <div className="cp-sub">{s.heading_cn}</div>
          {s.lines.map((l, i) => (
            <div key={i} style={{ fontSize: 12 }}>{l}</div>
          ))}
        </div>
      ))}
      {review.r_multiple != null && (
        <div style={{ fontSize: 12 }}>
          R 倍数：{review.r_multiple.toFixed(2)}（当初准备亏的钱为1份，结果赚了几个1份）
        </div>
      )}
      {review.narrative && (
        <div className="cp-narrative">
          <span className="muted">AI复盘：</span>
          {review.narrative}
        </div>
      )}
    </div>
  );
}

/** 仓位档位卡（供推荐卡与档位端点共用展示）。 */
export function SizingAdviceView({ advice }: { advice: SizingAdvice }) {
  return (
    <div className="cp-card">
      <div className="cp-label">
        仓位建议 · {advice.tier}档 {advice.tier_pct_cn}
      </div>
      {advice.reasons.map((r, i) => (
        <div key={i} style={{ fontSize: 12 }}>· {r}</div>
      ))}
      <div className="muted" style={{ fontSize: 11 }}>
        {advice.strength_cn}；{advice.disclaimer_cn}
      </div>
    </div>
  );
}

/** 卡片分发（对话流内按 card_type 渲染）。 */
export function CopilotCardDispatcher({
  card,
  preview,
}: {
  card: { card_type: string; data: unknown } | null;
  preview: TradePreview | null;
}) {
  if (preview) return <TradeConfirmCard preview={preview} />;
  if (!card) return null;
  if (card.card_type === "recommend")
    return <RecommendCardView card={card.data as RecommendCard} />;
  if (card.card_type === "holdings")
    return <HoldingsCardView data={card.data as HoldingsData} />;
  if (card.card_type === "review")
    return <ReviewCardView review={card.data as ReviewCard} />;
  return null;
}

/** 基金台账区（持仓页挂载）：真实成交 + 持仓盈亏速览。 */
export function TradesLedgerView() {
  const q = useQuery({
    queryKey: ["copilotTrades"],
    queryFn: () => api.copilotTrades(),
  });
  if (q.isLoading) return <div className="muted">台账加载中…</div>;
  if (q.isError) return <div className="cp-error">台账加载失败</div>;
  const { trades, positions } = q.data ?? { trades: [], positions: [] };
  return (
    <div className="cp-card">
      <div className="cp-label">
        基金台账（真实成交 · 确认后记账 · 按报单日净值定价）
      </div>
      {positions.length > 0 && (
        <div className="cp-section">
          <div className="cp-sub">持仓与盈亏</div>
          {positions.map((p) => (
            <div key={p.fund_code} className="cp-row">
              <span className="cp-sym">{p.fund_name}（{p.fund_code}）</span>
              <span className="muted">
                份额 {p.shares.toFixed(2)} · 成本 {p.cost.toFixed(0)} 元
                {p.market_value != null && <> · 现值 {p.market_value.toFixed(0)} 元</>}
                {p.unrealized_pnl != null && (
                  <> · 浮动 {p.unrealized_pnl >= 0 ? "+" : ""}{p.unrealized_pnl.toFixed(0)}</>
                )}
                {p.realized_pnl !== 0 && (
                  <> · 已实现 {p.realized_pnl >= 0 ? "+" : ""}{p.realized_pnl.toFixed(0)} 元</>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="cp-section">
        <div className="cp-sub">成交记录</div>
        {trades.length === 0 && (
          <div className="muted">
            还没有记录。对 agent 说「我买了1万012414」即可报单。
          </div>
        )}
        {trades.map((t) => (
          <div key={t.trade_id} className="cp-row">
            <span>{t.trade_date}</span>
            <span className="cp-sym">{t.fund_name}</span>
            <span>{t.side_cn} {t.amount.toFixed(0)} 元</span>
            <span className="muted">
              {t.price_status_cn}
              {t.priced_nav != null && ` @${t.priced_nav.toFixed(4)}`}
            </span>
            {t.side === "sell" && t.price_status === "priced" && (
              <ReviewFetcher tradeId={t.trade_id} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/** 复盘触发器：按需拉取单笔/周复盘卡。 */
export function ReviewFetcher({
  weekly,
  tradeId,
}: {
  weekly?: boolean;
  tradeId?: string;
}) {
  const [card, setCard] = useState<ReviewCard | null>(null);
  const q = useMutation({
    mutationFn: () =>
      weekly ? api.copilotReviewWeekly() : api.copilotReviewTrade(tradeId!),
    onSuccess: setCard,
  });
  return (
    <div style={{ display: "inline" }}>
      <button
        className="btn small"
        disabled={q.isPending || !!card}
        onClick={() => q.mutate()}
      >
        {q.isPending ? "生成中…" : card ? "已生成" : weekly ? "本周复盘" : "复盘"}
      </button>
      {card && <ReviewCardView review={card} />}
    </div>
  );
}
