import { useQuery } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";
import { api } from "../api/client";

/**
 * 极简全局顶栏。监督待办带红点（全库 open 待办数）。
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

  return (
    <nav className="top-nav">
      <span className="brand">LEI</span>
      <NavLink to="/" end>
        看盘
      </NavLink>
      <NavLink to="/grid">卡片墙</NavLink>
      <NavLink to="/plans">
        监督待办
        {open > 0 && <span className="nav-badge">{open}</span>}
      </NavLink>
      <span className="nav-spacer" />
    </nav>
  );
}
