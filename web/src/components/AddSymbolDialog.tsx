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

/** 添加自选：代码输入 或 板块/指数/美股ETF 选择器（四个 tab）。 */
export default function AddSymbolDialog({ groupId = null, onClose, onAdded }: Props) {
  const [tab, setTab] = useState<"code" | "sector" | "index" | "usetf">("code");
  const [input, setInput] = useState("");
  const [resolved, setResolved] = useState<ResolveResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const doResolve = async () => {
    if (!input.trim()) return;
    setBusy(true);
    setError(null);
    setResolved(null);
    try {
      setResolved(await api.resolve(input.trim(), true));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const doAdd = async (symbol: string) => {
    setBusy(true);
    setError(null);
    try {
      await api.addWatchlist(symbol, groupId);
      onAdded();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="dialog-mask" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h3>添加自选</h3>
        <div className="add-tabs">
          <button
            className={`add-tab ${tab === "code" ? "on" : ""}`}
            onClick={() => setTab("code")}
          >
            代码 / ETF
          </button>
          <button
            className={`add-tab ${tab === "sector" ? "on" : ""}`}
            onClick={() => setTab("sector")}
          >
            行业板块
          </button>
          <button
            className={`add-tab ${tab === "index" ? "on" : ""}`}
            onClick={() => setTab("index")}
          >
            策略指数
          </button>
          <button
            className={`add-tab ${tab === "usetf" ? "on" : ""}`}
            onClick={() => setTab("usetf")}
          >
            美股ETF
          </button>
        </div>

        {tab === "code" ? (
          <>
            <input
              type="text"
              placeholder="如 QQQ、159915、600519.SS、0700.HK"
              value={input}
              autoFocus
              onChange={(e) => {
                setInput(e.target.value);
                setResolved(null);
              }}
              onKeyDown={(e) => e.key === "Enter" && doResolve()}
            />
            <div className="hint">
              沪市指数请带 .SS 后缀（如 000001.SS 上证指数）；裸 6 位代码按股票规则解析。
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
                    行情暂不可用：{resolved.probe_error}（仍可添加，稍后重试）
                  </div>
                )}
              </div>
            )}
            <div className="actions">
              <button className="btn" onClick={onClose}>
                取消
              </button>
              {!resolved ? (
                <button
                  className="btn primary"
                  disabled={busy || !input.trim()}
                  onClick={doResolve}
                >
                  {busy ? "解析中…" : "解析"}
                </button>
              ) : (
                <button
                  className="btn primary"
                  disabled={busy}
                  onClick={() => doAdd(resolved.symbol)}
                >
                  {busy ? "添加中…" : "确认添加"}
                </button>
              )}
            </div>
          </>
        ) : tab === "sector" ? (
          <SectorPicker busy={busy} error={error} onPick={doAdd} onClose={onClose} />
        ) : tab === "index" ? (
          <IndexPicker busy={busy} error={error} onPick={doAdd} onClose={onClose} />
        ) : (
          <UsEtfPicker busy={busy} error={error} onPick={doAdd} onClose={onClose} />
        )}
      </div>
    </div>
  );
}

/** 板块/指数选择器共用：搜索 + 列表，点一下即添加。 */
function PickerList({
  items,
  q,
  busy,
  hint,
  onPick,
}: {
  items: { code: string; name: string; symbol: string }[];
  q: string;
  busy: boolean;
  hint: string;
  onPick: (symbol: string) => void;
}) {
  const filtered = useMemo(() => {
    const kw = q.trim();
    if (!kw) return items;
    return items.filter(
      (s) =>
        s.name.includes(kw) ||
        s.code.includes(kw) ||
        s.symbol.includes(kw.toUpperCase()),
    );
  }, [items, q]);

  return (
    <>
      <div className="hint">{hint}</div>
      <div className="sector-list">
        {filtered.length === 0 && <div className="muted">无匹配</div>}
        {filtered.map((s) => (
          <button
            key={s.code}
            className="sector-item"
            disabled={busy}
            onClick={() => onPick(s.symbol)}
            title={`${s.name}（${s.symbol}）`}
          >
            <span className="si-name">{s.name}</span>
            <span className="si-symbol">{s.symbol}</span>
          </button>
        ))}
      </div>
    </>
  );
}

/** 板块选择器：搜索 + 列表，点一下即添加。 */
function SectorPicker({
  busy,
  error,
  onPick,
  onClose,
}: {
  busy: boolean;
  error: string | null;
  onPick: (symbol: string) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["sectors"],
    queryFn: () => api.sectors(),
    staleTime: Infinity,
  });
  const items = data?.sectors ?? [];

  return (
    <>
      <input
        type="text"
        placeholder="搜索板块名或代码（如 电网、半导体、881121）"
        value={q}
        autoFocus
        onChange={(e) => setQ(e.target.value)}
      />
      {error && (
        <div className="resolve-result">
          <span className="bad">{error}</span>
        </div>
      )}
      {isLoading ? (
        <div className="muted">加载中…</div>
      ) : (
        <PickerList
          items={items}
          q={q}
          busy={busy}
          hint="同花顺行业板块（收盘后更新当日K线）。点名称即添加。"
          onPick={onPick}
        />
      )}
      <div className="actions">
        <button className="btn" onClick={onClose}>
          关闭
        </button>
      </div>
    </>
  );
}

/** 策略指数选择器：规模/红利/主题/海外指数。 */
function IndexPicker({
  busy,
  error,
  onPick,
  onClose,
}: {
  busy: boolean;
  error: string | null;
  onPick: (symbol: string) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["sectors"],
    queryFn: () => api.sectors(),
    staleTime: Infinity,
  });
  const items = data?.indices ?? [];

  return (
    <>
      <input
        type="text"
        placeholder="搜索指数名或代码（如 红利、500、000905）"
        value={q}
        autoFocus
        onChange={(e) => setQ(e.target.value)}
      />
      {error && (
        <div className="resolve-result">
          <span className="bad">{error}</span>
        </div>
      )}
      {isLoading ? (
        <div className="muted">加载中…</div>
      ) : (
        <PickerList
          items={items}
          q={q}
          busy={busy}
          hint="策略/规模/主题指数（沪深300、中证500、中证红利、VIX…）。点名称即添加。"
          onPick={onPick}
        />
      )}
      <div className="actions">
        <button className="btn" onClick={onClose}>
          关闭
        </button>
      </div>
    </>
  );
}

/** 美股 ETF 选择器：宽基/行业/风格/债券商品。名称为「中文名 + 缩写」。 */
function UsEtfPicker({
  busy,
  error,
  onPick,
  onClose,
}: {
  busy: boolean;
  error: string | null;
  onPick: (symbol: string) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["sectors"],
    queryFn: () => api.sectors(),
    staleTime: Infinity,
  });
  const items = data?.us_etfs ?? [];

  return (
    <>
      <input
        type="text"
        placeholder="搜索 ETF 名或代码（如 半导体、纳指、QQQ、GLD）"
        value={q}
        autoFocus
        onChange={(e) => setQ(e.target.value)}
      />
      {error && (
        <div className="resolve-result">
          <span className="bad">{error}</span>
        </div>
      )}
      {isLoading ? (
        <div className="muted">加载中…</div>
      ) : (
        <PickerList
          items={items}
          q={q}
          busy={busy}
          hint="美股 ETF：宽基（SPY/QQQ）、行业（XLK/SMH）、风格、债券商品（TLT/GLD）。点名称即添加。"
          onPick={onPick}
        />
      )}
      <div className="actions">
        <button className="btn" onClick={onClose}>
          关闭
        </button>
      </div>
    </>
  );
}
