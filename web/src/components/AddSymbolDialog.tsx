import { useState } from "react";
import { api } from "../api/client";
import type { ResolveResult } from "../types";

interface Props {
  /** 添加到哪个分组；null = 不分组 */
  groupId?: number | null;
  onClose: () => void;
  onAdded: () => void;
}

/** 添加自选：输入 → 解析确认（防 000001→.SZ 误路由）→ 添加。 */
export default function AddSymbolDialog({ groupId = null, onClose, onAdded }: Props) {
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

  const doAdd = async () => {
    if (!resolved) return;
    setBusy(true);
    setError(null);
    try {
      await api.addWatchlist(resolved.symbol, groupId);
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
        {error && <div className="resolve-result"><span className="bad">{error}</span></div>}
        {resolved && (
          <div className="resolve-result">
            <div>
              将添加：<b>{resolved.display_name ?? resolved.symbol}</b>（{resolved.symbol}
              {resolved.market_cn ? ` · ${resolved.market_cn}` : ""}）
            </div>
            {resolved.probe_ok === true && <div className="ok">✓ 行情数据可用</div>}
            {resolved.probe_ok === false && (
              <div className="bad">行情暂不可用：{resolved.probe_error}（仍可添加，稍后重试）</div>
            )}
          </div>
        )}
        <div className="actions">
          <button className="btn" onClick={onClose}>取消</button>
          {!resolved ? (
            <button className="btn primary" disabled={busy || !input.trim()} onClick={doResolve}>
              {busy ? "解析中…" : "解析"}
            </button>
          ) : (
            <button className="btn primary" disabled={busy} onClick={doAdd}>
              {busy ? "添加中…" : "确认添加"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
