import { useSyncExternalStore } from "react";
import { Route, Routes } from "react-router-dom";
import TopNav from "./components/TopNav";
import DashboardPage from "./pages/DashboardPage";
import DetailPage from "./pages/DetailPage";
import FundamentalsPage from "./pages/FundamentalsPage";
import SectorsPage from "./pages/SectorsPage";
import SupervisorPage from "./pages/SupervisorPage";
import WorkspacePage from "./pages/WorkspacePage";
import AgentConsole from "./components/AgentConsole";

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
        {/* 卡片墙总览：一屏扫全部标的时更直观 */}
        <Route path="/grid" element={<DashboardPage />} />
        {/* 单标的详情页：保留独立链接入口 */}
        <Route path="/symbol/:symbol" element={<DetailPage />} />
        {/* 基本面参考：宏观 + 行业板块全景（参考层，不进技术信号） */}
        <Route path="/fundamentals" element={<FundamentalsPage />} />
        {/* 行业板块趋势工作台：等权指数 / RS / 宽度 / 阶段（research_proxy） */}
        <Route path="/sectors" element={<SectorsPage />} />
        {/* 监督待办：跨标的计划 + 待办 + 当日判定 */}
        <Route path="/plans" element={<SupervisorPage />} />
      </Routes>
      {/* 全局 agent 控制台：任何页面可唤起，上下文跟随当前路由 */}
      <AgentConsole />
    </>
  );
}
