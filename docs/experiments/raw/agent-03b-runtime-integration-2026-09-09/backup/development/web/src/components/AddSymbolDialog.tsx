import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ResolveResult } from "../types";

interface Props {
  /** 添加到哪个分组；null = 不分组 */
  groupId?: number | null;
  onClose: () => void;
  onAdded: () => void;
}

type CatKey = "industry" | "concept" | "index" | "usetf";

const CATEGORIES: { key: CatKey; label: string }[] = [
  { key: "industry", label: "行业板块" },
  { key: "concept", label: "概念板块" },
  { key: "index", label: "指数" },
  { key: "usetf", label: "美股ETF" },
];

const CAT_LABEL: Record<CatKey, string> = {
  industry: "行业",
  concept: "概念",
  index: "指数",
  usetf: "美股ETF",
};

/** 目录渲染上限：全量约 660 条（90 行业 + 504 概念 + 指数 + ETF），避免一次性铺满 DOM。 */
const MAX_ROWS = 200;

interface CatalogItem {
  code: string;
  name: string;
  symbol: string;
  cat: CatKey;
}

/** 添加自选：统一搜索单入口——四类目录点选 + 任意代码解析，同一个搜索框。 */
export default function AddSymbolDialog({ groupId = null, onClose, onAdded }: Props) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<CatKey | "all">("all");
  const [resolved, setResolved] = useState<ResolveResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // 已成功添加的 symbol 集合：目录里原地显示「✓ 已添加」，避免「点了不知道加没加上」。
  const [addedCodes, setAddedCodes] = useState<ReadonlySet<string>>(() => new Set());

  const { data, isLoading } = useQuery({
    queryKey: ["sectors"],
    queryFn: () => api.sectors(),
    staleTime: Infinity,
  });

  const items = useMemo<CatalogItem[]>(() => {
    const all: CatalogItem[] = [
      ...(data?.sectors ?? []).map((s) => ({ ...s, cat: "industry" as const })),
      ...(data?.concepts ?? []).map((s) => ({ ...s, cat: "concept" as const })),
      ...(data?.indices ?? []).map((s) => ({ ...s, cat: "index" as const })),
      ...(data?.us_etfs ?? []).map((s) => ({ ...s, cat: "usetf" as const })),
    ];
    const kw = q.trim();
    const kwLower = kw.toLowerCase();
    const filtered = kw
      ? all.filter(
          (s) =>
            s.name.includes(kw) ||
            s.code.toLowerCase().includes(kwLower) ||
            s.symbol.toLowerCase().includes(kwLower),
        )
      : all;
    return cat === "all" ? filtered : filtered.filter((s) => s.cat === cat);
  }, [data, q, cat]);

  const doResolve = async () => {
    if (!q.trim()) return;
    setBusy(true);
    setError(null);
    setResolved(null);
    try {
      setResolved(await api.resolve(q.trim(), true));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  // close=false 用于目录点选：添加后不关弹窗、原地标记「已添加」，方便连加多个。
  const doAdd = async (symbol: string, close = true) => {
    setBusy(true);
    setError(null);
    try {
      await api.addWatchlist(symbol, groupId);
      setAddedCodes((prev) => new Set(prev).add(symbol));
      onAdded();
      if (close) onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  // 裸 0 开头 6 位码会被按深市股票解析（如 000905 → 000905.SZ），probe 失败时给出正确写法。
  const shIndexHint =
    resolved?.probe_ok === false && /^0\d{5}$/.test(q.trim())
      ? `；沪市指数请带 .SS 后缀重试（如 ${q.trim()}.SS），中证指数也可用 .CSI 写法`
      : "";

  const shown = items.slice(0, MAX_ROWS);

  return (
    <div className="dialog-mask" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h3>添加自选</h3>
        <input
          type="text"
          placeholder="搜索名称或代码（如 通信、931160、QQQ、BK1128）"
          value={q}
          autoFocus
          onChange={(e) => {
            setQ(e.target.value);
            setResolved(null);
            setError(null);
          }}
          onKeyDown={(e) => e.key === "Enter" && doResolve()}
        />
        <div className="add-tabs">
          <button className={`add-tab ${cat === "all" ? "on" : ""}`} onClick={() => setCat("all")}>
            全部
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              className={`add-tab ${cat === c.key ? "on" : ""}`}
              onClick={() => setCat(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div className="hint">
          目录点名称或「＋ 添加」即加（可连加）；任意代码（股票/ETF/指数/BK/SW/TH/美股）回车解析后添加。
        </div>

        {error && (
          <div className="resolve-result">
            <span className="bad">{error}</span>
          </div>
        )}
        {resolved && (
          <div className="resolve-result">
            <div>
              将添加：<b>{resolved.display_name ?? resolved.symbol}</b>（{resolved.symbol}
              {resolved.market_cn ? ` · ${resolved.market_cn}` : ""}）
            </div>
            {resolved.probe_ok === true && <div className="ok">✓ 行情数据可用</div>}
            {resolved.probe_ok === false && (
              <div className="bad">
                行情暂不可用：{resolved.probe_error}
                {shIndexHint}（仍可添加，稍后重试）
              </div>
            )}
          </div>
        )}
        {q.trim() && !resolved && (
          <div className="resolve-row">
            <span className="resolve-row-label">
              目录里没有？按代码添加「<b>{q.trim()}</b>」
            </span>
            <button className="btn" disabled={busy} onClick={doResolve}>
              {busy ? "解析中…" : "解析"}
            </button>
          </div>
        )}

        <div className="sector-list">
          {isLoading ? (
            <div className="muted">加载中…</div>
          ) : shown.length === 0 ? (
            <div className="muted">目录无匹配；可回车按代码解析添加</div>
          ) : (
            shown.map((s) => {
              const added = addedCodes.has(s.symbol);
              return (
                <div key={`${s.cat}-${s.code}`} className={`sector-item${added ? " added" : ""}`}>
                  <button
                    type="button"
                    className="si-main"
                    disabled={busy}
                    onClick={() => doAdd(s.symbol, false)}
                    title={`${s.name}（${s.symbol}）`}
                  >
                    <span className="si-name">{s.name}</span>
                    <span className="si-meta">
                      <span className={`si-cat cat-${s.cat}`}>{CAT_LABEL[s.cat]}</span>
                      <span className="si-symbol">{s.symbol}</span>
                    </span>
                  </button>
                  <button
                    type="button"
                    className={`si-add${added ? " done" : ""}`}
                    disabled={busy || added}
                    onClick={() => doAdd(s.symbol, false)}
                    title={added ? "已添加" : `添加 ${s.name}`}
                  >
                    {added ? "✓ 已添加" : "＋ 添加"}
                  </button>
                </div>
              );
            })
          )}
          {items.length > MAX_ROWS && (
            <div className="muted">已显示前 {MAX_ROWS} 条，输入关键词缩小范围</div>
          )}
        </div>

        <div className="actions">
          <button className="btn" onClick={onClose}>
            关闭
          </button>
          {resolved && (
            <button className="btn primary" disabled={busy} onClick={() => doAdd(resolved.symbol)}>
              {busy ? "添加中…" : "确认添加"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
