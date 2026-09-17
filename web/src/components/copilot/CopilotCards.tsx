import { useContext, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ResultContext, ResultSymbol } from "../agent/ResultContext";
import { api } from "../../api/client";
import type {
  RecommendCard,
  ReviewCard,
  SizingAdvice,
  TradePreview,
} from "../../types";

/** 推荐卡：前5标的+前3板块，symbol 可点击跳详情；「让AI讲讲」按需一次调用。 */
export function RecommendCardView({ card }: { card: RecommendCard }) {
  const context = useContext(ResultContext);
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
          <ResultSymbol symbol={it.symbol}>{it.display_name}</ResultSymbol>
          <span className={`badge v-${it.verdict}`}>{it.verdict_cn}</span>
          {it.sentiment_cn && (
            <span className="cp-chip" title="散户情绪叙事标注（不参与判定）">
              {it.sentiment_cn}
            </span>
          )}
          <span className="muted">{it.reasons.join("；")}</span>
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
      {!context.readOnly && <button
        className="btn small"
        disabled={explain.isPending || !!narrative}
        onClick={() => context.ask ? context.ask(`请解释 ${card.run_date} 的关注清单（${card.items.map(it => it.symbol).join("、")}），说明触发条件与失效位。`) : explain.mutate()}
      >
        {explain.isPending ? "生成中…" : narrative ? "已讲解" : "让AI讲讲"}
      </button>}
      {explain.isError && <p className="cp-error" role="alert">讲解读取失败，请重试。</p>}
    </div>
  );
}

/** 每次独立确认的稳定请求标识：同一张确认卡（含失败重试）共用一个ID，
 *  服务端凭它保证同一次确认只记一笔。ID 挂在 preview 对象上（WeakMap）：
 *  组件因展开/收起对话轮重挂后身份不变；用户主动发起新一笔报单会得到
 *  新的 preview 对象 → 新ID，即使金额日期代码完全相同也互不影响。 */
const confirmationIds = new WeakMap<TradePreview, string>();

function confirmationIdFor(preview: TradePreview): string {
  let id = confirmationIds.get(preview);
  if (!id) {
    id = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `req-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
    confirmationIds.set(preview, id);
  }
  return id;
}

/** 报单确认卡：字段可改，确认后才落库（设计定稿 D1 红线）。
 *  防重复记账三件套（工作台与侧栏助手共用本组件，两入口同样生效）：
 *  ① 同步提交锁（ref）——按钮 disabled 依赖渲染时机，同一帧的极速连点
 *    都发生在状态更新前，由 ref 在事件层直接拦截，正在执行时只放行第一次；
 *  ② 稳定请求ID——失败重试沿用同一ID，服务端幂等返原笔，不会记两笔；
 *  ③ 编辑阻断——上次提交结果未知（网络失败）又改了字段时拒绝发送，
 *    提示先核对原笔，防止静默多记一笔。 */
export function TradeConfirmCard({ preview }: { preview: TradePreview }) {
  const { readOnly } = useContext(ResultContext);
  const qc = useQueryClient();
  const [code, setCode] = useState(preview.fund_code ?? "");
  const [name, setName] = useState(preview.fund_name ?? "");
  const [amount, setAmount] = useState(
    preview.amount != null ? String(preview.amount) : "",
  );
  const [date, setDate] = useState(preview.trade_date);
  const submittingRef = useRef(false);
  const attemptedKeyRef = useRef<string | null>(null);
  const [editBlocked, setEditBlocked] = useState(false);
  const requestId = confirmationIdFor(preview);

  const buildPayload = () => ({
    fund_code: code.trim(),
    fund_name: name.trim() || code.trim(),
    side: preview.side,
    amount: Number(amount),
    trade_date: date,
    request_id: requestId,
  });
  // 影响落库结果的字段都进指纹；request_id 由卡片身份单独保证。
  const payloadKey = (p: ReturnType<typeof buildPayload>) =>
    JSON.stringify([p.fund_code, p.fund_name, p.side, p.amount, p.trade_date]);

  const create = useMutation({
    mutationFn: (payload: ReturnType<typeof buildPayload>) =>
      api.copilotTradesCreate(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["copilotTrades"] });
      qc.invalidateQueries({ queryKey: ["opsToday"] });
    },
    onSettled: () => {
      submittingRef.current = false;
    },
  });
  const missingHint = preview.missing.length
    ? `待补：${preview.missing.join("、")}`
    : "信息已抽全，请核对";
  const confirmLocked =
    readOnly ||
    create.isPending ||
    create.isSuccess ||
    !/^\d{6}$/.test(code.trim()) ||
    !(Number(amount) > 0) ||
    !Number.isFinite(Number(amount)) ||
    !/^\d{4}-\d{2}-\d{2}$/.test(date);
  const handleSubmit = () => {
    if (confirmLocked || submittingRef.current) return;
    const payload = buildPayload();
    if (
      attemptedKeyRef.current !== null &&
      attemptedKeyRef.current !== payloadKey(payload)
    ) {
      // 上次提交结果未知（失败/超时），字段又被改过：拒绝静默换一笔。
      setEditBlocked(true);
      return;
    }
    setEditBlocked(false);
    attemptedKeyRef.current = payloadKey(payload);
    submittingRef.current = true;
    create.mutate(payload);
  };
  return (
    <div className="cp-card">
      <div className="cp-label">报单确认（{preview.side_cn}）· 确认后记入基金台账</div>
      <div className="muted" style={{ fontSize: 11 }}>
        {missingHint}。金额单位为元；定价按报单日基金净值（ETF按单位净值）。
      </div>
      <div className="cp-form">
        <label>基金代码<input value={code} onChange={(e) => setCode(e.target.value)} placeholder="6位代码" inputMode="numeric" disabled={create.isPending || create.isSuccess || readOnly} /></label>
        <label>基金名称<input value={name} onChange={(e) => setName(e.target.value)} placeholder="基金名称" disabled={create.isPending || create.isSuccess || readOnly} /></label>
        <label>成交金额（元）<input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="实际成交金额" inputMode="decimal" disabled={create.isPending || create.isSuccess || readOnly} /></label>
        <label>成交日期<input type="date" value={date} onChange={(e) => setDate(e.target.value)} disabled={create.isPending || create.isSuccess || readOnly} /></label>
      </div>
      <button
        className="btn small primary"
        disabled={confirmLocked}
        onClick={handleSubmit}
      >
        {create.isPending ? "记账中…" : create.isSuccess ? "已记账" : "确认记账"}
      </button>
      {create.isSuccess && <p role="status">已记入基金台账。<Link to="/portfolio">查看成交记录</Link></p>}
      {editBlocked && !create.isSuccess && (
        <div className="cp-error" role="alert">
          上一次提交没有成功，你又修改了报单内容。系统无法确定上一笔有没有记上账，所以先不放行：
          请到「我的持仓」页核对成交记录；如果那里没有这一笔，请重新发起一次报单（对助手再说一遍），
          新确认卡会按新内容生成。
        </div>
      )}
      {create.error && (
        <div className="cp-error">
          {create.error instanceof Error ? create.error.message : String(create.error)}
          <div style={{ marginTop: 4 }}>
            内容没改时可直接再点一次「确认记账」，不会重复记两笔；拿不准是否已记账，请先到「我的持仓」页核对。
          </div>
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
      <div className="cp-label ar-holdings-title">持仓速览</div>
      {data.fund_positions.length > 0 && <div className="ar-table-wrap" role="region" aria-label="基金持仓明细，可横向滚动" tabIndex={0}><table className="ar-data-table">
        <caption className="ar-result-hint">基金持仓 · 金额单位为元</caption>
        <thead><tr><th>基金</th><th className="num">份额</th><th className="num">现值</th><th className="num">浮动盈亏</th><th className="num">已实现盈亏</th></tr></thead>
        <tbody>{data.fund_positions.map(p => <tr key={p.fund_code}>
          <td><strong>{p.fund_name}</strong><div className="muted">{p.fund_code}</div></td>
          <td className="num">{p.shares.toFixed(2)}</td>
          <td className="num">{p.market_value?.toFixed(2) ?? "—"}</td>
          <td className="num">{p.unrealized_pnl == null ? "—" : `${p.unrealized_pnl > 0 ? "+" : ""}${p.unrealized_pnl.toFixed(2)}`}</td>
          <td className="num">{p.realized_pnl > 0 ? "+" : ""}{p.realized_pnl.toFixed(2)}</td>
        </tr>)}</tbody>
      </table></div>}
      {data.active_plans.map((p) => (
        <div key={p.plan_id} className="cp-row">
          <ResultSymbol symbol={p.symbol}>{p.symbol}</ResultSymbol>
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
      {review.sections.map((s, index) => (
        <details key={s.heading_cn} className="cp-section ar-card-group" open={index === 0}>
          <summary>{s.heading_cn}<small>{s.lines.length} 项</small></summary>
          {s.lines.map((l, i) => (
            <div key={i} style={{ fontSize: 12 }}>{l}</div>
          ))}
        </details>
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
  // key = 确认身份：新一笔预览（新对象）强制重挂，字段与提交状态按新卡
  // 初始化；同一笔预览（含重挂恢复）复用同一实例身份，重试不换ID。
  if (preview) return <TradeConfirmCard key={confirmationIdFor(preview)} preview={preview} />;
  if (!card) return null;
  if (card.card_type === "recommend")
    return <RecommendCardView card={card.data as RecommendCard} />;
  if (card.card_type === "holdings")
    return <HoldingsCardView data={card.data as HoldingsData} />;
  if (card.card_type === "review")
    return <ReviewCardView review={card.data as ReviewCard} />;
  if (card.card_type === "scout")
    return <ScoutCardView data={card.data as ScoutCard} />;
  return <p className="cp-error" role="status">已收到功能结果，当前界面暂不支持此类型的展示。</p>;
}

type ScoutItem = {
  symbol?: string | null; display_name: string; kind: string; kind_cn: string;
  verdict_cn?: string; detail_cn?: string; winrate_cn?: string | null;
};
type ScoutCard = {
  available: boolean; trend: ScoutItem[]; ambush: ScoutItem[];
  sentiment: ScoutItem[]; note_cn: string;
};

/** 机会侦察卡：趋势信号/埋伏位/情绪信号三类聚合（叙事参考层）。 */
export function ScoutCardView({ data }: { data: ScoutCard }) {
  const groups: [string, ScoutItem[]][] = [
    ["① 趋势信号（系统判定）", data.trend],
    ["② 定投埋伏位（下跌型×筹码密集区）", data.ambush],
    ["③ 情绪信号", data.sentiment],
  ];
  return (
    <div className="cp-card">
      <div className="cp-label">最近机会扫描（每项带历史依据 · 叙事参考层）</div>
      {!data.available && (
        <div className="ops-empty">当前三类机会均未激活——空仓等待也是一种操作。</div>
      )}
      {groups.map(([title, items]) =>
        items.length === 0 ? null : (
          <details key={title} className="ar-card-group" open>
            <summary>{title}<small>{items.length} 项</small></summary>
            {items.map((it, i) => (
              <div key={i} className="cp-row" style={{ alignItems: "baseline" }}>
                {it.symbol ? <ResultSymbol symbol={it.symbol}>{it.display_name || it.kind_cn}</ResultSymbol> : <span className="cp-sym">{it.display_name || it.kind_cn}</span>}
                <span style={{ flex: 1 }}>
                  <span className={it.kind === "ambush" ? "cp-up" : ""}>
                    {it.verdict_cn}
                  </span>
                  {it.detail_cn && (
                    <span className="muted"> — {it.detail_cn}</span>
                  )}
                  {it.winrate_cn && (
                    <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                      历史：{it.winrate_cn}
                    </div>
                  )}
                </span>
              </div>
            ))}
          </details>
        ),
      )}
      <div className="muted" style={{ fontSize: 11, marginTop: 8 }}>{data.note_cn}</div>
    </div>
  );
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
