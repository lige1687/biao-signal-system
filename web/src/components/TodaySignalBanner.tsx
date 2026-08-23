/** 今日自选信号横幅 -- 看盘主页中栏顶部.
 *
 *  数据源: GET /api/signals/today (launchd 11:35/14:45/15:05 写库, 60s 轮询).
 *  买点行 (actionable/waiting/blocked) + 卖点行 (hard/warn/soft 四档口径) 统一展示;
 *  点行 = 选中该标的 (不跳页): 买·行动自动打开买点分析抽屉, 卖点行展开右栏解释.
 *  [刷新] 调 POST /api/signals/today/refresh (按当前时间自动选 as_of).
 *  买·受阻默认折叠 (<details>); 数据不可用显式列出, 不静默.
 *  获取失败显式红字提示 (不误显「今日尚未扫描」); 徽标旁给出上次扫描时刻.
 */
import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ScanItem, SignalAlert } from "../types";

const TIER_LABEL: Record<string, string> = {
  hard: "卖·硬",
  warn: "卖·预警",
  soft: "卖·提醒",
};

const TIER_COLOR: Record<string, string> = {
  hard: "var(--error, #e5484d)",
  warn: "var(--warn)",
  soft: "var(--text-faint)",
};

const BUY_LABEL: Record<string, string> = {
  actionable: "买·行动",
  waiting: "买·等待",
  blocked: "买·受阻",
};

const BUY_COLOR: Record<string, string> = {
  actionable: "var(--lei-green)",
  waiting: "var(--text-faint)",
  blocked: "var(--warn)",
};

function SellRow({
  it,
  onPick,
}: {
  it: SignalAlert;
  onPick: (symbol: string, side: "sell") => void;
}) {
  return (
    <li className="sig-row">
      <div className="sig-row-head">
        <button className="sig-symbol" onClick={() => onPick(it.symbol, "sell")}>
          {it.display_name || it.symbol}
        </button>
        <span
          className="sig-tier"
          style={{ background: TIER_COLOR[it.tier] ?? "var(--text-faint)" }}
        >
          {TIER_LABEL[it.tier] ?? it.tier}
        </span>
        <span className="sig-kind">{it.kind_cn}</span>
        {it.provenance === "research_proxy" && (
          <span className="sig-proxy">研究代理</span>
        )}
        {it.is_new ? (
          <span className="sig-new">新增</span>
        ) : (
          <span className="sig-cont">持续</span>
        )}
      </div>
      <div className="sig-title">{it.title}</div>
      <div className="sig-reason">{it.reason_cn}</div>
      {Object.keys(it.key_prices).length > 0 && (
        <div className="sig-prices">
          {Object.entries(it.key_prices).map(([k, v]) => (
            <span key={k}>
              {k} {v.toFixed(2)}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

function BuyRow({
  it,
  onPick,
}: {
  it: ScanItem;
  onPick: (symbol: string, side: "buy") => void;
}) {
  return (
    <li className="sig-row">
      <div className="sig-row-head">
        <button className="sig-symbol" onClick={() => onPick(it.symbol, "buy")}>
          {it.display_name || it.symbol}
        </button>
        <span
          className="sig-tier"
          style={{ background: BUY_COLOR[it.verdict] ?? "var(--text-faint)" }}
        >
          {BUY_LABEL[it.verdict] ?? it.verdict_cn}
        </span>
        {it.reward_risk_computable && it.reward_risk_ratio != null && (
          <span className="sig-kind">R/R {it.reward_risk_ratio.toFixed(1)}</span>
        )}
        {it.has_active_plan && <span className="sig-cont">已有计划</span>}
      </div>
      {it.best_scenario_cn && <div className="sig-title">{it.best_scenario_cn}</div>}
      {it.verdict === "blocked" && it.blocking_reasons.length > 0 && (
        <div className="sig-reason">阻断：{it.blocking_reasons.join("、")}</div>
      )}
      {it.verdict === "waiting" && it.missing_summary_cn && (
        <div className="sig-reason">缺：{it.missing_summary_cn}</div>
      )}
    </li>
  );
}

function Group({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="sig-group">
      <div className="sig-group-head">{title}</div>
      <ul className="sig-list">{children}</ul>
    </div>
  );
}

export default function TodaySignalBanner({
  onPick,
}: {
  onPick: (symbol: string, side: "buy" | "sell") => void;
}) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  // 回放模式：选了过去交易日则切换数据源（红点/今日查询不受影响）
  const [replayDate, setReplayDate] = useState("");
  const isReplay = replayDate !== "";
  const dayQuery = useQuery({
    queryKey: ["signalsDay", replayDate],
    queryFn: () => api.signalsDay(replayDate),
    enabled: isReplay,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const replay = useMutation({
    mutationFn: () => api.replayDay(replayDate),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["signalsDay", replayDate] });
    },
  });
  // request() 把后端 422 detail（含"最近的过去交易日是 YYYY-MM-DD"建议）放进 Error.message
  const replayError: string | null =
    isReplay && dayQuery.isError
      ? (dayQuery.error as Error | null)?.message || "该日期不可用（非交易日或格式错误）"
      : isReplay && replay.isError
        ? (replay.error as Error | null)?.message || "回放计算失败，请稍后重试"
        : null;
  const { data, isError } = useQuery({
    queryKey: ["signalsToday"],
    queryFn: () => api.signalsToday(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const refresh = useMutation({
    mutationFn: () => {
      const hour = new Date().getHours();
      return api.refreshSignals(hour >= 15 ? "close" : "intraday");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["signalsToday"] });
      qc.invalidateQueries({ queryKey: ["plansSummary"] });
    },
  });

  const active = isReplay ? dayQuery.data : data;
  const asOf = active?.as_of ?? null;
  // 回放日以查询结果为准（无快照/日期无效也要展开给出提示与补算入口，快照日含 available）；
  // 今日口径不变（今日响应恒含 available=true，不能并入判定，否则未扫描日会被误判已扫描）。
  const scanned = isReplay
    ? active != null || dayQuery.isError
    : asOf != null;
  const failed =
    (!isReplay && isError && !data) ||
    (isReplay && dayQuery.isError && !dayQuery.data);
  const scanTime = active?.generated_at
    ? new Date(active.generated_at).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;
  const buyA = active?.actionable ?? [];
  const buyW = active?.waiting ?? [];
  const buyB = active?.blocked ?? [];
  const sellH = active?.sell_hard ?? [];
  const sellWarn = active?.sell_warn ?? [];
  const sellS = active?.sell_soft ?? [];
  const unavailable = active?.unavailable ?? [];
  const empty =
    buyA.length + buyW.length + buyB.length + sellH.length + sellWarn.length +
    sellS.length + unavailable.length === 0;

  return (
    <div className="sig-banner">
      <div className="sig-banner-head">
        <b>{isReplay ? `🔔 自选信号 · ${replayDate}` : "🔔 今日自选信号"}</b>
        {isReplay && <span className="sig-asof replay">回放</span>}
        {scanned && (
          <span className={`sig-asof${asOf === "intraday" ? " intraday" : ""}`}>
            {asOf === "intraday" ? "盘中临时" : "收盘"}
          </span>
        )}
        {scanTime && <span className="muted">上次扫描 {scanTime}</span>}
        {failed ? (
          <span
            style={{ color: "var(--error, #e5484d)", fontSize: "12px" }}
            role="alert"
          >
            信号获取失败
          </span>
        ) : (
          <span className="muted">
            {scanned
              ? `买·行动 ${buyA.length} · 买·等待 ${buyW.length} · 卖·硬 ${sellH.length} · 卖·预警 ${sellWarn.length} · 卖·提醒 ${sellS.length}`
              : scanTime
                ? `今日尚未扫描 · 上次扫描 ${scanTime}`
                : "今日尚未扫描"}
          </span>
        )}
        <span className="sig-spacer" />
        <input
          type="date"
          className="sig-date"
          value={replayDate}
          max={new Date(Date.now() - 86400_000).toISOString().slice(0, 10)}
          onChange={(e) => {
            setReplayDate(e.target.value);
            setOpen(true);
          }}
          aria-label="选择回放交易日"
        />
        {isReplay ? (
          <>
            <button
              className="btn small"
              disabled={replay.isPending || !active}
              onClick={() => replay.mutate()}
            >
              {replay.isPending ? "回放计算中…" : "回放计算"}
            </button>
            <button
              className="btn small"
              onClick={() => {
                setReplayDate("");
                setOpen(false);
              }}
            >
              回到今天
            </button>
          </>
        ) : (
          <button
            className="btn small"
            disabled={refresh.isPending}
            onClick={() => refresh.mutate()}
          >
            {refresh.isPending ? "扫描中…" : "刷新"}
          </button>
        )}
        {scanned && (
          <button
            className="btn small"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "收起 ▲" : "展开 ▼"}
          </button>
        )}
      </div>
      {open && scanned && (
        <div className="sig-groups">
          {isReplay && (
            <div className="muted sig-replay-note">
              回放口径：当前自选 × 行情截至 {replayDate} 重算，含成分前视，仅形态参考，不构成买卖建议。
            </div>
          )}
          {isReplay && active?.available === false && !replay.isPending && (
            <div className="sig-empty">
              该日无快照。点 [回放计算] 补算（首次约 2-4 分钟，算完永久保存，之后秒开）。
            </div>
          )}
          {replayError && (
            <div className="sig-empty" role="alert">{replayError}</div>
          )}
          {buyA.length > 0 && (
            <Group title={`✅ 买·行动 ${buyA.length}`}>
              {buyA.map((it) => (
                <BuyRow key={it.symbol} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {sellH.length > 0 && (
            <Group title={`🔻 卖·硬信号 ${sellH.length}`}>
              {sellH.map((it) => (
                <SellRow key={`${it.symbol}-${it.kind}`} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {buyW.length > 0 && (
            <Group title={`⏳ 买·等待 ${buyW.length}`}>
              {buyW.map((it) => (
                <BuyRow key={it.symbol} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {sellWarn.length > 0 && (
            <Group title={`⚠️ 卖·预警（不必然反向） ${sellWarn.length}`}>
              {sellWarn.map((it) => (
                <SellRow key={`${it.symbol}-${it.kind}`} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {sellS.length > 0 && (
            <Group title={`🌑 卖·提醒 ${sellS.length}`}>
              {sellS.map((it) => (
                <SellRow key={`${it.symbol}-${it.kind}`} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {buyB.length > 0 && (
            <details className="sig-blocked">
              <summary className="sig-group-head">
                买·受阻 {buyB.length}（默认折叠）
              </summary>
              <ul className="sig-list">
                {buyB.map((it) => (
                  <BuyRow key={it.symbol} it={it} onPick={onPick} />
                ))}
              </ul>
            </details>
          )}
          {unavailable.length > 0 && (
            <div className="sig-group">
              <div className="sig-group-head">🚫 数据不可用</div>
              <ul className="sig-list">
                {unavailable.map((u) => (
                  <li key={u.symbol} className="sig-row muted">
                    {u.symbol}：{u.error ?? "原因未知"}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {empty && active != null && active.available !== false && (
            <div className="muted sig-empty">当前窗口内无买卖信号。</div>
          )}
        </div>
      )}
    </div>
  );
}
