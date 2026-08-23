import { useQuery } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";
import { api } from "../api/client";
import { agentConsoleStore } from "../App";

/**
 * 极简全局顶栏。监督待办带红点（全库 open 待办数）；
 * 看盘入口带红点（买卖信号合计 = 买点机会 + 卖点硬/预警）。
 * 计数轮询 60s：待办由日终监督周期产生，不需要更快。
 */
export default function TopNav() {
  const { data } = useQuery({
    queryKey: ["plansSummary"],
    queryFn: () => api.plansSummary(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const open = data?.open_actions ?? 0;
  const todayOpps = data?.today_signal_total ?? data?.today_opportunities ?? 0;

  return (
    <nav className="top-nav">
      <span className="brand">LEI</span>
      <NavLink to="/" end>
        看盘
        {todayOpps > 0 && <span className="nav-badge">{todayOpps}</span>}
      </NavLink>
      <NavLink to="/grid">卡片墙</NavLink>
      <NavLink to="/fundamentals">基本面</NavLink>
      <NavLink to="/sectors">行业板块</NavLink>
      <NavLink to="/daily">日报</NavLink>
      <NavLink to="/plans">
        监督待办
        {open > 0 && <span className="nav-badge">{open}</span>}
      </NavLink>
      <span className="nav-spacer" />
      <button className="btn small nav-agent" onClick={() => agentConsoleStore.openConsole(null)}>
        agent
      </button>
    </nav>
  );
}
