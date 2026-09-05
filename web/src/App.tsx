import { useSyncExternalStore } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import TopNav from "./components/TopNav";
import AgentConsole from "./components/AgentConsole";
import DetailPage from "./pages/DetailPage";
import FactorPanelPage from "./pages/FactorPanelPage";
import FundamentalsPage from "./pages/FundamentalsPage";
import NewsPage from "./pages/NewsPage";
import SectorsPage from "./pages/SectorsPage";
import DailyBriefPage from "./pages/DailyBriefPage";
import AgentWorkspacePage from "./pages/AgentWorkspacePage";
import SentimentPage from "./pages/SentimentPage";
import OpsPage from "./pages/OpsPage";
import SupervisorPage from "./pages/SupervisorPage";
import PortfolioPage from "./pages/PortfolioPage";
import WorkspacePage from "./pages/WorkspacePage";
import BacktestPage from "./pages/BacktestPage";
import ResearchPage from "./pages/ResearchPage";
import ReportsLibraryPage from "./pages/ReportsLibraryPage";

// ---- AgentConsole 全局开合（模块级单例 store，避免引入状态库）----
// 上下文标的由 AgentConsole 从 useLocation 自行解析（matchPath "/symbol/:symbol"），
// 这里的 symbol 只作为 openConsole 的参数留存，不污染 DetailPage。
type ConsoleState = { open: boolean; symbol: string | null };
const listeners = new Set<() => void>();
const closeConsole = () => {
  consoleState = { open: false, symbol: consoleState.symbol };
  snapshot = { ...consoleState, closeConsole };
  listeners.forEach((l) => l());
};
let consoleState: ConsoleState = { open: false, symbol: null };
// useSyncExternalStore 的 getSnapshot 必须返回稳定引用（每次新建字面量会无限重渲染），
// 因此快照缓存在模块级，仅在状态变更时重建。
let snapshot: ConsoleState & { closeConsole: () => void } = { ...consoleState, closeConsole };
export const agentConsoleStore = {
  openConsole(symbol: string | null) {
    consoleState = { open: true, symbol };
    snapshot = { ...consoleState, closeConsole };
    listeners.forEach((l) => l());
  },
  closeConsole,
};
export function useAgentConsole() {
  // subscribe 的清理函数须返回 void（React 类型要求），listeners.delete 的 boolean 不能直接透传。
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => { listeners.delete(cb); };
    },
    () => snapshot,
  );
}

export default function App() {
  return (
    <>
      <TopNav />
      <Routes>
        {/* 三栏看盘工作台：默认入口 */}
        <Route path="/" element={<WorkspacePage />} />
        {/* 单标的详情页：保留独立链接入口 */}
        <Route path="/symbol/:symbol" element={<DetailPage />} />
        {/* 基本面参考：宏观 + 行业板块全景（参考层，不进技术信号） */}
        <Route path="/fundamentals" element={<FundamentalsPage />} />
        {/* 行业板块趋势工作台：等权指数 / RS / 宽度 / 阶段（research_proxy） */}
        <Route path="/sectors" element={<SectorsPage />} />
        {/* 因子观测台：常见因子读数/分位/排名 + 实证评级留痕（research_proxy，不挡信号） */}
        <Route path="/factors" element={<FactorPanelPage />} />
        {/* 资讯流：基本面消息检索与排序（宏观/风险/政策/行业 + 博主观点，参考层） */}
        <Route path="/news" element={<NewsPage />} />
        {/* 回测工作台：全池回测 + 宽度择时 */}
        <Route path="/backtest" element={<BacktestPage />} />
        {/* 本轮研究展示：宽度/模块E/终审 轮次结果（静态数据页） */}
        <Route path="/research" element={<ResearchPage />} />
        {/* 实验报告库：全量实验/调研文档统一浏览（登记簿分类 + 一句话结论） */}
        <Route path="/library" element={<ReportsLibraryPage />} />
        {/* 收盘简报：环境异常 → 自选重点变化 → 板块观察池（research_proxy） */}
        <Route path="/daily" element={<DailyBriefPage />} />
        {/* 监督待办：跨标的计划 + 待办 + 当日判定 */}
        <Route path="/plans" element={<SupervisorPage />} />
        <Route path="/ops" element={<OpsPage />} />
        <Route path="/agent" element={<AgentWorkspacePage />} />
        <Route path="/sentiment" element={<SentimentPage />} />
        {/* 我的持仓：基金/ETF 快照 + 赛道分组 + 系统结论（叙事标注层） */}
        <Route path="/portfolio" element={<PortfolioPage />} />
        {/* 未知路径兜底：回看盘工作台，避免白屏 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {/* 全局 agent 控制台：任何页面可唤起，上下文跟随当前路由 */}
      <AgentConsole />
    </>
  );
}
