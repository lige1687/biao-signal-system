/** 今日机会雷达面板 -- dashboard 上的"哪些自选今天有机会/潜在有机会".
 *
 *  数据源: GET /api/opportunities/today (读 daily_opportunity_scan 表, launchd 15:00 写).
 *  - actionable (条件已成立): 绿, 最该关注
 *  - waiting (等待条件成立): 灰, 潜在机会, 缺的条件文案展示
 *  - blocked (环境阻断): 黄, 近期有信号但环境不允许开新仓, 展示阻断原因
 *
 *  [刷新] 调 POST /api/opportunities/today/refresh 立即重扫并落库.
 *  当日未扫描 (scanned=0) 时显示空态 + 刷新按钮.
 *
 *  红点计数 (actionable + waiting) 在 TopNav 的 plansSummary.today_opportunities,
 *  本面板只做展开详情。
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ScanItem } from "../types";

const VERDICT_COLOR: Record<string, string> = {
  actionable: "var(--lei-green)",
  blocked: "var(--warn)",
  waiting: "var(--text-faint)",
  none: "var(--text-faint)",
};

const VERDICT_LABEL: Record<string, string> = {
  actionable: "条件已成立",
  waiting: "等待条件成立",
  blocked: "环境阻断",
};

function ScanItemRow({ it }: { it: ScanItem }) {
  return (
    <li className="opp-row">
      <div className="opp-row-head">
        <Link to={`/symbol/${encodeURIComponent(it.symbol)}`} className="opp-symbol">
          {it.display_name || it.symbol}
        </Link>
        <span
          className="opp-verdict"
          style={{ background: VERDICT_COLOR[it.verdict] || "var(--text-faint)" }}
        >
          {VERDICT_LABEL[it.verdict] ?? it.verdict_cn}
        </span>
        {it.reward_risk_computable && it.reward_risk_ratio != null && (
          <span className="opp-rr">R/R {it.reward_risk_ratio.toFixed(1)}</span>
        )}
        {it.has_active_plan && <span className="opp-plan-tag">已有计划</span>}
      </div>
      {it.best_scenario_cn && (
        <div className="opp-scenario">{it.best_scenario_cn}</div>
      )}
      {it.verdict === "blocked" && it.blocking_reasons.length > 0 && (
        <div className="opp-blocked">
          阻断：{it.blocking_reasons.join("、")}
        </div>
      )}
      {it.verdict === "waiting" && it.missing_summary_cn && (
        <div className="opp-missing">缺：{it.missing_summary_cn}</div>
      )}
    </li>
  );
}

function Group({
  title,
  items,
  tone,
}: {
  title: string;
  items: ScanItem[];
  tone: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="opp-group">
      <div className="opp-group-head" style={{ color: tone }}>
        {title} <span className="opp-group-count">{items.length}</span>
      </div>
      <ul className="opp-list">
        {items.map((it) => (
          <ScanItemRow key={it.symbol} it={it} />
        ))}
      </ul>
    </div>
  );
}

export default function TodayOpportunityPanel() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["todayOpportunities"],
    queryFn: () => api.todayOpportunities(),
    staleTime: 60_000,
  });

  const refresh = useMutation({
    mutationFn: () => api.refreshTodayOpportunities(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["todayOpportunities"] });
      qc.invalidateQueries({ queryKey: ["plansSummary"] });
    },
  });

  const scanned = data?.scanned ?? 0;
  const actionable = data?.actionable ?? [];
  const waiting = data?.waiting ?? [];
  const blocked = data?.blocked ?? [];
  const oppCount = actionable.length + waiting.length;

  return (
    <div className="opp-panel">
      <div className="opp-panel-head">
        <b>📡 今日机会雷达</b>
        <span className="muted">
          {isLoading
            ? "加载中..."
            : scanned > 0
              ? `${oppCount} 个机会 · ${actionable.length} 可操作 / ${waiting.length} 待确认 / ${blocked.length} 阻断`
              : "今日尚未扫描"}
        </span>
        <span className="opp-spacer" />
        <button
          className="btn small"
          disabled={refresh.isPending}
          onClick={() => refresh.mutate()}
        >
          {refresh.isPending ? "扫描中…" : "刷新扫描"}
        </button>
      </div>
      {scanned === 0 && !isLoading ? (
        <div className="muted opp-empty">
          今日尚未扫描自选机会. 点 [刷新扫描] 立即生成, 或等 15:00 自动扫描.
        </div>
      ) : (
        <div className="opp-groups">
          <Group title="✅ 条件已成立" items={actionable} tone="var(--lei-green)" />
          <Group title="⏳ 等待条件成立" items={waiting} tone="var(--text-faint)" />
          <Group title="🚫 环境阻断" items={blocked} tone="var(--warn)" />
        </div>
      )}
    </div>
  );
}
