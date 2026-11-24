import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { smartPromptsApi, type CandidatePickItem } from "../api/smartPrompts";
import "../components/smart-prompts/smart-prompts.css";

function isGreenLight(light: string): boolean {
  return light.includes("绿") || light.includes("🟢");
}

function PickGroup({
  title,
  items,
}: {
  title: string;
  items: CandidatePickItem[];
}) {
  if (items.length === 0) return null;
  return (
    <div className="op-pick-group">
      <h3>
        {title} <small className="op-group-cnt">{items.length}</small>
      </h3>
      {items.map((item, idx) => {
        const code = item.code;
        const fullSym = code.includes(".")
          ? code
          : /^(60|68|51|56|58)/.test(code)
            ? `${code}.SS`
            : `${code}.SZ`;
        return (
          <div key={`${code}-${idx}`} className="op-pick-row">
            <div className="op-pick-head">
              <Link className="op-pick-link" to={`/?symbol=${encodeURIComponent(fullSym)}`}>
                {idx + 1}. {code} {item.name}
              </Link>
              <span className="op-holding-nums">
                收盘 {item.close} · {item.as_of}
              </span>
            </div>
            <p className="op-pick-reason">{item.plain_reason}</p>
          </div>
        );
      })}
    </div>
  );
}

export default function OnePageOverviewPage() {
  const [harborOpen, setHarborOpen] = useState(false);
  const [expandAllHoldings, setExpandAllHoldings] = useState(false);
  const [openedHoldings, setOpenedHoldings] = useState<Record<string, boolean>>({});

  const query = useQuery({
    queryKey: ["smartOnePage"],
    queryFn: () => smartPromptsApi.onePage(8, false),
    staleTime: 60_000,
    retry: 1,
  });

  const refreshForce = async () => {
    await smartPromptsApi.onePage(8, true);
    void query.refetch();
  };

  if (query.isLoading) {
    return (
      <div className="page op-page">
        <p>正在体检持仓健康灯与今日尖子生…</p>
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="page op-page" role="alert">
        <p>一页总览加载失败：{(query.error as Error | null)?.message ?? "未知错误"}</p>
        <button type="button" className="btn small" onClick={() => void query.refetch()}>
          重新加载
        </button>
      </div>
    );
  }

  const { market_weather, idle_cash_harbor, left_portfolio, right_picks } = query.data;
  const diag = left_portfolio.portfolio_diagnosis;
  const urgents = left_portfolio.urgent_actions;

  // 需要留意的（红/黄灯）置顶并默认展开，稳健绿灯默认紧凑单行，点击可展开明细
  const attentionItems = diag.items.filter((it) => !isGreenLight(it.health_light));
  const steadyItems = diag.items.filter((it) => isGreenLight(it.health_light));
  const sortedHoldings = [...attentionItems, ...steadyItems];

  const pickGroups = [
    {
      key: "right_side",
      title: "场内行业基金 · 刚抬头且不拥挤",
      short: "抬头行业基金",
      items: right_picks.right_side_sector_funds,
      emptyTip: "今日暂无同时满足【行业过半公司抬头 + 刚站上均线离底价近 + 成交不挤】的板块基金",
    },
    {
      key: "left_side",
      title: "场内基金 · 跌透刚站回均线",
      short: "跌透低吸基金",
      items: right_picks.left_side_turnaround_funds,
      emptyTip: "今日暂无跌透后刚刚重新站回近一月均价的基金",
    },
    {
      key: "leaders",
      title: "行业真龙头（大市值 + 现金流 + 刚过成本区）",
      short: "行业真龙头",
      items: right_picks.industry_leaders,
      emptyTip: "今日暂无同时过关的行业大龙头",
    },
    {
      key: "giants",
      title: "细分成长小巨人（高增长 + 现金流 + 刚过成本区）",
      short: "细分小巨人",
      items: right_picks.small_giants,
      emptyTip: "今日暂无同时过关的细分小巨人",
    },
  ];
  const totalPicks = pickGroups.reduce((sum, g) => sum + g.items.length, 0);
  const emptyGroups = pickGroups.filter((g) => g.items.length === 0);

  return (
    <div className="page op-page">
      <div className="op-weather-bar">
        <div className="op-weather-lines">
          <div>
            <strong>国内大盘：</strong>
            {market_weather.cn_plain_verdict}
          </div>
          <div>
            <strong>海外底仓：</strong>
            {market_weather.us_plain_verdict}
          </div>
        </div>
        <div className="op-weather-actions">
          <Link to="/portfolio" className="btn small">
            持仓明细
          </Link>
          <button
            type="button"
            className="btn small"
            disabled={query.isFetching}
            onClick={() => void refreshForce()}
          >
            {query.isFetching ? "重算中…" : "重新体检"}
          </button>
        </div>
      </div>

      {idle_cash_harbor && (
        <section className="op-harbor-bar op-harbor-compact" aria-label="闲钱去向指示灯">
          <div className="op-harbor-line">
            <strong>闲钱去向：</strong>
            <span className="op-harbor-headline">{idle_cash_harbor.headline_cn}</span>
            <div className="op-harbor-chips">
              {[idle_cash_harbor.gold, idle_cash_harbor.high_dividend].map((asset) => (
                <span
                  key={asset.symbol}
                  className={`op-harbor-chip${asset.is_steady ? " is-steady" : " is-off"}`}
                  title={`${asset.name}：${asset.status_cn}${asset.available && asset.close != null && asset.ma60 != null ? `（现价 ${asset.close} / 近三月均价 ${asset.ma60}）` : ""}`}
                >
                  {asset.is_steady ? "●" : "○"} {asset.name}
                </span>
              ))}
            </div>
            <button
              type="button"
              className="btn small op-harbor-toggle"
              aria-expanded={harborOpen}
              onClick={() => setHarborOpen((v) => !v)}
            >
              {harborOpen ? "收起 ▴" : "详情 ▾"}
            </button>
          </div>
          {harborOpen && (
            <div className="op-harbor-detail">
              <div className="op-harbor-sub">{idle_cash_harbor.allocation_cn}</div>
              <div className="op-harbor-grid">
                {[idle_cash_harbor.gold, idle_cash_harbor.high_dividend].map((asset) => (
                  <div
                    key={asset.symbol}
                    className={`op-harbor-pill${asset.is_steady ? " is-steady" : " is-off"}`}
                  >
                    <div className="op-harbor-pill-top">
                      {asset.symbol.includes(".") ? (
                        <Link className="op-pick-link" to={`/?symbol=${encodeURIComponent(asset.symbol)}`}>
                          {asset.code} {asset.name}
                        </Link>
                      ) : (
                        <strong>
                          {asset.code} {asset.name}
                        </strong>
                      )}
                      {asset.available && asset.close != null && asset.ma60 != null && (
                        <span className="op-holding-nums">
                          现价 {asset.close} / 近三月均价 {asset.ma60}（截至 {asset.as_of}）
                        </span>
                      )}
                    </div>
                    <div className="op-harbor-pill-status">{asset.status_cn}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {urgents.length > 0 && (
        <div className="op-urgent-strip" aria-label="今日需要留意的持仓动作提醒">
          {urgents.map((u, idx) => (
            <div
              key={`${u.name}-${idx}`}
              className={`op-urgent-item${
                u.level === "urgent" ? " is-urgent" : u.level === "opportunity" ? " is-opportunity" : ""
              }`}
            >
              <strong>{u.title}</strong> — {u.detail}
            </div>
          ))}
        </div>
      )}

      <div className="op-two-cols">
        <section className="op-col" aria-label="手头持仓健康灯">
          <div className="op-col-head">
            <h2>
              持仓健康灯
              <span className="op-col-stats">
                {attentionItems.length > 0 && (
                  <em className="is-warn">需留意 {attentionItems.length}</em>
                )}
                <em>稳健 {steadyItems.length}</em>
              </span>
            </h2>
            {steadyItems.length > 0 && (
              <button
                type="button"
                className="btn small"
                onClick={() => setExpandAllHoldings((v) => !v)}
              >
                {expandAllHoldings ? "折叠稳健项" : "展开全部"}
              </button>
            )}
          </div>

          {diag.summary_tips.length > 0 && (
            <ul className="op-tips-list">
              {diag.summary_tips.map((tip, idx) => (
                <li key={idx}>• {tip}</li>
              ))}
            </ul>
          )}

          <div className="op-holding-list">
            {sortedHoldings.map((item) => {
              const key = `${item.fund_name}-${item.codes_display}`;
              const steady = isGreenLight(item.health_light);
              const isOpen = !steady || expandAllHoldings || Boolean(openedHoldings[key]);
              const d200 =
                item.dist_ma200_pct != null
                  ? `${item.dist_ma200_pct >= 0 ? "+" : ""}${item.dist_ma200_pct.toFixed(0)}%`
                  : "—";
              const dd1y =
                item.drawdown_from_1y_high_pct != null
                  ? `${item.drawdown_from_1y_high_pct.toFixed(0)}%`
                  : "—";
              return (
                <article
                  key={key}
                  className={`op-holding-card${steady && !isOpen ? " is-compact" : ""}${!steady ? " is-attention" : ""}`}
                >
                  <div
                    className={`op-holding-top${steady ? " is-clickable" : ""}`}
                    onClick={
                      steady
                        ? () => setOpenedHoldings((prev) => ({ ...prev, [key]: !prev[key] }))
                        : undefined
                    }
                    title={steady ? "点击展开或收起详细建议与底色核查" : undefined}
                  >
                    <span className="op-holding-name">
                      {item.health_light} · {item.fund_name}
                    </span>
                    <span className="op-holding-nums">
                      ¥{item.market_value.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}（{item.weight_in_account_pct.toFixed(1)}%）·{" "}
                      <b style={{ color: item.account_return_pct >= 0 ? "#dc2626" : "#16a34a" }}>
                        {item.account_return_pct >= 0 ? "+" : ""}
                        {item.account_return_pct.toFixed(1)}%
                      </b>{" "}
                      · 年线 {d200} · 高点 {dd1y}
                      {steady && <span className="op-expand-caret">{isOpen ? " ▴" : " ▾"}</span>}
                    </span>
                  </div>
                  {isOpen && (
                    <div className="op-holding-body">
                      <p className="op-holding-advice">
                        <strong>怎么处理：</strong>
                        {item.action_advice_cn}
                      </p>
                      <p className="op-holding-truth">底色核查：{item.penetration_truth_cn}</p>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </section>

        <section className="op-col" aria-label="今日尖子生候选">
          <div className="op-col-head">
            <h2>
              今日尖子生
              <span className="op-col-stats">
                <em>命中 {totalPicks}</em>
              </span>
            </h2>
            <span className="op-col-hint">点名称直接看 K 线</span>
          </div>

          {right_picks.crowded_warnings.length > 0 && (
            <div className="op-urgent-strip">
              {right_picks.crowded_warnings.map((w) => (
                <div key={w.code} className="op-urgent-item is-urgent">
                  <strong>⚠️ 过热别追：{w.code} {w.name}</strong> — {w.note}
                </div>
              ))}
            </div>
          )}

          {totalPicks === 0 ? (
            <div className="op-all-empty">
              今日四类赛道均无同时满足严苛条件的候选，保持耐心等待。
            </div>
          ) : (
            pickGroups.map((g) => <PickGroup key={g.key} title={g.title} items={g.items} />)
          )}

          {emptyGroups.length > 0 && totalPicks > 0 && (
            <div className="op-empty-groups">
              <span>今日暂无命中：</span>
              {emptyGroups.map((g) => (
                <span key={g.key} className="op-empty-tag" title={g.emptyTip}>
                  {g.short} (0)
                </span>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
