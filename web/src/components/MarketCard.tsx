import { useNavigate } from "react-router-dom";
import type { Card } from "../types";
import ColorBadge from "./ColorBadge";
import Sparkline from "./Sparkline";

function fmtPrice(v: number | null): string {
  if (v == null) return "--";
  return v >= 100 ? v.toFixed(2) : v.toFixed(3);
}

function fmtChange(v: number | null): { text: string; cls: string } {
  if (v == null) return { text: "--", cls: "flat" };
  const sign = v > 0 ? "+" : "";
  const cls = v > 0 ? "up" : v < 0 ? "down" : "flat";
  return { text: `${sign}${v.toFixed(2)}%`, cls };
}

function fmtTime(iso: string | null): string {
  if (!iso) return "--";
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

interface Props {
  card: Card;
  onRemove?: (symbol: string) => void;
  onRetry?: (symbol: string) => void;
}

/** 看盘小卡片：价格 + 涨跌幅 + 迷你K线 + LEI 颜色 + 关键变化 + 有效结构。 */
export default function MarketCard({ card, onRemove, onRetry }: Props) {
  const navigate = useNavigate();
  const goDetail = () =>
    !card.error && navigate(`/symbol/${encodeURIComponent(card.symbol)}`);

  if (card.error) {
    return (
      <div className="card error">
        <div className="row">
          <span className="name">{card.display_name}</span>
          <span className="symbol">{card.symbol}</span>
          {card.market_cn && <span className="tag">{card.market_cn}</span>}
        </div>
        <div className="error-msg">{card.error}</div>
        <div className="footer">
          <span>数据时间 {fmtTime(card.data_time)}</span>
          <span className="spacer" />
          {onRetry && (
            <button
              className="btn small"
              onClick={(e) => {
                e.stopPropagation();
                onRetry(card.symbol);
              }}
            >
              重试
            </button>
          )}
        </div>
      </div>
    );
  }

  const change = fmtChange(card.change_pct);
  const structure = card.primary_structure;
  const distC = structure?.distance_to_c_pct;

  return (
    <div className="card" onClick={goDetail} title="点击查看详情">
      <div className="row">
        <span className="name">{card.display_name}</span>
        <span className="symbol">{card.symbol}</span>
        {card.market_cn && <span className="tag">{card.market_cn}</span>}
        <span className="spacer" style={{ flex: 1 }} />
        {card.group === "watchlist" && onRemove && (
          <button
            className="btn small"
            title="移出自选"
            onClick={(e) => {
              e.stopPropagation();
              onRemove(card.symbol);
            }}
          >
            ✕
          </button>
        )}
      </div>

      <div className="row">
        <span className={`price ${change.cls}`}>{fmtPrice(card.price)}</span>
        <span className={`change ${change.cls}`}>{change.text}</span>
      </div>

      <Sparkline
        points={card.sparkline}
        up={card.change_pct == null ? null : card.change_pct >= 0}
      />

      <div className="signal-row">
        <ColorBadge color={card.color} colorCn={card.color_cn} days={card.color_days} />
        {card.stage_cn && <span className="stage-chip">{card.stage_cn}</span>}
        {card.risk_state && card.risk_state !== "normal" && (
          <span className="stage-chip risky">{card.risk_state_cn}</span>
        )}
      </div>

      <div className="key-change" title={card.key_change_cn ?? undefined}>
        {card.key_change_cn
          ? `${card.key_change_date ?? ""} ${card.key_change_cn}`
          : "近期无关键变化"}
      </div>

      {structure && (
        <div className="structure-line">
          {structure.structure_type_cn} · {structure.status_cn}
          {distC != null && (
            <span className={distC >= 0 ? "dist-pos" : "dist-neg"}>
              {distC >= 0
                ? ` · 高于C点 ${distC.toFixed(1)}%`
                : ` · 跌破C点 ${Math.abs(distC).toFixed(1)}%`}
            </span>
          )}
        </div>
      )}
      {!structure && card.distance_to_b1_pct != null && (
        <div className="structure-line">
          距B1参考前高 {card.distance_to_b1_pct.toFixed(1)}%
        </div>
      )}

      <div className="footer">
        <span>
          数据时间 {fmtTime(card.data_time)} · {card.is_intraday_forming ? "盘中" : "已收盘"}
        </span>
        {card.stale && <span className="stale-chip">缓存兜底</span>}
        {card.persist_warning && (
          <span className="stale-chip" title={card.persist_warning}>
            未入库
          </span>
        )}
        <span className="spacer" />
        <span>{card.last_bar_date}</span>
      </div>
    </div>
  );
}
