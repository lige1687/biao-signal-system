// 临时演示配置（不提交）：后端走 8200 的演示实例（LEI_SQLITE_PATH=/tmp/newsfeed_e2e.db），
// 避免动生产 8000/5173。看完删掉本文件即可。
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  root: __dirname,
  server: {
    host: true,
    port: 5174,
    proxy: {
      "/api": "http://127.0.0.1:8200",
    },
  },
});
