import { useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { agentConsoleStore } from "../App";
import "./navigation-context.css";

type NavItem = { to: string; label: string };
type ArchiveGroup = { heading: string; items: NavItem[] };

const PRIMARY_LINKS: { to: string; label: string; match: (path: string) => boolean }[] = [
  { to: "/onepage", label: "一页看全", match: (p) => p === "/onepage" },
  { to: "/", label: "看盘", match: (p) => p === "/" || p.startsWith("/symbol/") },
  { to: "/portfolio", label: "持仓", match: (p) => p === "/portfolio" },
  {
    to: "/fundamentals",
    label: "宏观与情绪",
    match: (p) => p === "/fundamentals" || p === "/sentiment" || p === "/news",
  },
];

const ARCHIVE_GROUPS: ArchiveGroup[] = [
  {
    heading: "日常备用",
    items: [
      { to: "/ops", label: "今日重点清单" },
      { to: "/daily", label: "收盘简报" },
      { to: "/plans", label: "计划待办" },
    ],
  },
  {
    heading: "研究归档",
    items: [
      { to: "/strategy", label: "技术体系" },
      { to: "/fwd", label: "策略跟踪与复盘" },
      { to: "/library", label: "实验报告库" },
      { to: "/factors", label: "因子观测台" },
      { to: "/backtest", label: "历史回测" },
      { to: "/learning", label: "文献学习" },
      { to: "/mindset", label: "认知心态" },
      { to: "/upgrades", label: "系统待升级" },
      { to: "/research", label: "历史研究" },
      { to: "/agent", label: "AI 全屏工作台" },
    ],
  },
];

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

  const inArchive = ARCHIVE_GROUPS.some((g) => g.items.some((it) => it.to === location.pathname));

  return (
    <nav className="top-nav" aria-label="主导航" ref={navRef}>
      <NavLink to="/" className="brand" aria-label="BIAO 看盘首页">
        BIAO<span>趋势研究</span>
      </NavLink>
      {PRIMARY_LINKS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          className={item.match(location.pathname) ? "active" : ""}
        >
          {item.label}
        </NavLink>
      ))}
      <span className="nav-spacer" />
      <details
        className={`nav-more nav-archive${inArchive ? " is-current" : ""}`}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.currentTarget.removeAttribute("open");
            event.currentTarget.querySelector("summary")?.focus();
          }
        }}
      >
        <summary aria-label="展开备用与研究归档页面" title="备用工具与研究归档（平时不看，需要时直达）">
          <span>更多</span>
          <span aria-hidden="true">⌄</span>
        </summary>
        <div className="nav-more-links nav-archive-menu">
          {ARCHIVE_GROUPS.map((group) => (
            <div className="nav-archive-group" key={group.heading}>
              <div className="nav-archive-heading">{group.heading}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end
                  onClick={(event) => event.currentTarget.closest("details")?.removeAttribute("open")}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
      </details>
      <button
        className="btn small nav-agent"
        onClick={() => agentConsoleStore.openConsole(null)}
        title="打开 AI 助手；当前页面对象会显示在面板顶部"
      >
        问 AI
      </button>
    </nav>
  );
}
