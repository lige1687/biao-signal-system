import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { smartPromptsApi } from "../../api/smartPrompts";
import "./smart-prompts.css";

const STORAGE_PREFIX = "lei.smart_entry_price.";

function loadSavedEntryPrice(symbol: string): string {
  try {
    return window.localStorage.getItem(STORAGE_PREFIX + symbol) ?? "";
  } catch {
    return "";
  }
}

function saveEntryPrice(symbol: string, raw: string) {
  try {
    if (!raw.trim()) {
      window.localStorage.removeItem(STORAGE_PREFIX + symbol);
    } else {
      window.localStorage.setItem(STORAGE_PREFIX + symbol, raw.trim());
    }
  } catch {
    /* 忽略无痕模式写入限制 */
  }
}

export default function SmartSymbolPromptCard({ symbol }: { symbol: string }) {
  const [draftPrice, setDraftPrice] = useState<string>(() => loadSavedEntryPrice(symbol));
  const [committedPrice, setCommittedPrice] = useState<number | null>(() => {
    const v = Number(loadSavedEntryPrice(symbol));
    return Number.isFinite(v) && v > 0 ? v : null;
  });

  useEffect(() => {
    const saved = loadSavedEntryPrice(symbol);
    setDraftPrice(saved);
    const v = Number(saved);
    setCommittedPrice(Number.isFinite(v) && v > 0 ? v : null);
  }, [symbol]);

  const applyPrice = () => {
    saveEntryPrice(symbol, draftPrice);
    const v = Number(draftPrice);
    setCommittedPrice(Number.isFinite(v) && v > 0 ? v : null);
  };

  const { data, isLoading, isError } = useQuery({
    queryKey: ["smartPromptSymbol", symbol, committedPrice],
    queryFn: () => smartPromptsApi.symbol(symbol, committedPrice),
    enabled: Boolean(symbol),
    staleTime: 60_000,
    retry: 0,
  });

  if (isLoading) {
    return (
      <section className="sp-card" aria-label="大白话买卖与拿住提示">
        <span className="sp-card-meta">正在计算这只标的的底色排雷与买卖保护线…</span>
      </section>
    );
  }

  if (isError || !data) {
    return null;
  }

  if (!data.available) {
    return (
      <section className="sp-card" aria-label="大白话买卖与拿住提示">
        <span className="sp-card-meta">{data.reason ?? "暂无足够历史数据计算提示。"}</span>
      </section>
    );
  }

  return (
    <section className="sp-card" aria-label="大白话买卖与拿住提示">
      <div className="sp-card-head">
        <div className="sp-card-title">
          <span>实战大白话提示 · {data.name}</span>
          <span className="sp-card-meta">
            数据截至 {data.as_of} · 收盘 {data.close} · 大多数人成本约 {data.main_cost_peak}（场内约 {data.profit_holders_pct}% 的人赚钱）
          </span>
        </div>
        {data.kind !== "us" && data.kind !== "off_fund" && (
          <div className="sp-entry-box">
            <label htmlFor={`sp-entry-${symbol}`}>我的买进价：</label>
            <input
              id={`sp-entry-${symbol}`}
              type="number"
              step="0.01"
              min="0"
              placeholder="选填自动算"
              value={draftPrice}
              onChange={(e) => setDraftPrice(e.target.value)}
              onBlur={applyPrice}
              onKeyDown={(e) => {
                if (e.key === "Enter") applyPrice();
              }}
            />
            {committedPrice && (
              <button
                type="button"
                className="btn small"
                onClick={() => {
                  setDraftPrice("");
                  saveEntryPrice(symbol, "");
                  setCommittedPrice(null);
                }}
              >
                清除
              </button>
            )}
          </div>
        )}
      </div>

      <div className="sp-grid-3">
        <div className="sp-box">
          <div className="sp-box-label">① 底子与财务排雷</div>
          <div className="sp-box-badge">{data.quality_badge}</div>
          <p className="sp-box-text">{data.quality_detail}</p>
        </div>

        <div className="sp-box">
          <div className="sp-box-label">② 现在能不能买 / 买多少合适</div>
          <div className="sp-box-badge">{data.buy_light}</div>
          <p className="sp-box-text">{data.buy_advice}</p>
          {data.sizing_advice_cn && (
            <p className="sp-sizing-note">{data.sizing_advice_cn}</p>
          )}
        </div>

        <div className="sp-box">
          <div className="sp-box-label">③ 买进去怎么拿住不卖早</div>
          <div className="sp-box-badge">{data.hold_stage}</div>
          <p className="sp-box-text">{data.hold_advice}</p>
        </div>
      </div>
    </section>
  );
}
