import { Route, Routes } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import DetailPage from "./pages/DetailPage";
import WorkspacePage from "./pages/WorkspacePage";

export default function App() {
  return (
    <Routes>
      {/* 三栏看盘工作台：默认入口 */}
      <Route path="/" element={<WorkspacePage />} />
      {/* 卡片墙总览：一屏扫全部标的时更直观 */}
      <Route path="/grid" element={<DashboardPage />} />
      {/* 单标的详情页：保留独立链接入口 */}
      <Route path="/symbol/:symbol" element={<DetailPage />} />
    </Routes>
  );
}
