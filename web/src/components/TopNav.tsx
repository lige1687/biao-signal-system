import { useQuery } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";
import { api } from "../api/client";
import { agentConsoleStore } from "../App";

/**
 * 全局顶栏：按交易动线分四组（盯盘 / 持仓·执行 / 信息 / 研究），
 * 竖线分隔不加组名——13 个入口全部保持可见，靠分组提高可扫读性。
 * 「工作台 + AI 助手」是 AI 区，归到右侧与信息导航分开。
 * 监督待办带红点（全库 open 待办数）；看盘入口带红点（买卖信号合计）。
 * 计数轮询 60s：待办由日终监督周期产生，不需要更快。
 */
type NavItem = { to: string; label: string; end?: boolean; badge?: number };
type NavGroup = NavItem[];

export default function TopNav() {
  const { data } = useQuery({
    queryKey: ["plansSummary"],
    queryFn: () => api.plansSummary(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const open = data?.open_actions ?? 0;
  const todayOpps = data?.today_signal_total ?? data?.today_opportunities ?? 0;

  const groups: NavGroup[] = [
    [
      { to: "/", label: "看盘", end: true, badge: todayOpps || undefined },
      { to: "/sectors", label: "行业板块" },
    ],
    [
      { to: "/ops", label: "今日操作" },
      { to: "/portfolio", label: "我的持仓" },
      { to: "/plans", label: "监督待办", badge: open || undefined },
    ],
    [
      { to: "/fundamentals", label: "基本面" },
      { to: "/factors", label: "因子观测台" },
      { to: "/news", label: "资讯流" },
      { to: "/daily", label: "收盘简报" },
    ],
    [
      { to: "/backtest", label: "回测" },
      { to: "/research", label: "本轮研究" },
      { to: "/library", label: "实验报告库" },
    ],
  ];

  const link = (item: NavItem) => (
    <NavLink key={item.to} to={item.to} end={item.end}>
      {item.label}
      {item.badge != null && item.badge > 0 && <span className="nav-badge">{item.badge}</span>}
    </NavLink>
  );

  return (
    <nav className="top-nav">
      <span className="brand">LEI</span>
      {groups.map((g, i) => (
        <span className="nav-group" key={i}>
          {i > 0 && <span className="nav-sep" />}
          {g.map(link)}
        </span>
      ))}
      <span className="nav-spacer" />
      <span className="nav-ai">
        <NavLink to="/agent">工作台</NavLink>
        <button
          className="btn small nav-agent"
          onClick={() => agentConsoleStore.openConsole(null)}
          title="AI 助手：问行情、查信号、复盘对话"
        >
          AI 助手
        </button>
      </span>
    </nav>
  );
}
