import { sentimentApi } from "../api/client";
import { useQuery } from "@tanstack/react-query";
import { NavLink, useLocation } from "react-router-dom";
import { useEffect, useRef } from "react";
import { api } from "../api/client";
import { agentConsoleStore } from "../App";

/**
 * 全局顶栏：看盘与执行入口常驻，资料与研究入口分组展开。
 * 「工作台 + AI 助手」是 AI 区，归到右侧与信息导航分开。
 * 监督待办带红点（全库 open 待办数）；看盘入口带红点（买卖信号合计）。
 * 计数轮询 60s：待办由日终监督周期产生，不需要更快。
 */
type NavItem = { to: string; label: string; end?: boolean; badge?: number; dot?: string };
type NavGroup = NavItem[];

export default function TopNav() {
  const location = useLocation();
  const navRef = useRef<HTMLElement>(null);
  useEffect(() => {
    navRef.current?.querySelectorAll("details[open]").forEach((el) => el.removeAttribute("open"));
  }, [location.pathname]);
  useEffect(() => {
    const dismiss = (event: PointerEvent) => {
      navRef.current?.querySelectorAll("details[open]").forEach((el) => {
        if (!el.contains(event.target as Node)) el.removeAttribute("open");
      });
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);
  const { data: moodLight } = useQuery({
    queryKey: ["sentimentLight"],
    queryFn: () => sentimentApi.light(),
    refetchInterval: 5 * 60_000,
    staleTime: 5 * 60_000,
  });
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
      { to: "/sentiment", label: "情绪", dot: moodLight?.available && moodLight.light !== "gray"
        ? (moodLight.light === "blue" ? "#4d7fc4" : "#d24a43")
        : undefined },
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
      { to: "/mindset", label: "认知心态" },
    ],
    [
      { to: "/backtest", label: "回测" },
      { to: "/fwd", label: "前向成绩" },
      { to: "/research", label: "本轮研究" },
      { to: "/library", label: "实验报告库" },
      { to: "/learning", label: "文献学习库" },
      { to: "/upgrades", label: "系统待升级" },
    ],
  ];

  const link = (item: NavItem) => (
    <NavLink key={item.to} to={item.to} end={item.end}
      onClick={(event) => event.currentTarget.closest("details")?.removeAttribute("open")}>
      {item.label}
      {(item as { dot?: string }).dot && (
        <span className="nav-mood-dot" style={{ background: (item as { dot?: string }).dot }}
              title={item.dot === "#4d7fc4" ? "冰点机会窗口开启" : "情绪警报触发"} />
      )}
      {item.badge != null && item.badge > 0 && <span className="nav-badge">{item.badge}</span>}
    </NavLink>
  );

  return (
    <nav className="top-nav" aria-label="主导航" ref={navRef}>
      <NavLink to="/" className="brand" aria-label="BIAO 看盘首页">BIAO<span>趋势研究</span></NavLink>
      {groups.slice(0, 2).map((g, i) => (
        <span className="nav-group" key={i}>
          {i > 0 && <span className="nav-sep" />}
          {g.map(link)}
        </span>
      ))}
      {groups.slice(2).map((g, i) => (
        <details className={`nav-more${g.some((item) => item.to === location.pathname) ? " is-current" : ""}`}
          key={i} onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.currentTarget.removeAttribute("open");
              event.currentTarget.querySelector("summary")?.focus();
            }
          }}>
          <summary>{i === 0 ? "资讯与认知" : "策略研究"}<span aria-hidden="true">⌄</span></summary>
          <div className="nav-more-links">{g.map(link)}</div>
        </details>
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
