import { Route, Routes } from "react-router-dom";
import TopNav from "./components/TopNav";
import DashboardPage from "./pages/DashboardPage";
import DetailPage from "./pages/DetailPage";
import FundamentalsPage from "./pages/FundamentalsPage";
import SupervisorPage from "./pages/SupervisorPage";
import WorkspacePage from "./pages/WorkspacePage";

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
        {/* 监督待办：跨标的计划 + 待办 + 当日判定 */}
        <Route path="/plans" element={<SupervisorPage />} />
      </Routes>
    </>
  );
}
